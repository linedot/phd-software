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

import m5
from m5.objects import *

# Bine's N1 model
from common.cores.arm.O3_ARM_Neoverse_N1 import O3_ARM_Neoverse_N1,O3_ARM_Neoverse_N1_ICache,O3_ARM_Neoverse_N1_DCache

import argparse
import os
import shutil
import math

def lcm(a, b):
    return abs(a*b) // math.gcd(a, b)

def setup_cpu(simd_lat:int, simd_count:int, simd_width:int,
              decode_width:int, commit_width:int,
              fetch_buf_size: int):
    cpu = O3_ARM_Neoverse_N1()

    cpu.isa = ArmISA(sve_vl_se=simd_width/128)

    cpu.decodeWidth=decode_width
    cpu.fetchWidth=decode_width
    cpu.commitWidth=commit_width

    cpu.fetchBufferSize=fetch_buf_size

    for fu in cpu.fuPool.FUList:
        if str(fu.opList[0].opClass).startswith("Simd"):
            print(f"SIMD count: {fu.count}")
        for op in fu.opList:
            if ('SimdFloatMultAcc' == str(op.opClass)):
                print(f"SIMD latency: {op.opLat}")

    for fu in cpu.fuPool.FUList:
        for op in fu.opList:
            if ('SimdFloatMultAcc' == str(op.opClass)):
                op.opLat = simd_lat
                fu.count = simd_count

    cpu.icache = O3_ARM_Neoverse_N1_ICache()
    cpu.dcache = O3_ARM_Neoverse_N1_DCache()

    cpu.icache.cpu_side = cpu.icache_port
    cpu.dcache.cpu_side = cpu.dcache_port

    return cpu

def setup_system(mr:int, nr:int, simd_width:int, cpu):
    system = System()

    system.exit_on_work_items = True

    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = "1GHz"
    system.clk_domain.voltage_domain = VoltageDomain()

    system.mem_mode = "timing"
    system.mem_ranges = [AddrRange("512MB")]
    system.cpu = cpu

    system.membus = SystemXBar()
    system.cpu.icache.mem_side = system.membus.cpu_side_ports
    system.cpu.dcache.mem_side = system.membus.cpu_side_ports

    #system.cpu.icache_port = system.membus.cpu_side_ports
    #system.cpu.dcache_port = system.membus.cpu_side_ports

    system.cpu.createInterruptController()

    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR3_1600_8x8()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports

    system.system_port = system.membus.cpu_side_ports

    thispath = os.path.dirname(os.path.realpath(__file__))
    binary = os.path.join(
        thispath,
        "../",
        f"binaries/aarch64/gemmbench_{mr}_{nr}_avecpreload_bvecdist1_boff",
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

    process = Process()
    process.cmd = [binary,f"{iterations}"]
    system.cpu.workload = process
    system.cpu.createThreads()

    return system


if __name__ == "__m5_main__":


    parser = argparse.ArgumentParser(description="Run aarch64 m5 nanogemm benchmark for a given kernel size")
    parser.add_argument("--mr", metavar="mr", help='mr dimension in vectors', required=True)
    parser.add_argument("--nr", metavar="nr", help='mr dimension in elements', required=True)
    parser.add_argument("--simd_lat", metavar="simd_lat", help='SIMD latency in cycles', required=True)
    parser.add_argument("--simd_count", metavar="simd_count", help='SIMD FU count', required=True)
    parser.add_argument("--simd_width", metavar="simd_width", help='SIMD width in bits', required=True)
    parser.add_argument("--decode_width", metavar="decode_width", help='Max instr. issued to RS', required=True)
    parser.add_argument("--commit_width", metavar="commit_width", help='Max instr. retired per cycle', required=True)
    parser.add_argument("--fetch_buf_size", metavar="fetch_buf_size", help='Fetch Buffer Size in Bytes', required=True)
    parser.add_argument("--base_out_dir", metavar="base_out_dir", help='base directory in which output directories will be created', default=os.getcwd())


    args = parser.parse_args()

    mr = int(args.mr)
    nr = int(args.nr)
    simd_lat = int(args.simd_lat)
    simd_count = int(args.simd_count)
    simd_width = int(args.simd_width)
    decode_width = int(args.decode_width)
    commit_width = int(args.commit_width)
    fetch_buf_size = int(args.fetch_buf_size)
    base_out_dir = args.base_out_dir



    cpu = setup_cpu(simd_lat=simd_lat, simd_count=simd_count, simd_width=simd_width,
                    decode_width=decode_width,
                    commit_width=commit_width,
                    fetch_buf_size=fetch_buf_size)



    for fu in cpu.fuPool.FUList:
        if str(fu.opList[0].opClass).startswith("Simd"):
            print(f"SIMD count: {fu.count}")
        for op in fu.opList:
            if ('SimdFloatMultAcc' == str(op.opClass)):
                print(f"SIMD latency: {op.opLat}")

    system = setup_system(mr=mr, nr=nr, simd_width=simd_width, cpu=cpu)
    root = Root(full_system=False, system=system)

    
    m5.options.outdir=os.path.join(base_out_dir,f"gemm_m5_M{mr}_N{nr}_lat{simd_lat}_vl{simd_width}_nfu{simd_count}_dw{decode_width}_cw{commit_width}_fbs{fetch_buf_size}")
    print(f"gem5 output directory: {m5.options.outdir}")
    if os.path.exists(m5.options.outdir):
        print(f"Path exists, removing")
        shutil.rmtree(m5.options.outdir)
    os.makedirs(m5.options.outdir,exist_ok=True)
    print(f"created output dir")
    m5.core.setOutputDir(m5.options.outdir)
    m5.instantiate()

    noexit=True
    while noexit:
        exit_event = m5.simulate()
        if "workbegin" == exit_event.getCause():
            print("workbegin event detected, resetting statistics")
            m5.stats.reset()
        elif "workend" == exit_event.getCause():
            print("workend event detected, dumping statistics")
            m5.stats.dump()
        else:
            print("exit event neither workbegin nor workend, ending simulation")
            noexit=False

    print("Exiting @ tick %i because %s" % (m5.curTick(), exit_event.getCause()))

