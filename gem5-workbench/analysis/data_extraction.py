
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

def extract_target(select_stats  :dict[str,int],
                   target_stats  :Union[str,list[str]],
                   statfile_path :os.PathLike):
    try:
        df = pandas.read_hdf(statfile_path, key="gem5stats")
    except Exception as exc:
        print(f"error occured: {exc}")

    df["minCyclesPossible"] = (df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"] +\
            df["system.cpu.commitStats0.committedInstType::SimdFloatMult"])/df["simd_count"]
    df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]

    selector = " & ".join([f"(df['{key}'] == {value})" for key,value in select_stats.items()])
    if selector:
        df = df[eval(selector)]
    if isinstance(target_stats,str):
        if "all" == target_stats:
            return df
        else:
            raise RuntimeError(f"Invalid value: target_stats=\"{target_stats}\"")
    else:
        return df[index_params+target_stats]

def build_df(directory: os.PathLike,
             select_stats: dict,
             target_stats: Union[str,list[str]] = "all" ):
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
                        target_stats
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

    return stat_df
