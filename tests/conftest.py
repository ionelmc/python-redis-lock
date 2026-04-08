import pytest
from process_tests import TestProcess
from process_tests import wait_for_strings


@pytest.fixture
def redis_socket(tmp_path):
    return str(tmp_path.joinpath('redis.sock'))


@pytest.fixture
def redis_server(tmp_path, redis_socket):
    with TestProcess(
        'valkey-server', '--port', '0', '--save', '', '--appendonly', 'yes', '--dir', tmp_path, '--unixsocket', redis_socket
    ) as redis_server:
        wait_for_strings(
            redis_server.read,
            2,
            'oO0OoO0OoO0Oo Valkey is starting oO0OoO0OoO0Oo',
            'Ready to accept connections',
        )
        yield redis_server
