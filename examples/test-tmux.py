#!/usr/bin/env python
import subprocess
import sys

subprocess.check_call("tox -e py38-dj3-nocov --notest".split())

left_commands = [
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
    ".tox/py38-dj3-nocov/bin/python examples/plain.py %s" % sys.argv[1],
]
right_commands = left_commands
session = ''

if right_commands:
    session += 'tmux selectp -t0;tmux splitw -hd -p50 \"%s\"; ' % right_commands[-1]
for index, command in enumerate(right_commands[:-1]):
    session += 'tmux selectp -t1;tmux splitw -d -p%i \"%s\"; ' % (
        100 / (len(right_commands) - index),
        command
    )

for index, command in enumerate(left_commands[1:]):
    session += 'tmux selectp -t0;tmux splitw -d -p%i \"%s\"; ' % (
        100 / (len(left_commands) - index),
        command
    )
if left_commands:
    session += left_commands[0]

args = [
    'tmux',
    'new-session',
    session,
]
print('Running ', args)
subprocess.call(args)
