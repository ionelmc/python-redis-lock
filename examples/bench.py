import logging
import signal
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from sched import scheduler

from redis import StrictRedis

from redis_lock import Lock
from redis_lock import logger

logging.basicConfig(level="WARN", format="%(message)s")
logger.setLevel("WARN")


class Exit(Exception):
    pass


def bail(n, f):
    raise Exit()


signal.signal(signal.SIGALRM, bail)


def test(arg):
    t, duration, type_ = arg
    conn = StrictRedis()
    conn.flushdb()
    ret = []

    def run():
        iterations = 0
        signal.setitimer(signal.ITIMER_REAL, int(sys.argv[1]))
        try:
            if type_ == 'redis_lock':
                lock = Lock(conn, "test-lock")
            elif type_ == 'native':
                lock = conn.lock("test-lock")
            else:
                raise RuntimeError
            while True:
                with lock:
                    iterations += 1
                    if duration:
                        time.sleep(duration)
        except Exit as exc:
            logging.info("Got %r. Returning ...", exc)
        ret.append(iterations)

    sched = scheduler(time.time, time.sleep)
    logging.info("Running in %s seconds ...", t - time.time())
    sched.enterabs(t, 0, run, ())
    sched.run()
    return ret[0]


logging.critical("============== ============= =========== ========= ========== ========== ========== ==========")
logging.critical("Implementation Lock duration Concurrency Acquires: Total      Avg        Min        Max")
logging.critical("============== ============= =========== ========= ========== ========== ========== ==========")


for concurrency in (
    1,
    2,
    3,
    6,
    12,
    24,
    48
):
    for duration in (
        0,
        0.01,
        0.5,
    ):
        for type_ in (
            'redis_lock',
            'native',
        ):
            with ProcessPoolExecutor(max_workers=concurrency) as pool:
                t = round(time.time()) + 1
                load = [(t, duration, type_) for _ in range(concurrency)]
                logging.info("Running %s", load)
                ret = [i for i in pool.map(test, load)]
            if concurrency > 1:
                logging.critical(
                    "%14s %12.3fs %11s %20s %10.2f %10s %10s",
                    type_, duration, concurrency, sum(ret), sum(ret) / len(ret), min(ret), max(ret)
                )
            else:
                logging.critical(
                    "%14s %12.3fs %11s %20s",
                    type_, duration, concurrency, sum(ret),
                )
logging.critical("============== ============= =========== ========= ========== ========== ========== ==========")
