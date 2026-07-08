from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(str)


class Worker(QRunnable):
    def __init__(self, task: Callable[[Callable[[str], None]], object]) -> None:
        super().__init__()
        self.task = task
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.task(self.signals.progress.emit)
        except Exception as error:
            self.signals.failed.emit(str(error))
            return
        self.signals.finished.emit(result)
