#!/bin/bash
#SBATCH -N 36
#SBATCH -n 36
#SBATCH --cpus-per-task 256
#SBATCH -A zam
#SBATCH -p batch
#SBATCH --time=06:00:00

#nodes=($(scontrol show hostnames "$SLURM_JOB_NODELIST"))
#vlens=(128 256 512 1024)
#vcnts=(1 2 4)
#iq_offsets=(8 16 24)
#iq_steps=(2 2 4)
#for vlen_idx in "${!vlens[@]}"; do
#    for vcnt_idx in "${!vcnts[@]}"; do
#        for iqo_idx in "${!iq_offsets[@]}"; do
#            node_idx=$((vlen_idx*3*3+vcnt_idx*3+iqo_idx))
#            node=${nodes[$node_idx]}
#            vlen=${vlens[$vlen_idx]}
#            vcnt=${vcnts[$vcnt_idx]}
#            iqo=${iq_offsets[$iqo_idx]}
#            iqs=${iq_steps[$iqo_idx]}
#            echo "Running vlen ${vlen}/vcnt ${vcnt}/iqo ${iqo} on node ${node}"
#        PYTHONPATH=bine-configs:${HOME}/.local/lib/python3.11/site-packages:$PYTHONPATH srun --exact -N1 -n1 --cpu-bind=none -w ${node} build/ALL/gem5.opt --no-output-files configs/multi-isa-nanogemm.py --isa aarch64 --mr {1..8} --nr {1..30} --simd_lat 4 --simd_count ${vcnt} --simd_width ${vlen} --decode_width 8 --commit_width 8 --fetch_buf_size 64 --assoc 8 --l1_size 64 --ld_count 2 --st_count 2 --simd_phreg_count 48 52 56 60 64 68 72 76 80 84 88 92 96 104 112 120 128 --rob_size 16 18 20 22 24 26 28 32 36 40 44 48 52 56 60 64 128 --iq_size $iqo $(($iqo+$iqs)) $(($iqo+2*$iqs)) $(($iqo+3*$iqs)) --split_bytes 5000000000 --base_out_dir=${SCRATCH}/nassyr1/nanogemm-$(date +'%F')-job${SLURM_JOBID} --quiet --stat_filename stats_vlen${vlen}_vcnt${vcnt}_ --tqdm_position ${node_idx} &
#        done
#    done
#done
#
#wait
PYTHONPATH=bine-configs:${HOME}/.local/lib/python3.11/site-packages:$PYTHONPATH srun --cpus-per-task 256 build/ALL/gem5.opt --no-output-files configs/multi-isa-nanogemm.py --isa aarch64 --mr 2 --nr 10 --simd_lat 10 --simd_count 2 --simd_width 256 --decode_width 8 --commit_width 8 --fetch_buf_size 64 --assoc 8 --l1_size 64 --ld_count 2 --st_count 2 --simd_phreg_count $(seq 48 2 256) --rob_size $(seq 8 2 256) --iq_size $(seq 8 2 120) --split_bytes 5000000000 --base_out_dir=${SCRATCH}/nassyr1/nanogemm-pareto-$(date +'%F')-job${SLURM_JOBID} --quiet --sim_max_cores 256 --stat_filename stats_
