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

    csvfile = str(args.hdf5file).replace(".h5",".csv")

    df.to_csv(csvfile)

if "__main__" == __name__:
    main()
