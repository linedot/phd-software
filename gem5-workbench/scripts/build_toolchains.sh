#!/usr/bin/env bash
#

architectures=(aarch64 riscv64)
binutils_version=2.42
linux_version=6.7
gcc_version=13.2.0
gmp_version=6.3.0
glibc_version=2.39

script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd $script_dir/../

for arch in "${architectures[@]}";
do
    # Binutils
    bash scripts/build_binutils.sh --version $binutils_version \
        --architecture $arch \
        --outputdirectory $(pwd)/toolchains/$arch \
        --sysroot $(pwd)/toolchains/$arch/sysroot \
        --builddirectory /tmp/$arch-toolchain
    # Linux Headers
    bash scripts/build_linux_headers.sh --version $linux_version \
        --architecture $arch \
        --outputdirectory $(pwd)/toolchains/$arch \
        --sysroot $(pwd)/toolchains/$arch/sysroot \
        --builddirectory /tmp/$arch-toolchain
    # GCC and GLIBC
    bash scripts/build_gcc_and_glibc.sh --version_gmp $gmp_version \
        --version_gcc $gcc_version \
        --version_glibc $glibc_version \
        --architecture $arch \
        --outputdirectory $(pwd)/toolchains/$arch \
        --sysroot $(pwd)/toolchains/$arch/sysroot \
        --patchdirectory $(pwd)/patches \
        --builddirectory /tmp/$arch-toolchain
done
