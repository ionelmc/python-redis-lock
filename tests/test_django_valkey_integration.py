import os

import pytest

import redis_lock

try:
    import django
except ImportError:
    django = None
else:
    from django.core.cache import caches


@pytest.fixture(scope='module')
def redis_socket_static(tmpdir_factory):
    path = str(tmpdir_factory.getbasetemp() / 'redis.sock')
    os.environ['REDIS_SOCKET'] = path
    redis_lock.reset_all_script = None
    return path


@pytest.fixture
def redis_socket(redis_socket_static):
    return redis_socket_static


@pytest.mark.skipif('not django')
def test_django_works(redis_server):
    with caches['valkey'].lock('whateva'):
        pass


@pytest.mark.skipif('not django')
def test_django_add_or_set_locked(redis_server):
    def creator_42():
        return 42

    def none_creator():
        return None

    def assert_false_creator():
        raise AssertionError

    assert caches['valkey'].locked_get_or_set('foobar-aosl', creator_42) == 42
    assert caches['valkey'].locked_get_or_set('foobar-aosl', assert_false_creator) == 42

    try:
        caches['valkey'].locked_get_or_set('foobar-aosl2', none_creator)
    except ValueError:
        pass
    else:
        raise AssertionError


@pytest.mark.skipif('not django')
def test_reset_all(redis_server):
    lock1 = caches['valkey'].lock('foobar1')
    lock2 = caches['valkey'].lock('foobar2')
    lock1.acquire(blocking=False)
    lock2.acquire(blocking=False)
    caches['valkey'].reset_all()
    lock1 = caches['valkey'].lock('foobar1')
    lock2 = caches['valkey'].lock('foobar2')
    lock1.acquire(blocking=False)
    lock2.acquire(blocking=False)
    lock1.release()
    lock2.release()
