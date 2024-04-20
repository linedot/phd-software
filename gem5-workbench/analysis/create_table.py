#!/usr/bin/env python

import argparse
import pandas
import itertools
import math
import numpy as np

import sys
MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or simd_later is required.\n" % MIN_PYTHON)

def main():
    parser = argparse.ArgumentParser(description="Analyze gem5run of gemm benchmarks")
    parser.add_argument("--hdf5file", metavar="hdf5file", help='hdf5file to store the DataFrame to', required=True)
    
    args = parser.parse_args()


    df = pandas.read_hdf(args.hdf5file,key='gem5stats')

    # Now handled by the extract script
    #df["minCyclesPossible"] = (df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"] + \
    #        df["system.cpu.commitStats0.committedInstType::SimdFloatMult"])/df["simd_count"]
    #df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]
    #data_size = 8 # double
    #df["bytesRead"] = df["mr"]*df["kc"]*df["simd_width"]/8 + df["kc"]*df["nr"]*data_size + df["mr"]*df["nr"]*data_size
    #df["bytesWritten"] = df["mr"]*df["nr"]*data_size
    

    data_size = 8
    mr_elem = df['mr']*df['simd_width']/(data_size*8)
    # We take at least 1 bank
    ca=np.maximum(np.floor((df['assoc']-1.0)/(1.0+df['nr']/mr_elem)),1).astype(int)

    print(f"ca: {ca}")

    if 'cl_size' in df:
        cl_size = df['cl_size']
    else:
        cl_size = 64

    nl = df['l1_size']*1024/df['assoc']/cl_size

    print(f"nl: {nl}")

    print(nl)

    #print(f"ca: {ca}")
    # Equation 4 from "Analytical modeling is enough for High-Performance BLIS"

    kc=((ca*nl*cl_size).astype(int)/(mr_elem*data_size)).astype(int)

    print(f"kc: {kc}")

    max_vregs = 32
    vectors_in_mr = df['mr']
    avec_count = 2*vectors_in_mr
    b_regs = (max_vregs-vectors_in_mr*df['nr']-avec_count)
    smallest_unroll = np.floor(np.lcm(b_regs,df['nr'])/df['nr'])
    unroll_factor = smallest_unroll
    unroll_factor[3>unroll_factor] = 4
    unroll_factor[4 == unroll_factor] = 8
    unroll_factor[6 == unroll_factor] = 12

    print(f"unroll factor: {unroll_factor}")

    df['kc'] = np.floor(kc//unroll_factor)*unroll_factor

    print(f"new kc: {df['kc']}")


    #df = df[df["assoc"] == 4]
    df_efficient = df[df["efficiency"] > 0.95]
    # Somehow the index gets messed up between these, so set it explicitly for both
    for tdf in [df,df_efficient]:
        tdf.set_index(["mr","nr","simd_lat","simd_count","simd_width"],inplace=True,drop=False)
        tdf.sort_index(inplace=True)
        tdf.reset_index(drop=True,inplace=True)

    #simd_count_list = [1,2,4]
    #simd_width_list = [128,256,512,1024]
    #simd_lat_list = [4,6,10]

    simd_count_list = df['simd_count'].unique()
    simd_width_list = df['simd_width'].unique()
    simd_lat_list =   df['simd_lat'].unique()

    df_results = pandas.DataFrame()

    combinations = list(itertools.product(simd_lat_list,simd_width_list,simd_count_list))

    results = []
    for simd_lat,simd_width,simd_count in combinations:
        if 0 == len(df[(df["simd_count"] == simd_count) & (df["simd_lat"] == simd_lat) & (df["simd_width"] == simd_width)]):
            continue

        result = {}
        print(f"Combination ({simd_count},{simd_width},{simd_lat})")
        result[r"$(\NSIMD,\wSIMD,\lambdaSIMDfma)$"] = f"$({simd_count},{simd_width},{simd_lat})$"

        df_good = df_efficient[ \
                (df_efficient["simd_count"] == simd_count) & \
                (df_efficient["simd_lat"] == simd_lat) & \
                (df_efficient["simd_width"] == simd_width)]

        if(0 != len(df_good)):
            df_good = df_good.groupby(["mr","nr"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])

        result["\\ngood"] = len(df_good)

        if(0 == len(df_good)):
            df_good = df[ \
                (df["simd_count"] == simd_count) & \
                (df["simd_lat"] == simd_lat) & \
                (df["simd_width"] == simd_width)]

        best_idx = df_good["efficiency"].idxmax()
        best = df_good.loc[best_idx]

        result[r"$\epsfpmax$"] = best["efficiency"]
        result[r"$(m_r,n_r,k_c)$"] = f"$({int(best['mr'])},{int(best['nr'])},{int(best['kc'])})$"
        result[r"$\dt$ [cycle]"] = int(best["system.cpu.numCycles"])
        result[r"$\nrarchmin$"] = int(best["mr"]*best["nr"]+1+2*best["mr"])
        result[r"$\nrphysvmax$"] = int(best["simd_phreg_count"]-(1000-best["system.cpu.rename.max1000MinusVecFreeEntries"]))
        result[r"$\nrobmax$"] = int(best["system.cpu.rob.maxNumInstsInROB"])
        result[r"$\nreservmax$"] = int(best["iq_size"] - best["system.cpu.numFreeEntriesDist::min_value"])
        #result[r"$\nbissuemax$"] = best["system.cpu.numIssuedDist::max_value"]
        result[r"$\IPC$"] = f"{best['system.cpu.ipc']:.1f}"
        #result[r"$\nbimipcrate$"] = best["system.cpu.ipc"]/best["system.cpu.numIssuedDist::max_value"]

        results.append(result)

    df_results = pandas.DataFrame(results)

    #meanrate = df_results["\\nbimipcrate"].mean()
    #maxfactor = 1.0/df_results["\\nbimipcrate"].min()
    #print(f"IPC/issue avg: {meanrate}; up to {maxfactor} more issued than IPC")

    #print(df_results.to_simd_latex(index=False,
    #                          escape=False,
    #                          float_format="%.3f"))
    df_results.set_index(r"$(\NSIMD,\wSIMD,\lambdaSIMDfma)$",inplace=True)
    #df_results.reset_index(drop=True,inplace=True)
    print(df_results.style.to_latex(
        environment="table*",
        column_format="".join(['c' for c in range(df_results.columns.size)]),
        position_float="centering",
        hrules=True,
        caption="Summary results for each design point. The leftmost columns show the results for the most efficient kernel.",
        label="tab:simres_overview"))



if "__main__" == __name__:
    main()
