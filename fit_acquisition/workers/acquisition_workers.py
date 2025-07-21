from PySide6.QtCore import QObject, Signal, Slot


class StartTasksWorker(QObject):
    finished = Signal()

    def __init__(self, acquisition):
        super().__init__()
        self.acquisition = acquisition

    @Slot()
    def run(self):
        self.acquisition.log_start_message()
        self.acquisition.run_start_tasks()
        self.finished.emit()


class StopTasksWorker(QObject):
    finished = Signal()

    def __init__(self, acquisition):
        super().__init__()
        self.acquisition = acquisition

    @Slot()
    def run(self):
        self.acquisition.log_stop_message()
        self.acquisition.run_stop_tasks()
        self.finished.emit()


class PostTasksWorker(QObject):
    finished = Signal()

    def __init__(self, acquisition):
        super().__init__()
        self.acquisition = acquisition

    @Slot()
    def run(self):
        self.acquisition.start_post_acquisition()
        self.finished.emit()
