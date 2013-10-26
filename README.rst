=========================
    python-redis-lock
=========================

.. image:: https://secure.travis-ci.org/ionelmc/python-redis-lock.png?branch=master
    :alt: Build Status
    :target: http://travis-ci.org/ionelmc/python-redis-lock

.. image:: https://coveralls.io/repos/ionelmc/python-redis-lock/badge.png?branch=master
    :alt: Coverage Status
    :target: https://coveralls.io/r/ionelmc/python-redis-lock

.. image:: https://pypip.in/d/python-redis-lock/badge.png
    :alt: PYPI Package
    :target: https://pypi.python.org/pypi/python-redis-lock

.. image:: https://pypip.in/v/python-redis-lock/badge.png
    :alt: PYPI Package
    :target: https://pypi.python.org/pypi/python-redis-lock

Lock context manager implemented via redis SETNX/BLPOP.

Interface targeted to be exactly like `threading.Lock <docs.python.org/2/library/threading.html#threading.Lock>`_.

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

TODO
====

* ???

Requirements
============

Redis 2.6 or later.

Python 2.6, 2.7, 3.2, 3.3 and PyPy are supported.

Similar projects
================

* `bbangert/retools <https://github.com/bbangert/retools/blob/master/retools/lock.py>`_ - acquire does spinloop
* `distributing-locking-python-and-redis <https://chris-lamb.co.uk/posts/distributing-locking-python-and-redis>`_ - acquire does polling
* `cezarsa/redis_lock <https://github.com/cezarsa/redis_lock/blob/master/redis_lock/__init__.py>`_ - acquire does not block
* `andymccurdy/redis-py <https://github.com/andymccurdy/redis-py/blob/master/redis/client.py#L2167>`_ - acquire does spinloop
* `mpessas/python-redis-lock <https://github.com/mpessas/python-redis-lock/blob/master/redislock/lock.py>`_ - blocks fine but no expiration
