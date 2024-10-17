from gem5.components.boards.abstract_system_board import AbstractSystemBoard
from gem5.components.boards.riscv_board import RiscvBoard
from gem5.components.boards.se_binary_workload import SEBinaryWorkload
from gem5.components.cachehierarchies.abstract_cache_hierarchy import AbstractCacheHierarchy
from gem5.components.cachehierarchies.chi.private_l1_cache_hierarchy\
        import PrivateL1CacheHierarchy
from gem5.components.memory.abstract_memory_system import AbstractMemorySystem
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.components.processors.abstract_processor import AbstractProcessor
from gem5.components.processors.base_cpu_core import BaseCPUCore
from gem5.components.processors.base_cpu_processor import BaseCPUProcessor
from gem5.isas import ISA
from gem5.resources.resource import BinaryResource
from gem5.utils.override import overrides
import m5
from m5.objects import AddrRange, IOXBar, Port
from m5.defines import buildEnv

from typing import List

class seboard(AbstractSystemBoard, SEBinaryWorkload):
    def __init__(
        self,
        processor: AbstractProcessor,
        memory: AbstractMemorySystem,
        cache_hierarchy: AbstractCacheHierarchy,
        clk_freq: str,
    ) -> None:
        super().__init__(
            clk_freq=clk_freq,
            processor=processor,
            memory=memory,
            cache_hierarchy=cache_hierarchy,
        )

    @overrides(AbstractSystemBoard)
    def _setup_board(self) -> None:
        pass

    @overrides(AbstractSystemBoard)
    def has_io_bus(self) -> bool:
        return False

    @overrides(AbstractSystemBoard)
    def get_io_bus(self) -> IOXBar:
        raise NotImplementedError(
            "SEBoard does not have an IO Bus. "
            "Use `has_io_bus()` to check this."
        )

    @overrides(AbstractSystemBoard)
    def has_dma_ports(self) -> bool:
        return False

    @overrides(AbstractSystemBoard)
    def get_dma_ports(self) -> List[Port]:
        raise NotImplementedError(
            "SEBoard does not have DMA Ports. "
            "Use `has_dma_ports()` to check this."
        )

    @overrides(AbstractSystemBoard)
    def has_coherent_io(self) -> bool:
        return False

    @overrides(AbstractSystemBoard)
    def get_mem_side_coherent_io_port(self) -> Port:
        raise NotImplementedError(
            "SEBoard does not have any I/O ports. Use has_coherent_io to "
            "check this."
        )

    @overrides(AbstractSystemBoard)
    def _setup_memory_ranges(self) -> None:
        memory = self.get_memory()
        self.mem_ranges = [AddrRange(memory.get_size())]
        memory.set_memory_range(self.mem_ranges)

def setup_board(isa:str, binary: BinaryResource, cpu):

    isamap = {
        "riscv64": ISA.RISCV,
        "aarch64": ISA.ARM,
    }
    core = BaseCPUCore(core = cpu, isa = isamap[isa])

    cache_hierarchy = PrivateL1CacheHierarchy(
            size=f"{l1d_size}KiB",
            assoc=l1d_assoc,
            )
    memory = SingleChannelDDR4_2400("256MiB")

    processor = BaseCPUProcessor(cores = [core])

    board = SEBoard(clk_freq='1GHz',
                       processor=processor,
                       memory=memory,
                       cache_hierarchy=cache_hierarchy)

    board.cache_line_size = cl_size

    board.set_se_binary_workload(binary,arguments=[f"{iterations}"])

    return board
