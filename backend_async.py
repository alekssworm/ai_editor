# backend_async.py
import os

from PySide6.QtCore import QObject, Signal, Slot, QThread


ASYNC_DEBUG = os.environ.get("AI_BACKEND_ASYNC_DEBUG", "0") in {
    "1",
    "true",
    "True",
}


class BackendWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CallbackRelay(QObject):
    """Deliver worker results on the thread that created the relay (normally the UI thread)."""

    def __init__(self, on_ok, on_err, parent=None):
        super().__init__(parent)
        self.on_ok = on_ok
        self.on_err = on_err
        self.on_cleanup = None

    @Slot(object)
    def success(self, result):
        self.on_ok(result)

    @Slot(str)
    def failure(self, message):
        self.on_err(message)

    @Slot()
    def cleanup(self):
        if self.on_cleanup is not None:
            self.on_cleanup()


def run_in_thread(owner, func, on_ok, on_err, *args, **kwargs):
    """Run a function in a worker and deliver its callbacks on the owner's thread."""
    if not hasattr(owner, "_backend_jobs") or owner._backend_jobs is None:
        owner._backend_jobs = []

    thread = QThread()
    worker = BackendWorker(func, *args, **kwargs)
    relay_parent = owner if isinstance(owner, QObject) else None
    relay = CallbackRelay(on_ok, on_err, relay_parent)
    worker.moveToThread(thread)

    def _dbg(msg: str):
        if not ASYNC_DEBUG:
            return
        try:
            print(f"[DEBUG] {msg}")
        except Exception:
            pass

    _dbg("[ASYNC] start backend thread")

    thread.started.connect(worker.run)
    worker.finished.connect(relay.success)
    worker.error.connect(relay.failure)

    worker.finished.connect(thread.quit)
    worker.error.connect(thread.quit)

    worker.finished.connect(worker.deleteLater)
    worker.error.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    # Keep strong references until the worker finishes; otherwise PySide may
    # garbage-collect the thread before it has a chance to run.
    job = {"thread": thread, "worker": worker, "relay": relay}
    owner._backend_jobs.append(job)

    def _cleanup():
        try:
            owner._backend_jobs.remove(job)
        except Exception:
            pass
        _dbg("[ASYNC] backend thread finished")

    relay.on_cleanup = _cleanup
    thread.finished.connect(relay.cleanup)
    thread.start()
