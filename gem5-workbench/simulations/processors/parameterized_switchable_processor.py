from gem5.components.processors.switchable_processor import SwitchableProcessor
from gem5.components.boards.abstract_board import AbstractBoard
from gem5.components.boards.mem_mode import MemMode
from gem5.components.processors.cpu_types import CPUTypes, get_mem_mode
from gem5.components.processors.base_cpu_core import BaseCPUCore
from gem5.components.processors.simple_core import SimpleCore

from gem5.utils.override import *
from gem5.isas import ISA


def setup_core(arch_params:dict, core_id:int):
    import m5
    from m5.objects import ArmISA, RiscvISA
    from gem5.utils.requires import requires

    # Bine's N1 model
    from common.cores.arm.O3_ARM_Neoverse_N1 import O3_ARM_Neoverse_N1,O3_ARM_Neoverse_N1_but_RISCV,O3_ARM_Neoverse_N1_ICache,O3_ARM_Neoverse_N1_DCache


    isa        = arch_params["isa"]
    simd_width = arch_params["simd_width"]

    if "aarch64" == isa:
        requires(isa_required=ISA.ARM)
        cpu_isa = ArmISA(sve_vl_se=simd_width/128)
        core_isa = ISA.ARM
        cpu = O3_ARM_Neoverse_N1(isa=cpu_isa, cpu_id=core_id)
    elif "riscv64" == isa:
        requires(isa_required=ISA.RISCV)
        cpu_isa = RiscvISA(vlen=simd_width)
        core_isa = ISA.RISCV
        cpu = O3_ARM_Neoverse_N1_but_RISCV(isa=cpu_isa, cpu_id=core_id)
    else:
        raise RuntimeError(f"Unsupported ISA: {isa}")

    decode_width    = arch_params["decode_width"]
    cpu.decodeWidth = decode_width
    cpu.fetchWidth  = decode_width
    cpu.commitWidth = arch_params["commit_width"]

    cpu.numROBEntries    = arch_params["rob_size"]
    cpu.numIQEntries     = arch_params["iq_size"]
    cpu.numPhysFloatRegs = arch_params["simd_phreg_count"]
    cpu.numPhysVecRegs   = arch_params["simd_phreg_count"]

    cpu.fetchBufferSize  = arch_params["fetch_buf_size"]

    for fu in cpu.fuPool.FUList:
        for op in fu.opList:
            if ('SimdFloatMultAcc' == str(op.opClass)):
                op.opLat = arch_params["simd_lat"]
                fu.count = arch_params["simd_count"]
            elif ('MemWrite' == str(op.opClass)):
                fu.count = arch_params["st_count"]
            elif ('MemRead' == str(op.opClass)):
                fu.count = arch_params["ld_count"]

    return BaseCPUCore(core=cpu,isa=core_isa)

class parameterized_switchable_processor(SwitchableProcessor):
    """ 
    Switchable processor for the multi-sim setup
    """

    def __init__(
        self,
        arch_params: dict,
        num_cores: int,
    ) -> None:
        """
        :param arch_param: Dictionary of architecture parameters
        :param num_cores: Number of cores
        to.

        """

        if num_cores <= 0:
            raise AssertionError("Number of cores must be a positive integer!")

        self._start_key = "start"
        self._switch_key = "switch"
        self._current_is_start = True

        # TODO: avoid hardcoding
        self._mem_mode = MemMode.ATOMIC_NONCACHING

        print (arch_params['isa'])
        isa = ISA.RISCV
        if 'aarch64' == arch_params['isa']:
            isa = ISA.ARM
        elif 'riscv64' == arch_params['isa']:
            isa = ISA.RISCV
        else:
            raise RuntimeError("Unsupported ISA")

        print(f"ISA: {isa}")

        switchable_cores = {
            self._start_key: [
                SimpleCore(cpu_type=CPUTypes.ATOMIC, core_id=i, isa=isa)
                for i in range(num_cores)
            ],
            self._switch_key: [
                setup_core(arch_params=arch_params, core_id=i)
                for i in range(num_cores)
            ],
        }

        for cpu in switchable_cores[self._start_key]:
            cpu.core.createInterruptController()

        super().__init__(
            switchable_cores=switchable_cores, starting_cores=self._start_key
        )

    @overrides(SwitchableProcessor)
    def incorporate_processor(self, board: AbstractBoard) -> None:
        super().incorporate_processor(board=board)

        if (
            board.get_cache_hierarchy().is_ruby()
            and self._mem_mode == MemMode.ATOMIC
        ):
            warn(
                "Using an atomic core with Ruby will result in "
                "'atomic_noncaching' memory mode. This will skip caching "
                "completely."
            )
            self._mem_mode = MemMode.ATOMIC_NONCACHING
        board.set_mem_mode(self._mem_mode)

    def switch(self):
        """Switches to the "switched out" cores."""
        if self._current_is_start:
            self.switch_to_processor(self._switch_key)
            self._mem_mode = MemMode.TIMING
        else:
            self.switch_to_processor(self._start_key)
            self._mem_mode = MemMode.ATOMIC_NONCACHING

        self._current_is_start = not self._current_is_start
