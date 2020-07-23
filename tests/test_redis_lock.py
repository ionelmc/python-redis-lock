from __future__ import division
from __future__ import print_function

import gc
import multiprocessing
import os
import platform
import sys
import threading
import time
from collections import defaultdict
from functools import partial

import pytest
from process_tests import TestProcess
from process_tests import dump_on_error
from process_tests import wait_for_strings
from redis import StrictRedis

from redis_lock import AlreadyAcquired
from redis_lock import InvalidTimeout
from redis_lock import Lock
from redis_lock import NotAcquired
from redis_lock import NotExpirable
from redis_lock import TimeoutNotUsable
from redis_lock import TimeoutTooLarge
from redis_lock import reset_all

from conf import HELPER
from conf import TIMEOUT
from conf import UDS_PATH


def maybe_decode(data):
    if isinstance(data, bytes):
        return data.decode('ascii')
    else:
        return data


@pytest.yield_fixture
def redis_server(scope='module'):
    try:
        os.unlink(UDS_PATH)
    except OSError:
        pass
    with TestProcess('redis-server', '--port', '0', '--unixsocket', UDS_PATH) as process:
        with dump_on_error(process.read):
            wait_for_strings(process.read, TIMEOUT, "Running")
            yield process


def make_conn_factory(addfinalizer, **options):
    conn = StrictRedis(unix_socket_path=UDS_PATH, **options)
    addfinalizer(conn.flushdb)

    return conn


@pytest.fixture(scope='function', params=[True, False], ids=['decode_responses=True', 'decode_responses=False'])
def make_conn(request, redis_server):
    """Redis connection factory."""
    return partial(make_conn_factory, request.addfinalizer, decode_responses=request.param, encoding_errors='replace')


@pytest.fixture(scope='function')
def conn(request, make_conn):
    return make_conn()


@pytest.fixture
def make_process(request):
    """Process factory, that makes processes, that terminate themselves
    after a test run.
    """

    def make_process_factory(*args, **kwargs):
        process = multiprocessing.Process(*args, **kwargs)
        request.addfinalizer(process.terminate)

        return process

    return make_process_factory


def test_upgrade(request, conn):
    legacy_conn = make_conn_factory(request.addfinalizer, decode_responses=False)
    lock = Lock(conn, "foobar")
    legacy_conn.set(lock._name, b'\xd6{\xc93\xe9\xbd,\xdb\xb6\xa8<\x8ax\xd1<\xb9', nx=True, ex=lock._expire)
    assert not lock.acquire(blocking=False)


def test_simple(redis_server):
    with TestProcess(sys.executable, HELPER, 'test_simple') as proc:
        with dump_on_error(proc.read):
            name = 'lock:foobar'
            wait_for_strings(
                proc.read, TIMEOUT,
                'Getting %r ...' % name,
                'Got lock for %r.' % name,
                'Releasing %r.' % name,
                'DIED.',
            )


def test_no_block(conn):
    with Lock(conn, "foobar"):
        with TestProcess(sys.executable, HELPER, 'test_no_block') as proc:
            with dump_on_error(proc.read):
                name = 'lock:foobar'
                wait_for_strings(
                    proc.read, TIMEOUT,
                    'Getting %r ...' % name,
                    'Failed to get %r.' % name,
                    'acquire=>False',
                    'DIED.',
                )


def test_timeout(conn):
    with Lock(conn, "foobar"):
        lock = Lock(conn, "foobar")
        assert lock.acquire(timeout=1) is False


@pytest.mark.parametrize("timeout", [0, "0", "123"])
def test_timeout_int_conversion(conn, timeout):
    lock = Lock(conn, "foobar")
    lock.acquire(blocking=True, timeout=timeout)
    lock.release()


def test_timeout_expire(conn):
    lock1 = Lock(conn, "foobar", expire=1)
    lock1.acquire()
    lock2 = Lock(conn, "foobar")
    assert lock2.acquire(timeout=2)


def test_timeout_expire_with_renewal(conn):
    with Lock(conn, "foobar", expire=1, auto_renewal=True):
        lock = Lock(conn, "foobar")
        assert lock.acquire(timeout=2) is False


def test_timeout_acquired(conn):
    with TestProcess(sys.executable, HELPER, 'test_timeout') as proc:
        with dump_on_error(proc.read):
            name = 'lock:foobar'
            wait_for_strings(
                proc.read, TIMEOUT,
                'Getting %r ...' % name,
                'Got lock for %r.' % name,
            )
            lock = Lock(conn, "foobar")
            assert lock.acquire(timeout=2)


def test_not_usable_timeout(conn):
    lock = Lock(conn, "foobar")
    with pytest.raises(TimeoutNotUsable):
        lock.acquire(blocking=False, timeout=1)


def test_expire_less_than_timeout(conn):
    lock = Lock(conn, "foobar", expire=1)
    pytest.raises(TimeoutTooLarge, lock.acquire, blocking=True, timeout=2)

    lock = Lock(conn, "foobar", expire=1, auto_renewal=True)
    lock.acquire(blocking=True, timeout=2)
    lock.release()


def test_invalid_timeout(conn):
    lock = Lock(conn, "foobar")
    pytest.raises(InvalidTimeout, lock.acquire, blocking=True, timeout=-123)

    lock = Lock(conn, "foobar")
    pytest.raises(InvalidTimeout, lock.acquire, blocking=True, timeout=-1)
    pytest.raises(ValueError, lock.acquire, blocking=True, timeout="foobar")


def test_expire_int_conversion():
    conn = object()

    lock = Lock(conn, name='foobar', strict=False, expire=1)
    assert lock._expire == 1

    lock = Lock(conn, name='foobar', strict=False, expire=0)
    assert lock._expire is None

    lock = Lock(conn, name='foobar', strict=False, expire="1")
    assert lock._expire == 1

    lock = Lock(conn, name='foobar', strict=False, expire="123")
    assert lock._expire == 123


def test_expire(conn):
    lock = Lock(conn, "foobar", expire=TIMEOUT / 4)
    lock.acquire()
    with TestProcess(sys.executable, HELPER, 'test_expire') as proc:
        with dump_on_error(proc.read):
            name = 'lock:foobar'
            wait_for_strings(
                proc.read, TIMEOUT,
                'Getting %r ...' % name,
                'Got lock for %r.' % name,
                'Releasing %r.' % name,
                'DIED.',
            )
    lock = Lock(conn, "foobar")
    try:
        assert lock.acquire(blocking=False) is True
    finally:
        lock.release()


def test_expire_without_timeout(conn):
    first_lock = Lock(conn, 'expire', expire=2)
    second_lock = Lock(conn, 'expire', expire=1)
    first_lock.acquire()
    assert second_lock.acquire(blocking=False) is False
    assert second_lock.acquire() is True
    second_lock.release()


def test_extend(conn):
    name = 'foobar'
    key_name = 'lock:' + name
    with Lock(conn, name, expire=100) as lock:
        assert conn.ttl(key_name) <= 100

        lock.extend(expire=1000)
        assert conn.ttl(key_name) > 100


def test_extend_lock_default_expire(conn):
    name = 'foobar'
    key_name = 'lock:' + name
    with Lock(conn, name, expire=1000) as lock:
        time.sleep(3)
        assert conn.ttl(key_name) <= 997
        lock.extend()
        assert 997 < conn.ttl(key_name) <= 1000


def test_extend_lock_without_expire_fail(conn):
    name = 'foobar'
    with Lock(conn, name) as lock:
        with pytest.raises(NotExpirable):
            lock.extend(expire=1000)

        with pytest.raises(TypeError):
            lock.extend()


def test_extend_another_instance(conn):
    """It is possible to extend a lock using another instance of Lock with the
    same name.
    """
    name = 'foobar'
    key_name = 'lock:' + name
    lock = Lock(conn, name, expire=100)
    lock.acquire()
    assert 0 <= conn.ttl(key_name) <= 100

    another_lock = Lock(conn, name, id=lock.id)
    another_lock.extend(1000)

    assert conn.ttl(key_name) > 100


def test_extend_another_instance_different_id_fail(conn):
    """It is impossible to extend a lock using another instance of Lock with
    the same name, but different id.
    """
    name = 'foobar'
    key_name = 'lock:' + name
    lock = Lock(conn, name, expire=100)
    lock.acquire()
    assert 0 <= conn.ttl(key_name) <= 100

    another_lock = Lock(conn, name)
    with pytest.raises(NotAcquired):
        another_lock.extend(1000)

    assert conn.ttl(key_name) <= 100
    assert lock.id != another_lock.id


def test_double_acquire(conn):
    lock = Lock(conn, "foobar")
    with lock:
        pytest.raises(RuntimeError, lock.acquire)
        pytest.raises(AlreadyAcquired, lock.acquire)


def test_plain(conn):
    with Lock(conn, "foobar"):
        time.sleep(0.01)


def test_no_overlap(redis_server):
    """
    This test tries to simulate contention: lots of clients trying to acquire at the same time.

    If there would be a bug that would allow two clients to hold the lock at the same time it
    would most likely regress this test.

    The code here mostly tries to parse out the pid of the process and the time when it got and
    released the lock. If there's is overlap (eg: pid1.start < pid2.start < pid1.end) then we
    got a very bad regression on our hands ...

    The subprocess being run (check helper.py) will fork bunch of processes and will try to
    syncronize them (using the builting sched) to try to acquire the lock at the same time.
    """
    with TestProcess(sys.executable, HELPER, 'test_no_overlap') as proc:
        with dump_on_error(proc.read):
            name = 'lock:foobar'
            wait_for_strings(proc.read, 10 * TIMEOUT, 'Getting %r ...' % name)
            wait_for_strings(proc.read, 10 * TIMEOUT, 'Got lock for %r.' % name)
            wait_for_strings(proc.read, 10 * TIMEOUT, 'Releasing %r.' % name)
            wait_for_strings(proc.read, 10 * TIMEOUT, 'DIED.')

            class Event(object):
                pid = start = end = '?'

                def __str__(self):
                    return "Event(%s; %r => %r)" % (self.pid, self.start, self.end)

            events = defaultdict(Event)
            for line in proc.read().splitlines():
                try:
                    pid, time, junk = line.split(' ', 2)
                    pid = int(pid)
                except ValueError:
                    continue
                if 'Got lock for' in junk:
                    events[pid].pid = pid
                    events[pid].start = time
                if 'Releasing' in junk:
                    events[pid].pid = pid
                    events[pid].end = time
            assert len(events) == 125

            # not very smart but we don't have millions of events so it's
            # ok - compare all the events with all the other events:
            for event in events.values():
                for other in events.values():
                    if other is not event:
                        try:
                            if (
                                other.start < event.start < other.end or
                                other.start < event.end < other.end
                            ):
                                pytest.fail('%s overlaps %s' % (event, other))
                        except Exception:
                            print("[%s/%s]" % (event, other))
                            raise


NWORKERS = 125


@pytest.mark.skipif(platform.python_implementation() == 'PyPy', reason="This appears to be way too slow to run on PyPy")
def test_no_overlap2(make_process, make_conn):
    """The second version of contention test, that uses multiprocessing."""
    go = multiprocessing.Event()
    count_lock = multiprocessing.Lock()
    count = multiprocessing.Value('H', 0)

    def workerfn(go, count_lock, count):
        redis_lock = Lock(make_conn(), 'lock')
        with count_lock:
            count.value += 1

        go.wait()

        if redis_lock.acquire(blocking=True):
            with count_lock:
                count.value += 1

    for _ in range(NWORKERS):
        make_process(target=workerfn, args=(go, count_lock, count)).start()

    # Wait until all workers will come to point when they are ready to acquire
    # the redis lock.
    while count.value < NWORKERS:
        time.sleep(0.5)

    # Then "count" will be used as counter of workers, which acquired
    # redis-lock with success.
    count.value = 0

    go.set()

    time.sleep(1)

    assert count.value == 1


def test_reset(conn):
    lock = Lock(conn, "foobar")
    lock.reset()
    new_lock = Lock(conn, "foobar")
    new_lock.acquire(blocking=False)
    new_lock.release()
    pytest.raises(NotAcquired, lock.release)


def test_reset_all(conn):
    lock1 = Lock(conn, "foobar1")
    lock2 = Lock(conn, "foobar2")
    lock1.acquire(blocking=False)
    lock2.acquire(blocking=False)
    reset_all(conn)
    lock1 = Lock(conn, "foobar1")
    lock2 = Lock(conn, "foobar2")
    lock1.acquire(blocking=False)
    lock2.acquire(blocking=False)
    lock1.release()
    lock2.release()


def test_owner_id(conn):
    unique_identifier = "foobar-identifier"
    lock = Lock(conn, "foobar-tok", expire=TIMEOUT / 4, id=unique_identifier)
    lock_id = lock.id
    assert lock_id == unique_identifier


def test_get_owner_id(conn):
    lock = Lock(conn, "foobar-tok")
    lock.acquire()
    assert lock.get_owner_id() == lock.id
    lock.release()


def test_token(conn):
    lock = Lock(conn, "foobar-tok")
    tok = lock.id
    assert conn.get(lock._name) is None
    lock.acquire(blocking=False)
    assert maybe_decode(conn.get(lock._name)) == tok


def test_bogus_release(conn):
    lock = Lock(conn, "foobar-tok")
    pytest.raises(NotAcquired, lock.release)
    lock.acquire()
    lock2 = Lock(conn, "foobar-tok", id=lock.id)
    lock2.release()


def test_release_from_nonblocking_leaving_garbage(conn):
    for _ in range(10):
        lock = Lock(conn, 'release_from_nonblocking')
        lock.acquire(blocking=False)
        lock.release()
        assert conn.llen('lock-signal:release_from_nonblocking') == 1


def test_no_auto_renewal(conn):
    lock = Lock(conn, 'lock_renewal', expire=3, auto_renewal=False)
    assert lock._lock_renewal_interval is None
    lock.acquire()
    assert lock._lock_renewal_thread is None, "No lock refresh thread should have been spawned"


def test_auto_renewal_bad_values(conn):
    with pytest.raises(ValueError):
        Lock(conn, 'lock_renewal', expire=None, auto_renewal=True)


def test_auto_renewal(conn):
    lock = Lock(conn, 'lock_renewal', expire=3, auto_renewal=True)
    lock.acquire()

    assert isinstance(lock._lock_renewal_thread, threading.Thread)
    assert not lock._lock_renewal_stop.is_set()
    assert isinstance(lock._lock_renewal_interval, float)
    assert lock._lock_renewal_interval == 2

    time.sleep(3)
    assert maybe_decode(conn.get(lock._name)) == lock.id, "Key expired but it should have been getting renewed"

    lock.release()
    assert lock._lock_renewal_thread is None


@pytest.mark.parametrize('signal_expire', [1000, 1500])
@pytest.mark.parametrize('method', ['release', 'reset_all'])
def test_signal_expiration(conn, signal_expire, method):
    """Signal keys expire within two seconds after releasing the lock."""
    lock = Lock(conn, 'signal_expiration', signal_expire=signal_expire)
    lock.acquire()
    if method == 'release':
        lock.release()
    elif method == 'reset_all':
        reset_all(conn)
    time.sleep(0.5)
    assert conn.exists('lock-signal:signal_expiration')
    time.sleep((signal_expire - 500) / 1000.0)
    assert conn.llen('lock-signal:signal_expiration') == 0


def test_reset_signalizes(make_conn, make_process):
    """Call to reset() causes LPUSH to signal key, so blocked waiters
    become unblocked."""

    def workerfn(unblocked):
        conn = make_conn()
        lock = Lock(conn, 'lock')
        if lock.acquire():
            unblocked.value = 1

    unblocked = multiprocessing.Value('B', 0)
    conn = make_conn()
    lock = Lock(conn, 'lock')
    lock.acquire()

    worker = make_process(target=workerfn, args=(unblocked,))
    worker.start()
    worker.join(0.5)
    lock.reset()
    worker.join(0.5)

    assert unblocked.value == 1


def test_reset_all_signalizes(make_conn, make_process):
    """Call to reset_all() causes LPUSH to all signal keys, so blocked waiters
    become unblocked."""

    def workerfn(unblocked):
        conn = make_conn()
        lock1 = Lock(conn, 'lock1')
        lock2 = Lock(conn, 'lock2')
        if lock1.acquire() and lock2.acquire():
            unblocked.value = 1

    unblocked = multiprocessing.Value('B', 0)
    conn = make_conn()
    lock1 = Lock(conn, 'lock1')
    lock2 = Lock(conn, 'lock2')
    lock1.acquire()
    lock2.acquire()

    worker = make_process(target=workerfn, args=(unblocked,))
    worker.start()
    worker.join(0.5)
    reset_all(conn)
    worker.join(0.5)

    assert unblocked.value == 1


def test_auto_renewal_stops_after_gc(conn):
    """Auto renewal stops after lock is garbage collected."""
    lock = Lock(conn, 'spam', auto_renewal=True, expire=1)
    name = lock._name
    lock.acquire(blocking=True)
    lock_renewal_thread = lock._lock_renewal_thread
    del lock
    gc.collect()

    slept = 0
    interval = 0.1
    while slept <= 5:
        slept += interval
        lock_renewal_thread.join(interval)
        if not lock_renewal_thread.is_alive():
            break

    time.sleep(1.5)

    assert not lock_renewal_thread.is_alive()
    assert conn.get(name) is None


def test_given_id(conn):
    """It is possible to extend a lock using another instance of Lock with the
    same name.
    """
    name = 'foobar'
    key_name = 'lock:' + name
    orig = Lock(conn, name, expire=100, id=b"a")
    orig.acquire()
    pytest.raises(TypeError, Lock, conn, name, id=object())
    lock = Lock(conn, name, id=b"a")
    pytest.raises(AlreadyAcquired, lock.acquire)
    lock.extend(100)
    lock.release()  # this works, note that this ain't the object that acquired the lock
    pytest.raises(NotAcquired, orig.release)  # and this fails because lock was released above

    assert conn.ttl(key_name) == -2


def test_strict_check():
    pytest.raises(ValueError, Lock, object(), name='foobar')
    Lock(object(), name='foobar', strict=False)


def test_borken_expires():
    conn = object()
    pytest.raises(ValueError, Lock, redis_client=conn, name='foobar', expire=-1)
    pytest.raises(ValueError, Lock, redis_client=conn, name='foobar', expire=-123)
    pytest.raises(ValueError, Lock, redis_client=conn, name='foobar', expire="-1")
    lock = Lock(redis_client=conn, name='foobar', strict=False)
    pytest.raises(ValueError, lock.extend, expire=-1)
    pytest.raises(ValueError, lock.extend, expire=-123)
    pytest.raises(ValueError, lock.extend, expire="-1")


def test_locked_method(conn):
    lock_name = 'lock_name'

    lock = Lock(conn, lock_name, id='first')
    another_lock = Lock(conn, lock_name, id='another')

    assert lock.locked() is False
    assert another_lock.locked() is False

    assert lock.acquire() is True

    # another lock has same name and different id,
    # but method returns true
    assert lock.locked() is True
    assert another_lock.locked() is True
