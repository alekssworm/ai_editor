# backend_async.py
from PySide6.QtCore import QObject, Signal, Slot, QThread

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

def run_in_thread(owner, func, on_ok, on_err, *args, **kwargs):
    """
    owner — это self твоего окна (MainWindow/AIWindow).
    Важно хранить ссылки на thread И worker в owner, иначе PySide может
    собрать worker GC и тогда thread стартует, но ничего не выполнится.
    """
    if not hasattr(owner, "_backend_jobs") or owner._backend_jobs is None:
        owner._backend_jobs = []

    thread = QThread()
    worker = BackendWorker(func, *args, **kwargs)
    worker.moveToThread(thread)

    def _dbg(msg: str):
        try:
            print(f"[DEBUG] {msg}")
        except Exception:
            pass

    _dbg("[ASYNC] start backend thread")

    thread.started.connect(worker.run)
    worker.finished.connect(on_ok)
    worker.error.connect(on_err)

    worker.finished.connect(thread.quit)
    worker.error.connect(thread.quit)

    worker.finished.connect(worker.deleteLater)
    worker.error.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    # держим ссылки на thread+worker, иначе “ничего не происходит”
    job = {"thread": thread, "worker": worker}
    owner._backend_jobs.append(job)

    def _cleanup():
        try:
            owner._backend_jobs.remove(job)
        except Exception:
            pass
        _dbg("[ASYNC] backend thread finished")

    thread.finished.connect(_cleanup)
    thread.start()

