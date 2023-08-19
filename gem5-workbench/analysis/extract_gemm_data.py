#!/usr/bin/env python

import argparse
import os
import re
import pandas
import concurrent.futures

import sys
MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)


def mr_nr_process(mr:int, nr:int, 
                  lat_list:list, 
                  vlen_list:list, 
                  nfu_list:list, 
                  assoc_list:list, 
                  basedir:os.PathLike,
                  kc_regex:re.Pattern,
                  flop_regex:re.Pattern,
                  unroll_regex:re.Pattern,
                  stat_regex:re.Pattern):
    mr_nr_data=[]
    for lat in lat_list:
        for vlen in vlen_list:
            for nfu in nfu_list:
                for assoc in assoc_list:
                    confname = f"gemm_m5_M{mr}_N{nr}_lat{lat}_vl{vlen}_nfu{nfu}_dw8_cw8_fbs64_l1as{assoc}"
                    kc = 0
                    flops = 0
                    unroll = 0
                    stats = {"mr":mr, "nr":nr, "lat":lat, "vlen":vlen, "nfu":nfu, "assoc":assoc}
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

                    with open(os.path.join(basedir,f"{confname}","stats.txt")) as statfile:
                        meas_idx = 0
                        runstats = {}
                        for line in statfile:
                            if line.startswith("---------- End Sim"):
                                runstats["meas_idx"] = meas_idx
                                runstats = stats | runstats
                                mr_nr_data.append(runstats)
                                runstats = {}
                                meas_idx+=1
                                continue
                            stat_match = stat_regex.match(line)
                            if stat_match:
                                key = stat_match.groups()[0]
                                val = float(stat_match.groups()[1])
                                runstats[key] = val
    df = pandas.DataFrame(mr_nr_data)
    # Derivative metrics
    df = df.sort_values(["vlen","nfu","lat","mr","nr","meas_idx"])
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
    df.set_index(["mr","nr","lat","nfu","vlen","assoc","meas_idx"],inplace=True,drop=False)
    df.reset_index(drop=True,inplace=True)
    return df

def extract_data(basedir: os.PathLike):

    pathlist = [x for x in os.listdir(basedir)]

    dirlist = [d for d in pathlist if os.path.isdir(os.path.join(basedir,d))]

    param_regex = re.compile(r"gemm_m5_M(\d+)_N(\d+)_lat(\d+)_vl(\d+)_nfu(\d+)_dw8_cw8_fbs64_l1as(\d+)")
    flop_regex = re.compile(r"^Number of FLOPS per measurement:\s+(\d+)\s*$")
    kc_regex = re.compile(r"^k_c:\s+(\d+)\s*$")
    unroll_regex = re.compile(r"^Unroll:\s+(\d+)\s*$")
    stat_regex = re.compile(r"^([a-zA-Z0-9_\.\:]+)\s+([-+]?(([0-9]*[.]?[0-9]+([ed][-+]?[0-9]+)?)|(inf)|(nan)))")

    mr_nr_set = set()
    lat_set = set()
    vlen_set = set()
    nfu_set = set()
    assoc_set = set()

    for dir in dirlist:
        match = param_regex.match(dir)
        if not match:
            raise RuntimeError(f"Directory {dir} that doesn't match pattern exists in basedir {basedir}")
        mr,nr,lat,vlen,nfu,assoc = match.groups()
        mr_nr_set.add((int(mr),int(nr)))
        lat_set.add(int(lat))
        vlen_set.add(int(vlen))
        nfu_set.add(int(nfu))
        assoc_set.add(int(assoc))
    mr_nr_list = sorted(mr_nr_set)
    lat_list = sorted(lat_set)
    vlen_list = sorted(vlen_set)
    nfu_list = sorted(nfu_set)
    assoc_list = sorted(assoc_set)

    print(f"mr_nr_list: {mr_nr_list}")
    print(f"lat_list: {lat_list}")
    print(f"vlen_list: {vlen_list}")
    print(f"nfu_list: {nfu_list}")
    print(f"assoc_list: {assoc_list}")

    mr_nr_combination_count = len(mr_nr_list)
    # TODO: calculate analytically instead of being lazy
    # for mr in mr_list:
    #     for nr in nr_list:
    #         if nr > (32-(2*mr+1))/mr:
    #             continue
    #         mr_nr_combination_count+=1
    per_mr_nr_count = len(lat_list)*len(vlen_list)*len(nfu_list)*len(assoc_list)
    combination_count = mr_nr_combination_count*per_mr_nr_count
    alldfs = []


    print(f"Found {combination_count} parameter combinations")

    max_workers = min(os.cpu_count(),mr_nr_combination_count)
    print(f"Processing {mr_nr_combination_count} chunks of {per_mr_nr_count} combinations with {max_workers} concurrent workers")
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        mr_nr_done=1

        #def mr_nr_process(mr:int, nr:int, lat_list, vlen_list, nfu_list, assoc_list, basedir, kc_regex, flop_regex, unroll_regex, stat_regex):
        future_to_mrnr = {executor.submit(mr_nr_process, 
                                          mr, nr,
                                          lat_list,
                                          vlen_list,
                                          nfu_list,
                                          assoc_list,
                                          basedir,
                                          kc_regex,
                                          flop_regex,
                                          unroll_regex,
                                          stat_regex): (mr,nr) for mr,nr in mr_nr_list}
        for future in concurrent.futures.as_completed(future_to_mrnr):
            mr,nr = future_to_mrnr[future]
            try:
                data = future.result()
                print(f"\rprocessed {mr_nr_done*per_mr_nr_count}/{combination_count} combinations",end='')
                mr_nr_done+=1
            except Exception as exc:
                print(f"Exception during processing of ({mr},{nr}) combos: {exc}")
            else:
                alldfs.append(data)
        # Because the progress string doesn't have a newline
        print()

    print("Combining dataframes")
    df = pandas.concat(alldfs,axis=0)
    print("Finished combining dataframes")

    print(df[["efficiency","mr","nr","lat","nfu","vlen"]])
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
