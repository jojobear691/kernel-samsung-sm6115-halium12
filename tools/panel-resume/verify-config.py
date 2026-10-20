#!/usr/bin/env python3
"""Reject silent Kconfig drift when reproducing the tablet configuration."""
import pathlib
import re
import sys


def settings(path):
    result = {}
    for line in pathlib.Path(path).read_text().splitlines():
        match = re.fullmatch(r'(CONFIG_\w+)=(.*)', line)
        disabled = re.fullmatch(r'# (CONFIG_\w+) is not set', line)
        if match:
            result[match[1]] = match[2]
        elif disabled:
            result[disabled[1]] = 'n'
    return result


before, after = map(settings, sys.argv[1:])
changes = [(key, before.get(key), after.get(key))
           for key in sorted(before.keys() | after.keys())
           if before.get(key) != after.get(key)]
for key, old, new in changes:
    print(f'{key}: {old} -> {new}')
if changes:
    raise SystemExit('Configuration changed; review the public source match before building.')
print(f'PASS: all {len(before)} configuration settings match the running kernel.')
