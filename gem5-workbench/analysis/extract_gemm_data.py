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

from .data_extraction import build_df


def main():
    parser = argparse.ArgumentParser(description="Analyze gem5run of gemm benchmarks")
    parser.add_argument("--basedir", metavar="basedir", help='Base directory where simulation results are stored', required=True)
    parser.add_argument("--select", metavar="select", nargs='+', help='Select values, i.e "--select mr=2 nr=10 vlen=512"', default=[])
    parser.add_argument("--extract", metavar="extract", nargs='+', help='extract these values, i.e "efficiency,numCycles"', default=["all"])
    parser.add_argument("--inspect", metavar="inspect", nargs='+', help='inspect these values, i.e "efficiency,numCycles"', default=[])
    parser.add_argument("--list-stats", help='list available stats', action='store_true', default=False)
    parser.add_argument("--output", metavar="output", help='File to store the output to, extension must be either .h5 (for HDF5) or .csv for (CSV)', required=True)
    
    args = parser.parse_args()

    basedir = args.basedir
    if not os.path.exists(basedir) or not os.path.isdir(basedir):
        print(f"Not a directory: {basedir}")

    extract=args.extract
    if 1 == len(extract):
        if "all" == extract[0]:
            extract=extract[0]
    inspect=args.inspect

    stat_selection = {}
    for argsel in args.select:
        key,value = argsel.split("=")
        value = int(value)
        print(f"selecting {key} = {value}")
        stat_selection[key] = value


    df = build_df(basedir,
                  select_stats=stat_selection,
                  extract_stats=extract,
                  inspect_stats=inspect)

    if args.list_stats:
        print("Available stats:")
        for stat_name in df.columns.values:
            print(stat_name)
        exit(0)

    print(f"Saving dataframe to {args.output}")
    if args.output.endswith(".h5"):
        df.to_hdf(args.output, "gem5stats", mode='w',complevel=4, complib='blosc:zstd')
    elif args.output.endswith(".csv"):
        df.to_csv(args.output)

    print("done")

if "__main__" == __name__:
    main()
