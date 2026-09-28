"""
hang_watch.py — dump every thread's stack if a scheduled script runs too long (v4.6.3)

The scheduler kills a script at its timeout and logs only "Timed out", which
says nothing about where it was stuck. Arm this at script start with a delay
a little under the scheduler timeout; if the script is still running then,
a timestamped header and the stack of every thread are appended to
logs/<name>_hang.txt. A normal run cancels it and writes nothing.

Two mechanisms: a daemon Timer writes the header (needs the GIL), and
faulthandler's C-level watchdog writes the stacks (works even if a thread
holds the GIL).
"""

import faulthandler
import os
import threading
from datetime import datetime

_state = {}


def arm(name: str, after_seconds: float, log_dir=None) -> None:
    try:
        log_dir = str(log_dir or os.getenv('LOG_DIR', '/app/logs'))
        os.makedirs(log_dir, exist_ok=True)
        f = open(os.path.join(log_dir, f'{name}_hang.txt'), 'a')

        def _header():
            try:
                f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} {name} still running "
                        f"after {after_seconds:.0f}s (pid {os.getpid()}) =====\n")
                f.flush()
            except Exception:
                pass

        t = threading.Timer(max(1.0, after_seconds - 1.0), _header)
        t.daemon = True
        t.start()
        faulthandler.dump_traceback_later(after_seconds, repeat=False, file=f, exit=False)
        _state.update(file=f, timer=t)
    except Exception:
        pass


def disarm() -> None:
    try:
        faulthandler.cancel_dump_traceback_later()
        t = _state.get('timer')
        if t:
            t.cancel()
        f = _state.get('file')
        if f:
            f.close()
    except Exception:
        pass
