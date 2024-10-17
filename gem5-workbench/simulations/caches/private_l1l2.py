# Copyright (c) 2021 The Regents of the University of California
# All Rights Reserved.
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

from itertools import chain
from typing import List

from m5.objects import (
    NULL,
    RubyPortProxy,
    RubySequencer,
    RubySystem,
    RubyCache,
    Memory_Controller,
    MessageBuffer
)
from m5.objects.SubSystem import SubSystem

from gem5.coherence_protocol import CoherenceProtocol
from gem5.utils.requires import requires

requires(coherence_protocol_required=CoherenceProtocol.CHI)

from gem5.components.boards.abstract_board import AbstractBoard
from gem5.components.cachehierarchies.abstract_cache_hierarchy import (
    AbstractCacheHierarchy,
)
from gem5.components.cachehierarchies.ruby.abstract_ruby_cache_hierarchy import (
    AbstractRubyCacheHierarchy,
)
from gem5.components.cachehierarchies.ruby.topologies.simple_pt2pt import (
    SimplePt2Pt,
)
from gem5.components.processors.abstract_core import AbstractCore
from gem5.isas import ISA
from gem5.utils.override import overrides


from configs.ruby.CHI_config import (
    CHI_HNF,
    CHI_MN,
    CHI_RNF,
    CHI_RNI_DMA,
    CHI_RNI_IO,
    CHI_SNF_Base,
    CHI_SNF_MainMem,
    Versions,
    TriggerMessageBuffer,
    OrderedTriggerMessageBuffer,
    )

from .topologies.simple_pt2pt import SimplePt2Pt

class CHI_SNF_ExtCtrl(CHI_SNF_Base):

    def __init__(self, ruby_system, parent, mem_ctrl=None):
        super().__init__(ruby_system, parent)
        if mem_ctrl:
            self._cntrl = mem_ctrl

        self.connectController(self._cntrl)
        self.cntrl = self._cntrl

class PrivateL1L2SharedL3CacheHierarchy(AbstractRubyCacheHierarchy):
    """A 2-level cache based on CHI
    """

    def __init__(self, arch_params : dict[str, int]) -> None:
        """
        :param size: The size of the priavte I/D caches in the hierarchy.
        :param assoc: The associativity of each cache.
        """
        super().__init__()

        self._l1d_size  = arch_params['l1d_size']
        self._l1d_assoc = arch_params['l1d_assoc']
        self._l1d_lat   = arch_params['l1d_lat']
        self._l1i_size  = arch_params['l1i_size']
        self._l1i_assoc = arch_params['l1i_assoc']
        self._l1i_lat   = arch_params['l1i_lat']
        self._l2_size   = arch_params['l2_size']
        self._l2_assoc  = arch_params['l2_assoc']
        self._l2_lat    = arch_params['l2_lat']
        #self._l3_size   = arch_params['l3_size']
        #self._l3_assoc  = arch_params['l3_assoc']
        #self._l3_lat    = arch_params['l3_lat']

    @overrides(AbstractCacheHierarchy)
    def incorporate_cache(self, board: AbstractBoard) -> None:
        self.ruby_system = RubySystem()

        cpu_sequencers = []
        mem_cntrls = []
        mem_dests = []
        network_nodes = []
        network_cntrls = []
        hnf_dests = []
        all_cntrls = []

        # TODO: tagAccessLatency ?
        class L1ICache(RubyCache):
            size = f"{self._l1i_size}KiB"
            assoc = self._l1i_assoc
            dataAccessLatency = self._l1i_lat
            tagAccessLatency = 1
        class L1DCache(RubyCache):
            size = f"{self._l1d_size}KiB"
            assoc = self._l1d_assoc
            dataAccessLatency = self._l1d_lat
            tagAccessLatency = 1

       
        self.ruby_system.network = SimplePt2Pt(ruby_system=self.ruby_system)

        cores = [cpu.core for cpu in board.get_processor().get_cores()]

        # TODO: prefetchers
        self.ruby_system.rnf = [
            CHI_RNF(
                cpus=[cpu],
                ruby_system=self.ruby_system,
                l1Icache_type=L1ICache,
                l1Dcache_type=L1DCache,
                cache_line_size=board.get_cache_line_size(),
                )
            for cpu in cores
        ]

        class L2Cache(RubyCache):
            size = f"{self._l2_size}KiB"
            assoc = self._l2_assoc
            dataAccessLatency = self._l2_lat
            tagAccessLatency = 2

        #TODO: Parameterize L3 cache
        class HNFCache(RubyCache):
            dataAccessLatency = 10
            tagAccessLatency = 2
            size = "16MiB"
            assoc = 16

        for rnf in self.ruby_system.rnf:
            rnf.addPrivL2Cache(L2Cache)
            cpu_sequencers.extend(rnf.getSequencers())
            all_cntrls.extend(rnf.getAllControllers())
            network_nodes.append(rnf)
            network_cntrls.extend(rnf.getNetworkSideControllers())

        self.ruby_system.mn = [CHI_MN(self.ruby_system, [cpu.l1d for cpu in cores])]
        for mn in self.ruby_system.mn:
            all_cntrls.extend(mn.getAllControllers())
            network_nodes.append(mn)
            network_cntrls.extend(mn.getNetworkSideControllers())
            assert mn.getAllControllers() == mn.getNetworkSideControllers()

        # In CHI.py we have "other memories" here

        sysranges = [] + board.mem_ranges


        # TODO: Parameterize L3 caches
        #hnf_list = [i for i in range(options.num_l3caches)]
        hnf_list = [i for i in range(1)]
        CHI_HNF.createAddrRanges(sysranges, board.get_cache_line_size(), hnf_list)
        self.ruby_system.hnf = [
            CHI_HNF(i, self.ruby_system, HNFCache, None)
            for i in range(1)
        ]

        for hnf in self.ruby_system.hnf:
            network_nodes.append(hnf)
            network_cntrls.extend(hnf.getNetworkSideControllers())
            assert hnf.getAllControllers() == hnf.getNetworkSideControllers()
            all_cntrls.extend(hnf.getAllControllers())
            hnf_dests.extend(hnf.getAllControllers())
        
        num_dirs = len(board.get_mem_ports())
        self.ruby_system.snf = [
            CHI_SNF_MainMem(self.ruby_system, None, None)
            for i in range(num_dirs)
        ]
        for snf, (rng, port) in zip(self.ruby_system.snf, board.get_mem_ports()):
            snf._cntrl.addr_ranges = [rng]
            snf._cntrl.__dict__["range"] = rng
            snf._cntrl.memory_out_port = port


        # Create the memory controllers
        # Notice we don't define a Directory_Controller type so we don't use
        # create_directories shared by other protocols.
        # TODO: number of directories
        #num_dirs = 1
        #self.ruby_system.snf = [
        #    CHI_SNF_MainMem(self.ruby_system, None, None)
        #    for i in range(num_dirs)
        #]


        for snf in self.ruby_system.snf:
            network_nodes.append(snf)
            network_cntrls.extend(snf.getNetworkSideControllers())
            assert snf.getAllControllers() == snf.getNetworkSideControllers()
            mem_cntrls.extend(snf.getAllControllers())
            all_cntrls.extend(snf.getAllControllers())
            mem_dests.extend(snf.getAllControllers())


        # In CHI.py SNFs for other memories here


        if board.has_dma_ports():
            self.ruby_system.dma_rni = [
                CHI_RNI_DMA(self.ruby_system, dma_port, None)
                for dma_port in board.get_dma_ports()
            ]
            for rni in self.ruby_system.dma_rni:
                network_nodes.append(rni)
                network_cntrls.extend(rni.getNetworkSideControllers())
                all_cntrls.extend(rni.getAllControllers())

        if board.is_fullsystem():
            self.ruby_system.io_rni = CHI_RNI_IO(self.ruby_system, None)
            network_nodes.append(self.ruby_system.io_rni)
            network_cntrls.extend(self.ruby_system.io_rni.getNetworkSideControllers())
            all_cntrls.extend(self.ruby_system.io_rni.getAllControllers())

        # This is with L3
        # Assign downstream destinations
        for rnf in self.ruby_system.rnf:
            rnf.setDownstream(hnf_dests)
        if board.has_dma_ports():
            for rni in self.ruby_system.dma_rni:
                rni.setDownstream(hnf_dests)
        if board.is_fullsystem():
            self.ruby_system.io_rni.setDownstream(hnf_dests)
        for hnf in self.ruby_system.hnf:
            hnf.setDownstream(mem_dests)

        # This is without L3
        #for rnf in self.ruby_system.rnf:
        #    rnf.setDownstream(mem_dests)
        #if board.has_dma_ports():
        #    for rni in self.ruby_system.dma_rni:
        #        rni.setDownstream(mem_dests)
        #if board.is_fullsystem():
        #    self.ruby_system.io_rni.setDownstream(mem_dests)


        # Default values from CHI_config.py
        router_link_latency = 1
        node_link_latency = 1
        router_latency = 1
        router_buffer_size = 4
        cntrl_msg_size = 8
        data_width = 32
        cross_links = []
        cross_link_latency = 0
        
        # Setup data message size for all controllers
        for cntrl in all_cntrls:
            cntrl.data_channel_size = data_width

        # Network configurations
        # virtual networks: 0=request, 1=snoop, 2=response, 3=data
        self.ruby_system.number_of_virtual_networks = 4
        self.ruby_system.network.number_of_virtual_networks = 4


        self.ruby_system.network.control_msg_size = cntrl_msg_size
        self.ruby_system.network.data_msg_size = data_width
        #if options.network == "simple":
        self.ruby_system.network.buffer_size = router_buffer_size

        self.ruby_system.network.connectControllers(all_cntrls)

        self.ruby_system.network.setup_buffers()        

        for seq, cpu in zip(cpu_sequencers,cores):
            seq.connectCpuPorts(cpu)

        self.ruby_system.num_of_sequencers = len(cpu_sequencers)+len(self.ruby_system.dma_rni)

        # Set up a proxy port for the system_port. Used for load binaries and
        # other functional-only things.
        self.ruby_system.sys_port_proxy = RubyPortProxy(
                ruby_system=self.ruby_system
                )
        board.connect_system_port(self.ruby_system.sys_port_proxy.in_ports)


