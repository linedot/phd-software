#!/bin/bash
#SBATCH -N 4
#SBATCH -n 4
#SBATCH -A zam
#SBATCH -p dc-cpu

nodes=($(cluset -e "$SLURM_JOB_NODELIST"))
vlens=(128 256 512 1024)
for vlen_idx in "${!vlens[@]}"; do  
    node=${nodes[$vlen_idx]}
    vlen=${vlens[$vlen_idx]}
    echo "Running vlen ${vlen} on node ${node}"
    srun --exact -n 1 -N 1 --cpu-bind=none -w ${node} bash benchmarks/gemm_gem5_benchmarks.sh ${vlen} &
done

wait
