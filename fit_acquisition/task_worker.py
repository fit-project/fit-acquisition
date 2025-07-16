from PySide6.QtCore import QObject, Signal
from fit_acquisition.lang import load_translations


class TaskWorker(QObject):
    started = Signal()
    finished = Signal()
    error = Signal(object)

    def __init__(self):
        QObject.__init__(self)
        self.__translations = load_translations()

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, options):
        self._options = options

    @property
    def translations(self):
        return self.__translations

    def start(self):
        pass

    def stop(self):
        pass
