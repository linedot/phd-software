import os
import math



def prepare_nanogemm(kernel_params : dict, arch_params : dict):
    thispath = os.path.dirname(os.path.realpath(__file__))
    bin_name = ""
    isa = arch_params["isa"]
    if "riscv64" == isa:
        bin_name = f"gemmbench_{mr}_{nr}_avecpreload_bvecfmavf"
    elif "aarch64" == isa:
        bin_name = f"gemmbench_{mr}_{nr}_avecpreload_bvecdist1_boff"
    else:
        raise RuntimeError("Unknown isa {isa}")


    # from uarch_bench/gemmerator.py
    #TODO: build boilerplate to unify kc calculation (it's calculated independently in 3 locations)
    #TODO: remote hardcoded vregs
    max_vregs = 32
    vectors_in_mr = mr
    avec_count = 2*vectors_in_mr
    b_regs = (max_vregs-vectors_in_mr*nr-avec_count)
    smallest_unroll = lcm(b_regs,nr)//nr
    unroll_factor = smallest_unroll
    if 3 > unroll_factor:
        unroll_factor = 4
    if 4 == unroll_factor:
        unroll_factor = 8
    if 6 == unroll_factor:
        unroll_factor = 12
    w_l1 = l1d_assoc
    cl   = arch_params["cl_size"]
    nl   = l1d_size/w_l1/cl
    # TODO: remove hardcoded data_size
    data_size = 8
    mr_elem = mr*simd_width/(data_size*8)
    # We take at least 1 bank
    ca=max(1,int(math.floor((w_l1-1.0)/(1.0+nr/mr_elem))))

    print(f"ca: {ca}")
    # Equation 4 from "Analytical modeling is enough for High-Performance BLIS"
    kc=int((ca*nl*cl)/(mr_elem*data_size))
    print(f"assoc: {w_l1}, cl:{cl}, nl:{nl}, mr_elem: {mr_elem}, nr: {nr} ===> kc: {kc}")
    iterations=max(2,int(kc)//unroll_factor)
    print(f"unroll: {unroll_factor} ===> iterations: {iterations} ===> kc: {iterations*unroll_factor}")

    
    return bin_name, iterations
