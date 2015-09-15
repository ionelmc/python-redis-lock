import pytest

try:
    import django
except ImportError:
    django = None
else:
    from django.core.cache import cache


@pytest.mark.skipif("not django")
def test_django_works(redis_server):
    with cache.lock('whateva'):
        pass


@pytest.mark.skipif("not django")
def test_reset_all(redis_server):
    lock1 = cache.lock("foobar1")
    lock2 = cache.lock("foobar2")
    lock1.acquire(blocking=False)
    lock2.acquire(blocking=False)
    cache.reset_all()
    lock1 = cache.lock("foobar1")
    lock2 = cache.lock("foobar2")
    lock1.acquire(blocking=False)
    lock2.acquire(blocking=False)
    lock1.release()
    lock2.release()
