# Software for my PhD #

GEM5 and uarch exploration


# ARM "Hello World" example: #

## Build gem5 in workbench: ##

```
git clone --recurse-submodules https://github.com/linedot/phd-software.gi
cd phd-software/gem5
scons ../gem5-workbench/build/ARM/gem5.opt -j$(nproc)
```

## Run the example with the simple configuration: ##

```
cd ../gem5-workbench
./build/ARM/gem5.opt configs/simple-arm.py
```
