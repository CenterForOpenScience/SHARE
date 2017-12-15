import threading


class SyncedThread(threading.Thread):

    def __init__(self, target, args=(), kwargs={}):
        self._end = threading.Event()
        self._start = threading.Event()

        def _target(*args, **kwargs):
            with target(*args, **kwargs):
                self._start.set()
                self._end.wait(10)

        super().__init__(target=_target, args=args, kwargs=kwargs)

    def start(self):
        super().start()
        self._start.wait(10)

    def join(self, timeout=1):
        self._end.set()
        return super().join(timeout)
