
vlens=(128 256 512 1024)
assocs=(4 8 16)
for vlen_idx in "${!vlens[@]}"; do
    for ass_idx in "${!assocs[@]}"; do
        vlen=${vlens[$vlen_idx]}
        assoc=${assocs[$ass_idx]}
        echo "Running vlen ${vlen}/assoc ${assoc} on node $(hostname)"
        bash benchmarks/gemm_gem5_benchmarks.sh ${vlen} ${assoc}
    done
done
