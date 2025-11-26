import time


class TimerError(Exception):

    """A custom exception used to report errors in use of Timer class"""


class Timeable:
    records = []

    def __init__(self, timer_name=None):
        if timer_name == None:
            self.timer_name = self.__class__.__name__
        else:
            self.timer_name = timer_name

        self.records = []

        self._start_time = None

        super(Timeable, self).__init__()

    def start_timer(self):
        """Start a new timer"""

        if self._start_time is not None:

            raise TimerError("Timer is running. Use .stop_timer() to stop it")

        self._start_time = time.perf_counter()

    def stop_timer(self):
        """Stop the timer, and report the elapsed time"""

        if self._start_time is None:

            raise TimerError("Timer is not running. Use .start_timer() to start it")

        elapsed_time = time.perf_counter() - self._start_time

        self._start_time = None

        elapsed_time = f"{elapsed_time:0.4f}"

        Timeable.records.append({"name": self.timer_name, "elapsed_time": elapsed_time})

        print(f"{self.timer_name}: Elapsed time: {elapsed_time} seconds")
