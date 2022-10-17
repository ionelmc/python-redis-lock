import pytest
from process_tests import TestProcess
from process_tests import wait_for_strings


@pytest.fixture
def redis_socket(tmp_path):
    return str(tmp_path.joinpath('redis.sock'))


@pytest.fixture
def redis_server(tmp_path, redis_socket):
    with TestProcess(
        'redis-server', '--port', '0', '--save', '', '--appendonly', 'yes', '--dir', tmp_path, '--unixsocket', redis_socket
    ) as redis_server:
        wait_for_strings(redis_server.read, 2, 'ready to accept connections')
        yield redis_server
