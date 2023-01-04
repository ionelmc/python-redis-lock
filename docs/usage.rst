=====
Usage
=====

To use redis-lock in a project::

    import redis_lock

Blocking lock::

    conn = StrictRedis()
    lock = redis_lock.Lock(conn, "name-of-the-lock"):
    if lock.acquire():
        print("Got the lock. Doing some work ...")
        time.sleep(5)

Blocking lock with timeout::

    conn = StrictRedis()
    lock = redis_lock.Lock(conn, "name-of-the-lock"):
    if lock.acquire(timeout=3):
        print("Got the lock. Doing some work ...")
        time.sleep(5)
    else:
        print("Someone else has the lock.")

Non-blocking lock::

    conn = StrictRedis()
    lock = redis_lock.Lock(conn, "name-of-the-lock"):
    if lock.acquire(blocking=False):
        print("Got the lock. Doing some work ...")
        time.sleep(5)
    else:
        print("Someone else has the lock.")

Releasing previously acquired lock::

    conn = StrictRedis()
    lock = redis_lock.Lock(conn, "name-of-the-lock")
    lock.acquire()
    print("Got the lock. Doing some work ...")
    time.sleep(5)
    lock.release()

The above example could be rewritten using context manager::

    conn = StrictRedis()
    with redis_lock.Lock(conn, "name-of-the-lock"):
        print("Got the lock. Doing some work ...")
        time.sleep(5)

You can pass `blocking=False` parameter to the contex manager (default value
is True, will raise a NotAcquired exception if lock won't be acquired)::

    conn = StrictRedis()
    with redis_lock.Lock(conn, "name-of-the-lock", blocking=False):
        print("Got the lock. Doing some work ...")
        time.sleep(5)

In cases, where lock not necessarily in acquired state, and
user need to ensure, that it has a matching ``id``, example::

    lock1 = Lock(conn, "foo")
    lock1.acquire()
    lock2 = Lock(conn, "foo", id=lock1.id)
    lock2.release()

To check if lock with same name is already locked
(it can be this or another lock with identical names)::

    is_locked = Lock(conn, "lock-name").locked()

You can control the log output by modifying various loggers::

    logging.getLogger("redis_lock.thread").disabled = True
    logging.getLogger("redis_lock").disable(logging.DEBUG)
