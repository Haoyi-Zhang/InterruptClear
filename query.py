#!/usr/bin/env python3
"""Check a certificate, then select all least-cost plans at a smaller budget."""
from pathlib import Path
import argparse
import json
from icnc.checker import check, read
from icnc.frontier import Meter, synthesize
from icnc.model import parse, query_cap, installation_weights

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('model', type=Path)
    ap.add_argument('certificate', type=Path)
    ap.add_argument('--cap', type=int, nargs=3, metavar=('EVENTS','DELIVERIES','DEPTH'))
    ap.add_argument('--weights', type=Path, help='query-only JSON object of all existing atom prices (integers 0..256)')
    args = ap.parse_args()
    try:
        raw = read(args.model)
        model = parse(raw)
        certificate = read(args.certificate)
        check(raw, certificate, Meter(100000).charge)
        cap = query_cap(model.cap if args.cap is None else args.cap, model.cap)
        weights = None if args.weights is None else read(args.weights, limit=65536)
        prices = installation_weights(model, weights)
        result = synthesize(model, tuple(tuple(row) for row in certificate['frontier']), cap, weights=weights)
        result['named_optimal_plans'] = [[name for i, (name, _) in enumerate(model.atoms) if mask & (1 << i)] for mask in result['optimal_plans']]
        print(json.dumps({'checked': True, 'cap': cap,
                          'installation_weights': dict(zip((a for a,_ in model.atoms), prices)),
                          'weights_scope': 'query-only objective; trusted model, offered clears and certificate unchanged',
                          **result}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'checked': False, 'reason': str(error)}))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
