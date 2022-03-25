import os

import pytest
from process_tests import TestProcess
from process_tests import wait_for_strings

from conf import TIMEOUT
from conf import UDS_PATH


@pytest.fixture
def redis_server(tmp_path):
    try:
        os.unlink(UDS_PATH)
    except OSError:
        pass
    with TestProcess(
        'redis-server',
        '--port', '0',
        '--save', '',
        '--appendonly', 'yes',
        '--dir', tmp_path,
        '--unixsocket', UDS_PATH
    ) as redis_server:
        wait_for_strings(redis_server.read, TIMEOUT, 'ready to accept connections')
        yield redis_server
