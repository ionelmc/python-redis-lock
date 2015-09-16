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

Controlled execution lock::

    conn = StrictRedis()
    with redis_lock.Lock(conn, "name-of-the-lock"):
        print("Got the lock. Doing some work ...")
        time.sleep(5)
