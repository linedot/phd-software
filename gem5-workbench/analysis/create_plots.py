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

    df["minCyclesPossible"] = (df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"] +\
            df["system.cpu.commitStats0.committedInstType::SimdFloatMult"])/df["nfu"]
    df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]
    data_size = 8 # double
    df["bytesRead"] = df["mr"]*df["kc"]*df["vlen"]/8 + df["kc"]*df["nr"]*data_size + df["mr"]*df["nr"]*data_size
    df["bytesWritten"] = df["mr"]*df["nr"]*data_size

    df_good = df[df["efficiency"] > 0.95]

    df_nfu2_lat4 = df_good[(df_good["nfu"] == 2) & (df_good["lat"] == 4)]

    df_assoc4 = df_nfu2_lat4[df_nfu2_lat4["assoc"] == 4]

    df_good = df_assoc4.groupby(["mr","nr","vlen"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])
    df_good.reset_index(drop = True, inplace = True)
    
    df_good = df_good.groupby(["vlen"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])

    print(df_good)

    df_good["l1bw"] = df_good["bytesRead"]/df_good["system.cpu.numCycles"]

    plt.rcParams['text.usetex'] = True
    plt.rcParams.update({'font.size': 20})
    fig = plt.figure(figsize=(8,4))
    ax = sns.lineplot(x="vlen", y="l1bw", data=df_good)
    ax.set_xticks([df_good.iloc[i]["vlen"] for i in range(len(df_good))])
    ax.set_xlabel(r"$w_{SIMD}$ [bit]")
    ax.set_ylabel(r"$bw_{L1D}$ [byte/cycle]")

    fig.savefig("nfu2_lat4_best_l1bw.pdf",bbox_inches='tight')


    df_nfu2_vlen512_lat4 = df_good[(df_good["nfu"] == 2) & (df_good["lat"] == 4) & (df_good["vlen"] == 512)]

    df_assoc4 = df_nfu2_lat4[df_nfu2_lat4["assoc"] == 4]

    df_good = df_assoc4.groupby(["mr","nr"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])
    df_good.reset_index(drop = True, inplace = True)


    df_good["l1bw"] = df_good["bytesRead"]/df_good["system.cpu.numCycles"]

    #df_good["ukrsize"] = df_good["mr"]*df_good["nr"]
    #df_good=df_good.sort_values("ukrsize")
    #df_good.reset_index(drop = True, inplace = True)

    df_good=df_good.sort_values(["mr","nr"])
    df_good.reset_index(drop = True, inplace = True)

    print(df_good)

    plt.rcParams['text.usetex'] = True
    plt.rcParams.update({'font.size': 20})
    #plt.margins(x=1.0)
    fig = plt.figure(figsize=(8,4))
    ax = sns.barplot(x=df_good.index, y="l1bw", data=df_good)
    ax.set_xticklabels(["{0},{1}".format(
        int(df_good.iloc[i]["mr"]),
        int(df_good.iloc[i]["nr"])) for i in range(len(df_good))],rotation=90)
    ax.set_xlabel(r"$(m_r,n_r)$")
    ax.set_ylabel(r"$bw_{L1D}$ [byte/cycle]")

    fig.savefig("nfu2_lat4_vlen512_good_l1bw.pdf",bbox_inches='tight')



if "__main__" == __name__:
    main()
