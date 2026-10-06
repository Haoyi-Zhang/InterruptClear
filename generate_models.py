#!/usr/bin/env python3
"""Generate the twelve fixed models without running scientific analysis."""
from pathlib import Path
import argparse
import json
from icnc.examples import fixed
from icnc.model import parse

ROOT = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT / 'models')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    models = fixed()
    for model in models:
        path = args.output / (model.name + '.json')
        raw = model.raw()
        if parse(raw) != model:
            raise RuntimeError('canonical model round trip')
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'generated_fixed_models': len(models)}))

if __name__ == '__main__':
    main()
