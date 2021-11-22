#!/bin/sh

set -e

TAG=$(date "+%S")
sed -E -i "" -e "s/TAG = '[[:digit:]]+'/TAG = '${TAG}'/g" ./rules.bzl
bazel build -j 1 --experimental_skylark_debug //:dbg-test
