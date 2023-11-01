# Copyright (c) 2015 Jason Power
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
This is the ARM equivalent to `simple.py` (which is designed to run using the
X86 ISA). More detailed documentation can be found in `simple.py`.
"""


import argparse
import itertools
import os
import psutil
import math
import concurrent.futures

import pandas as pd


def prepare_statdict(statmap):
    import _m5.stats
    statdict = {}
    statdict["mr"] = []
    statdict["nr"] = []
    statdict["simd_lat"] = []
    statdict["simd_count"] = []
    statdict["simd_width"] = []
    statdict["simd_phreg_count"] = []
    statdict["ld_count"] = []
    statdict["st_count"] = []
    statdict["l1_size"] = []
    statdict["rob_size"] = []
    statdict["assoc"] = []
    statdict["decode_width"] = []
    statdict["commit_width"] = []
    statdict["fetch_buf_size"] = []
    statdict["run"] = []
    for name,stat in statmap.items():
        stat.prepare()
        if isinstance(stat,_m5.stats.FormulaInfo):
            if len(stat.subnames) > 1:
                for sname in stat.subnames:
                    if sname == "":
                        continue
                    statdict[f"{name}::{sname}"] = []
            else:
                statdict[f"{name}"] = []
        elif isinstance(stat,_m5.stats.ScalarInfo):
            statdict[f"{name}"] = []
        elif isinstance(stat, _m5.stats.DistInfo):
            for i,v in enumerate(stat.values):
                bucket_start = stat.min_val+i*stat.bucket_size
                if bucket_start.is_integer():
                    bucket_start = int(bucket_start)
                bucket_end = stat.min_val+(i+1)*stat.bucket_size-1
                if bucket_end.is_integer():
                    bucket_end = int(bucket_end)
                bucket = f"{bucket_start}-{bucket_end}"
                if bucket_end == bucket_start:
                    bucket = f"{bucket_start}"
                statdict[f"{name}::{bucket}"] = []
            statdict[f"{name}::min_value"] = []
            statdict[f"{name}::max_value"] = []
            statdict[f"{name}::mean"] = []
            statdict[f"{name}::stddev"] = []
            statdict[f"{name}::samples"] = []
            statdict[f"{name}::total"] = []
            statdict[f"{name}::overflows"] = []
        elif isinstance(stat, _m5.stats.VectorInfo):
            for sname,sval in zip(stat.subnames,stat.value):
                if sname == "":
                    continue
                statdict[f"{name}::{sname}"] = []
    return statdict


def append_stats(statmap, statdict):
    import _m5.stats
    import functools
    for name,stat in statmap.items():
        stat.prepare()
        if isinstance(stat,_m5.stats.FormulaInfo):
            if len(stat.subnames) > 1:
                for sname,sval in zip(stat.subnames,stat.value):
                    if sname == "":
                        continue
                    statdict[f"{name}::{sname}"].append(sval)
            else:
                val = stat.result
                statdict[f"{name}"].append(val[0])
        elif isinstance(stat,_m5.stats.ScalarInfo):
            statdict[f"{name}"].append(stat.result)
        elif isinstance(stat, _m5.stats.DistInfo):
            for i,v in enumerate(stat.values):
                bucket_start = stat.min_val+i*stat.bucket_size
                if bucket_start.is_integer():
                    bucket_start = int(bucket_start)
                bucket_end = stat.min_val+(i+1)*stat.bucket_size-1
                if bucket_end.is_integer():
                    bucket_end = int(bucket_end)
                bucket = f"{bucket_start}-{bucket_end}"
                if bucket_end == bucket_start:
                    bucket = f"{bucket_start}"
                # Sometimes the bucket doesn't exist.
                # In this case initialize the value list with as many
                # zeroes as there are elements in the min_val list, as
                # min_val should have been recorded every time
                must_len = len(statdict[f"{name}::min_value"])
                if f"{name}::{bucket}" not in statdict:
                    statdict[f"{name}::{bucket}"] = [0]*must_len
                # Also if the bucket exists, but the len is too small, 
                # fill the missing values with zeroes
                bucket_vlist_len = len(statdict[f"{name}::{bucket}"])
                if must_len > bucket_vlist_len:
                    statdict[f"{name}::{bucket}"].extend([0]*(must_len-bucket_vlist_len))
                statdict[f"{name}::{bucket}"].append(v)
            statdict[f"{name}::min_value"].append(stat.min_val)
            statdict[f"{name}::max_value"].append(stat.max_val)
            count = functools.reduce(lambda a,b : a+b, stat.values, 0)
            statdict[f"{name}::mean"].append(stat.sum/max(1.0,count))
            stddev = math.sqrt(
                              max(0.0,(stat.squares*count - stat.sum*stat.sum))/
                              max(1.0,(count*(count-1.0))))
            statdict[f"{name}::stddev"].append(stddev)
            statdict[f"{name}::samples"].append(count)
            statdict[f"{name}::total"].append(stat.sum)
            statdict[f"{name}::overflows"].append(stat.overflow)
        elif isinstance(stat, _m5.stats.VectorInfo):
            for sname,sval in zip(stat.subnames,stat.value):
                if sname == "":
                    continue
                statdict[f"{name}::{sname}"].append(sval)
        elif isinstance(stat, _m5.stats.Info):
            pass
            # I'm not sure what to do with a _m5.stats.Info object?
            #print(f"{name}{stat.name}/unit = {stat.unit}")
            #print(f"{name}{stat.name}/flags = {stat.flags}")
            #print(f"{name}{stat.name}/desc = {stat.desc}")
        else:
            print("%s is a %s and has %s" %(f"{name}{stat.name}",type(stat),dir(stat)))


def build_stat_tree(statmap : dict, name: str, groups):
    for key in groups:
        group = groups[key]
        subgroups = group.getStatGroups()
        if 0 != len(subgroups):
            build_stat_tree(statmap, f"{name}{key}.", subgroups)
        stats = group.getStats()
        statmap.update({f"{name}{key}.{stat.name}" : stat for stat in stats if f"{name}{stat.name}" not in statmap })

def lcm(a, b):
    return abs(a*b) // math.gcd(a, b)

def setup_cpu(isa:str,
              simd_lat:int, simd_count:int, 
              simd_width:int, simd_phreg_count:int,
              ld_count:int, st_count:int,
              rob_size:int,
              assoc:int, l1_size:int,
              decode_width:int, commit_width:int,
              fetch_buf_size: int):

    import m5
    from m5.objects import ArmISA, RiscvISA
    from gem5.utils.requires import requires
    from gem5.isas import ISA

    # Bine's N1 model
    from common.cores.arm.O3_ARM_Neoverse_N1 import O3_ARM_Neoverse_N1,O3_ARM_Neoverse_N1_but_RISCV,O3_ARM_Neoverse_N1_ICache,O3_ARM_Neoverse_N1_DCache
        

    if "aarch64" == isa:
        requires(isa_required=ISA.ARM)
        cpu_isa = ArmISA(sve_vl_se=simd_width/128)
        cpu = O3_ARM_Neoverse_N1(isa=cpu_isa)
    elif "riscv64" == isa:
        requires(isa_required=ISA.RISCV)
        cpu_isa = RiscvISA(vlen=simd_width)
        cpu = O3_ARM_Neoverse_N1_but_RISCV(isa=cpu_isa)
    else:
        raise RuntimeError(f"Unsupported ISA: {isa}")

    cpu.decodeWidth=decode_width
    cpu.fetchWidth=decode_width
    cpu.commitWidth=commit_width

    cpu.numROBEntries = rob_size
    cpu.numPhysFloatRegs = simd_phreg_count
    cpu.numPhysVecRegs = simd_phreg_count

    cpu.fetchBufferSize=fetch_buf_size

    for fu in cpu.fuPool.FUList:
        for op in fu.opList:
            if ('SimdFloatMultAcc' == str(op.opClass)):
                op.opLat = simd_lat
                fu.count = simd_count
            elif ('VectorFloatArith' == str(op.opClass)):
                op.opLat = simd_lat
                fu.count = simd_count
            elif ('MemWrite' == str(op.opClass)):
                fu.count = st_count
            elif ('MemRead' == str(op.opClass)):
                fu.count = ld_count

    cpu.icache = O3_ARM_Neoverse_N1_ICache()
    cpu.dcache = O3_ARM_Neoverse_N1_DCache()
    cpu.dcache.assoc = assoc
    cpu.dcache.size = f"{l1_size}kB"

    cpu.icache.cpu_side = cpu.icache_port
    cpu.dcache.cpu_side = cpu.dcache_port

    return cpu

def setup_system(isa:str, mr:int, nr:int, simd_width:int, cpu):
    import m5
    from m5.objects import System, SrcClockDomain, VoltageDomain, AddrRange, SystemXBar, MemCtrl, DDR4_2400_8x8, SEWorkload, Process

    system = System()

    system.exit_on_work_items = True

    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = "1GHz"
    system.clk_domain.voltage_domain = VoltageDomain()

    system.mem_mode = "timing"
    system.mem_ranges = [AddrRange("256MiB")]
    #system.cpu = cpu

    system.membus = SystemXBar()
    #system.cpu.icache.mem_side = system.membus.cpu_side_ports
    #system.cpu.dcache.mem_side = system.membus.cpu_side_ports

    #system.cpu.icache_port = system.membus.cpu_side_ports
    #system.cpu.dcache_port = system.membus.cpu_side_ports

    #system.cpu.createInterruptController()

    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR4_2400_8x8(device_size="256MiB")
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports

    system.system_port = system.membus.cpu_side_ports
    system.cpu = cpu

    system.cpu.icache.mem_side = system.membus.cpu_side_ports
    system.cpu.dcache.mem_side = system.membus.cpu_side_ports

    system.cpu.createInterruptController()

    #system.system_port = system.membus.cpu_side_ports

    thispath = os.path.dirname(os.path.realpath(__file__))
    bin_name = ""
    if "riscv64" == isa:
        bin_name = f"gemmbench_{mr}_{nr}_avecpreload_bvecfmavf"
    elif "aarch64" == isa:
        bin_name = f"gemmbench_{mr}_{nr}_avecpreload_bvecdist1_boff"
    else:
        raise RuntimeError("Unknown isa {isa}")
    binary = os.path.join(
        thispath,
        "../",
        f"binaries/{isa}/{bin_name}",
    )

    system.workload = SEWorkload.init_compatible(binary)

    # from uarch_bench/gemmerator.py
    max_vregs = 32
    vectors_in_mr = mr
    avec_count = 2*vectors_in_mr
    b_regs = (max_vregs-vectors_in_mr*nr-avec_count)
    smallest_unroll = lcm(b_regs,nr)//nr
    unroll_factor = smallest_unroll
    if 3 > unroll_factor:
        unroll_factor = 4
    if 4 == unroll_factor:
        unroll_factor = 8
    if 6 == unroll_factor:
        unroll_factor = 12
    w_l1 = cpu.dcache.assoc
    cl   = system.cache_line_size
    nl   = cpu.dcache.size/w_l1/cl
    # NOTE: DOUBLE_SPECIFIC!
    data_size = 8
    mr_elem = mr*simd_width/(data_size*8)
    # We take at least 1 bank
    ca=max(1,int(math.floor((w_l1-1.0)/(1.0+nr/mr_elem))))

    print(f"ca: {ca}")
    # Equation 4 from "Analytical modeling is enough for High-Performance BLIS"
    kc=int((ca*nl*cl)/(mr_elem*data_size))
    print(f"assoc: {w_l1}, cl:{cl}, nl:{nl}, mr_elem: {mr_elem}, nr: {nr} ===> kc: {kc}")
    iterations=int(kc)//unroll_factor
    print(f"unroll: {unroll_factor} ===> iterations: {iterations} ===> kc: {iterations*unroll_factor}")

    process = Process(output="/dev/null",errout="/dev/null")
    process.cmd = [binary,f"{iterations}"]
    system.cpu.workload = process
    system.cpu.createThreads()

    return system



def simrun(isa,combo):
    import m5
    from m5.objects import Root
    import resource

    # Should be inherited from parent process, but isn't
    # Suppress file creation
    m5.options.outdir="/dev/null"
    m5.options.dump_config=False
    m5.options.json_config=False
    m5.options.dot_config=False
    m5.options.dot_dvfs_config=False
    m5.core.setOutputDir("/dev/null")

    # Let's see if we can stop memuse explosions with this
    softlimit = 12*1024*1024*1024
    hardlimit = 16*1024*1024*1024
    resource.setrlimit(resource.RLIMIT_AS, (softlimit,hardlimit))


    mr,nr,simd_lat,simd_count,simd_width,simd_phreg_count,ld_count,st_count,l1_size,rob_size,assoc,decode_width,commit_width,fetch_buf_size = combo
    cpu = setup_cpu(isa=isa,
                    simd_lat=simd_lat, simd_count=simd_count, 
                    simd_width=simd_width, simd_phreg_count=simd_phreg_count,
                    ld_count=ld_count, st_count=st_count,
                    rob_size=rob_size,
                    assoc=assoc, l1_size=l1_size,
                    decode_width=decode_width,
                    commit_width=commit_width,
                    fetch_buf_size=fetch_buf_size)
    system = setup_system(isa=isa, mr=mr, nr=nr, simd_width=simd_width, cpu=cpu)

    #m5.options.outdir=os.path.join(base_out_dir,f"gemm_m5_M{mr}_N{nr}_lat{simd_lat}_vl{simd_width}_nfu{simd_count}_dw{decode_width}_cw{commit_width}_fbs{fetch_buf_size}_l1as{assoc}_st{st_count}_ld{ld_count}_l1d{l1_size}_phr{simd_phreg_count}_rob{rob_size}")
    #print(f"gem5 output directory: {m5.options.outdir}")
    #if os.path.exists(m5.options.outdir):
    #    print(f"Path exists, removing")
    #    shutil.rmtree(m5.options.outdir)
    #os.makedirs(m5.options.outdir,exist_ok=True)
    #print(f"created output dir")
    #m5.core.setOutputDir(m5.options.outdir)

    root = Root(full_system=False, system=system)
    m5.instantiate()

    statgroups = root.getStatGroups()
    statmap = {}
    build_stat_tree(statmap, name="", groups=statgroups)

    stat_df = pd.DataFrame(columns=[name for name in statmap.keys()])
    stat_df.reset_index(drop=True,inplace=True)
    statdict = prepare_statdict(statmap)


    run = 0
    noexit=True
    print("starting workload loop")
    while noexit:
        exit_event = m5.simulate()
        if "workbegin" == exit_event.getCause():
            print("workbegin event detected, resetting statistics")
            m5.stats.reset()
        elif "workend" == exit_event.getCause():
            print("workend event detected, dumping statistics")
            #m5.stats.dump()
            append_stats(statmap,statdict)
            statdict["mr"].append(mr)
            statdict["nr"].append(nr)
            statdict["simd_lat"].append(simd_lat)
            statdict["simd_count"].append(simd_count)
            statdict["simd_width"].append(simd_width)
            statdict["simd_phreg_count"].append(simd_phreg_count)
            statdict["ld_count"].append(ld_count)
            statdict["st_count"].append(st_count)
            statdict["l1_size"].append(l1_size)
            statdict["rob_size"].append(rob_size)
            statdict["assoc"].append(assoc)
            statdict["decode_width"].append(decode_width)
            statdict["commit_width"].append(commit_width)
            statdict["fetch_buf_size"].append(fetch_buf_size)
            statdict["run"].append(run)
            run = run+1
            cycle_value = statdict["system.cpu.numCycles"][run-1]
            print(f"Cycles: {cycle_value}")
        else:
            print("exit event neither workbegin nor workend, ending simulation")
            noexit=False

    print("Exiting @ tick %i because %s" % (m5.curTick(), exit_event.getCause()))

    import sys
    dictsize = sys.getsizeof(statdict)
    if dictsize > 512*1024:
        print(f"Huge dict: {dictsize} bytes. truncating")
        must_len = len(statdict["system.cpu.numCycles"])
        for k in statdict.keys():
            del statdict[k][must_len:]
        dictsize = sys.getsizeof(statdict)
        print(f"New size: {dictsize}")
    return statdict


def main():
    import resource

    ram_available = psutil.virtual_memory().total
    # Let's see if we can stop memuse explosions with this
    softlimit = int(0.5*ram_available)
    hardlimit = int(0.75*ram_available)
    resource.setrlimit(resource.RLIMIT_AS, (softlimit,hardlimit))
    import m5
    parser = argparse.ArgumentParser(description="Run aarch64 m5 nanogemm benchmark for a given kernel size")
    parser.add_argument("--isa", metavar="isa", help='ISA to use (aarch64,riscv64)', required=True)
    parser.add_argument("--mr", nargs='+', type=int,
                        metavar="mr", 
                        help='mr dimension in vectors', required=True)
    parser.add_argument("--nr", nargs='+', type=int,
                        metavar="nr",
                        help='mr dimension in elements', required=True)
    parser.add_argument("--simd_lat", 
                        nargs='+', type=int,
                        metavar="simd_lat",
                        help='SIMD latency in cycles', required=True)
    parser.add_argument("--simd_count", nargs='+', type=int,
                        metavar="simd_count",
                        help='SIMD FU count', required=True)
    parser.add_argument("--simd_width", nargs='+', type=int,
                        metavar="simd_width",
                        help='SIMD width in bits', required=True)
    parser.add_argument("--simd_phreg_count", nargs='+', type=int,
                        metavar="simd_phreg_count",
                        help='Number of physical SIMD registers', required=True)
    parser.add_argument("--rob_size", metavar="rob_size",
                        nargs='+', type=int,
                        help='Number of ROB (reorder buffer) entries',
                        required=True)
    parser.add_argument("--assoc", nargs='+', type=int,
                        metavar="assoc",
                        help='L1D cache associativity', required=True)
    parser.add_argument("--l1_size", nargs='+', type=int,
                        metavar="l1_size",
                        help='L1D cache size in KiByte', required=True)
    parser.add_argument("--ld_count", nargs='+', type=int,
                        metavar="ld_count",
                        help='number of load units', required=True)
    parser.add_argument("--st_count", nargs='+', type=int,
                        metavar="st_count",
                        help='number of store units', required=True)
    parser.add_argument("--decode_width", nargs='+', type=int,
                        metavar="decode_width",
                        help='Max instr. issued to RS', required=True)
    parser.add_argument("--commit_width", nargs='+', type=int,
                        metavar="commit_width",
                        help='Max instr. retired per cycle', required=True)
    parser.add_argument("--fetch_buf_size", nargs='+', type=int,
                        metavar="fetch_buf_size",
                        help='Fetch Buffer Size in Bytes', required=True)
    parser.add_argument("--split_bytes", type=int,
                        metavar="split_bytes",
                        help='Write gathered stats to hdf5 file after internal struct reaches this size', default=4*2**30)
    parser.add_argument("--quiet",
                        metavar="quiet",
                        help='Be silent (no stderr/stdout from simulations)',
                        action=argparse.BooleanOptionalAction)
    parser.add_argument("--base_out_dir", 
                        metavar="base_out_dir", help='base directory in which hdf5 files containing sim stats will be created', default=os.getcwd())


    args = parser.parse_args()

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


    # Create parameter combinations

    param_lists = [args.mr,args.nr,
                   args.simd_lat,args.simd_count,args.simd_width,
                   args.simd_phreg_count,
                   args.ld_count,args.st_count,
                   args.l1_size,
                   args.rob_size,
                   args.assoc,
                   args.decode_width,
                   args.commit_width,
                   args.fetch_buf_size]

    isa = args.isa

    # Non-List problematic
    combinations = list(itertools.product(*param_lists))
    combination_count = len(combinations)

    max_vregs = 32
    # Filter invalid mr/nr combinations
    print("filtering out invalid mr/nr combinations")
    combinations = [combo for combo in combinations if max_vregs > (combo[0]*combo[1]+combo[0]*2+1)]
    print(f"Filtered out {combination_count - len(combinations)} combinations")


    statdict = {}

    hw_cores = int(os.cpu_count())
    print(f"System has {hw_cores} hardware cores")
    ram_per_worker = 200*2**20
    hw_max_ram_cores = int((0.50*ram_available)/ram_per_worker)
    print(f"System has enough memory for {hw_max_ram_cores} concurrent workers")
    hw_cores = min(hw_cores, hw_max_ram_cores)
    combination_count = len(combinations)
    print(f"Number of combinations: {combination_count}")
    max_workers = min(hw_cores, combination_count)

    import gem5.utils.multiprocessing as gem5mp
    import tqdm
    import functools
    import signal
    reference_key = "system.cpu.numCycles"
    def fix_stat_list(d : dict, k : str, must_len : int):
        v = d[k]
        vlen = len(v)
        if vlen < must_len:
            d[k].extend([0]*(must_len-vlen))
        elif vlen > must_len:
            # This shouldn't happen, but who knows
            del d[k][must_len:]
    # Ignore signals in the pool
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = gem5mp.Pool(processes=max_workers,maxtasksperchild=1)
    # The previous signal call is supposed to return the "default"
    # signal handler, but somehow it isn't a valid handler with gem5
    # Therefore let's just set one that will terminate the program
    # TODO: exit gracefully
    signal.signal(signal.SIGINT, lambda sig,frame : exit(0))

    out_file_count = 0;
    import sys
    os.makedirs(args.base_out_dir,exist_ok=True)
    try:
        for result in tqdm.tqdm(pool.imap_unordered(
                functools.partial(
                    simrun, isa
                    ),
                    combinations
                ),
                unit='sim',
                desc='Simulating: ',
                total=combination_count,
                delay=1,
                smoothing=0.1):
            if not statdict:
                statdict = result
                for k in statdict.keys():
                    fix_stat_list(result, k, len(statdict[reference_key]))
            else:
                must_len_old = len(statdict[reference_key])
                must_len_new = len(result[reference_key])
                for k in statdict.keys():
                    if k not in statdict:
                        statdict[k] = [0]*must_len_old
                    if k not in result:
                        result[k] = [0]*must_len_new
                    fix_stat_list(result, k, must_len_new)
                    fix_stat_list(statdict, k, must_len_old)
                    statdict[k].extend(result[k])
            # sys.getsizeof() won't give an accurate number, so let's estimate
            dictsize = len(statdict[reference_key])*len(statdict)*8
            if dictsize > args.split_bytes:
                print("statdict too big, flushing to file")
                h5_filepath = os.path.join(args.base_out_dir,
                                           f"stats{out_file_count}.h5")
                stat_df = pd.DataFrame(statdict)
                stat_df.to_hdf(h5_filepath, 
                               "gem5stats", 
                               mode='w',
                               complevel=4,
                               complib='blosc:zstd')
                print(f"wrote data to {h5_filepath}")
                out_file_count = out_file_count + 1
                print(f"resetting statdict")
                for v in statdict.values():
                    del v[:]
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("Keyboard interrupt received, terminating pool")
        pool.terminate()
    else:
        pool.close()
    pool.join()

    if statdict:
        final_df = pd.DataFrame(statdict)
        h5_filepath = os.path.join(args.base_out_dir,
                                   f"stats{out_file_count}.h5")
        final_df.to_hdf(h5_filepath, 
                        "gem5stats", 
                        mode='w',
                        complevel=4,
                        complib='blosc:zstd')


if __name__ == "__main__":
    main()

if __name__ == "__m5_main__":
    # So basically the __m5_main__ thing messes up multiprocessing, so 
    # run it again with __main__
    import runpy
    runpy.run_path(__file__, run_name="__main__")

