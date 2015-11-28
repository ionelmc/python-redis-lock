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

In cases, where lock not necessarily in acquired state, and
user need to ensure, that it's released, ``force`` parameter could be used::

    lock = Lock(conn, "foo")
    try:
      if lock.acquire(block=False):
        print("Got the lock. Do crazy dance")
      else:
        print("Didn't get the lock. Do normal dance")
    finally:
      lock.release(force=True)
