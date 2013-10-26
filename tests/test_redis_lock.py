from __future__ import print_function

import unittest
import os
import sys
import time
import logging
from collections import defaultdict

from process_tests import TestProcess, ProcessTestCase, setup_coverage
from redis import StrictRedis

from redis_lock import Lock

TIMEOUT = int(os.getenv('REDIS_LOCK_TEST_TIMEOUT', 10))
UDS_PATH = '/tmp/redis-lock-tests.sock'

class RedisLockTestCase(ProcessTestCase):
    def setUp(self):
        try:
            os.unlink(UDS_PATH)
        except OSError:
            pass
        self.redis_server = TestProcess('redis-server', '--port', '0', '--unixsocket', UDS_PATH)
        self.wait_for_strings(self.redis_server.read, TIMEOUT, "Running")

    def tearDown(self):
        self.redis_server.close()

    def test_simple(self):
        with TestProcess(sys.executable, __file__, 'daemon', 'test_simple') as proc:
            with self.dump_on_error(proc.read):
                name = 'lock:foobar'
                self.wait_for_strings(proc.read, TIMEOUT,
                    'Getting %r ...' % name,
                    'Got lock for %r.' % name,
                    'Releasing %r.' % name,
                    'UNLOCK_SCRIPT not cached.',
                    'DIED.',
                )

    def test_no_block(self):
        with Lock(StrictRedis(unix_socket_path=UDS_PATH), "foobar"):
            with TestProcess(sys.executable, __file__, 'daemon', 'test_no_block') as proc:
                with self.dump_on_error(proc.read):
                    name = 'lock:foobar'
                    self.wait_for_strings(proc.read, TIMEOUT,
                        'Getting %r ...' % name,
                        'Failed to get %r.' % name,
                        'acquire=>False',
                        'DIED.',
                    )

    def test_expire(self):
        conn = StrictRedis(unix_socket_path=UDS_PATH)
        with Lock(conn, "foobar", expire=TIMEOUT/4):
            with TestProcess(sys.executable, __file__, 'daemon', 'test_expire') as proc:
                with self.dump_on_error(proc.read):
                    name = 'lock:foobar'
                    self.wait_for_strings(proc.read, TIMEOUT,
                        'Getting %r ...' % name,
                        'Got lock for %r.' % name,
                        'Releasing %r.' % name,
                        'UNLOCK_SCRIPT not cached.',
                        'DIED.',
                    )
        lock = Lock(conn, "foobar")
        try:
            self.assertEqual(lock.acquire(blocking=False), True)
        finally:
            lock.release()

    def test_double_acquire(self):
        lock = Lock(StrictRedis(unix_socket_path=UDS_PATH), "foobar")
        with lock:
            self.assertRaises(RuntimeError, lock.acquire)

    def test_plain(self):
        with Lock(StrictRedis(unix_socket_path=UDS_PATH), "foobar"):
            time.sleep(0.01)

    def test_no_overlap(self):
        with TestProcess(sys.executable, __file__, 'daemon', 'test_no_overlap') as proc:
            with self.dump_on_error(proc.read):
                name = 'lock:foobar'
                self.wait_for_strings(proc.read, TIMEOUT, 'Getting %r ...' % name)
                self.wait_for_strings(proc.read, TIMEOUT, 'Got lock for %r.' % name)
                self.wait_for_strings(proc.read, TIMEOUT, 'Releasing %r.' % name)
                self.wait_for_strings(proc.read, TIMEOUT, 'UNLOCK_SCRIPT not cached.')
                self.wait_for_strings(proc.read, 10*TIMEOUT, 'DIED.')

                class Event(object):
                    def __str__(self):
                        return "Event(%s; %r => %r)" % (self.pid, self.start, self.end)

                events = defaultdict(Event)
                for line in proc.read().splitlines():
                    pid, time, junk = line.split(' ', 2)
                    if 'Got lock for' in junk:
                        events[pid].pid = pid
                        events[pid].start = time
                    if 'Releasing' in junk:
                        events[pid].pid = pid
                        events[pid].end = time
                self.assertEqual(len(events), 125)

                for event in events.values():
                    for other in events.values():
                        if other is not event:
                            try:
                                if other.start < event.start < other.end or \
                                   other.start < event.end < other.end:
                                    self.fail('%s overlaps %s' % (event, other))
                            except:
                                print("[%s/%s]" %(event, other))
                                raise


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'daemon':
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(process)d %(asctime)s,%(msecs)05d %(name)s %(levelname)s %(message)s',
            datefmt="%x~%X"
        )
        test_name = sys.argv[2]

        setup_coverage()

        if test_name == 'test_simple':
            conn = StrictRedis(unix_socket_path=UDS_PATH)
            with Lock(conn, "foobar"):
                time.sleep(0.1)
        elif test_name == 'test_no_block':
            conn = StrictRedis(unix_socket_path=UDS_PATH)
            lock = Lock(conn, "foobar")
            res = lock.acquire(blocking=False)
            logging.info("acquire=>%s", res)
        elif test_name == 'test_expire':
            conn = StrictRedis(unix_socket_path=UDS_PATH)
            with Lock(conn, "foobar", expire=TIMEOUT/4):
                time.sleep(0.1)
            with Lock(conn, "foobar", expire=TIMEOUT/4):
                time.sleep(0.1)
        elif test_name == 'test_no_overlap':
            from sched import scheduler
            sched = scheduler(time.time, time.sleep)
            start = time.time() + TIMEOUT/2
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
                        conn = StrictRedis(unix_socket_path=UDS_PATH)
                        sched.run()
                    finally:
                        os._exit(0)
            for pid in pids:
                os.waitpid(pid, 0)
        else:
            raise RuntimeError('Invalid test spec %r.' % test_name)
        logging.info('DIED.')
    else:
        unittest.main()
