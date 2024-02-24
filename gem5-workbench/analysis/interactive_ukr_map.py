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


from .data_extraction import build_df


def main():
    parser = argparse.ArgumentParser(description="Analyze gem5run of gemm benchmarks")
    parser.add_argument("--stat-dir", metavar="stat_dir",
                        help='Directory containing hdf5 files with the simulation stats',
                        required=True)
    parser.add_argument("--target-stat",
                        type=str,
                        metavar="target_stat",
                        help='Stat to visualize (default: efficiency)',
                        default="efficiency")
    parser.add_argument("--analysis-stat",
                        type=str,
                        choices=[
                            'rob_size',
                            'simd_phreg_count',
                            'iq_size',
                            ],
                        metavar="analysis_stat",
                        help='(lineplot only) stat to use as x-axis',
                        default="rob_size")
    parser.add_argument("--plot-type",
                        type=str,
                        metavar="plot_type",
                        choices=[
                            'heatmap',
                            'lineplot'
                            ],
                        help='type of plot',
                        default="heatmap")
    
    args = parser.parse_args()

    #df = pandas.read_hdf(args.hdf5file,key='gem5stats')
    df = build_df(args.stat_dir, args.target_stat)

    # Now handled by the extract script
    #df["minCyclesPossible"] = (df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"] +\
    #        df["system.cpu.commitStats0.committedInstType::SimdFloatMult"])/df["simd_count"]
    #df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]
    #data_size = 8 # double
    #df["bytesRead"] = df["mr"]*df["kc"]*(df["simd_width"]/8) + df["kc"]*df["nr"]*data_size + df["mr"]*df["nr"]*(df["simd_width"]/8)
    #df["bytesWritten"] = df["mr"]*df["nr"]*(df["simd_width"]/8)

    df = pandas.DataFrame(df)

    simd_width_list = pandas.unique(df[["simd_width"]].values.ravel())
    simd_count_list = pandas.unique(df[["simd_count"]].values.ravel())
    simd_phreg_count_list = pandas.unique(df[["simd_phreg_count"]].values.ravel())
    iq_size_list = pandas.unique(df[["iq_size"]].values.ravel())
    rob_size_list = pandas.unique(df[["rob_size"]].values.ravel())
    simd_lat_list = pandas.unique(df[["simd_lat"]].values.ravel())
    assoc_list = pandas.unique(df[["assoc"]].values.ravel())
    l1_size_list = pandas.unique(df[["l1_size"]].values.ravel())
    ld_count_list = pandas.unique(df[["ld_count"]].values.ravel())
    st_count_list = pandas.unique(df[["st_count"]].values.ravel())

    simd_width_list = [int(v) for v in simd_width_list]
    simd_count_list = [int(v) for v in simd_count_list]
    simd_lat_list = [int(v) for v in simd_lat_list]
    simd_phreg_count_list = [int(v) for v in simd_phreg_count_list]
    iq_size_list = [int(v) for v in iq_size_list]
    rob_size_list = [int(v) for v in rob_size_list]
    assoc_list = [int(v) for v in assoc_list]
    l1_size_list = [int(v) for v in l1_size_list]
    ld_count_list = [int(v) for v in ld_count_list]
    st_count_list = [int(v) for v in st_count_list]


    
    grid_kws = {'width_ratios': (0.9, 0.05), 'wspace': 0.2}
    fig, (ax, cbar_ax) = plt.subplots(1,2,gridspec_kw=grid_kws)
    fig.subplots_adjust(bottom=0.6,right=0.85)

    ax_simd_width  = fig.add_axes([0.25, 0.1, 0.65, 0.03])
    ax_simd_count   = fig.add_axes([0.25, 0.15, 0.65, 0.03])
    ax_simd_lat   = fig.add_axes([0.25, 0.2, 0.65, 0.03])
    ax_simd_phreg_count   = fig.add_axes([0.25, 0.25, 0.65, 0.03])
    ax_iq_size   = fig.add_axes([0.25, 0.30, 0.65, 0.03])
    ax_rob_size   = fig.add_axes([0.25, 0.35, 0.65, 0.03])
    #ax_assoc = fig.add_axes([0.25, 0.25, 0.65, 0.03])
    #ax_l1_size = fig.add_axes([0.25, 0.30, 0.65, 0.03])
    #ax_ld_count = fig.add_axes([0.25, 0.35, 0.65, 0.03])
    #ax_st_count = fig.add_axes([0.25, 0.40, 0.65, 0.03])

    ssimd_width = Slider(
            ax_simd_width, "$w_{SIMD}$",
            min(simd_width_list), max(simd_width_list),
            valinit=simd_width_list[0],valstep=simd_width_list,
            initcolor="none")
    ssimd_count = Slider(
            ax_simd_count, "$N_{SIMD}$",
            min(simd_count_list), max(simd_count_list),
            valinit=simd_count_list[0],valstep=simd_count_list,
            initcolor="none")
    ssimd_lat = Slider(
            ax_simd_lat, r"$\lambda_{SIMD}$",
            min(simd_lat_list), max(simd_lat_list),
            valinit=simd_lat_list[0],valstep=simd_lat_list,
            initcolor="none")
    ssimd_phreg_count = Slider(
            ax_simd_phreg_count, r"$N_{VRF}$",
            min(simd_phreg_count_list), max(simd_phreg_count_list),
            valinit=simd_phreg_count_list[0],valstep=simd_phreg_count_list,
            initcolor="none")
    siq_size = Slider(
            ax_iq_size, r"$N_{IQ}$",
            min(iq_size_list), max(iq_size_list),
            valinit=iq_size_list[0],valstep=iq_size_list,
            initcolor="none")
    srob_size = Slider(
            ax_rob_size, r"$N_{ROB}$",
            min(rob_size_list), max(rob_size_list),
            valinit=rob_size_list[0],valstep=rob_size_list,
            initcolor="none")
    #sassoc = Slider(
    #        ax_assoc, "$w_{L1D}$",
    #        min(assoc_list), max(assoc_list),
    #        valinit=assoc_list[0],valstep=assoc_list,
    #        initcolor="none")
    #sl1_size = Slider(
    #        ax_l1_size, "$S_{L1D}$ [KiByte]",
    #        min(l1_size_list), max(l1_size_list),
    #        valinit=l1_size_list[0],valstep=l1_size_list,
    #        initcolor="none")
    #sld_count = Slider(
    #        ax_ld_count, "$N_{LD}$",
    #        min(ld_count_list), max(ld_count_list),
    #        valinit=ld_count_list[0],valstep=ld_count_list,
    #        initcolor="none")
    #sst_count = Slider(
    #        ax_st_count, "$N_{ST}$",
    #        min(st_count_list), max(st_count_list),
    #        valinit=st_count_list[0],valstep=st_count_list,
    #        initcolor="none")

    def update_plot(val):
        nonlocal ax
        nonlocal cbar_ax
        simd_width = ssimd_width.val
        simd_count = ssimd_count.val
        simd_lat = ssimd_lat.val
        simd_phreg_count = ssimd_phreg_count.val
        iq_size = siq_size.val
        rob_size = srob_size.val
        #assoc = sassoc.val
        #l1_size = sl1_size.val
        #ld_count = sld_count.val
        #st_count = sst_count.val

        #df_specific = df[(df["assoc"] == assoc) & \
        #                 (df["simd_width"] == simd_width) & \
        #                 (df["simd_count"] == simd_count) & \
        #                 (df["simd_lat"] == simd_lat) & \
        #                 (df["l1_size"] == l1_size) & \
        #                 (df["ld_count"] == ld_count) & \
        #                 (df["st_count"] == st_count)];

        ax.cla()
        if 'heatmap' == args.plot_type:
            df_specific = df[(df["iq_size"] == iq_size) & \
                             (df["simd_width"] == simd_width) & \
                             (df["simd_count"] == simd_count) & \
                             (df["simd_lat"] == simd_lat) & \
                             (df["simd_phreg_count"] == simd_phreg_count) & \
                             (df["rob_size"] == rob_size)];
            df_specific = df_specific.groupby(["mr","nr"], group_keys=False).apply(lambda x: x.loc[x.efficiency.idxmax()])
            df_specific.reset_index(drop = True, inplace = True)
            df_specific[["mr","nr"]] = df_specific[["mr","nr"]].astype(int)
            df_map = df_specific.pivot(index='mr', columns='nr', values='efficiency')

            best = df_specific.loc[df_specific["efficiency"].idxmax()]
            best_mr = int(best["mr"])
            best_nr = int(best["nr"])
            best_eff = best["efficiency"]
            s = sns.heatmap(df_map,ax=ax,cbar_ax=cbar_ax,vmin=0.0,vmax=1.0,
                        cbar_kws={'label': '$\\epsilon_{FP,max}$'},
                        cmap="PiYG")
            s.set(xlabel="$n_r$",ylabel="$m_r$")
        
            props = dict(boxstyle='round', facecolor='darkgreen', alpha=0.5)
            ax.text(0.3,0.4,f"best: ({best_mr},{best_nr}); $\\epsilon_{{FP}}={best_eff:.3f}$",transform=ax.transAxes, fontsize=14,
                    verticalalignment='top', bbox=props)
        elif 'lineplot' == args.plot_type:
            df_specific = df[(df["simd_width"] == simd_width) & \
                             (df["simd_count"] == simd_count) & \
                             (df["simd_lat"] == simd_lat)];
            for astat,fval in zip(['rob_size','simd_phreg_count','iq_size'],
                                  [rob_size,simd_phreg_count,iq_size]):
                if astat != args.analysis_stat:
                    df_specific = df_specific[df_specific[astat] == fval]
            df_specific.reset_index(drop = True, inplace = True)
            s = sns.lineplot(df_specific,x=args.analysis_stat,y='efficiency',ax=ax)
            s.set(xlabel=args.analysis_stat,ylabel='$\\epsilon_{FP,max}$')
            ax.set(ylim=(0.0,1.0))

    update_plot(0)

    ssimd_width.on_changed(update_plot)
    ssimd_count.on_changed(update_plot)
    ssimd_lat.on_changed(update_plot)
    ssimd_phreg_count.on_changed(update_plot)
    siq_size.on_changed(update_plot)
    srob_size.on_changed(update_plot)
    #sassoc.on_changed(update_plot)
    #sl1_size.on_changed(update_plot)
    #sld_count.on_changed(update_plot)
    #sst_count.on_changed(update_plot)


    plt.show()



if "__main__" == __name__:
    main()
