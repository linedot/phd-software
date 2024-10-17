"""
This is a custom gem5 simulation script for running the parameterized nanogemm 
benchmark on a parameterized architecture
"""


import argparse
import itertools
import os
import psutil
import math
import concurrent.futures
import functools
import resource
import signal
import sys
import tqdm
import socket
from queue import Empty

import m5
import gem5.utils.multiprocessing as gem5mp
from gem5.utils.multiprocessing.context import gem5Context

from resultdb import resultdb
from simargs import process_arguments
from simrun import simrun
from stats import build_stat_tree, prepare_statdict, append_stats

sim_params = ['mr','nr',
              'simd_lat','simd_count','simd_width',
              'simd_phreg_count',
              'ld_count','st_count',
              'cl_size',
              'l1_size',
              'assoc',
              'iq_size',
              'rob_size',
              'decode_width', 'commit_width',
              'fetch_buf_size'
              ]

def main():

    ram_available = psutil.virtual_memory().total
    # Let's see if we can stop memuse explosions with this
    softlimit = int(0.75*ram_available)
    hardlimit = int(0.9*ram_available)
    resource.setrlimit(resource.RLIMIT_AS, (softlimit,hardlimit))

    args = process_arguments()
    argdict = vars(args)



    # Create parameter combinations

    param_lists = [argdict[p] for p in sim_params]

    isa = args.isa

    # Non-List problematic
    combinations = list(itertools.product(*param_lists))
    combination_count = len(combinations)

    max_vregs = 32
    # Filter invalid mr/nr combinations
    print("filtering out invalid mr/nr combinations")
    combinations = [combo for combo in combinations if max_vregs > (combo[0]*combo[1]+combo[0]*2+1)]
    print(f"Filtered out {combination_count - len(combinations)} combinations")

    combination_count = len(combinations)
    print(f"Number of combinations: {combination_count}")

    from mpi4py import MPI

    comm = MPI.COMM_WORLD
    mpi_size = comm.Get_size()
    mpi_rank = comm.Get_rank()

    chunksize = combination_count//(mpi_size-1)

    if 0 != mpi_rank:
        combo_start = chunksize*(mpi_rank-1)
        if mpi_rank != mpi_size-1:
            combo_end = chunksize*(mpi_rank)
            combinations = combinations[combo_start:combo_end]
            print(f"MPI rank {mpi_rank} will work on combinations [{combo_start}:{combo_end}]")
        else:
            combinations = combinations[combo_start:]
            print(f"MPI rank {mpi_rank} will work on combinations [{combo_start}:]")

    combination_count = len(combinations)
    print(f"Number of combinations: {combination_count}")

    # MPI STUFF

    if 0 == mpi_rank:
        s=socket.socket()
        s.bind(("",0))
        port = s.getsockname()[1]
        s.close()
        hostname = socket.gethostname()
        if args.db_jsc_hostname:
            hostname += 'i'
    else:
        hostname = None 
        port = None

    hostname = comm.bcast(hostname, root=0)
    port = comm.bcast(port, root=0)

    db = resultdb(basedir=args.db_base_dir,
                  hostname=hostname,
                  port=port,
                  tablename=args.db_table_name,
                  resetdata=args.db_table_reset)

    if 0 == mpi_rank:
        db.startpg()

    comm.barrier()

    if 0 != mpi_rank:
        hw_cores = int(os.cpu_count())
        print(f"System has {hw_cores} hardware cores")
        ram_per_worker = 800*2**20
        hw_max_ram_cores = int((0.50*ram_available)/ram_per_worker)
        print(f"System has enough memory for {hw_max_ram_cores} concurrent workers")
        hw_cores = min(hw_cores, hw_max_ram_cores)
        max_workers = min(hw_cores, combination_count)
        max_workers = min(max_workers,128) # 256 workers on jusuf seems to be slow?
        max_workers = max(max_workers,1)   # Use at least 1 worker


        sim_worker_count = max_workers


        # Ignore signals in the pool
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # Suppress file creation
        m5.options.outdir="/dev/null"
        m5.options.no_output_files=True
        m5.options.dump_config=False
        m5.options.json_config=False
        m5.options.dot_config=False
        m5.options.dot_dvfs_config=False
        m5.core.setOutputDir("/dev/null")
        if args.quiet:
            # Suppress spamming the terminal
            m5.options.quiet=True
            m5.options.redirect_stderr=True
            m5.options.redirect_stdout=True
            m5.options.silent_redirect=True
            m5.options.stderr_file="/dev/null"
            m5.options.stdout_file="/dev/null"

        pool = gem5mp.Pool(processes=sim_worker_count,
                           maxtasksperchild=1)
        # The previous signal call is supposed to return the "default"
        # signal handler, but somehow it isn't a valid handler with gem5
        # Therefore let's just set one that will terminate the program
        # TODO: exit gracefully
        def stop_processes_and_exit(sig,frame):
            pool.terminate()
            #for p in dp_processes:
            #    p.terminate()
            exit(-1)
        signal.signal(signal.SIGINT, stop_processes_and_exit)


        try:
            for result in tqdm.tqdm(pool.imap_unordered(
                    functools.partial(
                        simrun, isa, db
                        ),
                        combinations
                    ),
                    unit='sim',
                    desc='Simulating: ',
                    total=combination_count,
                    delay=1,
                    smoothing=0.1,
                    position=args.tqdm_position):
                sys.stdout.flush()

        except KeyboardInterrupt:
            print("Keyboard interrupt received, terminating pool")
            pool.terminate()
        else:
            print("Closing sim worker pool")
            pool.close()
        print("Joining simulation pool")
        pool.join()

    comm.barrier()

    if 0 == mpi_rank:
        conn = db.connect()
        cursor = conn.cursor()
        row_count = db.get_row_count(cursor)
        conn.close()
        db.stoppg()

        print(f"Rows in database: {row_count}")


if __name__ == "__main__":
    main()

if __name__ == "__m5_main__":
    # So basically the __m5_main__ thing messes up multiprocessing, so 
    # run it again with __main__
    import runpy
    runpy.run_path(__file__, run_name="__main__")

