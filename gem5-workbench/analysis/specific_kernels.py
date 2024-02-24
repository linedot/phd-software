#!/usr/bin/env python

import argparse
import pandas
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
sns.set(font_scale=1.5)

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
    #df["minCyclesPossible"] = (df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"] +\
    #        df["system.cpu.commitStats0.committedInstType::SimdFloatMult"])/df["nfu"]
    #df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]
    #data_size = 8 # double
    #df["bytesRead"] = df["mr"]*df["kc"]*(df["vlen"]/8) + df["kc"]*df["nr"]*data_size + df["mr"]*df["nr"]*(df["vlen"]/8)
    #df["bytesWritten"] = df["mr"]*df["nr"]*(df["vlen"]/8)

    df_nfu1_lat4 = df[(df["nfu"] == 1) & (df["lat"] == 4)]
    df_nfu2_lat10 = df[(df["nfu"] == 2) & (df["lat"] == 10)]
    df_nfu2_lat4 = df[(df["nfu"] == 2) & (df["lat"] == 4)]

    df_assoc4 = df_nfu1_lat4[df_nfu1_lat4["assoc"] == 4]

    df_good = df_assoc4.groupby(["mr","nr","vlen"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])
    df_good.reset_index(drop = True, inplace = True)

    df_good["l1bw"] = (df_good["bytesRead"]+df_good["bytesWritten"])/df_good["system.cpu.numCycles"]

    df_mr2_nr4_vlen128 = df_good[(df_good["mr"] == 2) & (df_good["nr"] == 4)& (df_good["vlen"] == 128)]

    print(df_mr2_nr4_vlen128[["mr","nr","kc","unroll","flops","minCyclesPossible","efficiency","bytesRead","bytesWritten","l1bw"]])

    df_mr2_nr1_vlen128 = df_good[(df_good["mr"] == 2) & (df_good["nr"] == 1)& (df_good["vlen"] == 128)]

    print(df_mr2_nr1_vlen128[["mr","nr","kc","unroll","flops","minCyclesPossible","efficiency","bytesRead","bytesWritten","l1bw"]])

    df_assoc4 = df_nfu2_lat10[df_nfu2_lat10["assoc"] == 4]

    df_good = df_assoc4.groupby(["mr","nr","vlen"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])
    df_good.reset_index(drop = True, inplace = True)

    df_good["l1bw"] = (df_good["bytesRead"]+df_good["bytesWritten"])/df_good["system.cpu.numCycles"]

    df_mr2_nr10_vlen128 = df_good[(df_good["mr"] == 2) & (df_good["nr"] == 10)& (df_good["vlen"] == 512)]

    print(df_mr2_nr10_vlen128[["mr","nr","kc","unroll","flops","minCyclesPossible","efficiency","bytesRead","bytesWritten","l1bw"]])

    df_mr2_nr4_vlen128 = df_good[(df_good["mr"] == 2) & (df_good["nr"] == 4)& (df_good["vlen"] == 512)]

    print(df_mr2_nr4_vlen128[["mr","nr","kc","unroll","flops","minCyclesPossible","efficiency","bytesRead","bytesWritten","l1bw"]])

    df_assoc4 = df_nfu2_lat4[df_nfu2_lat4["assoc"] == 4]

    df_good = df_assoc4.groupby(["mr","nr","vlen"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])
    df_good.reset_index(drop = True, inplace = True)

    df_good["l1bw"] = (df_good["bytesRead"]+df_good["bytesWritten"])/df_good["system.cpu.numCycles"]

    df_mr2_nr4_vlen256 = df_good[(df_good["mr"] == 2) & (df_good["nr"] == 4)& (df_good["vlen"] == 256)]

    print(df_mr2_nr4_vlen256[["mr","nr","kc","unroll","flops","minCyclesPossible","efficiency","bytesRead","bytesWritten","l1bw"]])

    df_mr2_nr2_vlen256 = df_good[(df_good["mr"] == 2) & (df_good["nr"] == 2)& (df_good["vlen"] == 256)]

    print(df_mr2_nr2_vlen256[["mr","nr","kc","unroll","flops","minCyclesPossible","efficiency","bytesRead","bytesWritten","l1bw"]])




if "__main__" == __name__:
    main()
