#!/usr/bin/env python

import pandas

import argparse
import concurrent.futures
import itertools
import os
import psutil
import re
import sys
import copy

from functools import reduce

MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)


def inner_process(outer_param_dict : dict,
                  inner_param_dict : dict,
                  outer_params : list,
                  inner_params : list,
                  basedir:os.PathLike,
                  kc_regex:re.Pattern,
                  flop_regex:re.Pattern,
                  unroll_regex:re.Pattern,
                  stat_regex:re.Pattern):
    inner_df=pandas.DataFrame()
    param_lists = [inner_param_dict[param] for param in inner_params]
    param_lists += [[outer_param_dict[param]] for param in outer_params]
    combinations = itertools.product(*param_lists)

    params = inner_params+outer_params
    for combo in combinations:
        values = { param : combo[i] for (i,param) in enumerate(params) }
        mr,nr = values['mr_nr']
        lat = values['lat']
        vlen = values['vlen']
        nfu = values['nfu']
        assoc = values['assoc']
        st_count = values['st_count']
        ld_count = values['ld_count']
        l1_size = values['l1_size']
        confname = f"gemm_m5_M{mr}_N{nr}_lat{lat}_vl{vlen}_nfu{nfu}_dw8_cw8_fbs64_l1as{assoc}_st{st_count}_ld{ld_count}_l1d{l1_size}"
        kc = 0
        flops = 0
        unroll = 0
        stats = copy.deepcopy(values)
        del stats["mr_nr"]
        stats["mr"] = mr
        stats["nr"] = nr
        sortindexby = [p for p in params if p != "mr_nr"]+["meas_idx"]
        with open(os.path.join(basedir,f"{confname}.log")) as logfile:
            for line in logfile:
                kc_match = kc_regex.match(line)
                if kc_match:
                    kc = int(kc_match.groups()[0])
                    continue
                flop_match = flop_regex.match(line)
                if flop_match:
                    flops = int(flop_match.groups()[0])
                    continue
                unroll_match = unroll_regex.match(line)
                if unroll_match:
                    unroll = int(unroll_match.groups()[0])
                    continue
        stats["unroll"] = unroll
        stats["flops"] = flops
        stats["kc"] = kc

        filestats = []
        with open(os.path.join(basedir,f"{confname}","stats.txt")) as statfile:
            meas_idx = 0
            runstats = {}
            for line in statfile:
                if line.startswith("---------- End Sim"):
                    runstats["meas_idx"] = meas_idx
                    runstats = stats | runstats
                    filestats.append(runstats)
                    runstats = {}
                    meas_idx+=1
                    continue
                stat_match = stat_regex.match(line)
                if stat_match:
                    key = stat_match.groups()[0]
                    val = float(stat_match.groups()[1])
                    runstats[key] = val
                    
        inner_df = pandas.concat([inner_df,pandas.DataFrame(filestats)])
    df = inner_df.copy()
    # Derivative metrics
    df = df.sort_values(sortindexby)
    df.reset_index(drop=True, inplace=True)
    df["minCyclesPossible"] = (df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"] +\
            df["system.cpu.commitStats0.committedInstType::SimdFloatMult"])/df["nfu"]
    df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]
    data_size = 8 # double
    df["bytesRead"] = df["mr"]*df["kc"]*(df["vlen"]/8) + \
                      df["kc"]*df["nr"]*data_size + \
                      df["mr"]*df["nr"]*(df["vlen"]/8 + \
                      2*data_size)
    df["bytesWritten"] = df["mr"]*df["nr"]*(df["vlen"]/8)
    df.set_index(sortindexby,inplace=True,drop=False)
    df.reset_index(drop=True,inplace=True)
    return df

def extract_data(basedir: os.PathLike):


    param_regex = re.compile(r"gemm_m5_M(\d+)_N(\d+)_lat(\d+)_vl(\d+)_nfu(\d+)_dw8_cw8_fbs64_l1as(\d+)_st(\d+)_ld(\d+)_l1d(\d+)")
    flop_regex = re.compile(r"^Number of FLOPS per measurement:\s+(\d+)\s*$")
    kc_regex = re.compile(r"^k_c:\s+(\d+)\s*$")
    unroll_regex = re.compile(r"^Unroll:\s+(\d+)\s*$")
    stat_regex = re.compile(r"^([a-zA-Z0-9_\.\:]+)\s+([-+]?(([0-9]*[.]?[0-9]+([ed][-+]?[0-9]+)?)|(inf)|(nan)))")

    mr_nr_set = set()
    lat_set = set()
    vlen_set = set()
    nfu_set = set()
    assoc_set = set()
    st_count_set = set()
    ld_count_set = set()
    l1_size_set = set()

    path_iter = os.scandir(basedir)
    print("Generating list of subdirectories")
    dirlist = [d for d in path_iter if d.is_dir()]
    print(f"Subdirectory list generated. Size: {len(dirlist)}")
    for d in dirlist:
        match = param_regex.match(d.name)
        if not match:
            raise RuntimeError(f"Directory {d.name} that doesn't match pattern exists in basedir {basedir}")
        mr,nr,lat,vlen,nfu,assoc,st_count,ld_count,l1_size = match.groups()
        mr_nr_set.add((int(mr),int(nr)))
        lat_set.add(int(lat))
        vlen_set.add(int(vlen))
        nfu_set.add(int(nfu))
        assoc_set.add(int(assoc))
        st_count_set.add(int(st_count))
        ld_count_set.add(int(ld_count))
        l1_size_set.add(int(l1_size))
    param_lists = {}
    param_lists['mr_nr'] = sorted(mr_nr_set)
    param_lists['lat'] = sorted(lat_set)
    param_lists['vlen'] = sorted(vlen_set)
    param_lists['nfu'] = sorted(nfu_set)
    param_lists['assoc'] = sorted(assoc_set)
    param_lists['st_count'] = sorted(st_count_set)
    param_lists['ld_count'] = sorted(ld_count_set)
    param_lists['l1_size'] = sorted(l1_size_set)

    print(f"mr_nr_list: {param_lists['mr_nr']}")
    print(f"lat_list: {param_lists['lat']}")
    print(f"vlen_list: {param_lists['vlen']}")
    print(f"nfu_list: {param_lists['nfu']}")
    print(f"assoc_list: {param_lists['assoc']}")
    print(f"st_count_list: {param_lists['st_count']}")
    print(f"ld_count_list: {param_lists['ld_count']}")
    print(f"l1_size_list: {param_lists['l1_size']}")

    combination_count = reduce(lambda a,b : a*b, [len(l) for l in param_lists.values()])

    alldfs = []
    print(f"Found {combination_count} parameter combinations")
    
    hw_cores = int(os.cpu_count())
    print(f"System has {hw_cores} cpus")

    # We want to schedule n combinations on m threads so that n is the smallest 
    # number of combinations > m
    # For this we split it in outer parameters (for scheduling concurrently) and 
    # inner parameters (that each worker will go through)
    # We start with outer parameters only being kernel size and add parameters
    # that result in the number of combinations closest to number of hw workers
    # until the number of outer combinations is larger than number of hw workers

    # Actually if we start with just kernel size, we have like 5k inner combinations, 
    # which would roughly estimating increase the ram use per worker to around 30GiB,
    # so let's start with more outer params
    outer_params = ["mr_nr","lat","nfu"]
    inner_params = [key for key in param_lists.keys() if key not in outer_params]
    outer_combination_count = reduce(lambda a,b : a*b, [len(l) for l in [param_lists[key] for key in outer_params]])
    inner_combination_count = reduce(lambda a,b : a*b, [len(l) for l in [param_lists[key] for key in inner_params]])

    def calculate_max_ram_cores(combos:int):
        # Ran OOM when using 256 workers on a 256gb machine (this was with ~600 combinations/files
        # per worker, 1TB machine was fine, so let's assume a usage of around 3 GiB and use up to
        # 60% of available RAM
        ram_available = psutil.virtual_memory().total
        # TODO: calculate dynamically based on combinations per worker
        ram_per_worker = 3*2**30/600*combos
        hw_max_ram_cores = int((0.60*ram_available)/ram_per_worker)
        print(f"System has enough memory for {hw_max_ram_cores} concurrent workers")
        return hw_max_ram_cores

    hw_max_ram_cores = calculate_max_ram_cores(inner_combination_count)
    hw_cores = min(hw_cores, hw_max_ram_cores)
    while hw_cores > outer_combination_count:
        counts = [outer_combination_count*len(param_lists[param]) for param in inner_params]
        index_min = counts.index(min(counts))
        outer_params += [inner_params[index_min]]

        inner_params = [key for key in param_lists.keys() if key not in outer_params]
        outer_combination_count = reduce(lambda a,b : a*b, [len(l) for l in [param_lists[key] for key in outer_params]])
        inner_combination_count = reduce(lambda a,b : a*b, [len(l) for l in [param_lists[key] for key in inner_params]])
        hw_max_ram_cores = calculate_max_ram_cores(inner_combination_count)
        hw_cores = min(hw_cores, hw_max_ram_cores)

    print(f"Outer params: {outer_params} ({outer_combination_count} combinations), inner params: {inner_params} ({inner_combination_count} combinations)")

    outer_combinations = itertools.product(*[param_lists[key] for key in outer_params])
    outer_combination_dicts = [ {key : combination[i] for i,key in enumerate(outer_params)} for combination in outer_combinations]

    max_workers = min(hw_cores,outer_combination_count)
    print(f"Processing {outer_combination_count} chunks of {inner_combination_count} combinations with {max_workers} concurrent workers")
    inner_param_dict = {key : l for key,l in param_lists.items() if key in inner_params}
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        inner_done=1

        future_to_odict = {executor.submit(inner_process, 
                                           outer_param_dict,
                                           inner_param_dict,
                                           outer_params,
                                           inner_params,
                                           basedir,
                                           kc_regex,
                                           flop_regex,
                                           unroll_regex,
                                           stat_regex): outer_param_dict for outer_param_dict in outer_combination_dicts}
        for future in concurrent.futures.as_completed(future_to_odict):
            odict = future_to_odict[future]
            try:
                data = future.result()
                print(f"\rprocessed {inner_done*inner_combination_count}/{combination_count} combinations",end='')
                inner_done+=1
            except Exception as exc:
                print(f"Exception during processing of combination {odict}.")
                print(f"exc type: {type(exc)}")
                print(f"exc args: {exc.args}")
                print(f"exc     : {exc}")
            else:
                alldfs.append(data)
        # Because the progress string doesn't have a newline
        print()

    print("Combining dataframes")
    df = pandas.concat(alldfs,axis=0)
    print("Finished combining dataframes")

    #print(df[["efficiency","mr","nr","lat","nfu","vlen"]])
    return df


def main():
    parser = argparse.ArgumentParser(description="Analyze gem5run of gemm benchmarks")
    parser.add_argument("--basedir", metavar="basedir", help='base directory in which output directories were created by gem5', required=True)
    parser.add_argument("--hdf5file", metavar="hdf5file", help='hdf5file to store the DataFrame to', required=True)
    
    args = parser.parse_args()

    basedir = args.basedir
    if not os.path.exists(basedir) or not os.path.isdir(basedir):
        print(f"Not a directory: {basedir}")

    df = extract_data(basedir)

    print(f"Saving dataframe to {args.hdf5file}")
    df.to_hdf(args.hdf5file, "gem5stats", mode='w',complevel=4,complib='blosc:zstd')
    print("done")

if "__main__" == __name__:
    main()
