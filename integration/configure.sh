#!/usr/bin/env bash
set -euo pipefail
source_dir=${1:?kernel source directory}
repo_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$source_dir"
test "$(git rev-parse HEAD)" = 0970a5d23405622c10bc4ff60ef0ba30499611e1
test "$(git -C KernelSU-Next rev-parse HEAD)" = 8f902aeb16033024143ae36cf711df902cf02fae
git apply --check "$repo_dir/integration/los-4.19-policy-lock.patch"
git apply "$repo_dir/integration/los-4.19-policy-lock.patch"
git -C KernelSU-Next apply --check "$repo_dir/integration/ksun-v3.4.1-los-4.19.patch"
git -C KernelSU-Next apply "$repo_dir/integration/ksun-v3.4.1-los-4.19.patch"
ln -s ../KernelSU-Next/kernel drivers/kernelsu
printf '\nsource "drivers/kernelsu/Kconfig"\n' >> drivers/Kconfig
printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> drivers/Makefile
mkdir -p out
cp "$repo_dir/configs/los-stock.config" out/.config
scripts/kconfig/merge_config.sh -m -O out out/.config "$repo_dir/configs/docker-ksun.config"
make O=out ARCH=arm64 CC=clang olddefconfig
python3 "$repo_dir/integration/verify_config.py" out/.config
