# Software for my PhD #

GEM5 and uarch exploration

# Clone repo and prepare build dir:
 
```
git clone --recurse-submodules https://github.com/linedot/phd-software.git
mkdir phd-software/gem5-workbench/build
```

# Building cross-toolchains


## Build ARM cross-toolchain
```
cd phd-software/gem5-workbench/
# Binutils
bash scripts/build_binutils.sh --version 2.40 --architecture aarch64 --outputdirectory $(pwd)/toolchains/aarch64 --sysroot $(pwd)/toolchains/aarch64/sysroot --builddirectory /tmp/build-binutils-aarch64
# Linux Headers
bash scripts/build_linux_headers.sh --version 6.4 --architecture aarch64 --outputdirectory $(pwd)/toolchains/aarch64 --sysroot $(pwd)/toolchains/aarch64/sysroot --builddirectory /tmp/build-linux-headers-aarch64
# GCC and GLIBC
bash scripts/build_gcc_and_glibc.sh --version_gcc 13.1.0 --version_glibc 2.37 --architecture aarch64 --outputdirectory $(pwd)/toolchains/aarch64 --sysroot $(pwd)/toolchains/aarch64/sysroot --patchdirectory $(pwd)/patches --builddirectory /tmp/build-gcc-and-glibc-aarch64
```

This will create an AArch64 GCC/GLIBC-based toolchain in `gem5-workbench/toolchains/aarch64`

## Build RISCV cross-toolchain
```
cd phd-software/gem5-workbench/
# Binutils
bash scripts/build_binutils.sh --version 2.40 --architecture riscv64 --outputdirectory $(pwd)/toolchains/riscv64 --sysroot $(pwd)/toolchains/riscv64/sysroot --builddirectory /tmp/build-binutils-riscv64
# Linux Headers
bash scripts/build_linux_headers.sh --version 6.4 --architecture riscv64 --outputdirectory $(pwd)/toolchains/riscv64 --sysroot $(pwd)/toolchains/riscv64/sysroot --builddirectory /tmp/build-linux-headers-riscv64
# GCC and GLIBC
bash scripts/build_gcc_and_glibc.sh --version_gcc 13.1.0 --version_glibc 2.37 --architecture riscv64 --outputdirectory $(pwd)/toolchains/riscv64 --sysroot $(pwd)/toolchains/riscv64/sysroot --patchdirectory $(pwd)/patches --builddirectory /tmp/build-gcc-and-glibc-riscv64
```

This will create a RISCV GCC/GLIBC-based toolchain in `gem5-workbench/toolchains/riscv64`


# Building gem5

Build gem5 with `PROTOCOL=CHI` for both ISAs. Also cross-compile the m5 utility + libm5. 

gem5 itself can be build out-of-source, scons will magically pick up the `build/<ISA>/gem5.<suffix>` part out of the path for the configuration.
libm5/m5 util needs to be build in-source and also uses different ISA names for some reason.

## BUILD ARM gem5 + m5 lib

```
cd phd-software/gem5
scons ../gem5-workbench/build/ARM/gem5.opt -j$(nproc) PROTOCOL=CHI
cd gem5/util/m5
PATH=$(pwd)/toolchains/aarch64/bin/:$PATH scons arm64.CROSS_COMPILE=aarch64-linux-gnu- build/arm64/out/m5
cp -r build/arm64/out/m5 ../../../gem5-workbench/build/ARM/
```

## BUILD RISCV gem5 + m5 lib


Building M5 lib requires static `libstdc++.a`. On my distro (Arch Linux), while there is a riscv64-linux-gnu-gcc package, it does not contain a static libstdc++ (the aarch64 version does), so I had to download the PKGBUILD, edit it to add the `staticlibs` option and rebuild it.

```
cd phd-software/gem5
scons ../gem5-workbench/build/RISCV/gem5.opt -j$(nproc) PROTOCOL=CHI
cd gem5/util/m5
PATH=$(pwd)/toolchains/riscv64/bin/:$PATH scons riscv.CROSS_COMPILE=riscv64-linux-gnu- build/riscv/out/m5
cp -r build/riscv/out/m5 ../../../gem5-workbench/build/RISCV/
```

# ARM "Hello World" example: #

## Run the example with the simple configuration: ##

```
cd ../gem5-workbench
./build/ARM/gem5.opt configs/simple-arm.py
```

# Build benchmarks with our cross-toolchains:

```
PATH=$(pwd)/toolchains/riscv64/bin/:$(pwd)/toolchains/aarch64/bin/:$PATH ./scripts/build_benchmarks.sh
```
