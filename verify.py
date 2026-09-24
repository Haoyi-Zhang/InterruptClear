#!/usr/bin/env python3
from pathlib import Path
import json,sys
from icnc.model import load_model
from icnc.certificate import strict_json_load,verify_certificate
if len(sys.argv)!=3:raise SystemExit('usage: verify.py MODEL CERTIFICATE')
m=load_model(sys.argv[1]);c=strict_json_load(sys.argv[2]);ok,msg=verify_certificate(m,c);print(msg);raise SystemExit(0 if ok else 1)
