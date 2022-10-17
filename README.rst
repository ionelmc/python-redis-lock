========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |github-actions| |requires|
        | |coveralls| |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|
.. |docs| image:: https://readthedocs.org/projects/python-redis-lock/badge/?style=flat
    :target: https://python-redis-lock.readthedocs.io/
    :alt: Documentation Status

.. |github-actions| image:: https://github.com/ionelmc/python-redis-lock/actions/workflows/github-actions.yml/badge.svg
    :alt: GitHub Actions Build Status
    :target: https://github.com/ionelmc/python-redis-lock/actions

.. |requires| image:: https://requires.io/github/ionelmc/python-redis-lock/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/ionelmc/python-redis-lock/requirements/?branch=master

.. |coveralls| image:: https://coveralls.io/repos/ionelmc/python-redis-lock/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/ionelmc/python-redis-lock

.. |codecov| image:: https://codecov.io/gh/ionelmc/python-redis-lock/branch/master/graphs/badge.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/ionelmc/python-redis-lock

.. |version| image:: https://img.shields.io/pypi/v/python-redis-lock.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/python-redis-lock

.. |wheel| image:: https://img.shields.io/pypi/wheel/python-redis-lock.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/python-redis-lock

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/python-redis-lock.svg
    :alt: Supported versions
    :target: https://pypi.org/project/python-redis-lock

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/python-redis-lock.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/python-redis-lock

.. |commits-since| image:: https://img.shields.io/github/commits-since/ionelmc/python-redis-lock/v4.0.0.svg
    :alt: Commits since latest release
    :target: https://github.com/ionelmc/python-redis-lock/compare/v4.0.0...master



.. end-badges

Lock context manager implemented via redis SETNX/BLPOP.

* Free software: BSD 2-Clause License

Interface targeted to be exactly like `threading.Lock <https://docs.python.org/2/library/threading.html#threading.Lock>`_.

Usage
=====

Because we don't want to require users to share the lock instance across processes you will have to give them names.

.. code-block:: python

    from redis import Redis
    conn = Redis()

    import redis_lock
    lock = redis_lock.Lock(conn, "name-of-the-lock")
    if lock.acquire(blocking=False):
        print("Got the lock.")
        lock.release()
    else:
        print("Someone else has the lock.")

Locks as Context Managers
=========================

.. code-block:: python

    conn = StrictRedis()
    with redis_lock.Lock(conn, "name-of-the-lock"):
        print("Got the lock. Doing some work ...")
        time.sleep(5)


You can also associate an identifier along with the lock so that it can be retrieved later by the same process, or by a
different one. This is useful in cases where the application needs to identify the lock owner (find out who currently
owns the lock).

.. code-block:: python

    import socket
    host_id = "owned-by-%s" % socket.gethostname()
    lock = redis_lock.Lock(conn, "name-of-the-lock", id=host_id)
    if lock.acquire(blocking=False):
        assert lock.locked() is True
        print("Got the lock.")
        lock.release()
    else:
        if lock.get_owner_id() == host_id:
            print("I already acquired this in another process.")
        else:
            print("The lock is held on another machine.")


Avoid dogpile effect in django
------------------------------

The dogpile is also known as the thundering herd effect or cache stampede. Here's a pattern to avoid the problem
without serving stale data. The work will be performed a single time and every client will wait for the fresh data.

To use this you will need `django-redis <https://github.com/jazzband/django-redis>`_, however, ``python-redis-lock``
provides you a cache backend that has a cache method for your convenience. Just install ``python-redis-lock`` like
this:

.. code-block:: bash

    pip install "python-redis-lock[django]"

Now put something like this in your settings:

.. code-block:: python

    CACHES = {
        'default': {
            'BACKEND': 'redis_lock.django_cache.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient'
            }
        }
    }

.. note::
    If using a `django-redis` < `3.8.x`, you'll probably need `redis_cache`
    which has been deprecated in favor to `django_redis`. The `redis_cache`
    module is removed in `django-redis` versions > `3.9.x`. See `django-redis notes <https://github.com/jazzband/django-redis#configure-as-cache-backend>`_.


This backend just adds a convenient ``.lock(name, expire=None)`` function to django-redis's cache backend.

You would write your functions like this:

.. code-block:: python

    from django.core.cache import cache

    def function():
        val = cache.get(key)
        if not val:
            with cache.lock(key):
                val = cache.get(key)
                if not val:
                    # DO EXPENSIVE WORK
                    val = ...
                    cache.set(key, value)
        return val

Troubleshooting
---------------

In some cases, the lock remains in redis forever (like a server blackout / redis or application crash / an unhandled
exception). In such cases, the lock is not removed by restarting the application. One solution is to turn on the
`auto_renewal` parameter in combination with `expire` to set a time-out on the lock, but let `Lock()` automatically
keep resetting the expire time while your application code is executing:

.. code-block:: python

    # Get a lock with a 60-second lifetime but keep renewing it automatically
    # to ensure the lock is held for as long as the Python process is running.
    with redis_lock.Lock(conn, name='my-lock', expire=60, auto_renewal=True):
        # Do work....

Another solution is to use the ``reset_all()`` function when the application starts:

.. code-block:: python

    # On application start/restart
    import redis_lock
    redis_lock.reset_all()

Alternatively, you can reset individual locks via the ``reset`` method.

Use these carefully, if you understand what you do.


Features
========

* based on the standard SETNX recipe
* optional expiry
* optional timeout
* optional lock renewal (use a low expire but keep the lock active)
* no spinloops at acquire

Implementation
==============

``redis_lock`` will use 2 keys for each lock named ``<name>``:

* ``lock:<name>`` - a string value for the actual lock
* ``lock-signal:<name>`` - a list value for signaling the waiters when the lock is released

This is how it works:

.. image:: https://raw.githubusercontent.com/ionelmc/python-redis-lock/master/docs/redis-lock%20diagram%20(v3.0).png
    :alt: python-redis-lock flow diagram

Documentation
=============

https://python-redis-lock.readthedocs.io/en/latest/

Development
===========

To run the all tests run::

    tox

Requirements
============

:OS: Any
:Runtime: Python 2.7, 3.3 or later, or PyPy
:Services: Redis 2.6.12 or later.

Similar projects
================

* `bbangert/retools <https://github.com/bbangert/retools/blob/0.4/retools/lock.py>`_ - acquire does spinloop
* `distributing-locking-python-and-redis <https://chris-lamb.co.uk/posts/distributing-locking-python-and-redis>`_ - acquire does polling
* `cezarsa/redis_lock <https://github.com/cezarsa/redis_lock/blob/0.2.0/redis_lock/__init__.py>`_ - acquire does not block
* `andymccurdy/redis-py <https://github.com/andymccurdy/redis-py/blob/3.5.3/redis/lock.py>`_ - acquire does spinloop
* `mpessas/python-redis-lock <https://github.com/mpessas/python-redis-lock/blob/b512eef0fc5e1e2e82a6a31f65cd88c2c37dfe4b/redislock/lock.py>`_ - blocks fine but no expiration
* `brainix/pottery <https://github.com/brainix/pottery/blob/v1.1.5/pottery/redlock.py>`_ - acquire does spinloop
