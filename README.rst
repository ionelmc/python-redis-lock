===============================
redis-lock
===============================

| |docs| |travis| |appveyor| |coveralls| |landscape| |scrutinizer|
| |version| |downloads| |wheel| |supported-versions| |supported-implementations|

.. |docs| image:: https://readthedocs.org/projects/python-redis-lock/badge/?style=flat
    :target: https://readthedocs.org/projects/python-redis-lock
    :alt: Documentation Status

.. |travis| image:: http://img.shields.io/travis/ionelmc/python-redis-lock/master.png?style=flat
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/ionelmc/python-redis-lock

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/ionelmc/python-redis-lock?branch=master
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/ionelmc/python-redis-lock

.. |coveralls| image:: http://img.shields.io/coveralls/ionelmc/python-redis-lock/master.png?style=flat
    :alt: Coverage Status
    :target: https://coveralls.io/r/ionelmc/python-redis-lock

.. |landscape| image:: https://landscape.io/github/ionelmc/python-redis-lock/master/landscape.svg?style=flat
    :target: https://landscape.io/github/ionelmc/python-redis-lock/master
    :alt: Code Quality Status

.. |version| image:: http://img.shields.io/pypi/v/python-redis-lock.png?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |downloads| image:: http://img.shields.io/pypi/dm/python-redis-lock.png?style=flat
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |wheel| image:: https://pypip.in/wheel/python-redis-lock/badge.png?style=flat
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |supported-versions| image:: https://pypip.in/py_versions/python-redis-lock/badge.png?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |supported-implementations| image:: https://pypip.in/implementation/python-redis-lock/badge.png?style=flat
    :alt: Supported imlementations
    :target: https://pypi.python.org/pypi/python-redis-lock

.. |scrutinizer| image:: https://img.shields.io/scrutinizer/g/ionelmc/python-redis-lock/master.png?style=flat
    :alt: Scrtinizer Status
    :target: https://scrutinizer-ci.com/g/ionelmc/python-redis-lock/

An example package. Replace this with a proper project description. Generated with https://github.com/ionelmc/cookiecutter-pylibrary

* Free software: BSD license

Lock context manager implemented via redis SETNX/BLPOP.

Interface targeted to be exactly like `threading.Lock <http://docs.python.org/2/library/threading.html#threading.Lock>`_.

Usage
=====

Because we don't want to require users to share the lock instance across processes you will have to give them names. Eg::

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

Avoid dogpile effect in django
------------------------------

The dogpile is also known as the thundering herd effect or cache stampede. Here's a pattern to avoid the problem
without serving stale data. The work will be performed a single time and every client will wait for the fresh data.

To use this you will need `django-redis <https://github.com/niwibe/django-redis>`_, however, ``python-redis-lock``
provides you a cache backend that has a cache method for your convenience. Just install ``python-redis-lock`` like this::

    pip install "python-redis-lock[django]"

Now put something like this in your settings::

    CACHES = {
        'default': {
            'BACKEND': 'redis_lock.django_cache.RedisCache',
            'LOCATION': '127.0.0.1:6379',
            'OPTIONS': {
                'DB': 1
            }
        }
    }

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
------------------------------

In some cases, the lock remains in redis forever (like a server blackout / redis or application crash / an unhandled exception). In such cases, the lock is not removed by restarting the application. One solution is to use the ``reset()`` function when the application starts::

    # On application start/restart
    import redis_lock
    redis_lock.reset()


Use it carefully if you understand what you do.

Features
========

* based on the standard SETNX recipe
* optional expiry
* no spinloops at acquire

Implementation
==============

``redis_lock`` will use 2 keys for each lock named ``<name>``:

* ``lock:<name>`` - a string value for the actual lock
* ``lock-signal:<name>`` - a list value for signaling the waiters when the lock is released

This is how it works:

.. image:: https://raw.github.com/ionelmc/python-redis-lock/master/docs/redis-lock%20diagram.png
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
:Runtime: Python 2.6, 2.7, 3.2, 3.3 or PyPy
:Services: Redis 2.6.12 or later.

Similar projects
================

* `bbangert/retools <https://github.com/bbangert/retools/blob/master/retools/lock.py>`_ - acquire does spinloop
* `distributing-locking-python-and-redis <https://chris-lamb.co.uk/posts/distributing-locking-python-and-redis>`_ - acquire does polling
* `cezarsa/redis_lock <https://github.com/cezarsa/redis_lock/blob/master/redis_lock/__init__.py>`_ - acquire does not block
* `andymccurdy/redis-py <https://github.com/andymccurdy/redis-py/blob/master/redis/client.py#L2167>`_ - acquire does spinloop
* `mpessas/python-redis-lock <https://github.com/mpessas/python-redis-lock/blob/master/redislock/lock.py>`_ - blocks fine but no expiration