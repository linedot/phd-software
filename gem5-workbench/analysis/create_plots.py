#!/usr/bin/env python

import argparse
import pandas
import matplotlib

import sys
MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

def main():
    parser = argparse.ArgumentParser(description="Analyze gem5run of gemm benchmarks")
    parser.add_argument("--hdf5file", metavar="hdf5file", help='hdf5file to store the DataFrame to', required=True)
    
    args = parser.parse_args()


    df = pandas.read_hdf(args.hdf5file,key='gem5stats')

    df["minCyclesPossible"] = df["system.cpu.commitStats0.committedInstType::SimdFloatMultAcc"]/df["nfu"]
    df["efficiency"] = df["minCyclesPossible"]/df["system.cpu.numCycles"]
    data_size = 8 # double
    df["bytesRead"] = df["mr"]*df["kc"]*df["vlen"]/8 + df["kc"]*df["nr"]*data_size + df["mr"]*df["nr"]*data_size
    df["bytesWritten"] = df["mr"]*df["nr"]*data_size

    efficient_nfu2_lat4_vlen128 = df[(df["efficiency"] > 0.95) & (df["mr"] == 2) & (df["lat"] == 4) & (df["vlen"] == 128)]
    efficient_nfu2_lat4_vlen256 = df[(df["efficiency"] > 0.95) & (df["mr"] == 2) & (df["lat"] == 4) & (df["vlen"] == 256)]
    efficient_nfu2_lat4_vlen512 = df[(df["efficiency"] > 0.95) & (df["mr"] == 2) & (df["lat"] == 4) & (df["vlen"] == 512)]
    efficient_nfu2_lat4_vlen1024 = df[(df["efficiency"] > 0.95) & (df["mr"] == 2) & (df["lat"] == 4) & (df["vlen"] == 1024)]

    most_efficient_128_idx = efficient_nfu2_lat4_vlen128["efficiency"].idxmax()
    most_efficient_128 = efficient_nfu2_lat4_vlen128.loc[most_efficient_128_idx]
    most_efficient_256_idx = efficient_nfu2_lat4_vlen256["efficiency"].idxmax()
    most_efficient_256 = efficient_nfu2_lat4_vlen256.loc[most_efficient_256_idx]
    most_efficient_512_idx = efficient_nfu2_lat4_vlen512["efficiency"].idxmax()
    most_efficient_512 = efficient_nfu2_lat4_vlen512.loc[most_efficient_512_idx]
    most_efficient_1024_idx = efficient_nfu2_lat4_vlen1024["efficiency"].idxmax()
    most_efficient_1024 = efficient_nfu2_lat4_vlen1024.loc[most_efficient_1024_idx]

    print(most_efficient_128[["mr","nr","vlen","assoc","flops","efficiency","bytesRead","system.cpu.numCycles"]])
    print(most_efficient_256[["mr","nr","vlen","assoc","flops","efficiency","bytesRead","system.cpu.numCycles"]])
    print(most_efficient_512[["mr","nr","vlen","assoc","flops","efficiency","bytesRead","system.cpu.numCycles"]])
    print(most_efficient_1024[["mr","nr","vlen","assoc","flops","efficiency","bytesRead","system.cpu.numCycles"]])

if "__main__" == __name__:
    main()
