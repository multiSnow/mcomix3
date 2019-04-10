from threading import Lock,Timer

class Interval:
    # Call function every delay milliseconds with optional args and kwargs.
    def __init__(self,delay,function,args=(),kwargs={}):
        if not callable(function):
            raise ValueError('{} is not callable'.format(function))

        self.delay=delay
        self.function=function
        self.args=args
        self.kwargs=kwargs
        self.timer=None

        self._lock=Lock()
        self._calling=False

    def _caller(self):
        # Call function with optional args and kwargs, then set a new Timer
        self._calling=True
        try:
            self.function(*self.args,**self.kwargs)
        except Exception as e:
            pass
        self._calling=False
        self.reset()

    def _settimer(self):
        # Set and start Timer
        # this function should be always called in lock
        if self.is_running():
            return
        self.timer=Timer(self.delay/1000,self._caller)
        self.timer.start()

    def start(self):
        # Start or restart intervaller.
        with self._lock:
            if self.is_running():
                return
            self._settimer()

    def stop(self):
        # Stop intervaller.
        with self._lock:
            if not self.is_running():
                return
            self.timer.cancel()
            self.timer=None

    def reset(self):
        # Reset Timer
        with self._lock:
            if not self.is_running():
                return
            if self._calling:
                return
            self.timer.cancel()
            self.timer=None
            self._settimer()

    def is_running(self):
        return self.timer is not None

if __name__=='__main__':
    exit(0)
