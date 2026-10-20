#!/usr/bin/env bash
# Build-only experiment. This script never contacts or modifies a device.
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"
if ! git diff --quiet HEAD --; then
    echo 'Refusing to build with uncommitted tracked source changes.' >&2
    exit 1
fi
input="$root/tools/panel-resume"
build_root=${PANEL_BUILD_ROOT:-"$root/../panel-resume-build"}
mkdir -p "$build_root" "$root/panel-artifacts"
build_root=$(realpath "$build_root")
artifacts="$root/panel-artifacts"
clang_rev=08a599bf1eb61163577487592663c15a2fc64c5d
gcc_rev=e9c7c9eb5c3ab5d4f1f09b3ce97498fc59c3bdcd
base=c058c8a0930d4352eaa96a172f83515077e9ea62

checkout_pinned() {
    local directory=$1 url=$2 revision=$3 sparse=${4:-}
    # A fresh directory avoids accidentally using unrelated local toolchains.
    if [[ -e "$directory" ]]; then
        echo "Refusing to reuse existing toolchain directory: $directory" >&2
        return 1
    fi
    git init -q "$directory"
    git -C "$directory" remote add origin "$url"
    git -C "$directory" config remote.origin.promisor true
    git -C "$directory" config remote.origin.partialclonefilter blob:none
    if [[ -n "$sparse" ]]; then
        git -C "$directory" sparse-checkout init --cone
        git -C "$directory" sparse-checkout set "$sparse"
    fi
    git -C "$directory" fetch --depth=1 --filter=blob:none origin "$revision"
    git -C "$directory" checkout -q --detach FETCH_HEAD
    [[ $(git -C "$directory" rev-parse HEAD) == "$revision" ]]
}

git merge-base --is-ancestor "$base" HEAD
git show "$base:drivers/input/touchscreen/hxchipset/himax_platform.c" > "$artifacts/himax_platform.original.c"
set +e
python3 "$input/test_resume_order.py" "$artifacts/himax_platform.original.c" > "$artifacts/test-original.log" 2>&1
baseline_rc=$?
set -e
cat "$artifacts/test-original.log"
[[ $baseline_rc == 1 ]]
[[ $(grep -c '^FAIL ' "$artifacts/test-original.log") == 2 ]]
[[ $(grep -c '^PASS ' "$artifacts/test-original.log") == 2 ]]
python3 "$input/test_resume_order.py" drivers/input/touchscreen/hxchipset/himax_platform.c | tee "$artifacts/test-candidate.log"

checkout_pinned "$build_root/clang" \
    https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86 \
    "$clang_rev" clang-r416183b
checkout_pinned "$build_root/gcc" \
    https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9 \
    "$gcc_rev"
export PATH="$build_root/clang/clang-r416183b/bin:$build_root/gcc/bin:$PATH"
clang --version | tee "$artifacts/compiler.txt"
grep -F 'Android (7284624, based on r416183b) clang version 12.0.5' "$artifacts/compiler.txt"
aarch64-linux-android-ld --version | tee "$artifacts/linker.txt"
grep -E 'GNU ld.*2\.27' "$artifacts/linker.txt"

out="$build_root/out"
mkdir "$out"
cp "$input/running.config" "$out/.config"
make_args=(O="$out" ARCH=arm64 CC=clang HOSTCC=gcc HOSTCXX=g++
    CROSS_COMPILE=aarch64-linux-android- CLANG_TRIPLE=aarch64-linux-gnu-
    LOCALVERSION=+ KBUILD_BUILD_USER=panel-test KBUILD_BUILD_HOST=github-actions)
make "${make_args[@]}" olddefconfig 2>&1 | tee "$artifacts/configure.log"
cp "$out/.config" "$artifacts/resolved.config"
scripts/diffconfig "$input/running.config" "$out/.config" | tee "$artifacts/config-diff.txt"
python3 "$input/verify-config.py" "$input/running.config" "$out/.config"
release=$(make -s "${make_args[@]}" kernelrelease)
printf '%s\n' "$release" | tee "$artifacts/kernelrelease.txt"
[[ "$release" == '4.19.300-perf+' ]]
make -j"${PANEL_BUILD_JOBS:-2}" "${make_args[@]}" \
    drivers/input/touchscreen/hxchipset/himax_platform.o 2>&1 | tee "$artifacts/driver-build.log"
make -j"${PANEL_BUILD_JOBS:-2}" "${make_args[@]}" Image.gz 2>&1 | tee "$artifacts/build.log"
test -s "$out/arch/arm64/boot/Image.gz"
test -s "$out/Module.symvers"
cp "$out/arch/arm64/boot/Image.gz" "$out/Module.symvers" "$out/System.map" "$artifacts/"
{
    printf 'candidate_source=%s\n' "$(git rev-parse HEAD)"
    printf 'public_base=%s\n' "$base"
    printf 'clang_source=%s\n' "$clang_rev"
    printf 'binutils_source=%s\n' "$gcc_rev"
    printf 'kernelrelease=%s\n' "$release"
    printf 'validation=build and callback ordering only; no tablet boot test\n'
    printf 'original_build_tree=not compared; currently on disconnected drive\n'
    printf 'image_type=bare compressed kernel; not a flashable boot image\n'
    printf 'install_status=not installed\n'
} > "$artifacts/provenance.txt"
cd "$artifacts"
sha256sum Image.gz Module.symvers System.map resolved.config > SHA256SUMS
cat provenance.txt SHA256SUMS
