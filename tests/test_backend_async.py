from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QObject, QThread, QTimer
from PySide6.QtWidgets import QApplication

from backend_async import run_in_thread


class BackendAsyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_callback_returns_to_owner_thread(self) -> None:
        owner = QObject()
        callbacks_on_owner_thread = []
        values = []

        run_in_thread(
            owner,
            lambda: 42,
            lambda value: (
                values.append(value),
                callbacks_on_owner_thread.append(
                    QThread.currentThread() == self.app.thread()
                ),
            ),
            self.fail,
        )

        loop = QEventLoop()
        owner._backend_jobs[0]["thread"].finished.connect(loop.quit)
        QTimer.singleShot(3000, loop.quit)
        loop.exec()
        self.app.processEvents()

        self.assertEqual(values, [42])
        self.assertEqual(callbacks_on_owner_thread, [True])
        self.assertEqual(owner._backend_jobs, [])


if __name__ == "__main__":
    unittest.main()
