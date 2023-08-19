#!/usr/bin/env python

import argparse
import pandas
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
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

    df = pandas.DataFrame(df)

    vlen_list = pandas.unique(df[["vlen"]].values.ravel())
    nfu_list = pandas.unique(df[["nfu"]].values.ravel())
    lat_list = pandas.unique(df[["lat"]].values.ravel())
    assoc_list = pandas.unique(df[["assoc"]].values.ravel())

    vlen_list = [int(v) for v in vlen_list]
    nfu_list = [int(v) for v in nfu_list]
    lat_list = [int(v) for v in lat_list]
    assoc_list = [int(v) for v in assoc_list]


    
    grid_kws = {'width_ratios': (0.9, 0.05), 'wspace': 0.2}
    fig, (ax, cbar_ax) = plt.subplots(1,2,gridspec_kw=grid_kws)
    fig.subplots_adjust(bottom=0.5,right=0.85)

    ax_vlen  = fig.add_axes([0.25, 0.1, 0.65, 0.03])
    ax_nfu   = fig.add_axes([0.25, 0.15, 0.65, 0.03])
    ax_lat   = fig.add_axes([0.25, 0.2, 0.65, 0.03])
    ax_assoc = fig.add_axes([0.25, 0.25, 0.65, 0.03])

    svlen = Slider(
            ax_vlen, "$w_{SIMD}$",
            min(vlen_list), max(vlen_list),
            valinit=vlen_list[0],valstep=vlen_list,
            initcolor="none")
    snfu = Slider(
            ax_nfu, "$N_{SIMD}$",
            min(nfu_list), max(nfu_list),
            valinit=nfu_list[0],valstep=nfu_list,
            initcolor="none")
    slat = Slider(
            ax_lat, r"$\lambda_{SIMD}$",
            min(lat_list), max(lat_list),
            valinit=lat_list[0],valstep=lat_list,
            initcolor="none")
    sassoc = Slider(
            ax_assoc, "$w_{L1D}$",
            min(assoc_list), max(assoc_list),
            valinit=assoc_list[0],valstep=assoc_list,
            initcolor="none")

    def update_heatmap(val):
        nonlocal ax
        nonlocal cbar_ax
        vlen = svlen.val
        nfu = snfu.val
        lat = slat.val
        assoc = sassoc.val

        df_specific = df[(df["assoc"] == assoc) & (df["vlen"] == vlen) & (df["nfu"] == nfu) & (df["lat"] == lat)];
        df_specific = df_specific.groupby(["mr","nr"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])
        df_specific.reset_index(drop = True, inplace = True)
        df_specific[["mr","nr"]] = df_specific[["mr","nr"]].astype(int)
        df_map = df_specific.pivot(index='mr', columns='nr', values='efficiency')

        ax.cla()
        sns.heatmap(df_map,ax=ax,cbar_ax=cbar_ax,vmin=0.0,vmax=1.0,
                    cbar_kws={'label': 'max. efficiency'})
        #fig.canvas.draw_idle()

    update_heatmap(0)

    svlen.on_changed(update_heatmap)
    snfu.on_changed(update_heatmap)
    slat.on_changed(update_heatmap)
    sassoc.on_changed(update_heatmap)


    plt.show()



if "__main__" == __name__:
    main()
