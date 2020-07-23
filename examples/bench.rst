Benchmarks
==========

Easy way to run it locally, provides you have a redis server running on default port::

    tox -e py38-dj3-cover -- python examples/bench.py 10

Note that the database will lose all it's data. The benchmark will keep using a lock in a loop till 10 seconds elapse with various settings.
The concurrency is the number of processes that will try to acquire the same log and the lock duration is an artificial time slept before
releasing.

My local run with version 3.6.0 of redis-lock:

============== ============= =========== ========= ========== ========== ========== ==========
Implementation Lock duration Concurrency Acquires: Total      Avg        Min        Max
============== ============= =========== ========= ========== ========== ========== ==========
    redis_lock        0.000s           1                26296
        native        0.000s           1                35605
    redis_lock        0.010s           1                  931
        native        0.010s           1                  945
    redis_lock        0.500s           1                   20
        native        0.500s           1                   20
    redis_lock        0.000s           2                35477   17738.50      17661      17816
        native        0.000s           2                34861   17430.50      13930      20931
    redis_lock        0.010s           2                  940     470.00        470        470
        native        0.010s           2                  942     471.00        461        481
    redis_lock        0.500s           2                   20      10.00         10         10
        native        0.500s           2                   20      10.00          0         20
    redis_lock        0.000s           3                46123   15374.33      15291      15437
        native        0.000s           3                35285   11761.67       7759      14038
    redis_lock        0.010s           3                  943     314.33        314        315
        native        0.010s           3                  944     314.67          0        776
    redis_lock        0.500s           3                   20       6.67          6          7
        native        0.500s           3                   20       6.67          0         20
    redis_lock        0.000s           6                42249    7041.50       6863       7170
        native        0.000s           6                33852    5642.00       4488       6864
    redis_lock        0.010s           6                  942     157.00        157        157
        native        0.010s           6                  945     157.50         19        275
    redis_lock        0.500s           6                   20       3.33          3          4
        native        0.500s           6                   20       3.33          0         20
    redis_lock        0.000s          12                42506    3542.17       3206       3819
        native        0.000s          12                34203    2850.25       1748       4492
    redis_lock        0.010s          12                  942      78.50         77         79
        native        0.010s          12                  944      78.67          0        332
    redis_lock        0.500s          12                   20       1.67          1          2
        native        0.500s          12                   20       1.67          0         20
    redis_lock        0.000s          24                42192    1758.00       1603       1893
        native        0.000s          24                34925    1455.21        681       2402
    redis_lock        0.010s          24                  944      39.33         39         40
        native        0.010s          24                  945      39.38          0        256
    redis_lock        0.500s          24                   20       0.83          0          1
        native        0.500s          24                   20       0.83          0         20
    redis_lock        0.000s          48                44867     934.73        768       1172
        native        0.000s          48                34961     728.35        311       1399
    redis_lock        0.010s          48                  943      19.65         19         20
        native        0.010s          48                  942      19.62          0        254
    redis_lock        0.500s          48                   20       0.42          0          1
        native        0.500s          48                   20       0.42          0         20
============== ============= =========== ========= ========== ========== ========== ==========

Key takeaways:

* For a single client (no contention) redis-lock is a little bit slower. In the past it was faster but various fixes added a little bit of
  overhead in the lock releasing script. Note the ``Total`` column.
* When two clients are involved things change a lot:

  * The native implementation will loose throughput because the acquiring routine basically does ``while True: sleep(0.1)``.
    Note the ``Total`` column.
  * The native implementation favours the first client (it will get most of the acquires because the waiting client simply sleeps a lot).
    Note the ``Min`` column.

* When either concurrency (number of clients) or duration (amount of time slept while lock is acquired) are high for the native
  implementation things get very wild:

  * Some clients never get to acquire the lock.
    Note the ``Min`` column being ``0`` and the ``Max`` column being very high (indicating how many acquires a single client got).

