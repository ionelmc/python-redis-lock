from __future__ import division
from __future__ import print_function

import logging
import os
import sys
import threading
import time

from redis import StrictRedis

from redis_lock import Lock

from config import TIMEOUT

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG, format='%(process)d %(asctime)s,%(msecs)05d %(name)s %(levelname)s %(message)s', datefmt="%x~%X"
    )
    redis_socket = sys.argv[1]
    test_name = sys.argv[2]
    if ':' in test_name:
        test_name, effect = test_name.split(':')
        logging.info('Applying effect %r.', effect)
        if effect == 'gevent':
            from gevent import monkey

            monkey.patch_all()
        elif effect == 'eventlet':
            import eventlet

            eventlet.monkey_patch()
        else:
            raise RuntimeError('Invalid effect spec %r.' % effect)
    logging.info('threading.get_ident.__module__=%s', threading.get_ident.__module__)
    if test_name == 'test_simple':
        conn = StrictRedis(unix_socket_path=redis_socket)
        with Lock(conn, "foobar"):
            time.sleep(0.1)
    elif test_name == 'test_simple_auto_renewal':
        conn = StrictRedis(unix_socket_path=redis_socket)
        with Lock(conn, "foobar", expire=1, auto_renewal=True) as lock:
            time.sleep(2)
    elif test_name == 'test_no_block':
        conn = StrictRedis(unix_socket_path=redis_socket)
        lock = Lock(conn, "foobar")
        res = lock.acquire(blocking=False)
        logging.info("acquire=>%s", res)
    elif test_name == 'test_timeout':
        conn = StrictRedis(unix_socket_path=redis_socket)
        with Lock(conn, "foobar"):
            time.sleep(1)
    elif test_name == 'test_expire':
        conn = StrictRedis(unix_socket_path=redis_socket)
        with Lock(conn, "foobar", expire=TIMEOUT / 4):
            time.sleep(0.1)
        with Lock(conn, "foobar", expire=TIMEOUT / 4):
            time.sleep(0.1)
    elif test_name == 'test_no_overlap':
        from sched import scheduler

        sched = scheduler(time.time, time.sleep)
        start = time.time() + TIMEOUT / 2

        # the idea is to start all the lock at the same time - we use the scheduler to start everything in TIMEOUT/2 seconds, by
        # that time all the forks should be ready

        def cb_no_overlap():
            with Lock(conn, "foobar"):
                time.sleep(0.001)

        sched.enterabs(start, 0, cb_no_overlap, ())
        pids = []

        for _ in range(125):
            pid = os.fork()
            if pid:
                pids.append(pid)
            else:
                try:
                    conn = StrictRedis(unix_socket_path=redis_socket)
                    sched.run()
                finally:
                    os._exit(0)
        for pid in pids:
            os.waitpid(pid, 0)
    else:
        raise RuntimeError('Invalid test spec %r.' % test_name)
    logging.info('DIED.')
