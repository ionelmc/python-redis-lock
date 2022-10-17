import os
from pathlib import Path

TIMEOUT = int(os.getenv('REDIS_LOCK_TEST_TIMEOUT', 10))
HELPER = str(Path(__file__).parent / 'helper.py')
