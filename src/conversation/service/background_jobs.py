"""
Background Jobs - Serviços que rodam em background
"""
import asyncio
from datetime import datetime
from typing import Callable
from .conversation_service import ConversationService
from ..config.settings import settings


class BackgroundJobScheduler:
    """
    Agendador de jobs em background para manutenção de conversas.
    """
    
    def __init__(self):
        self.conversation_service = ConversationService()
        self._running = False
        self._tasks = []
    
    async def start(self):
        """Inicia todos os jobs em background"""
        if self._running:
            print("Jobs já estão rodando")
            return
        
        self._running = True
        print("Iniciando background jobs...")
        
        # Iniciar jobs
        self._tasks = [
            asyncio.create_task(self._run_expiry_check_job()),
            asyncio.create_task(self._run_idle_timeout_job()),
        ]
        
        print(f"{len(self._tasks)} jobs iniciados")
    
    async def stop(self):
        """Para todos os jobs em background"""
        if not self._running:
            return
        
        self._running = False
        print("Parando background jobs...")
        
        # Cancelar todas as tasks
        for task in self._tasks:
            task.cancel()
        
        # Aguardar cancelamento
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        
        print("Background jobs parados")
    
    async def _run_periodic_job(self, job_name: str, interval_seconds: int,
                                job_func: Callable):
        """
        Executa um job periodicamente.
        
        Args:
            job_name: Nome do job para logs
            interval_seconds: Intervalo entre execuções
            job_func: Função a ser executada
        """
        print(f"Job '{job_name}' iniciado (intervalo: {interval_seconds}s)")
        
        while self._running:
            try:
                print(f"[{datetime.utcnow().isoformat()}] Executando job '{job_name}'...")
                result = await job_func()
                print(f"Job '{job_name}' concluído. Resultado: {result}")
            except Exception as e:
                print(f"Erro no job '{job_name}': {e}")
            
            # Aguardar próxima execução
            await asyncio.sleep(interval_seconds)
    
    async def _run_expiry_check_job(self):
        """Job para verificar e processar conversas expiradas"""
        async def check_expired():
            processed = await self.conversation_service.process_expired_conversations()
            return f"{len(processed)} conversas expiradas processadas"
        
        interval = settings.expiry_check_interval_minutes * 60
        await self._run_periodic_job(
            "Expiry Check",
            interval,
            check_expired
        )
    
    async def _run_idle_timeout_job(self):
        """Job para verificar e processar conversas inativas"""
        async def check_idle():
            processed = await self.conversation_service.process_idle_conversations()
            return f"{len(processed)} conversas inativas processadas"
        
        interval = settings.cleanup_job_interval_minutes * 60
        await self._run_periodic_job(
            "Idle Timeout Check",
            interval,
            check_idle
        )


# Instância global do scheduler
_scheduler: BackgroundJobScheduler = None


def get_scheduler() -> BackgroundJobScheduler:
    """Retorna a instância global do scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundJobScheduler()
    return _scheduler


async def start_background_jobs():
    """Inicia os jobs em background (função helper)"""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_background_jobs():
    """Para os jobs em background (função helper)"""
    scheduler = get_scheduler()
    await scheduler.stop()
