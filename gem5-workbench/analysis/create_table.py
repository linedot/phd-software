#!/usr/bin/env python

import argparse
import pandas
import itertools

import sys
MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

def main():
    parser = argparse.ArgumentParser(description="Analyze gem5run of gemm benchmarks")
    parser.add_argument("--hdf5file", metavar="hdf5file", help='hdf5file to store the DataFrame to', required=True)
    
    args = parser.parse_args()


    df = pandas.read_hdf(args.hdf5file,key='gem5stats')

    # Now handled by the extract script
    #df["minCyclesPossible"] = (df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"] + \
    #        df["system.cpu.commitStats0.committedInstType::SimdFloatMult"])/df["nfu"]
    #df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]
    #data_size = 8 # double
    #df["bytesRead"] = df["mr"]*df["kc"]*df["vlen"]/8 + df["kc"]*df["nr"]*data_size + df["mr"]*df["nr"]*data_size
    #df["bytesWritten"] = df["mr"]*df["nr"]*data_size


    df_assoc4 = df[df["assoc"] == 4]
    df_efficient = df_assoc4[df_assoc4["efficiency"] > 0.95]

    nfu_list = [1,2,4]
    vlen_list = [128,256,512,1024]
    lat_list = [4,6,10]

    df_results = pandas.DataFrame()

    combinations = list(itertools.product(lat_list,vlen_list,nfu_list))

    results = []
    for lat,vlen,nfu in combinations:

        result = {}
        print(f"Combination ({nfu},{vlen},{lat})")
        result[r"$(\NSIMD,\wSIMD,\lambdaSIMDfma)$"] = f"$({nfu},{vlen},{lat})$"

        df_good = df_efficient[ \
                (df_efficient["nfu"] == nfu) & \
                (df_efficient["lat"] == lat) & \
                (df_efficient["vlen"] == vlen)]

        if(0 != len(df_good)):
            df_good = df_good.groupby(["mr","nr"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])

        result["\\ngood"] = len(df_good)

        if(0 == len(df_good)):
            df_good = df_assoc4[ \
                (df_assoc4["nfu"] == nfu) & \
                (df_assoc4["lat"] == lat) & \
                (df_assoc4["vlen"] == vlen)]

        best_idx = df_good["efficiency"].idxmax()
        best = df_good.loc[best_idx]

        result[r"$\epsfpmax$"] = best["efficiency"]
        result[r"$(m_r,n_r,k_c)$"] = f"$({int(best['mr'])},{int(best['nr'])},{int(best['kc'])})$"
        result[r"$\dt$ [cycle]"] = int(best["system.cpu.numCycles"])
        result[r"$\nrarchmin$"] = int(best["mr"]*best["nr"]+1+2*best["mr"])
        result[r"$\nrphysvmax$"] = int(256-(1000-best["system.cpu.rename.max1000MinusVecFreeEntries"]))
        result[r"$\nrobmax$"] = int(best["system.cpu.rob.maxNumInstsInROB"])
        result[r"$\nreservmax$"] = int(120- best["system.cpu.numFreeEntriesDist::min_value"])
        #result[r"$\nbissuemax$"] = best["system.cpu.numIssuedDist::max_value"]
        result[r"$\IPC$"] = f"{best['system.cpu.ipc']:.1f}"
        #result[r"$\nbimipcrate$"] = best["system.cpu.ipc"]/best["system.cpu.numIssuedDist::max_value"]

        results.append(result)

    df_results = pandas.DataFrame(results)

    #meanrate = df_results["\\nbimipcrate"].mean()
    #maxfactor = 1.0/df_results["\\nbimipcrate"].min()
    #print(f"IPC/issue avg: {meanrate}; up to {maxfactor} more issued than IPC")

    #print(df_results.to_latex(index=False,
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
