#!/bin/bash

BENCHMARKS_PATH=$(pwd)
ASMGEN_PATH=${BENCHMARKS_PATH}/../../asmgen
ASMGEN_GEMM_PATH=${BENCHMARKS_PATH}/../../asmgen-gemm
AARCH64_TOOLCHAIN_PATH=${BENCHMARKS_PATH}/../toolchains/aarch64
RISCV64_TOOLCHAIN_PATH=${BENCHMARKS_PATH}/../toolchains/riscv64
AARCH64_BINARIES_PATH=${BENCHMARKS_PATH}/../binaries/aarch64
RISCV64_BINARIES_PATH=${BENCHMARKS_PATH}/../binaries/riscv64
GEM5_PATH=${BENCHMARKS_PATH}/../../gem5

function wrong_directory() {
    echo "Something wrong with directories (please run this inside gem5-workbench/benchmarks)"
    exit 1
}

function toolchain_missing_compiler() {
    echo "Can't find $1, did you build the toolchain?"
}

for dir in $BENCHMARKS_PATH $UARCH_BENCH_PATH $AARCH64_TOOLCHAIN_PATH $RISCV64_TOOLCHAIN_PATH $AARCH64_BINARIES_PATH $RISCV64_BINARIES_PATH $GEM5_PATH;
do
    echo "checking $dir"
    [[ -d "$dir" ]] || wrong_directory
done

[[ -f "$BENCHMARKS_PATH/gemmbench_gem5.cpp.in" ]] || wrong_directory

AARCH64_GCC=$AARCH64_TOOLCHAIN_PATH/bin/aarch64-linux-gnu-g++
[[ -f "$AARCH64_GCC" ]] || toolchain_missing_compiler "$AARCH64_GCC"

RISCV64_GCC=$RISCV64_TOOLCHAIN_PATH/bin/riscv64-linux-gnu-g++
[[ -f "$RISCV64_GCC" ]] || toolchain_missing_compiler "$RISCV64_GCC"

GENSRC_PATH=$BENCHMARKS_PATH/generated_sources/

mkdir -p $GENSRC_PATH

# start with empty files
makefile_sve=$GENSRC_PATH/Makefile.sve
makefile_rvv=$GENSRC_PATH/Makefile.rvv
echo "default: all" > $makefile_sve
echo >> $makefile_sve
echo "default: all" > $makefile_rvv
echo >> $makefile_rvv


echo "Generating Makefiles for gemm benchmarks"

sve_benchmarks=()
rvv_benchmarks=()
for mr in {1..8}; do
    max_n=$(((32-2*$mr-1)/$mr))
    for nr in $(seq -s ' ' 1 $max_n); do 
        bench_name=gemmbench_${mr}_${nr}_avecpreload_bvecdist1_boff
        sve_benchmarks+=("$bench_name")
cat <<EOT >> $makefile_sve
$GENSRC_PATH/${bench_name}_sve.cpp: gemmbench_gem5.cpp.in
	python3 ${ASMGEN_GEMM_PATH}/gemmerator.py \
	-T sve \
	--nr $nr --mr $mr \
	-V 32 \
	-M l1 \
	-t double \
	--bvec-strat dist1_boff \
	--avec-strat preload \
	gemmbench_gem5.cpp.in \
    --output-filename $GENSRC_PATH/${bench_name}_sve.cpp

EOT

cat <<EOT >> $makefile_sve
${AARCH64_BINARIES_PATH}/${bench_name}: $GENSRC_PATH/${bench_name}_sve.cpp
	${AARCH64_GCC} \
	    -static \
	    -march=armv8.2-a+sve -Ofast \
	    -o ${AARCH64_BINARIES_PATH}/$bench_name $GENSRC_PATH/${bench_name}_sve.cpp \
	    -I ${GEM5_PATH}/include/ -L ${GEM5_PATH}/util/m5/build/arm64/out/ -lm5

EOT
        bench_name=gemmbench_${mr}_${nr}_avecpreload_bvecfmavf
        rvv_benchmarks+=("$bench_name")

cat <<EOT >> $makefile_rvv
$GENSRC_PATH/${bench_name}_rvv.cpp: gemmbench_gem5.cpp.in
	python3 ${ASMGEN_GEMM_PATH}/gemmerator.py \
	-T rvv \
	--nr $nr --mr $mr \
	-V 32 \
	-M l1 \
	-t double \
	--bvec-strat fmavf \
	--avec-strat preload \
	gemmbench_gem5.cpp.in \
    --output-filename $GENSRC_PATH/${bench_name}_rvv.cpp

EOT

cat <<EOT >> $makefile_rvv
${RISCV64_BINARIES_PATH}/${bench_name}: $GENSRC_PATH/${bench_name}_rvv.cpp
	${RISCV64_GCC} \
	    -static \
	    -march=rv64imafdcv_zicbop -Ofast \
	    -o ${RISCV64_BINARIES_PATH}/$bench_name $GENSRC_PATH/${bench_name}_rvv.cpp \
	    -I ${GEM5_PATH}/include/ -L ${GEM5_PATH}/util/m5/build/riscv/out/ -lm5

EOT
    done
done

declare -A bpaths
bpaths[sve]=$AARCH64_BINARIES_PATH
bpaths[rvv]=$RISCV64_BINARIES_PATH

declare -A makefiles
makefiles[sve]=$makefile_sve
makefiles[rvv]=$makefile_rvv

REDBOLD=$(tput bold)$(tput setaf 1)
NC=$(tput sgr0)

for tgt in sve rvv; do
    src_str="sources="
    bin_str="binaries="
    bvarname=${tgt}_benchmarks[@]
    for b in ${!bvarname}; do
        src_str+="$GENSRC_PATH/${b}_${tgt}.cpp "
        bin_str+="${bpaths[$tgt]}/${b} "
    done

    echo "$src_str" >> ${makefiles[$tgt]}
    echo >> ${makefiles[$tgt]}
    echo "$bin_str" >> ${makefiles[$tgt]}
    echo >> ${makefiles[$tgt]}
    echo "all: \$(binaries)" >> ${makefiles[$tgt]}
    echo >> ${makefiles[$tgt]}
    echo "cleanbin: \$(binaries)" >> ${makefiles[$tgt]}
    echo "	rm \$(binaries)" >> ${makefiles[$tgt]}
    echo >> ${makefiles[$tgt]}
    echo "cleansrc: \$(sources)" >> ${makefiles[$tgt]}
    echo "	rm \$(sources)" >> ${makefiles[$tgt]}
    echo >> ${makefiles[$tgt]}
    echo "clean: cleansrc cleanbin" >> ${makefiles[$tgt]}
    echo >> ${makefiles[$tgt]}

    echo ".PHONY: all cleansrc cleanbin clean" >> ${makefiles[$tgt]}

    echo "Finished generating ${tgt} Makefile: ${makefiles[$tgt]}"

    makecmd="make -j$(nproc) -f ${makefiles[$tgt]}"
    echo "Running make cmd: $makecmd"
    logfile="make_${tgt}_$(date +"%Y_%m_%d_%I_%M_%p").log"
    echo "logfile: $logfile"
    $makecmd > $logfile 2>&1
    if [ $? -ne 0 ]; then
        echo -e "make ${REDBOLD}FAILED${NC}, see logfile"
        exit 3
    fi
done

echo
echo "=================================="
echo
echo "Finished building gemm benchmarks."
echo "Generated cpp files are in this directory."
echo "Built binaries are in ${AARCH64_BINARIES_PATH} or ${RISCV64_BINARIES_PATH} respectively."
echo "You can run"
echo 
echo "make -f <target makefile> cleanbin"
echo "to clean up the binaries,"
echo 
echo "make -f <target makefile> cleansrc"
echo
echo "to remove the generated sources or"
echo 
echo "make -f <target makefile> clean"
echo
echo "to remove both"
