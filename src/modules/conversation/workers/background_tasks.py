"""
Background tasks worker - Enhanced version.
Runs periodic maintenance tasks like conversation timeout and expiration.

Features:
- Graceful shutdown handling
- Metrics tracking
- Health monitoring
- Configurable intervals per task
- Error recovery
- Batch processing for better performance
"""
import time
import signal
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass

from src.modules.conversation.services.conversation_service import ConversationService
from src.core.utils import get_logger
from src.core.config import settings

logger = get_logger(__name__)


@dataclass
class TaskMetrics:
    """Metrics for a background task."""
    name: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_items_processed: int = 0
    last_run_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None
    total_execution_time_seconds: float = 0.0
    
    def record_success(self, items_processed: int, execution_time: float):
        """Record successful task execution."""
        self.total_runs += 1
        self.successful_runs += 1
        self.total_items_processed += items_processed
        self.last_run_at = datetime.now(timezone.utc)
        self.last_success_at = datetime.now(timezone.utc)
        self.total_execution_time_seconds += execution_time
        
    def record_failure(self, error: str, execution_time: float):
        """Record failed task execution."""
        self.total_runs += 1
        self.failed_runs += 1
        self.last_run_at = datetime.now(timezone.utc)
        self.last_error = error
        self.total_execution_time_seconds += execution_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        avg_time = (
            self.total_execution_time_seconds / self.total_runs 
            if self.total_runs > 0 else 0
        )
        success_rate = (
            (self.successful_runs / self.total_runs * 100) 
            if self.total_runs > 0 else 0
        )
        
        return {
            "name": self.name,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate_percent": round(success_rate, 2),
            "total_items_processed": self.total_items_processed,
            "average_execution_time_seconds": round(avg_time, 3),
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_error": self.last_error
        }


class BackgroundWorker:
    """
    Background worker for periodic maintenance tasks.
    
    Responsibilities:
    - Process idle conversations (IDLE_TIMEOUT)
    - Process expired conversations (EXPIRED)
    - Monitor and report metrics
    - Handle graceful shutdown
    """
    
    def __init__(
        self, 
        interval_seconds: int = 60,
        batch_size: int = 100,
        enable_metrics: bool = True
    ):
        """
        Initialize background worker.
        
        Args:
            interval_seconds: Seconds between task runs
            batch_size: Maximum items to process per task
            enable_metrics: Whether to track metrics
        """
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self.enable_metrics = enable_metrics
        self.running = False
        
        # Initialize services
        self.conversation_service = ConversationService()
        
        # Metrics
        self.metrics: Dict[str, TaskMetrics] = {
            "idle_conversations": TaskMetrics("idle_conversations"),
            "expired_conversations": TaskMetrics("expired_conversations"),
        }
        
        # Task configuration - can be customized per task
        self.task_config = {
            "idle_conversations": {
                "enabled": True,
                "interval_multiplier": 1,  # Run every cycle
            },
            "expired_conversations": {
                "enabled": True,
                "interval_multiplier": 1,  # Run every cycle
            }
        }
        
        self.cycle_count = 0
        self.started_at: Optional[datetime] = None
        
    def run(self):
        """Run the worker loop."""
        self.running = True
        self.started_at = datetime.now(timezone.utc)
        
        logger.info(
            "Starting background worker",
            interval=self.interval_seconds,
            batch_size=self.batch_size,
            tasks=list(self.task_config.keys())
        )
        
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        try:
            self._main_loop()
        except Exception as e:
            logger.error("Fatal error in main loop", error=str(e), exc_info=True)
        finally:
            self._shutdown()
        
    def _main_loop(self):
        """Main worker loop."""
        while self.running:
            try:
                cycle_start_time = time.time()
                self.cycle_count += 1
                
                logger.debug(
                    "Starting task cycle",
                    cycle=self.cycle_count,
                    uptime_seconds=int((datetime.now(timezone.utc) - self.started_at).total_seconds())
                )
                
                # Run tasks
                self._run_tasks()
                
                # Log metrics periodically (every 10 cycles)
                if self.enable_metrics and self.cycle_count % 10 == 0:
                    self._log_metrics()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - cycle_start_time
                sleep_time = max(0, self.interval_seconds - elapsed)
                
                if elapsed > self.interval_seconds:
                    logger.warning(
                        "Task cycle took longer than interval",
                        elapsed_seconds=round(elapsed, 2),
                        interval_seconds=self.interval_seconds
                    )
                
                # Sleep with periodic wake-ups to check shutdown flag
                if self.running and sleep_time > 0:
                    self._interruptible_sleep(sleep_time)
                    
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error("Error in worker cycle", error=str(e), exc_info=True)
                # Sleep a bit on error to avoid tight loops
                time.sleep(10)
    
    def _run_tasks(self):
        """Execute all enabled maintenance tasks."""
        # Task 1: Process idle conversations
        if self._should_run_task("idle_conversations"):
            self._run_idle_conversations_task()
        
        # Task 2: Process expired conversations
        if self._should_run_task("expired_conversations"):
            self._run_expired_conversations_task()
    
    def _should_run_task(self, task_name: str) -> bool:
        """Check if task should run in this cycle."""
        config = self.task_config.get(task_name, {})
        
        if not config.get("enabled", True):
            return False
        
        multiplier = config.get("interval_multiplier", 1)
        return self.cycle_count % multiplier == 0
    
    def _run_idle_conversations_task(self):
        """Process idle conversations (transition to IDLE_TIMEOUT)."""
        task_name = "idle_conversations"
        start_time = time.time()
        
        try:
            logger.debug("Processing idle conversations")
            
            # Get idle timeout from settings
            idle_minutes = settings.conversation.idle_timeout_minutes
            
            # Process idle conversations
            count = self.conversation_service.process_idle_conversations(
                idle_minutes=idle_minutes,
                limit=self.batch_size
            )
            
            execution_time = time.time() - start_time
            
            if count > 0:
                logger.info(
                    "Processed idle conversations",
                    count=count,
                    idle_minutes=idle_minutes,
                    execution_time_seconds=round(execution_time, 3)
                )
            
            # Record metrics
            if self.enable_metrics:
                self.metrics[task_name].record_success(count, execution_time)
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Error processing idle conversations",
                error=str(e),
                execution_time_seconds=round(execution_time, 3),
                exc_info=True
            )
            
            if self.enable_metrics:
                self.metrics[task_name].record_failure(str(e), execution_time)
    
    def _run_expired_conversations_task(self):
        """Process expired conversations (transition to EXPIRED)."""
        task_name = "expired_conversations"
        start_time = time.time()
        
        try:
            logger.debug("Processing expired conversations")
            
            # Process expired conversations
            count = self.conversation_service.process_expired_conversations(
                limit=self.batch_size
            )
            
            execution_time = time.time() - start_time
            
            if count > 0:
                logger.info(
                    "Processed expired conversations",
                    count=count,
                    execution_time_seconds=round(execution_time, 3)
                )
            
            # Record metrics
            if self.enable_metrics:
                self.metrics[task_name].record_success(count, execution_time)
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Error processing expired conversations",
                error=str(e),
                execution_time_seconds=round(execution_time, 3),
                exc_info=True
            )
            
            if self.enable_metrics:
                self.metrics[task_name].record_failure(str(e), execution_time)
    
    def _interruptible_sleep(self, seconds: float):
        """Sleep that can be interrupted by shutdown signal."""
        # Sleep in small increments to check shutdown flag
        sleep_increment = 1.0  # Check every second
        remaining = seconds
        
        while remaining > 0 and self.running:
            sleep_time = min(sleep_increment, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time
    
    def _log_metrics(self):
        """Log metrics for all tasks."""
        uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        
        logger.info(
            "Background worker metrics",
            cycle_count=self.cycle_count,
            uptime_seconds=int(uptime),
            uptime_hours=round(uptime / 3600, 2)
        )
        
        for task_name, metrics in self.metrics.items():
            stats = metrics.get_stats()
            logger.info(
                f"Task metrics: {task_name}",
                **stats
            )
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the worker.
        
        Returns:
            Health status dictionary
        """
        if not self.started_at:
            return {
                "status": "not_started",
                "running": False
            }
        
        uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        
        # Check if any task has recent failures
        has_recent_failures = any(
            m.failed_runs > 0 and 
            m.last_run_at and 
            (datetime.now(timezone.utc) - m.last_run_at).total_seconds() < 600  # Last 10 min
            for m in self.metrics.values()
        )
        
        status = "healthy"
        if has_recent_failures:
            status = "degraded"
        if not self.running:
            status = "stopped"
        
        return {
            "status": status,
            "running": self.running,
            "started_at": self.started_at.isoformat(),
            "uptime_seconds": int(uptime),
            "cycle_count": self.cycle_count,
            "tasks": {
                name: metrics.get_stats()
                for name, metrics in self.metrics.items()
            }
        }
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(
            "Shutdown signal received",
            signal=signal_name,
            cycle_count=self.cycle_count
        )
        self.running = False
    
    def _shutdown(self):
        """Perform cleanup on shutdown."""
        logger.info("Background worker shutting down")
        
        # Log final metrics
        if self.enable_metrics and self.started_at:
            logger.info("Final metrics before shutdown:")
            self._log_metrics()
        
        logger.info(
            "Background worker stopped",
            total_cycles=self.cycle_count,
            total_uptime_seconds=int(
                (datetime.now(timezone.utc) - self.started_at).total_seconds()
            ) if self.started_at else 0
        )


def main():
    """Main entry point for background worker."""
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Background tasks worker")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Seconds between task runs (default: 60)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Maximum items to process per task (default: 100)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run tasks once and exit"
    )
    parser.add_argument(
        "--no-metrics",
        action="store_true",
        help="Disable metrics tracking"
    )
    
    args = parser.parse_args()
    
    # Create worker
    worker = BackgroundWorker(
        interval_seconds=args.interval,
        batch_size=args.batch_size,
        enable_metrics=not args.no_metrics
    )
    
    if args.once:
        # Run once mode
        logger.info("Running tasks once and exiting")
        worker.started_at = datetime.now(timezone.utc)
        worker.cycle_count = 1
        worker._run_tasks()
        worker._log_metrics()
        logger.info("Tasks completed")
    else:
        # Continuous mode
        worker.run()


if __name__ == "__main__":
    main()
    