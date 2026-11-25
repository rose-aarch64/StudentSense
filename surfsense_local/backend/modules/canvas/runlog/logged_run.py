from collections.abc import Iterator
from contextlib import contextmanager

from modules.canvas.runlog.log import RunHandle
from modules.canvas.runlog.stop_code import stop_code


@contextmanager
def logged(handle: RunHandle) -> Iterator[None]:
    """End the run's log as the work inside it ended: done, or stopped with why.

    Put inside the route's error mapping, so the log sees the original error.
    """
    try:
        yield
    except BaseException as error:
        handle.add("stopped", "error", error=stop_code(error))
        handle.finish("failed")
        raise
    handle.finish("done")
