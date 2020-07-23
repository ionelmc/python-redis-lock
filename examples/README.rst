Examples
========


Visual display of locks working
-------------------------------

Requirements: tmux, tox, redis-server

To run (make sure the redis server runs on the default port beforehand)::

    python ./examples/test-tmux.py LOCKNAME

This will open a tmux session with a bunch of panes, all waiting on the same lock.

After all the panes acquire the lock you can make the process/pane exit by pressing any key.

The result should be something like this: https://asciinema.org/a/DhfkKYMWg5IJLSL6LkRaDVwjc
