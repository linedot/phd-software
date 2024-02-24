# Software for my PhD #

GEM5 and uarch exploration

# Clone repo and prepare build dir:
 
```
git clone --recurse-submodules https://github.com/linedot/phd-software.git
mkdir phd-software/gem5-workbench/build
```

# Building cross-toolchains


## Run the build script
```
cd phd-software/gem5-workbench/
./scripts/build_toolchains

```
This will create riscv64 and aarch64 GCC/GLIBC-based toolchains in `gem5-workbench/toolchains/riscv64` and `gem5-workbench/toolchains/aarch64` respectively


# Building gem5

Build gem5 with `PROTOCOL=CHI` for both ISAs. Also cross-compile the m5 utility + libm5. 

gem5 itself can be build out-of-source, scons will magically pick up the `build/<ISA>/gem5.<suffix>` part out of the path for the configuration.
libm5/m5 util needs to be build in-source and also uses different ISA names for some reason.

## BUILD gem5 for all ISAs:
```
cd phd-software/gem5-workbench
scons -C ../gem5 --verbose --no-compress-debug --ignore-style --with-lto -j $(nproc) build/ALL/gem5.opt PROTOCOL=CHI

```

## BUILD aarch64 m5 lib

Other cross-toolchains in your $PATH might mess up the build

```
cd phd-software/gem5-workbench
AARCH64_TOOLCHAIN=$(pwd)/toolchains/aarch64
PATH=$AARCH64_TOOLCHAIN/bin:$PATH scons -C ../gem5/util/m5 arm64.CROSS_COMPILE=aarch64-linux-gnu- build/arm64/out/m5
```

## BUILD riscv64 m5 lib

Other cross-toolchains in your $PATH might mess up the build

```
cd phd-software/gem5-workbench
RISCV64_TOOLCHAIN=$(pwd)/toolchains/riscv64
PATH=$RISCV64_TOOLCHAIN/bin:$PATH scons -C ../gem5/util/m5 riscv.CROSS_COMPILE=riscv64-linux-gnu- build/riscv/out/m5
```
