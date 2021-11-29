#!/bin/sh

set -e

TAG=$(date "+%S")
sed -E -e "s/TAG = '[[:digit:]]+'/TAG = '${TAG}'/g" ./_rules.bzl > ./rules.bzl
bazel build -j 1 --experimental_skylark_debug //:dbg-test
