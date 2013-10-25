from logging import getLogger
logger = getLogger(__name__)

from os import urandom
from hashlib import sha1
from contextlib import contextmanager
from redis import StrictRedis
from redis.exceptions import NoScriptError

UNLOCK_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        redis.call("lpush", KEYS[2], 1)
        return redis.call("del", KEYS[1])
    else
        return 0
    end
"""
UNLOCK_SCRIPT_HASH = sha1(UNLOCK_SCRIPT).hexdigest()


class Lock(object):
    def __init__(self, redis_client, name, expire=None):
        self._client = redis_client
        self._expire = expire
        self._tok = None
        self._name = 'lock:'+name
        self._signal = 'lock-signal:'+name

    def __enter__(self, blocking=True):
        logging.debug("Getting %r ...", self._name)

        if self._tok is None:
            self._tok = urandom(16) if self._expire else 1
        else:
            raise RuntimeError("Already aquired from this Lock instance.")

        busy = True
        while busy:
            busy = not self._client.set(self._name, self._tok, nx=True, ex=self._expire)
            if busy:
                if blocking:
                    self._client.blpop(self._signal, self._expire or 0)
                else:
                    logging.debug("Failed to get %r.", self._name)
                    return False

        logging.debug("Got lock for %r.", self._name)

        self._client.delete(self._signal)
        return True
    acquire = __enter__


    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        logging.debug("Releasing %r.", self._name)
        try:
            self._client.evalsha(UNLOCK_SCRIPT_HASH, 2, self._name, self._signal, self._tok)
        except NoScriptError:
            logging.warn("UNLOCK_SCRIPT not cached.")
            self._client.eval(UNLOCK_SCRIPT, 2, self._name, self._signal, self._tok)
    release = __exit__


if __name__ == '__main__':
    import sys

    try:
        import tty, termios
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
    import os
    import sys
    import time
    import logging
    logging.basicConfig(level="DEBUG", format="%(asctime)s | %(process)6s | %(message)s")

    c = StrictRedis()
    pid = os.getpid()
    def run():
        with Lock(c, sys.argv[1], expire=5):
            time.sleep(0.05)
            #logging.debug("GOT LOCK. WAITING ...")
            #time.sleep(1)
            #for i in range(5):
            #    time.sleep(1)
            #    print i,
            #print
            #logging.debug("DONE.")

        #raw_input("Exit?")
        getch()

    import sched
    s = sched.scheduler(time.time, time.sleep)
    now = int(time.time()) / 10
    t = (now+1) * 10
    logging.debug("Running in %s seconds ...", t - time.time())
    s.enterabs(t, 0, run, ())
    s.run()
    #run()
