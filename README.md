# Software for my PhD #

GEM5 and uarch exploration

# Clone repo and prepare build dir:
 
```
git clone --recurse-submodules https://github.com/linedot/phd-software.git
mkdir phd-software/gem5-workbench/build
```

# Building gem5

Build gem5 with `PROTOCOL=CHI` for both ISAs. Also cross-compile the m5 utility + libm5. I'm using the distro packages for the cross-compilers:

```
# Specific to Arch Linux:
pacman -S risc-v # install risc-v group (contains riscv64-linux-gnu-gcc)
pacman -S aarch64-linux-gnu-gcc # No group for aarch64 currently
```

gem5 itself can be build out-of-source, scons will magically pick up the `build/<ISA>/gem5.<suffix>` part out of the path for the configuration.
libm5/m5 util needs to be build in-source and also uses different ISA names for some reason.

## BUILD ARM gem5 + m5 lib

```
cd phd-software/gem5
scons ../gem5-workbench/build/ARM/gem5.opt -j$(nproc) PROTOCOL=CHI
cd gem5/util/m5
scons arm64.CROSS_COMPILE=aarch64-linux-gnu- build/arm64/out/m5
cp -r build/arm64/out/m5 ../../../gem5-workbench/build/ARM/
```

## BUILD RISCV gem5 + m5 lib


Building M5 lib requires static `libstdc++.a`. On my distro (Arch Linux), while there is a riscv64-linux-gnu-gcc package, it does not contain a static libstdc++ (the aarch64 version does), so I had to download the PKGBUILD, edit it to add the `staticlibs` option and rebuild it.

```
cd phd-software/gem5
scons ../gem5-workbench/build/RISCV/gem5.opt -j$(nproc) PROTOCOL=CHI
cd gem5/util/m5
scons riscv.CROSS_COMPILE=riscv64-linux-gnu- build/riscv/out/m5
cp -r build/riscv/out/m5 ../../../gem5-workbench/build/RISCV/
```

# ARM "Hello World" example: #

## Run the example with the simple configuration: ##

```
cd ../gem5-workbench
./build/ARM/gem5.opt configs/simple-arm.py
```
