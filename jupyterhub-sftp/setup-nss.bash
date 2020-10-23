#!/bin/bash
set -euo pipefail

# FIXME: Pin this
git clone --depth 1 https://github.com/donapieppo/libnss-ato
pushd libnss-ato

make
make install

popd
rm -rf libnss-ato
