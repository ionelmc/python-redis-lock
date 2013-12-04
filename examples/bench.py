import logging
logging.basicConfig(level="WARN", format="%(message)s")

import os
import sys
import time
import signal
from futures import ProcessPoolExecutor
from sched import scheduler
from redis import StrictRedis
from redis_lock import Lock

class Exit(Exception):
    pass

def bail(n, f):
    raise Exit()

signal.signal(signal.SIGALRM, bail)

def test((t, duration, type_)):
    conn = StrictRedis()
    conn.flushdb()
    ret = []

    def run():
        iterations = 0
        signal.setitimer(signal.ITIMER_REAL, int(sys.argv[1]))
        try:
            if type_ == 'redis_lock':
                while True:
                    with Lock(conn, "test-lock", expire=5):
                        iterations += 1
                        time.sleep(duration)
            elif type_ == 'native':
                while True:
                    with conn.lock("test-lock", timeout=5):
                        iterations += 1
                        time.sleep(duration)
        except:
            logging.info("Got %r. Returning ...", sys.exc_value)
        ret.append(iterations)

    sched = scheduler(time.time, time.sleep)
    logging.info("Running in %s seconds ...", t - time.time())
    sched.enterabs(t, 0, run, ())
    sched.run()
    return ret[0]
logging.critical("========== ======== =========== ======== ========== ===== =====")
logging.critical("Type       Duration Concurrency Sum      Avg        Min   Max")
logging.critical("========== ======== =========== ======== ========== ===== =====")

for type_ in (
    'redis_lock',
    'native',
):
    for duration in (
        0,
        0.001,
        0.01,
        0.05,
        0.1
    ):
        for concurrency in (
            1,
            2,
            3,
            4,
            5,
            6,
            12,
            24,
            48
        ):
            with ProcessPoolExecutor(max_workers=concurrency) as pool:
                t = round(time.time()) + 1
                load = [(t, duration, type_) for _ in range(concurrency)]
                logging.info("Running %s", load)
                ret = [i for i in pool.map(test, load)]

            logging.critical(
                "%10s %-8.3f %-11s %-8s %-10.2f %-5s %-5s",
                type_, duration, concurrency, sum(ret), sum(ret)/len(ret), min(ret), max(ret)
            )
logging.critical("========== ======== =========== ======== ========== ===== =====")
