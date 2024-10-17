import argparse
import os


class param:
    def __init__(self, description, nargs='+', type=int, choices=None, required=True):
        self.description = description
        self.type = type
        self.choices = choices
        self.nargs = nargs
        self.required = required

kernel_params = {
    "mr" : param("Kernel mr size given in number of SIMD registers"),
    "nr" : param("Kernel nr size given in number of elements"),
}

supported_isas = ["aarch64", "riscv64"]
arch_params = {
    "isa" :              param(f"ISA to use ({', '.join(supported_isas)})", nargs=1, type=str, choices=supported_isas),
    "simd_lat" :         param("Latency of the SIMD FMA instruction"),
    "simd_count" :       param("Latency of the SIMD FMA instruction"),
    "simd_width" :       param("Size of SIMD registers in bits"),
    "simd_phreg_count" : param("Number of physical SIMD registers in the register file"),
    "iq_size" :          param("Number of Instruction Queue (IQ) entries"),
    "rob_size" :         param("Number of ReOrder Buffer (ROB) entries"),
    "l1d_assoc" :        param("Associativity of L1 data cache"),
    "l1d_size" :         param("Size of L1 data cache in KiByte"),
    "l1d_lat" :          param("Data access latency of the L1 data cache in cycles"),
    "l1i_assoc" :        param("Associativity of L1 instruction cache"),
    "l1i_size" :         param("Size of L1 instruction cache in KiByte"),
    "l1i_lat" :          param("Data access latency of the L1 instruction cache in cycles"),
    "l2_assoc" :         param("Associativity of L2 cache"),
    "l2_size" :          param("Size of L2 cache in KiByte"),
    "l2_lat" :           param("Data access latency of the L2 cache in cycles"),
    "cl_size" :          param("Cache line size in bytes"),
    "ld_count" :         param("Number of load units/ports (L1D to register file)"),
    "st_count" :         param("Number of store units/ports (register file to L1D)"),
    "decode_width" :     param("Max. number of instructions issued concurrently to RS per cycle"),
    "commit_width" :     param("Max. number of instructions retired per cycle"),
    "fetch_buf_size" :   param("Size of fetch buffer in bytes"),
}
# Add sim params manually as they probably won't be used somewhere else


def process_arguments():
    parser = argparse.ArgumentParser(description="Run aarch64 m5 nanogemm benchmark for a given kernel size")

    #TODO: zip dicts?
    for name,param in kernel_params.items():
        parser.add_argument(f"--{name}", nargs=param.nargs, type=param.type, help=param.description, required=param.required)
    for name,param in arch_params.items():
        parser.add_argument(f"--{name}", nargs=param.nargs, type=param.type, help=param.description, required=param.required)

    parser.add_argument("--split_bytes", type=int,
                        metavar="split_bytes",
                        help='Write gathered stats to hdf5 file after internal struct reaches this size', default=4*2**30)
    parser.add_argument("--sim_max_cores", type=int,
                        metavar="sim_max_cores",
                        help='Use at most this many cores for the simulation (default: os.cpu_count())',
                        default=os.cpu_count())
    parser.add_argument("--stat_filename", type=str,
                        metavar="stat_filename",
                        help='Base name of the hdf5 file for stats, multiple files will be called stat_filename0.h5,stat_filename1.h5, etc...', default="statfile")
    parser.add_argument("--tqdm_position", type=int,
                        metavar="tqdm_position",
                        help='where to place progress bar (useful when running multiple jobs on a cluster)',
                        default=0)
    parser.add_argument("--quiet",
                        metavar="quiet",
                        help='Be silent (no stderr/stdout from simulations)',
                        action=argparse.BooleanOptionalAction)
    parser.add_argument("--base_out_dir", 
                        metavar="base_out_dir", help='base directory in which hdf5 files containing sim stats will be created', default=os.getcwd())

    # DB stuff didn't work out

    #parser.add_argument("--db_base_dir", 
    #                    type=str,
    #                    required=True,
    #                    help='Base directory where to create/open database for saving results')
    #parser.add_argument("--db_table_name", 
    #                    type=str,
    #                    required=True,
    #                    help='Name of the table in the database to use for storing results')
    #parser.add_argument("--db_table_reset", 
    #                    action='store_true',
    #                    help='Remove any previous data from the table in the DB')
    #parser.add_argument("--db_jsc_hostname", 
    #                    action='store_true',
    #                    help='Hostname fix for JSC machines (add "i" to hostname)')


    return  parser.parse_args()
