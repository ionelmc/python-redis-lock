========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |requires|
        | |coveralls| |codecov|
        | |landscape| |scrutinizer| |codacy| |codeclimate|
    * - package
      - |version| |downloads| |wheel| |supported-versions| |supported-implementations|

.. |docs| image:: https://readthedocs.org/projects/python-redis-lock/badge/?style=flat
    :target: https://readthedocs.org/projects/python-redis-lock
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/ionelmc/python-redis-lock.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/ionelmc/python-redis-lock

.. |requires| image:: https://requires.io/github/ionelmc/python-redis-lock/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/ionelmc/python-redis-lock/requirements/?branch=master

.. |coveralls| image:: https://coveralls.io/repos/ionelmc/python-redis-lock/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/ionelmc/python-redis-lock

.. |codecov| image:: https://codecov.io/github/ionelmc/python-redis-lock/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/ionelmc/python-redis-lock

.. |landscape| image:: https://landscape.io/github/ionelmc/python-redis-lock/master/landscape.svg?style=flat
    :target: https://landscape.io/github/ionelmc/python-redis-lock/master
    :alt: Code Quality Status

.. |codacy| image:: https://img.shields.io/codacy/REPLACE_WITH_PROJECT_ID.svg?style=flat
    :target: https://www.codacy.com/app/ionelmc/python-redis-lock
    :alt: Codacy Code Quality Status

.. |codeclimate| image:: https://codeclimate.com/github/ionelmc/python-redis-lock/badges/gpa.svg
   :target: https://codeclimate.com/github/ionelmc/python-redis-lock
   :alt: CodeClimate Quality Status

.. |version| image:: https://img.shields.io/pypi/v/python-redis-lock.svg?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |downloads| image:: https://img.shields.io/pypi/dm/python-redis-lock.svg?style=flat
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |wheel| image:: https://img.shields.io/pypi/wheel/python-redis-lock.svg?style=flat
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/python-redis-lock.svg?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/python-redis-lock.svg?style=flat
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |scrutinizer| image:: https://img.shields.io/scrutinizer/g/ionelmc/python-redis-lock/master.svg?style=flat
    :alt: Scrutinizer Status
    :target: https://scrutinizer-ci.com/g/ionelmc/python-redis-lock/


.. end-badges

Lock context manager implemented via redis SETNX/BLPOP.

* Free software: BSD license

Interface targeted to be exactly like `threading.Lock <http://docs.python.org/2/library/threading.html#threading.Lock>`_.

Usage
=====

Because we don't want to require users to share the lock instance across processes you will have to give them names.
Eg::

    conn = StrictRedis()
    with redis_lock.Lock(conn, "name-of-the-lock"):
        print("Got the lock. Doing some work ...")
        time.sleep(5)

Eg::

    lock = redis_lock.Lock(conn, "name-of-the-lock")
    if lock.acquire(blocking=False):
        print("Got the lock.")
    else:
        print("Someone else has the lock.")


You can also associate an identifier along with the lock so that it can be retrieved later by the same process, or by a
different one. This is useful in cases where the application needs to identify the lock owner (find out who currently
owns the lock). Eg::

    import socket
    host_id = "owned-by-%s" % socket.gethostname()
    lock = redis_lock.Lock(conn, "name-of-the-lock", id=host_id)
    if lock.acquire(blocking=False):
        print("Got the lock.")
    else:
        if lock.get_owner_id() == host_id:
            print("I already acquired this in another process.")
        else:
            print("The lock is held on another machine.")


Avoid dogpile effect in django
------------------------------

The dogpile is also known as the thundering herd effect or cache stampede. Here's a pattern to avoid the problem
without serving stale data. The work will be performed a single time and every client will wait for the fresh data.

To use this you will need `django-redis <https://github.com/niwibe/django-redis>`_, however, ``python-redis-lock``
provides you a cache backend that has a cache method for your convenience. Just install ``python-redis-lock`` like
this::

    pip install "python-redis-lock[django]"

Now put something like this in your settings::

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
    module is removed in `django-redis` versions > `3.9.x`. See `django-redis notes <http://niwinz.github.io/django-redis/latest/#_configure_as_cache_backend>`_.


This backend just adds a convenient ``.lock(name, expire=None)`` function to django-redis's cache backend.

You would write your functions like this::

    from django.core.cache import cache

    def function():
        val = cache.get(key)
        if val:
            return val
        else:
            with cache.lock(key):
                val = cache.get(key)
                if val:
                    return val
                else:
                    # DO EXPENSIVE WORK
                    val = ...

                    cache.set(key, value)
                    return val


Troubleshooting
---------------

In some cases, the lock remains in redis forever (like a server blackout / redis or application crash / an unhandled
exception). In such cases, the lock is not removed by restarting the application. One solution is to turn on the
`auto_renewal` parameter in combination with `expire` to set a time-out on the lock, but let `Lock()` automatically
keep resetting the expire time while your application code is executing::

    # Get a lock with a 60-second lifetime but keep renewing it automatically
    # to ensure the lock is held for as long as the Python process is running.
    with redis_lock.Lock('my-lock', expire=60, auto_renewal=True):
        # Do work....

Another solution is to use the ``reset_all()`` function when the application starts::

    # On application start/restart
    import redis_lock
    redis_lock.reset_all()

Alternativelly, you can reset individual locks via the ``reset`` method.

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

.. image:: https://raw.github.com/ionelmc/python-redis-lock/master/docs/redis-lock%20diagram%20(v3.0).png
    :alt: python-redis-lock flow diagram

Documentation
=============

https://python-redis-lock.readthedocs.org/

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

* `bbangert/retools <https://github.com/bbangert/retools/blob/master/retools/lock.py>`_ - acquire does spinloop
* `distributing-locking-python-and-redis <https://chris-lamb.co.uk/posts/distributing-locking-python-and-redis>`_ - acquire does polling
* `cezarsa/redis_lock <https://github.com/cezarsa/redis_lock/blob/master/redis_lock/__init__.py>`_ - acquire does not block
* `andymccurdy/redis-py <https://github.com/andymccurdy/redis-py/blob/master/redis/client.py#L2167>`_ - acquire does spinloop
* `mpessas/python-redis-lock <https://github.com/mpessas/python-redis-lock/blob/master/redislock/lock.py>`_ - blocks fine but no expiration
