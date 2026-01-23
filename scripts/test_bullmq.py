import asyncio
from bullmq import Queue, Worker

async def process(job, token):
    print(f"Processing job {job.id}: {job.data}")
    return "done"

async def main():
    queue = Queue("test_queue", {"connection": {"host": "localhost", "port": 6379}})
    
    # Add job
    await queue.add("test_task", {"foo": "bar"})
    print("Job added")
    
    # Worker
    worker = Worker("test_queue", process, {"connection": {"host": "localhost", "port": 6379}})
    
    # Wait a bit
    await asyncio.sleep(2)
    
    await worker.close()
    await queue.close()

if __name__ == "__main__":
    asyncio.run(main())
