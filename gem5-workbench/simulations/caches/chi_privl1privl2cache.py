from m5.objects import RubySystem
from configs.ruby.CHI import create_system

from gem5.components.memory import DIMM_DDR5_6400

from simsetup import setup_cpu

from simargs import process_arguments, kernel_params, arch_params

def main():
    
    arg_dict = vars(process_arguments())
    kparams = {k : arg_dict[k][0] for k in kernel_params.keys()}
    aparams = {k : arg_dict[k][0] for k in arch_params.keys()}

    options = {}

    memory = DIMM_DDR5_6400(size="2GB")


    ruby_system = RubySystem(
            # Set block sizes for Ruby
            #block_size_bytes = options.cache_line_size,
            block_size_bytes = aparams["cl_size"],
            memory_size_bits = 48
        )

    cpu = setup_cpu(aparams)

    system = create_system(
            options=options, 
            full_system=True,
            dma_ports=[],
            bootmem=None,
            ruby_system=ruby_system,
            cpus=[cpu]
            )

if "__m5_main__" == __name__:
    main()
