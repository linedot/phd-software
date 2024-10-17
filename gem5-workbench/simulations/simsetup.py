import os
import math

from processors.parameterized_switchable_processor import parameterized_switchable_processor

def lcm(a, b):
    return abs(a*b) // math.gcd(a, b)

def setup_cpu(arch_params:dict):

    import m5
    from m5.objects import ArmISA, RiscvISA
    from gem5.utils.requires import requires
    from gem5.isas import ISA

    # Bine's N1 model
    from common.cores.arm.O3_ARM_Neoverse_N1 import O3_ARM_Neoverse_N1,O3_ARM_Neoverse_N1_but_RISCV,O3_ARM_Neoverse_N1_ICache,O3_ARM_Neoverse_N1_DCache
        
    isa = arch_params["isa"]
    simd_width = arch_params["simd_width"]

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

    cpu.decodeWidth = arch_params["decode_width"]
    cpu.fetchWidth  = arch_params["decode_width"]
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

    # TODO: Cache
    #cpu.icache = O3_ARM_Neoverse_N1_ICache()
    #cpu.dcache = O3_ARM_Neoverse_N1_DCache()
    #cpu.dcache.assoc = assoc
    #cpu.dcache.size = f"{l1_size}kB"

    #cpu.icache.cpu_side = cpu.icache_port
    #cpu.dcache.cpu_side = cpu.dcache_port

    return cpu

def setup_processor(arch_params : dict):

    processor = parameterized_switchable_processor(
        arch_params,
        #TODO: add num_cores to arch_params
        num_cores=1,
    )

    return processor

