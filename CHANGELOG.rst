
Changelog
=========

4.0.0 (2022-10-17)
------------------

* Dropped support for Python 2.7 and 3.6.
* Switched from Travis to GitHub Actions.
* Made logging messages more consistent.
* Replaced the ``redis_lock.refresh.thread.*`` loggers with a single ``redis_lock.refresh.thread`` logger.
* Various testing cleanup (mainly removal of hardcoded tmp paths).

3.7.0 (2020-11-20)
------------------

* Made logger names more specific. Now can have granular filtering on these new logger names:

  * ``redis_lock.acquire`` (emits `DEBUG` messages)
  * ``redis_lock.acquire`` (emits `WARN` messages)
  * ``redis_lock.acquire`` (emits `INFO` messages)
  * ``redis_lock.refresh.thread.start`` (emits `DEBUG` messages)
  * ``redis_lock.refresh.thread.exit`` (emits `DEBUG` messages)
  * ``redis_lock.refresh.start`` (emits `DEBUG` messages)
  * ``redis_lock.refresh.shutdown`` (emits `DEBUG` messages)
  * ``redis_lock.refresh.exit`` (emits `DEBUG` messages)
  * ``redis_lock.release`` (emits `DEBUG` messages)

  Contributed by Salomon Smeke Cohen in :pr:`80`.
* Fixed few CI issues regarding doc checks.
  Contributed by Salomon Smeke Cohen in :pr:`81`.

3.6.0 (2020-07-23)
------------------

* Improved ``timeout``/``expire`` validation so that:

  - ``timeout`` and ``expire are converted to ``None`` if they are falsy. Previously only ``None`` disabled these options, other falsy
    values created buggy situations.
  - Using ``timeout`` greater than ``expire`` is now allowed, if ``auto_renewal`` is set to ``True``. Previously a ``TimeoutTooLarge`` error
    was raised.
    See :issue:`74`.
  - Negative ``timeout`` or ``expire`` are disallowed. Previously such values were allowed, and created buggy situations.
    See :issue:`73`.
* Updated benchmark and examples.
* Removed the custom script caching code. Now the ``register_script`` method from the redis client is used.
  This will fix possible issue with redis clusters in theory, as the redis client has some specific handling for that.

3.5.0 (2020-01-13)
------------------

* Added a ``locked`` method. Contributed by Artem Slobodkin in :pr:`72`.

3.4.0 (2019-12-06)
------------------

* Fixed regression that can cause deadlocks or slowdowns in certain configurations.
  See: :issue:`71`.

3.3.1 (2019-01-19)
------------------

* Fixed failures when running python-redis-lock 3.3 alongside 3.2.
  See: :issue:`64`.

3.3.0 (2019-01-17)
------------------

* Fixed deprecated use of ``warnings`` API. Contributed by Julie MacDonell in
  :pr:`54`.
* Added ``auto_renewal`` option in ``RedisCache.lock`` (the Django cache backend wrapper). Contributed by c
  in :pr:`55`.
* Changed log level for "%(script)s not cached" from WARNING to INFO.
* Added support for using ``decode_responses=True``. Lock keys are pure ascii now.

3.2.0 (2016-10-29)
------------------

* Changed the signal key cleanup operation do be done without any expires. This prevents lingering keys around for some time.
  Contributed by Andrew Pashkin in :pr:`38`.
* Allow locks with given `id` to acquire. Previously it assumed that if you specify the `id` then the lock was already
  acquired. See :issue:`44` and
  :issue:`39`.
* Allow using other redis clients with a ``strict=False``. Normally you're expected to pass in an instance
  of ``redis.StrictRedis``.
* Added convenience method `locked_get_or_set` to Django cache backend.

3.1.0 (2016-04-16)
------------------

* Changed the auto renewal to automatically stop the renewal thread if lock gets garbage collected. Contributed by
  Andrew Pashkin in :pr:`33`.

3.0.0 (2016-01-16)
------------------

* Changed ``release`` so that it expires signal-keys immediately. Contributed by Andrew Pashkin in :pr:`28`.
* Resetting locks (``reset`` or ``reset_all``) will release the lock. If there's someone waiting on the reset lock now it will
  acquire it. Contributed by Andrew Pashkin in :pr:`29`.
* Added the ``extend`` method on ``Lock`` objects. Contributed by Andrew Pashkin in :pr:`24`.
* Documentation improvements on ``release`` method. Contributed by Andrew Pashkin in :pr:`22`.
* Fixed ``acquire(block=True)`` handling when ``expire`` option was used (it wasn't blocking indefinitely). Contributed by
  Tero Vuotila in :pr:`35`.
* Changed ``release`` to check if lock was acquired with he same id. If not, ``NotAcquired`` will be raised.
  Previously there was just a check if it was acquired with the same instance (self._held).
  **BACKWARDS INCOMPATIBLE**
* Removed the ``force`` option from ``release`` - it wasn't really necessary and it only encourages sloppy programming. See
  :issue:`25`.
  **BACKWARDS INCOMPATIBLE**
* Dropped tests for Python 2.6. It may work but it is unsupported.

2.3.0 (2015-09-27)
------------------

* Added the ``timeout`` option. Contributed by Victor Torres in :pr:`20`.

2.2.0 (2015-08-19)
------------------

* Added the ``auto_renewal`` option. Contributed by Nick Groenen in :pr:`18`.

2.1.0 (2015-03-12)
------------------

* New specific exception classes: ``AlreadyAcquired`` and ``NotAcquired``.
* Slightly improved efficiency when non-waiting acquires are used.

2.0.0 (2014-12-29)
------------------

* Rename ``Lock.token`` to ``Lock.id``. Now only allowed to be set via constructor. Contributed by Jardel Weyrich in :pr:`11`.

1.0.0 (2014-12-23)
------------------

* Fix Django integration. (reported by Jardel Weyrich)
* Reorganize tests to use py.test.
* Add test for Django integration.
* Add ``reset_all`` functionality. Contributed by Yokotoka in :pr:`7`.
* Add ``Lock.reset`` functionality.
* Expose the ``Lock.token`` attribute.

0.1.2 (2013-11-05)
------------------

* `?`

0.1.1 (2013-10-26)
------------------

* `?`

0.1.0 (2013-10-26)
------------------

* `?`

0.0.1 (2013-10-25)
------------------

* First release on PyPI.
