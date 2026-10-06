#!/bin/sh
set -eu
cd "$(dirname "$0")"
sh ./verify.sh
(cd ../paper && sh ./build.sh)
