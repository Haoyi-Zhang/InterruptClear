#!/usr/bin/env python3
"""Check a certificate, then select all least-cost plans at a smaller budget."""
from pathlib import Path
import argparse
import json
from icnc.checker import check, read
from icnc.frontier import Meter, synthesize
from icnc.model import parse

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('model', type=Path)
    ap.add_argument('certificate', type=Path)
    ap.add_argument('--cap', type=int, nargs=3, metavar=('EVENTS','DELIVERIES','DEPTH'))
    args = ap.parse_args()
    try:
        raw = read(args.model)
        model = parse(raw)
        certificate = read(args.certificate)
        check(raw, certificate, Meter(100000).charge)
        cap = model.cap if args.cap is None else tuple(args.cap)
        if len(cap) != 3 or any(type(x) is not int or not 0 <= x <= maximum for x, maximum in zip(cap, model.cap)):
            raise ValueError('query must be componentwise within the construction cap')
        result = synthesize(model, tuple(tuple(row) for row in certificate['frontier']), cap)
        result['named_optimal_plans'] = [[name for i, (name, _) in enumerate(model.atoms) if mask & (1 << i)] for mask in result['optimal_plans']]
        print(json.dumps({'checked': True, 'cap': cap, **result}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'checked': False, 'reason': str(error)}))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
