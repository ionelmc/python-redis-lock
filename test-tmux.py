#!/usr/bin/env python
import sys
import subprocess

left_commands = [
    ".ve/bin/python -u src/redis_lock.py %s" % sys.argv[1],
    ".ve/bin/python -u src/redis_lock.py %s" % sys.argv[1],
    ".ve/bin/python -u src/redis_lock.py %s" % sys.argv[1],
    ".ve/bin/python -u src/redis_lock.py %s" % sys.argv[1],
    ".ve/bin/python -u src/redis_lock.py %s" % sys.argv[1],
    ".ve/bin/python -u src/redis_lock.py %s" % sys.argv[1],
    ".ve/bin/python -u src/redis_lock.py %s" % sys.argv[1],
    ".ve/bin/python -u src/redis_lock.py %s" % sys.argv[1],
    ".ve/bin/python -u src/redis_lock.py %s" % sys.argv[1],
]
right_commands = [
]
session = ''

if right_commands:
    session += 'tmux selectp -t 0; tmux splitw -hd -p 35 \"%s\"; ' % right_commands[-1]
for index, command in enumerate(right_commands[:-1]):
    session += 'tmux selectp -t 1; tmux splitw -d -p %i \"%s\"; ' % (
        100 / (len(right_commands) - index),
        command
    )

for index, command in enumerate(left_commands[1:]):
    session += 'tmux selectp -t 0; tmux splitw -d -p %i \"%s\"; ' % (
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
print 'Running ', args
subprocess.call(args)
