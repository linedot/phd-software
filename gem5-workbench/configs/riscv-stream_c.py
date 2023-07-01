from gem5.utils.requires import requires

from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.cachehierarchies.chi.private_l1_cache_hierarchy import PrivateL1CacheHierarchy
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.components.processors.simple_switchable_processor import (
        SimpleSwitchableProcessor
        )
from gem5.components.processors.cpu_types import CPUTypes

from gem5.coherence_protocol import CoherenceProtocol

from gem5.isas import ISA
from gem5.resources.resource import Resource
from gem5.simulate.simulator import Simulator
from gem5.simulate.exit_event import ExitEvent

import m5

requires(isa_required=ISA.RISCV,
         coherence_protocol_required=CoherenceProtocol.CHI)

cache_hierarchy = PrivateL1CacheHierarchy("64KiB", 8)

#cache_hierarchy = MESIThreeLevelCacheHierarchy(
#        l1i_size="64KiB", l1i_assoc="4",
#        l1d_size="64KiB", l1d_assoc="4",
#        l2_size="1MiB", l2_assoc="8",
#        l3_size="8MiB", l3_assoc=16, num_l3_banks=1)
memory = SingleChannelDDR4_2400("2GiB")
processor = SimpleSwitchableProcessor(CPUTypes.TIMING, CPUTypes.O3, 1, isa=ISA.RISCV)

board = RiscvBoard(clk_freq="600MHz", processor=processor, memory=memory, cache_hierarchy=cache_hierarchy)

#riscv_img = Resource("riscv-lupio-busybox-img")
#kernel = Resource("riscv-bootloader-vmlinux-5.10")
riscv_img = Resource("riscv-ubuntu-20.04-img")
kernel = Resource("riscv-bootloader-vmlinux-5.10")

command = (
    "m5 exit;"
    "echo Hello from RISCV! Running O3 now;"
    "m5 exit;"
    )

board.set_kernel_disk_workload(
        kernel=kernel,
        disk_image=riscv_img,
        readfile_contents=command
        )

simulator = Simulator(
    board=board,
    on_exit_event={
        # Here we want override the default behavior for the first m5 exit
        # exit event. Instead of exiting the simulator, we just want to
        # switch the processor. The 2nd 'm5 exit' after will revert to using
        # default behavior where the simulator run will exit.
        ExitEvent.EXIT: (func() for func in [processor.switch])
    },
)
simulator.run(2000)
simulator.save_checkpoint("testcheckpoint")

#simulator.run()
