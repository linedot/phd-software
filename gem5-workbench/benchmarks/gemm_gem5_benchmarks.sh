#!/bin/bash

vlen=$1
base_dir=gem5run_$(date +"%Y_%m_%d_%H_%M")
mkdir -p $base_dir
dw=8
cw=8

if ! command -v parallel --version &> /dev/null;
then
# Just run everything and hope the system has enough RAM/cores lol

#for vlen in {128,256,512,1024}; do
for lat in {4,6,10}; do
for nfu in {1,2,4}; do
for mr in {1..8}; do
    max_n=$(((32-2*$mr-1)/$mr))
    for nr in $(seq -s ' ' 1 $max_n); do
        echo "Starting with params: mr=${mr}; nr=${nr}; nfu=${nfu}; lat=${lat}; vlen=${vlen}"
        PYTHONPATH=bine-configs build/ARM/gem5.opt configs/aarch64-nanogemm.py \
            --mr $mr --nr $nr \
            --simd_lat ${lat} --simd_count ${nfu} --simd_width ${vlen}\
            --decode_width ${dw} --commit_width ${cw} --fetch_buf_size 64 \
            --base_out_dir $base_dir > $base_dir/gemm_m5_M${mr}_N${nr}_lat${lat}_vl${vlen}_nfu${nfu}_dw${dw}_cw${cw}.log 2>&1 &
    done
done
done
done
#done

else
# use GNU Parallel
total_mem_mb=$(free -m | grep -oP '\d+' | head -n 1)
# one run allocates around 120MiB (measured empirically with /usr/bin/time -f "%M")
# free outputs MiB, assumption is 1st number is total memory
# Let's be conservative and use up to 60% of the total memory
threads_mem=$((total_mem_mb*6/10/120))
threads_cpu=$(nproc)

# Use the smaller of the two as number of jobs
num_jobs=$(( threads_mem < threads_cpu ? threads_mem : threads_cpu ))


function run_gem5() {
    mr=$1
    nr=$2
    lat=$3
    nfu=$4
    vlen=$5
    dw=$6
    cw=$7
    base_dir=$8

    if (( $(( nr > (32-2*mr-1)/mr )) ))
    then
        echo "Skipping mr ${mr} x nr ${nr}"
        return
    fi
    echo "Starting with params: mr=${mr}; nr=${nr}; nfu=${nfu}; lat=${lat}; vlen=${vlen}"
PYTHONPATH=bine-configs build/ARM/gem5.opt configs/aarch64-nanogemm.py \
    --mr ${mr} --nr ${nr} \
    --simd_lat ${lat} --simd_count ${nfu} --simd_width ${vlen}\
    --decode_width ${dw} --commit_width ${cw} --fetch_buf_size 64 \
    --base_out_dir $base_dir > $base_dir/gemm_m5_M${mr}_N${nr}_lat${lat}_vl${vlen}_nfu${nfu}_dw${dw}_cw${cw}.log 2>&1
    echo "Finished with params: mr=${mr}; nr=${nr}; nfu=${nfu}; lat=${lat}; vlen=${vlen}"
}
export -f run_gem5

echo "Running gem5 simulations in parallel"
parallel -j $num_jobs run_gem5 ::: {1..8} ::: {1..30} ::: {4,6,10} ::: {1,2,4} ::: $vlen ::: $dw ::: $cw ::: $base_dir
echo "Finished all simulations"

fi
