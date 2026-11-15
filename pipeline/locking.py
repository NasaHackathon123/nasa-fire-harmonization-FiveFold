"""OS advisory locks are released even when a process is interrupted."""
import os
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def exclusive(path, *, shared=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        deadline = time.monotonic() + (1 if shared else 0)
        while True:
            try:
                if os.name == 'nt':
                    import msvcrt
                    # CRT readers can serialize within one Windows process.
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBRLCK if shared else msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ValueError('Another data operation is running') from None
                time.sleep(.01)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
