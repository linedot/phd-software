#!/usr/bin/env python

import argparse
import pandas
import matplotlib.pyplot as plt
import numpy as np
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

    data_size = 8
    mr_elem = df['mr']*df['simd_width']/(data_size*8)
    # We take at least 1 bank
    ca=np.maximum(np.floor((df['assoc']-1.0)/(1.0+df['nr']/mr_elem)),1).astype(int)

    nl = df['l1_size']*1024/df['assoc']/64

    print(nl)

    #print(f"ca: {ca}")
    # Equation 4 from "Analytical modeling is enough for High-Performance BLIS"

    kc=((ca*nl*64)/(mr_elem*data_size)).astype(int)

    max_vregs = 32
    vectors_in_mr = df['mr']
    avec_count = 2*vectors_in_mr
    b_regs = (max_vregs-vectors_in_mr*df['nr']-avec_count)
    smallest_unroll = np.floor(np.lcm(b_regs,df['nr'])/df['nr'])
    unroll_factor = smallest_unroll
    unroll_factor[3>unroll_factor] = 4
    unroll_factor[4 == unroll_factor] = 8
    unroll_factor[6 == unroll_factor] = 12

    df['unroll'] = unroll_factor
    df['kc'] = np.floor(kc/unroll_factor)*unroll_factor
    df['flops'] = df['simd_width']/data_size*2.0*(vectors_in_mr*df['nr']*df['unroll'])*df['kc']+3.0*df['nr']*vectors_in_mr

    # Now handled by the extract script
    #df["minCyclesPossible"] = (df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"] +\
    #        df["system.cpu.commitStats0.committedInstType::SimdFloatMult"])/df["simd_count"]
    #df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]

    df["bytesRead"] = df["mr"]*df["kc"]*(df["simd_width"]/data_size) + df["kc"]*df["nr"]*data_size + df["mr"]*df["nr"]*(df["simd_width"]/data_size)
    df["bytesWritten"] = df["mr"]*df["nr"]*(df["simd_width"]/data_size)

    df_good = df[df["efficiency"] > 0.95]
    print(df_good)

    df_simd_count2_lat4 = df_good[(df_good["simd_count"] == 2) & (df_good["simd_lat"] == 4)]

    #df_assoc4 = df_simd_count2_lat4[df_simd_count2_lat4["assoc"] == 4]

    df_good_n2_l4 = df_simd_count2_lat4.groupby(["mr","nr","simd_width"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])
    df_good_n2_l4.reset_index(drop = True, inplace = True)
    
    df_good_n2_l4 = df_good_n2_l4.groupby(["simd_width"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])

    df_good_n2_l4["l1bw"] = (df_good_n2_l4["bytesRead"]+df_good_n2_l4["bytesWritten"])/df_good_n2_l4["system.cpu.numCycles"]

    print(df_good_n2_l4[["mr","nr","kc","unroll","flops","minCyclesPossible","efficiency","bytesRead","bytesWritten","l1bw"]])

    plt.rcParams['text.usetex'] = True
    plt.rcParams.update({'font.size': 20})
    fig = plt.figure(figsize=(8,4))
    ax = sns.lineplot(x="simd_width", y="l1bw", data=df_good_n2_l4)
    ax.set_xticks([df_good_n2_l4.iloc[i]["simd_width"] for i in range(len(df_good_n2_l4))])
    ax.set_xlabel(r"$w_{SIMD}$ [bit]")
    ax.set_ylabel(r"$bw_{L1D}$ [byte/cycle]")

    fig.savefig("simd_count2_lat4_best_l1bw.pdf",bbox_inches='tight')


    for vlen in [128,256,512,1024]:
        df_simd_count2_vlen_lat4 = df_good[(df_good["simd_count"] == 2) & (df_good["simd_lat"] == 4) & (df_good["simd_width"] == vlen)]

        #df_assoc4 = df_simd_count2_lat4[df_simd_count2_lat4["assoc"] == 4]

        df_good_n2_vlen_l4 = df_simd_count2_vlen_lat4.groupby(["mr","nr"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])
        df_good_n2_vlen_l4.reset_index(drop = True, inplace = True)


        df_good_n2_vlen_l4["l1bw"] = df_good_n2_vlen_l4["bytesRead"]/df_good_n2_vlen_l4["system.cpu.numCycles"]

        #df_good_n2_vlen_l4["ukrsize"] = df_good_n2_vlen_l4["mr"]*df_good_n2_vlen_l4["nr"]
        #df_good_n2_vlen_l4=df_good_n2_vlen_l4.sort_values("ukrsize")
        #df_good_n2_vlen_l4.reset_index(drop = True, inplace = True)

        df_good_n2_vlen_l4=df_good_n2_vlen_l4.sort_values(["mr","nr"])
        df_good_n2_vlen_l4.reset_index(drop = True, inplace = True)

        print(df_good_n2_vlen_l4[["mr","nr","kc","unroll","flops","minCyclesPossible","efficiency","bytesRead","bytesWritten","l1bw"]])

        plt.rcParams['text.usetex'] = True
        plt.rcParams.update({'font.size': 20})
        #plt.margins(x=1.0)
        fig = plt.figure(figsize=(8,4))
        ax = sns.barplot(x=df_good_n2_vlen_l4.index, y="l1bw", data=df_good_n2_vlen_l4, color='black')
        ax.set_xticklabels(["{0},{1}".format(
            int(df_good_n2_vlen_l4.iloc[i]["mr"]),
            int(df_good_n2_vlen_l4.iloc[i]["nr"])) for i in range(len(df_good_n2_vlen_l4))],rotation=90)
        ax.set_xlabel(r"$(m_r,n_r)$")
        ax.set_ylabel(r"$bw_{L1D}$ [byte/cycle]")

        fig.savefig(f"simd_count2_lat4_vlen{vlen}_good_l1bw.pdf",bbox_inches='tight')

    goodmaps = []
    for vlen in df["simd_width"].unique():
        for nsimd in df["simd_count"].unique():
            for lsimd in df["simd_lat"].unique():
                thisdf = df_good[(df_good["simd_count"] == nsimd) & (df_good["simd_lat"] == lsimd) & (df_good["simd_width"] == vlen)]
                goodmaps.append({
                    "simd_width" : vlen,
                    "simd_count" : nsimd,
                    "simd_lat"   : lsimd,
                    "n_good"     : (len(thisdf))
                            }
                        )

    gmapdf = pandas.DataFrame(goodmaps)

    for (lsimd, group) in gmapdf.groupby("simd_lat"):
        fig, ax = plt.subplots(figsize=(8,4))
        plotdf = group.pivot(index="simd_width", columns="simd_count", values="n_good")
        sns.heatmap(plotdf.T, annot=True, ax=ax)
        ax.set_xlabel("$w_{SIMD}$ [bit]")
        ax.set_ylabel("$N_{SIMD}$")
        fig.savefig(f"lsimd{lsimd}_good_heatmap.pdf",bbox_inches='tight')

if "__main__" == __name__:
    main()
