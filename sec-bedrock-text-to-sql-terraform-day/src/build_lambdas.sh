#!/usr/bin/env bash

set -euo pipefail

rm -rf build
mkdir -p build/basic
mkdir -p build/complex
mkdir -p build/router

echo "Building Basic Query Lambda..."

python -m pip install \
  -r lambda_src/basic/requirements.txt \
  -t build/basic

cp lambda_src/basic/handler.py \
   build/basic/handler.py

cp lambda_src/basic/sql_validator.py \
   build/basic/sql_validator.py

cp lambda_src/common/redshift_executor.py \
   build/basic/redshift_executor.py

(
  cd build/basic
  zip -qr ../basic-query.zip .
)

echo "Building Complex Query Lambda..."

cp lambda_src/complex/handler.py \
   build/complex/handler.py

cp lambda_src/complex/parameter_validator.py \
   build/complex/parameter_validator.py

cp lambda_src/complex/template_registry.py \
   build/complex/template_registry.py

cp lambda_src/common/redshift_executor.py \
   build/complex/redshift_executor.py

(
  cd build/complex
  zip -qr ../complex-query.zip .
)

echo "Building Router Lambda..."

cp lambda_src/router/handler.py \
   build/router/handler.py

(
  cd build/router
  zip -qr ../router.zip .
)

echo "Lambda packages created:"
ls -lh build/*.zip