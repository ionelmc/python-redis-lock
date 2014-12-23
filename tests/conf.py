import os


TIMEOUT = int(os.getenv('REDIS_LOCK_TEST_TIMEOUT', 10))
UDS_PATH = '/tmp/redis-lock-tests.sock'
HELPER = os.path.join(os.path.dirname(__file__), 'helper.py')
