#!/bin/bash
#SBATCH -N 12
#SBATCH -n 12
#SBATCH -A zam
#SBATCH -p dc-cpu
#SBATCH --time=04:00:00

nodes=($(scontrol show hostnames "$SLURM_JOB_NODELIST"))
vlens=(128 256 512 1024)
assocs=(4 8 16)
for vlen_idx in "${!vlens[@]}"; do
    for ass_idx in "${!assocs[@]}"; do
        node_idx=$((vlen_idx*3+ass_idx))
        node=${nodes[$node_idx]}
        vlen=${vlens[$vlen_idx]}
        assoc=${assocs[$ass_idx]}
        echo "Running vlen ${vlen}/assoc ${assoc} on node ${node}"
        srun --exact -n 1 -N 1 --cpu-bind=none -w ${node} bash benchmarks/gemm_gem5_benchmarks.sh ${vlen} ${assoc} &
    done
done

wait
