import logging
import os
import sched
import sys
import time

import redis

import redis_lock

try:
    import termios
    import tty
except ImportError:
    # Probably Windows.
    try:
        import msvcrt
    except ImportError:
        # FIXME what to do on other platforms?
        # Just give up here.
        raise ImportError('getch not available')
    else:
        getch = msvcrt.getch
else:
    def getch():
        """getch() -> key character

        Read a single keypress from stdin and return the resulting character.
        Nothing is echoed to the console. This call will block if a keypress
        is not already available, but will not wait for Enter to be pressed.

        If the pressed key was a modifier key, nothing will be detected; if
        it were a special function key, it may return the first character of
        of an escape sequence, leaving additional characters in the buffer.
        """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

logging.basicConfig(level="DEBUG", format="%(asctime)s | %(process)6s | %(message)s")

c = redis.StrictRedis()
pid = os.getpid()
lock = redis_lock.Lock(c, sys.argv[1], expire=5)


def run():
    with lock:
        logging.debug("GOT LOCK. WAITING ...")
        time.sleep(0.05)
        logging.debug("DONE. Press any key to exit.")

    getch()


if __name__ == "__main__":
    s = sched.scheduler(time.time, time.sleep)
    now = int(time.time()) / 10
    t = (now + 1) * 10
    logging.debug("Running in %s seconds ...", t - time.time())
    s.enterabs(t, 0, run, ())
    s.run()
