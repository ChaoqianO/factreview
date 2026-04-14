"""Parallel reference verification with ordered result output."""

from __future__ import annotations
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from queue import Queue
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkItem:
    index: int
    source_paper: Any
    reference: Dict[str, Any]


@dataclass
class Result:
    index: int
    errors: Optional[List[Dict[str, Any]]]
    url: Optional[str]
    time: float
    reference: Dict[str, Any]
    verified_data: Optional[Dict[str, Any]] = None


class ParallelProcessor:
    """Verify references in parallel while printing results in order."""

    def __init__(self, verify_fn: Callable, max_workers: int = 6):
        self.verify_fn = verify_fn
        self.max_workers = max_workers
        self._result_q: Queue = Queue()
        self._buffer: Dict[int, Result] = {}
        self._lock = Lock()
        self._next = 0
        self._total = 0
        self._done = 0

    def run(self, source_paper: Any, bibliography: List[Dict],
            callback: Optional[Callable] = None) -> Dict[str, Any]:
        if not bibliography:
            return self._stats()

        self._total = len(bibliography)
        self._next = 0
        self._done = 0
        self._buffer.clear()

        work_q: Queue = Queue()
        for i, ref in enumerate(bibliography):
            work_q.put(WorkItem(i, source_paper, ref))
        for _ in range(self.max_workers):
            work_q.put(None)

        printer = Thread(target=self._printer, args=(callback,), daemon=True)
        printer.start()

        with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="Ref") as pool:
            futs = [pool.submit(self._worker, work_q) for _ in range(self.max_workers)]
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:
                    logger.error("Worker failed: %s", e)

        printer.join()
        return self._stats()

    def _worker(self, q: Queue):
        while True:
            item = q.get(block=True)
            if item is None:
                q.task_done()
                break
            try:
                t0 = time.time()
                errors, url, vd = self.verify_fn(item.source_paper, item.reference)
                r = Result(item.index, errors, url, time.time() - t0, item.reference, vd)
            except Exception as e:
                logger.error("Verify failed [%d]: %s", item.index, e)
                r = Result(item.index, [{"error_type": "unverified",
                           "error_details": str(e)}], None, 0, item.reference)
            self._result_q.put(r)
            q.task_done()

    def _printer(self, callback: Optional[Callable]):
        while self._done < self._total:
            result = self._result_q.get()
            with self._lock:
                self._buffer[result.index] = result
                while self._next in self._buffer:
                    r = self._buffer.pop(self._next)
                    self._next += 1
                    self._done += 1
                    if callback:
                        try:
                            callback(r)
                        except Exception as e:
                            logger.error("Callback error: %s", e)

    def _stats(self) -> Dict[str, Any]:
        return {"total": self._total, "completed": self._done}
