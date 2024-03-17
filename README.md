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

# NANOGEMM

## Installing asmgen

I recommend creating a venv and installing asmgen into it

```
cd gem5-workbench
python -m venv --system-site-packages venvs/nanogemm
. venvs/nanogemm/bin/activate
python -m build ../asmgen -o build/python/
pip install build/python/asmgen-0.1.0-py3-none-any.whl
deactivate

```

## Building gemm benchmarks

```
cd gem5-workbench
. venvs/nanogemm/bin/activate
cd benchmarks
./gen_gemm_gem5_benches.sh
```

## Running gem5 simulation

One single configuration:

```
cd gem5-workbench
PYTHONPATH=bine-configs build/ALL/gem5.opt --no-output-files configs/multi-isa-nanogemm.py --isa aarch64 --mr 2 --nr 4 --simd_lat 4 --simd_count 2 --simd_width 256 --decode_width 8 --commit_width 8 --fetch_buf_size 64 --assoc 16 --l1_size 64 --ld_count 2 --st_count 2 --simd_phreg_count 128  --rob_size 128 --iq_size 128 --split_bytes 500000000 --base_out_dir=$(pwd)/nanogemm-$(date "+%Y-%m-%d")

```

If you specify multiple values for parameters, the simulation script will run every possible combination of parameters
