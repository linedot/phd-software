#!/bin/bash

vlen=$1
base_dir=gem5run_$(date +"%Y_%m_%d_%I_%M_%p")
mkdir -p $base_dir
dw=8
cw=8
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
