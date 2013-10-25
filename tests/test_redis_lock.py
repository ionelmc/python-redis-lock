from __future__ import print_function

from process_tests import TestProcess, ProcessTestCase
import unittest
import os
import sys
import time
import logging
import atexit

from redis_lock import Lock
from redis import StrictRedis

TIMEOUT = int(os.getenv('REDIS_LOCK_TEST_TIMEOUT', 10))
UDS_PATH = '/tmp/redis-lock-tests.sock'

class RedisLockTestCase(ProcessTestCase):
    def setUp(self):
        self.redis_server = TestProcess('redis-server', '--port', '0', '--unixsocket', UDS_PATH)

    def tearDown(self):
        print(self.redis_server.read())
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

cov = None
def maybe_enable_coverage():
    global cov
    try:
        from coverage.control import coverage
        from coverage.collector import Collector
    except ImportError:
        cov = None
        return
    if cov:
        cov.save()
        cov.stop()
    if Collector._collectors:
        Collector._collectors[-1].stop()
    cov = cov or os.environ.get("WITH_COVERAGE")
    if cov:
        cov = coverage(auto_data=True, data_suffix=True, timid=False, include=['src/*'])
        cov.start()

        @atexit.register
        def cleanup():
            if cov.collector._collectors:
                cov.stop()
            cov.save()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'daemon':
        logging.basicConfig(
            level=logging.DEBUG,
            format='[pid=%(process)d - %(asctime)s]: %(name)s - %(levelname)s - %(message)s',
        )
        test_name = sys.argv[2]

        maybe_enable_coverage()
        conn = StrictRedis(unix_socket_path=UDS_PATH)

        if test_name == 'test_simple':
            with Lock(conn, "foobar"):
                time.sleep(0.1)
        else:
            raise RuntimeError('Invalid test spec.')
        print('DIED.')
    else:
        unittest.main()
