#!/usr/bin/env python3
"""Replay one frontier certificate against a caller-supplied trusted model."""
from pathlib import Path
import argparse
import json
import sys
from icnc.checker import check, read, Rejected

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('model', type=Path)
    ap.add_argument('certificate', type=Path)
    args = ap.parse_args()
    counts = {}
    def charge(kind, amount=1):
        counts[kind] = counts.get(kind, 0) + amount
        if sum(counts.values()) > 100000:
            raise Rejected('checker work ceiling; no verdict')
    try:
        result = check(read(args.model), read(args.certificate), charge)
    except (ValueError, TypeError, KeyError, IndexError, OSError) as error:
        print(json.dumps({'accepted': False, 'reason': str(error)}))
        return 2
    print(json.dumps({'accepted': True, 'check': result, 'charged_obligations': counts}, sort_keys=True))
    return 0

if __name__ == '__main__':
    sys.exit(main())
