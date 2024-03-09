#!/usr/bin/env python

import argparse
import itertools
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


from .data_extraction import build_df,index_params

param_tex_names = {
        "mr" : "$m_r$",
        "nr" : "$n_r$",
        "simd_width" : "$w_{SIMD}$",
        "simd_count" : "$N_{SIMD}$",
        "simd_lat" : "$\lambda_{SIMD}$",
        "simd_phreg_count" : "$N_{VRF}$",
        "iq_size" : "$N_{IQ}$",
        "rob_size" : "$N_{ROB}$",
        "assoc" : "$w_{L1D}$",
        "l1_size" : "$S_{L1D}$",
        "ld_count" : "$N_{L1D}$",
        "st_count" : "$N_{ST}$",
        "decode_width" : "$w_{DEC}$",
        "commit_width" : "$w_{COM}$",
        "fetch_buf_size" : "$w_{FB}$",
        "run" : "i_{run}"
        }

reduce_params = [
        "run"
        ]

def pareto(df : pandas.DataFrame,
           analysis_stats : list[str],
           target_stat : str,
           target_thresholds : list[float]):
    pareto_df = pandas.DataFrame()
    df_list = []

    pareto_datapoints = []
    for th in target_thresholds:
        #print(f"pareto for {target_stat} > {th}")
        tdf = df[df[target_stat] > th].copy()
        if tdf.empty:
            continue
        tdf["pareto_threshold"] = th

        astat_max_dict = {astat: tdf[astat].max()
                          for astat in analysis_stats}

        for stats in itertools.permutations(analysis_stats):

            # start with max values for each stat
            astat_datapoint_dict = astat_max_dict.copy()
            for astat in stats:
                # Fix the stats we are not minimizing
                selector = " & ".join([f"{stat} == {vmax}"
                                       for stat,vmax in astat_datapoint_dict.items() 
                                       if stat != astat])
                adf = tdf.query(selector)
                if adf.empty:
                    continue

                # Get index of row with the smallest target_stat
                idx_min_t = adf[target_stat].idxmin()
                # In the edge case where there are multiple rows, get the smallest astat
                min_t = adf.loc[idx_min_t][target_stat]
                edge_case_df = adf[adf[target_stat] == min_t]
                if len(edge_case_df):
                    astat_dp_val = edge_case_df[astat].min()
                else:
                    astat_dp_val = adf.loc[adf[target_stat].idxmin()][astat]
                
                # for the next stat, this value will be set to the minimized value instead of max
                astat_datapoint_dict[astat] = astat_dp_val
            datapoint = tuple(astat_datapoint_dict[astat] for astat in analysis_stats)
            #print(f"pareto datapoint {analysis_stats} = {datapoint}")
            if datapoint not in pareto_datapoints:
                pareto_datapoints.append(datapoint)
                selector = " & ".join([f"{stat} == {vmax}"
                                       for stat,vmax in astat_datapoint_dict.items()])
                df_list.append(tdf.query(selector))
    pareto_df = pandas.concat(df_list)
    print(pareto_df.to_string())
    return pareto_df

def main():
    parser = argparse.ArgumentParser(description="Analyze gem5run of gemm benchmarks")
    parser.add_argument("--stat-dir", metavar="stat_dir",
                        help='Directory containing hdf5 files with the simulation stats',
                        required=True)
    parser.add_argument("--analysis-stat",
                        type=str,
                        nargs=3,
                        metavar="analysis_stat",
                        help='stats to do pareto analysis for ',
                        default=["rob_size","iq_size","simd_phreg_count"])
    parser.add_argument("--target-stat",
                        type=str,
                        metavar="target_stat",
                        help='Stat to minimize in analysis (default: efficiency)',
                        default="efficiency")
    parser.add_argument("--target-thresholds",
                        type=float,
                        nargs='+',
                        metavar="target_thresholds",
                        help='Thresholds for the target stat to use in the analysis (default: "0.5 0.75 0.85 0.90 0.95"',
                        default=[0.5, 0.75, 0.85, 0.90, 0.95])
    
    args = parser.parse_args()

    df = build_df(directory=args.stat_dir,
                  select_stats={},
                  extract_stats=[args.target_stat])

    # filter out analysis stats
    variable_params = [s for s in index_params if s not in args.analysis_stat and s not in reduce_params]
    variable_param_lists = {key : 
                            pandas.unique(df[[key]].values.ravel())
                            for key in variable_params }

    variable_param_lists = {k : v for k,v in variable_param_lists.items() if 1 < len(v)}


    slider_y_step = min(0.05,0.5/len(variable_param_lists))
    
    grid_kws = {'width_ratios': (1.0,), 'wspace': 0.2}
    fig, ax = plt.subplots(1,1,gridspec_kw=grid_kws)
    fig.subplots_adjust(
            bottom=0.2+slider_y_step*(len(variable_param_lists)+1),
            right=1.0)

    variable_param_axes = {key : 
                           fig.add_axes(
                               [0.25, 0.1+i*slider_y_step, 0.65, 0.03])
                           for i,key in enumerate(variable_param_lists.keys())}

    variable_param_sliders = {
            key : Slider(
                ax=variable_param_axes[key],
                label=param_tex_names[key],
                valmin=min(variable_param_lists[key]),
                valmax=max(variable_param_lists[key]),
                valinit=variable_param_lists[key][0],
                valstep=variable_param_lists[key],
                initcolor="none"
                )
            for key in variable_param_lists.keys()
            }


    target_thresholds = [float(th) for th in args.target_thresholds]


    threshold_ax = fig.add_axes(
            [0.25,0.1+len(variable_param_lists)*slider_y_step,0.65,0.03]
            )

    threshold_slider = Slider(
            ax=threshold_ax,
            label="$\\epsilon_{FP,thresh}$",
            valmin=min(target_thresholds),
            valmax=max(target_thresholds),
            valinit=target_thresholds[0],
            valstep=target_thresholds,
            initcolor="none"
            )
    full_pareto_df = pandas.DataFrame()

    def update_threshold(val):
        nonlocal ax
        nonlocal full_pareto_df

        ax.cla()
        pareto_df = full_pareto_df[full_pareto_df["pareto_threshold"] == threshold_slider.val]

        sp = sns.scatterplot(ax=ax, data=pareto_df, 
                        x=args.analysis_stat[0],
                        y=args.analysis_stat[1],
                        hue=args.analysis_stat[2])

        ax.set_xlabel(param_tex_names[args.analysis_stat[0]])
        ax.set_ylabel(param_tex_names[args.analysis_stat[1]])
        sp.legend(title=param_tex_names[args.analysis_stat[2]])

        ax.set(
                xlim=(df[args.analysis_stat[0]].min(),df[args.analysis_stat[0]].max()),
                ylim=(df[args.analysis_stat[1]].min(),df[args.analysis_stat[1]].max()),
                )

    def update_plot(val):
        nonlocal ax
        nonlocal full_pareto_df

        selector = " & ".join([f"{key} == {slider.val}" for key,slider in variable_param_sliders.items()])
        if selector:
            df_specific = df.query(selector)
        else:
            df_specific = df


        df_specific = df_specific.groupby(variable_params, group_keys=False).apply(lambda x: x.loc[x[args.target_stat].idxmax()])
        df_specific.reset_index(drop = True, inplace = True)


        full_pareto_df = pareto(df=df_specific, 
               analysis_stats=args.analysis_stat, 
               target_stat=args.target_stat, 
               target_thresholds=target_thresholds)

        update_threshold(val)

    update_plot(0)

    for k,v in variable_param_sliders.items():
        v.on_changed(update_plot)

    threshold_slider.on_changed(update_threshold)

    plt.show()



if "__main__" == __name__:
    main()
