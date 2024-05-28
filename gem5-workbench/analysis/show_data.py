#!/usr/bin/env python

import argparse
import pandas
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
sns.set(font_scale=1.5)

import sys
MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

def main():
    parser = argparse.ArgumentParser(description="Analyze gem5run of gemm benchmarks")
    parser.add_argument("--hdf5file", metavar="hdf5file", help='hdf5file to read the DataFrame from', required=True)
    parser.add_argument("--columns", metavar="columns", nargs='+', help='columns to display', default=['mr','nr','simd_lat','kc','efficiency'])
    
    args = parser.parse_args()

    df = pandas.read_hdf(args.hdf5file,key='gem5stats')

    with pandas.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        print(df[args.columns])

if "__main__" == __name__:
    main()
