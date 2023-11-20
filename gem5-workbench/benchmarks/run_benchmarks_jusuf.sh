#!/bin/bash
#SBATCH -N 12
#SBATCH -n 12
#SBATCH -A zam
#SBATCH -p batch
#SBATCH --time=06:00:00

nodes=($(scontrol show hostnames "$SLURM_JOB_NODELIST"))
vlens=(128 256 512 1024)
vcnts=(1 2 4)
for vlen_idx in "${!vlens[@]}"; do
    for vcnt_idx in "${!vcnts[@]}"; do
        node_idx=$((vlen_idx*3+vcnt_idx))
        node=${nodes[$node_idx]}
        vlen=${vlens[$vlen_idx]}
        vcnt=${vcnts[$vcnt_idx]}
        echo "Running vlen ${vlen}/vcnt ${vcnt} on node ${node}"
	PYTHONPATH=bine-configs:${HOME}/.local/lib/python3.11/site-packages:$PYTHONPATH srun --exact -N1 -n1 --cpu-bind=none -w ${node} build/ALL/gem5.opt --no-output-files configs/multi-isa-nanogemm.py --isa aarch64 --mr {1..8} --nr {1..30} --simd_lat 4 --simd_count ${vcnt} --simd_width ${vlen} --decode_width 8 --commit_width 8 --fetch_buf_size 64 --assoc 8 --l1_size 64 --ld_count 2 --st_count 2 --simd_phreg_count 48 52 56 60 64 68 72 76 80 84 88 92 96 104 112 120 128 --rob_size 16 18 20 22 24 26 28 32 36 40 44 48 52 56 60 64 128 --iq_size 8 10 12 14 16 18 20 24 28 32 --split_bytes 10000000000 --base_out_dir=${SCRATCH}/nassyr1/nanogemm-$(date +'%F')-job${SLURM_JOBID} --quiet --stat_filename stats_vlen${vlen}_vcnt${vcnt}_ --tqdm_position ${node_idx} &
    done
done

wait
