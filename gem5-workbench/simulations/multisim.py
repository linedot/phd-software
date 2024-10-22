import pandas as pd

import m5
from gem5.coherence_protocol import CoherenceProtocol
from gem5.components.boards.arm_board import ArmBoard
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.memory import DIMM_DDR5_6400
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.switchable_processor import SwitchableProcessor
from gem5.components.cachehierarchies.chi.private_l1_cache_hierarchy import  PrivateL1CacheHierarchy
from gem5.isas import ISA
from gem5.resources.resource import obtain_resource,DiskImageResource, FileResource, CheckpointResource
from gem5.resources.workload import Workload
from gem5.simulate.exit_event import ExitEvent
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires
from m5.objects import ArmAllRelease
from m5.objects import VExpress_GEM5_V1, VExpress_GEM5_V2


import os

from stats import prepare_statdict, append_stats, build_stat_tree, prepare_stats
from simargs import kernel_params, arch_params, process_arguments

from simsetup import setup_processor

from caches.parameterized_chi_cache_hierarchy import parameterized_chi_cache_hierarchy

def main():

    args = vars(process_arguments())

    kparams = {k:args[k][0] for k in kernel_params.keys()}
    aparams = {k:args[k][0] for k in arch_params.keys()}

    cache_hierarchy =  parameterized_chi_cache_hierarchy(aparams)
    #cache_hierarchy =  PrivateL1CacheHierarchy(assoc=4,size="64KiB")

    memory = DIMM_DDR5_6400(size="4GB")

    processor = setup_processor(aparams)


    isa_map = {
        "aarch64" : ISA.ARM,
        "riscv64" : ISA.RISCV,
    }

    isa = isa_map[aparams['isa']]


    if ISA.ARM==isa:
        release = ArmAllRelease()
        platform = VExpress_GEM5_V2()
        board = ArmBoard(
            clk_freq="1GHz",
            processor=processor,
            memory=memory,
            cache_hierarchy=cache_hierarchy,
            release=release,
            platform=platform,
        )
        #bootloader=FileResource("/home/linedot/.cache/gem5/arm64-bootloader")
        #kernel=    FileResource("/home/linedot/.cache/gem5/arm64-linux-kernel-5.15.36")
        #disk_image=DiskImageResource("/home/linedot/.cache/gem5/arm-ubuntu-22.04-img")
        bootloader=FileResource("bootloaders/boot_v2.arm64")
        #kernel=    FileResource("kernels/vmlinux-debian-aarch64-6.9.8")
        kernel=    FileResource("kernels/vmlinux-aarch64-6.1.97")
        #disk_image=DiskImageResource("images/debian-gem5-aarch64.img")
        disk_image=DiskImageResource("images/ubuntu-gemmbench-aarch64.img")
        #bootloader=obtain_resource("arm64-bootloader")
        #kernel=    obtain_resource("arm64-linux-kernel-5.15.36")
        #disk_image=obtain_resource("arm-ubuntu-22.04-img")
    elif ISA.RISCV == isa:
        board = RiscvBoard(
            clk_freq="1GHz",
            processor=processor,
            memory=memory,
            cache_hierarchy=cache_hierarchy,
        )
        bootloader=FileResource("bootloaders/u-boot")
        kernel=    FileResource("kernels/vmlinux-debian-riscv64-6.9.8")
        disk_image=DiskImageResource("images/debian-gem5-riscv64.img")


    checkpoint = None
    if os.path.exists("gemmbench_checkpoint_aarch64"):
        checkpoint = CheckpointResource("gemmbench_checkpoint_aarch64")
    board.set_kernel_disk_workload(                
        bootloader=bootloader,
        kernel=kernel,
        disk_image=disk_image,
        kernel_args=["console=ttyAMA0","norandmaps","noquiet", "no_systemd", "root=/dev/vda2", "rw"],
        readfile_contents="echo Requesting checkpoint save;"\
                          "m5 checkpoint;"\
                          "echo Requesting CPU switch;"\
                          "m5 exit;"\
                          "echo \"Running on $(nproc) CPUs\";"\
                          "for bench in /tmp/gemmbench/gemmbench*; do "\
                          " $bench 32;"\
                          "done;"\
                          "echo \"Finished running benchmarks\""
                          "sleep 1; m5 exit",
        checkpoint=checkpoint,

        #readfile_contents="m5 switchcpu; echo \"Running on $(nproc) CPUs\"; sleep 1; m5 exit",
    )

    #board.workload.wait_for_remote_gdb = True


    def handle_workbegin():
        print("workbegin event detected, resetting statistics")
        m5.stats.reset()

    run = 0
    statdict = {}
    statmap = {}


    #Fake parameters

    mr = 2
    nr = 10
    simd_lat = 4
    simd_count = 2
    simd_width = 128
    simd_phreg_count = 384
    ld_count = 2
    st_count = 2
    l1_size = 64
    cl_size = 64
    assoc=8
    iq_size = 200
    rob_size = 200
    decode_width=8
    commit_width=8
    fetch_buf_size=64

    def handle_workend():
        nonlocal run
        nonlocal statdict
        nonlocal statmap
        print("workend event detected, saving statistics")
        root = handle_workend.simulator._root
        statgroups = root.getStatGroups()
        if 0 == run:
            print("First run, initializing statdict")

            statmap = {}
            build_stat_tree(statmap, name="", groups=statgroups)
            statdict = prepare_statdict(statmap)
        prepare_stats(statgroups)
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
        statdict["cl_size"].append(cl_size)
        statdict["assoc"].append(assoc)
        statdict["iq_size"].append(iq_size)
        statdict["rob_size"].append(rob_size)
        statdict["decode_width"].append(decode_width)
        statdict["commit_width"].append(commit_width)
        statdict["fetch_buf_size"].append(fetch_buf_size)
        statdict["run"].append(run)
        run = run+1
        for key in statdict.keys():
            if "numCycles" in key:
                reference_key = key
        cycle_value = statdict[reference_key][run-1]
        print(f"Cycles: {cycle_value}")
        m5.stats.reset()

    def handle_workend_dummy():
        print("Workend event detected. Dummy function.")

    if not os.path.exists("gemmbench_checkpoint_aarch64"):
        exit_functions = [
            lambda : print("Acknowledging kernel boot"),
            # lambda : print("Acknowledging systemd will be booted"),
            processor.switch
        ]
    else:
        exit_functions = [processor.switch]

    print("Creating simulator")
    simulator = Simulator(
            board=board,
            on_exit_event={
                ExitEvent.EXIT : (func() for func in exit_functions),
                ExitEvent.WORKEND    : handle_workend,
                ExitEvent.WORKBEGIN  : handle_workbegin,
                ExitEvent.CHECKPOINT : (func() for func in [
                    lambda : simulator.save_checkpoint("gemmbench_checkpoint_aarch64")
                    ]),
                }
            )

    print("Assigning simulator to function")
    handle_workend.simulator = simulator

    noexit=True
    print("starting simulator")


    simulator.run()


    reference_key = "system.cpu.numCycles"
    for key in statdict.keys():
        if "numCycles" in key:
            reference_key = key
    def fix_stat_list(d : dict, k : str, must_len : int):
        v = d[k]
        vlen = len(v)
        if vlen < must_len:
            d[k].extend([0]*(must_len-vlen))
        elif vlen > must_len:
            # This shouldn't happen, but who knows
            del d[k][must_len:]
    for k in statdict.keys():
       fix_stat_list(statdict, k, len(statdict[reference_key]))


    df = pd.DataFrame(statdict)
    #df.to_csv("teststats.csv")
    df.to_hdf(path_or_buf="teststats.h5", key="gem5_stats", complib="blosc:zstd")


if __name__ == "__m5_main__":
    main()
