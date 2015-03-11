
Changelog
=========

2.1.0 (2015-03-12)
------------------

* New specific exception classes: ``AlreadyAcquired`` and ``NotAcquired``.
* Slightly improved efficiency when non-waiting acquires are used.

2.0.0 (2014-12-29)
------------------

* Rename ``Lock.token`` to ``Lock.id``. Now only allowed to be set via constructor. (contributed by Jardel Weyrich)

1.0.0 (2014-12-23)
------------------

* Fix Django integration. (reported by Jardel Weyrich)
* Reorganize tests to use py.test.
* Add test for Django integration.
* Add ``reset_all`` functionality. (contributed by Yokotoka)
* Add ``Lock.reset`` functionality.
* Expose the ``Lock.token`` attribute.

0.1.2 (2013-11-05)
------------------

* ?

0.1.1 (2013-10-26)
------------------

* ?

0.1.0 (2013-10-26)
------------------

* ?

0.0.1 (2013-10-25)
------------------

* First release on PyPI.
