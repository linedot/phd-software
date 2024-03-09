
import pandas
import os
import sys

from typing import Union

MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)


index_params = ["mr","nr",
                "simd_lat","simd_count","simd_width","simd_phreg_count",
                "ld_count","st_count",
                "l1_size","assoc",
                "decode_width","commit_width",
                "iq_size","rob_size",
                "fetch_buf_size",
                "run"]

def inspect_changing(df : pandas.DataFrame,
                     inspection_stats : list[str],
                     rel_diff_threshold : float):

    changed_with_dict = {stat : [] for stat in inspection_stats}
    istat_diff_dict = {stat: 0.0 for stat in inspection_stats}
    istat_val_dict = {stat: 0.0 for stat in inspection_stats}
    chstat_diff_dict = {stat : [] for stat in inspection_stats}
    chstat_val_dict = {stat : [] for stat in inspection_stats}
    for stat in inspection_stats:
        sorted_df = df.sort_values(by=stat).copy()
        changed_selector = sorted_df[stat].diff().abs() > 0
        stat_changed_df = sorted_df[changed_selector]
        istat_diff_dict[stat] = stat_changed_df[stat].diff().values
        istat_val_dict[stat] = stat_changed_df[stat].values

        # There might be a better way than dot-product-to-str and then split
        changed_series = stat_changed_df.diff().abs().gt(stat_changed_df.abs()*rel_diff_threshold).dot(stat_changed_df.columns+',').str[:-1] 
        changed_series = changed_series.apply(lambda x : x.split(','))
        changed_with_dict[stat]  = changed_series.values


        # Same here - there must be a more graceful way to do this
        chstat_val_dict[stat] = [row[stat_list].values if \
                not ((stat_list[0] == '') and (len(stat_list) == 1)) else\
                [0] for stat_list,(index,row) in \
                zip(changed_series,
                    sorted_df[changed_selector].iterrows()) ]
        chstat_diff_dict[stat] = [row[stat_list].values if \
                not ((stat_list[0] == '') and (len(stat_list) == 1)) else\
                [0] for stat_list,(index,row) in \
                zip(changed_series,
                    sorted_df.diff()[changed_selector].iterrows()) ]

    for stat in inspection_stats:
        print(f"changed with {stat}:")
        for changed_stat_list,idiff,ival,chstat_diff_list,chstat_val_list in\
                zip(changed_with_dict[stat][1:],
                    istat_diff_dict[stat][1:],
                    istat_val_dict[stat][1:],
                    chstat_diff_dict[stat][1:],
                    chstat_val_dict[stat][1:]):
            if (len(changed_stat_list) == 1) and (changed_stat_list[0] == stat):
                continue
            if (len(changed_stat_list) == 1) and \
                    (chstat_diff_list[0] == 0) and \
                    (chstat_val_list[0] == 0):
                continue
            print(f"\t{stat} changes {ival-idiff:.2f} -> {ival:.2f}:")
            for changed_stat,changed_val,changed_diff in \
                    zip(changed_stat_list,
                        chstat_val_list,
                        chstat_diff_list):
                print(f"\t\t{changed_stat} {changed_val-changed_diff:.3f} -> {changed_val:.3f}")

def extract_target(select_stats  :dict[str,int],
                   inspect_stats :Union[str,list[str]],
                   extract_stats :Union[str,list[str]],
                   statfile_path :os.PathLike):
    try:
        df = pandas.read_hdf(statfile_path, key="gem5stats")
    except Exception as exc:
        print(f"error occured: {exc}")

    df["minCyclesPossible"] = (df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"] +\
            df["system.cpu.commitStats0.committedInstType::SimdFloatMult"])/df["simd_count"]
    df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]

    selector = " & ".join([f"{key} == {value}" for key,value in select_stats.items()])
    if selector:
        df = df.query(selector)

    if isinstance(extract_stats,str):
        if "all" == extract_stats:
            return df
        else:
            raise RuntimeError(f"Invalid value: extract_stats=\"{extract_stats}\"")
    else:
        return df[index_params+extract_stats]




def build_df(directory: os.PathLike,
             select_stats: dict,
             inspect_stats: list[str] = [],
             extract_stats: Union[str,list[str]] = "all" ):
    import tqdm
    import multiprocessing as mp
    from multiprocessing.pool import Pool
    import psutil
    import functools


    statfile_list = []
    for root, _, files in os.walk(directory, topdown=False):
        for name in files:
            if name.endswith(".h5"):
                statfile_list.append(os.path.join(root, name))

    statfile_count = len(statfile_list)

    ram_available = psutil.virtual_memory().total
    hw_cores = int(os.cpu_count())
    print(f"System has {hw_cores} hardware cores")
    ram_per_worker = 20000*2**20
    hw_max_ram_cores = int((0.50*ram_available)/ram_per_worker)
    print(f"System has enough memory for {hw_max_ram_cores} concurrent workers")
    hw_cores = min(hw_cores, max(hw_max_ram_cores,1))
    max_workers = min(hw_cores, statfile_count)

    stat_df = pandas.DataFrame()
    df_list = []
    df_merge_count = 100
    with Pool(max_workers) as pool:
        for result in tqdm.tqdm(
                pool.imap_unordered(
                    functools.partial(
                        extract_target,
                        select_stats,
                        inspect_stats,
                        extract_stats
                        ),
                        statfile_list
                    ),
                unit='files',
                desc='Extracting data: ',
                total=statfile_count,
                delay=1,
                smoothing=0.1,
                ):
            if stat_df.empty:
                stat_df = result
            else:
                df_list.append(result)

            if len(df_list) > df_merge_count:
                stat_df = pandas.concat([stat_df]+df_list)
                df_list = []

    if df_list:
        stat_df = pandas.concat([stat_df]+df_list)
        df_list = []

    inspect_changing(df=stat_df, 
                     inspection_stats=inspect_stats, 
                     rel_diff_threshold=0.02)

    return stat_df
