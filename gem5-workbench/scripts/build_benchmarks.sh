#!/bin/bash

correct_directory=1
wb_dir=$(pwd)

if [[ "gem5-workbench" != "$(basename ${wb_dir})" ]]; then
    correct_directory=0
fi

for dir in benchmarks bine-configs configs patches; do
    if [ ! -d "$wb_dir/$dir" ]; then
        correct_directory=0
    fi
done

if [ "$correct_directory" -eq "0" ]; then
    echo "Not running from gem5-workbench/something wrong with directory"
    exit -1
fi

bmark_dir=$wb_dir/benchmarks
bin_dir=$wb_dir/binaries
patch_dir=$wb_dir/patches

mkdir -p $bin_dir/arm
mkdir -p $bin_dir/riscv

function build_stream()
{
    outdir=$1
    (set -e

    reverse_patches=()
    for i in `seq $((${#stream_patches[@]} - 1)) -1 0`; do
        reverse_patches=(${reverse_patches[@]} "${stream_patches[$i]}")
    done

    cd $bmark_dir/STREAM
    for patch in "${stream_patches[@]}"; do
        patch -p1 < $patch_dir/$patch
    done
    make
    mv stream_c.exe $outdir
    make clean
    for patch in $(echo "${reverse_patches[@]}"); do
        patch -R -p1 < $patch_dir/$patch
    done
)} 

function build_tinymembench()
{
    outdir=$1
    (set -e

    reverse_patches=()
    for i in `seq $((${#tinymembench_patches[@]} - 1)) -1 0`; do
        reverse_patches=(${reverse_patches[@]} "${tinymembench_patches[$i]}")
    done

    cd $bmark_dir/tinymembench
    for patch in "${tinymembench_patches[@]}"; do
        patch -p1 < $patch_dir/$patch
    done
    make
    mv tinymembench $outdir
    make clean
    for patch in $(echo "${reverse_patches[@]}"); do
        patch -R -p1 < $patch_dir/$patch
    done
)} 

function build_npb()
{
    outdir=$1
    compiler=$2
    archflags=$3
    CASES=( bt.S cg.S ep.S ft.S is.S lu.S mg.S sp.S )
    (set -e

    reverse_patches=()
    for i in `seq $((${#npb_patches[@]} - 1)) -1 0`; do
        reverse_patches=(${reverse_patches[@]} "${npb_patches[$i]}")
    done

    cd $bmark_dir/STREAM
    for patch in "${npb_patches[@]}"; do
        patch -p1 < $patch_dir/$patch
    done



    cd $bmark_dir/NPB3.0-omp-C
    sed "s/^CC\s\+=\s\+cc/CC = $compiler/g" config/make.def.template |\
        sed "s/^CLINK\s\+=\s\+cc/CLINK = $compiler/g" |\
        sed "s/^CLINKFLAGS\s\+=\s*/CLINKFLAGS = -flto -static/g" |\
        sed "s/^C_LIB\s\+=\s*/C_LIB = -lm/g" |\
        sed "s#^BINDIR\s\+=.*#BINDIR = ${outdir}#g" |\
        sed "s/^CFLAGS\s\+=\s\+-O3/CFLAGS = -Ofast -march=$archflags/g" > config/make.def
    for bin in "${CASES[@]}"; do
        make ${bin%%.*} CLASS=${bin#*.}
        make clean
    done
    rm config/make.def


    for patch in $(echo "${reverse_patches[@]}"); do
        patch -R -p1 < $patch_dir/$patch
    done
)} 

## ======= ARM =======

echo Building ARM binaries
echo

export CC=aarch64-linux-gnu-gcc
export CXX=aarch64-linux-gnu-g++

arch_bin_dir=$bin_dir/arm

# ---- STREAM ----
stream_patches=( "STREAM-aarch64-static.patch" )
stream_logfile=$arch_bin_dir/STREAM.build.log

echo -n "Building STREAM (logfile: $stream_logfile) ..."
build_stream $arch_bin_dir > $stream_logfile 2>&1 
stream_success=$?
if [ ${stream_success} -ne 0 ]; then
    echo "FAILED"
    exit -1
else
    echo "SUCCESS"
fi

# ---- tinymembench ----
tinymembench_patches=( "tinymembench-static.patch" )
tinymembench_logfile=$arch_bin_dir/tinymembench.build.log

echo -n "Building tinymembench (logfile: $tinymembench_logfile) ..."
build_tinymembench $arch_bin_dir > $tinymembench_logfile 2>&1 
tinymembench_success=$?
if [ ${tinymembench_success} -ne 0 ]; then
    echo "FAILED"
    exit -1
else
    echo "SUCCESS"
fi

# ---- NPB ----
npb_patches=()
npb_logfile=$arch_bin_dir/npb.build.log
echo -n "Building NAS Parallel Benchmarks (logfile: $npb_logfile) ..."
build_npb $arch_bin_dir $CC "armv8.2-a+sve" > $npb_logfile 2>&1 
npb_success=$?
if [ ${npb_success} -ne 0 ]; then
    echo "FAILED"
    exit -1
else
    echo "SUCCESS"
fi

## ======= RISCV =======

echo Building RISCV binaries
echo

export CC=riscv64-linux-gnu-gcc
export CXX=riscv64-linux-gnu-g++

arch_bin_dir=$bin_dir/riscv

# ---- STREAM ----
stream_patches=( "STREAM-riscv64-static.patch" )
stream_logfile=$arch_bin_dir/STREAM.build.log

echo -n "Building STREAM (logfile: $stream_logfile) ..."
build_stream $arch_bin_dir > $stream_logfile 2>&1 
stream_success=$?
if [ ${stream_success} -ne 0 ]; then
    echo "FAILED"
    exit -1
else
    echo "SUCCESS"
fi

# ---- tinymembench ----
tinymembench_patches=( "tinymembench-static.patch" )
tinymembench_logfile=$arch_bin_dir/tinymembench.build.log

echo -n "Building tinymembench (logfile: $tinymembench_logfile) ..."
build_tinymembench $arch_bin_dir > $tinymembench_logfile 2>&1 
tinymembench_success=$?
if [ ${tinymembench_success} -ne 0 ]; then
    echo "FAILED"
    exit -1
else
    echo "SUCCESS"
fi

# ---- NPB ----
npb_patches=()
npb_logfile=$arch_bin_dir/npb.build.log
echo -n "Building NAS Parallel Benchmarks (logfile: $npb_logfile) ..."
build_npb $arch_bin_dir $CC "rv64imafdcv" > $npb_logfile 2>&1 
npb_success=$?
if [ ${npb_success} -ne 0 ]; then
    echo "FAILED"
    exit -1
else
    echo "SUCCESS"
fi
