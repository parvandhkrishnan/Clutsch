import threading
import queue
import time
import uuid
import logging
from typing import Callable, Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("background_worker")

class BackgroundWorker:
    def __init__(self, num_workers: int = 4, max_queue_size: int = 1000):
        self.task_queue = queue.Queue(maxsize=max_queue_size)
        self.executor = ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="PFWorker")
        self.results: Dict[str, Any] = {}
        self.status: Dict[str, str] = {}
        self.errors: Dict[str, str] = {}
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()
        logger.info(f"BackgroundWorker initialized with {num_workers} workers.")

    def _process_queue(self):
        while not self._stop_event.is_set():
            try:
                # Use timeout to allow checking stop_event
                task_id, func, args, kwargs = self.task_queue.get(timeout=1.0)
                self.status[task_id] = "processing"
                
                # Submit to thread pool
                self.executor.submit(self._run_task, task_id, func, args, kwargs)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in queue processing: {e}")

    def _run_task(self, task_id, func, args, kwargs):
        try:
            logger.info(f"Starting task {task_id}")
            result = func(*args, **kwargs)
            self.results[task_id] = result
            self.status[task_id] = "completed"
            logger.info(f"Task {task_id} completed successfully")
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self.status[task_id] = "failed"
            self.errors[task_id] = str(e)
        finally:
            self.task_queue.task_done()

    def enqueue(self, func: Callable, *args, **kwargs) -> str:
        task_id = str(uuid.uuid4())
        try:
            self.status[task_id] = "queued"
            self.task_queue.put((task_id, func, args, kwargs), block=False)
            return task_id
        except queue.Full:
            logger.warning(f"Task queue is full. Task {task_id} rejected.")
            self.status[task_id] = "rejected"
            self.errors[task_id] = "Queue full"
            return task_id

    def get_status(self, task_id: str) -> str:
        return self.status.get(task_id, "unknown")

    def get_result(self, task_id: str) -> Any:
        return self.results.get(task_id)

    def get_error(self, task_id: str) -> Optional[str]:
        return self.errors.get(task_id)

    def stop(self):
        self._stop_event.set()
        self.executor.shutdown(wait=True)

# Singleton worker instance
background_worker = BackgroundWorker()
