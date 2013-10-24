from logging import getLogger
logger = getLogger(__name__)

from os import urandom
from hashlib import sha1
from contextlib import contextmanager
from redis import StrictRedis
from redis.exceptions import NoScriptError

UNLOCK_SCRIPT = """
    redis.call("lpush", KEYS[2], "X")
    redis.call("del",KEYS[1])
"""
UNLOCK_SCRIPT_HASH = sha1(UNLOCK_SCRIPT).hexdigest()

@contextmanager
def lock(conn, name):
    name_ready = name + ":ready"
    logging.debug("Getting lock for %r ...", name)
    busy = True
    while busy:
        busy = not conn.set(name, "X", nx=True)
        if busy:
            conn.blpop(name_ready, 0)
    logging.debug("Got lock for %r.", name)
    conn.delete(name_ready)
    try:
        yield
    finally:
        logging.debug("Removing lock for %r.", name)
        try:
            print conn.evalsha(UNLOCK_SCRIPT_HASH, 2, name, name_ready)
        except NoScriptError:
            logging.warn("UNLOCK_SCRIPT not cached.")
            print conn.eval(UNLOCK_SCRIPT, 2, name, name_ready)


if __name__ == '__main__':
    import os
    import sys
    import time
    import logging
    logging.basicConfig(level="DEBUG", format="%(asctime)s | %(process)6s | %(message)s")

    c = StrictRedis()
    pid = os.getpid()

    with lock(c, sys.argv[1]):
        time.sleep(0.05)
        #logging.debug("GOT LOCK. WAITING ...")
        #time.sleep(1)
        #for i in range(5):
        #    time.sleep(1)
        #    print i,
        #print
        #logging.debug("DONE.")

    raw_input("Exit?")
