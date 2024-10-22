# Implementation

- PrivL1L2CacheHierarchy
    - (DONE: `CHI_SNF_ExtCtrl`) Figure out memory controllers for main memory
        - `board.get_mem_ports()` every port needs SNF? every port needs 1 directory?
        - MemRange (CHI.py) vs Memory ports on board (PrivL1CacheHierarchy)
    - (DONE: same as l1 version ) Sequencers to cores
    - (DONE: Adapted SimplePt2Pt) figure out how to have `ruby_system.network` before creating all the nodes (incomplete/uninitialized struct?)
    - use CHI.py classes or port them if unusable (due to system/options/... structures)
        - `CHI_HNF`
        - `CHI_MN`
        - `CHI_RNF`
        - `CHI_RNI_DMA`
        - `CHI_RNI_IO`
        - `CHI_SNF_MainMem`
            - Needs modification (Compare `MemoryController` vs this class)
            - Implemented `CHI_SNF_ExtCtrl` which accepts external controller
    - (DONE: use `mem_dests` instead of `hnf_dests`) Figure out how to remove L3
    - (DONE: ) Figure out topology struct
        - (DONE: Adapted SimplePt2Pt) Pt2Pt from config vs SimplePt2Pt from L1 example
    - Carlos: Better to implement own hierarchy based on `Cache_Controller` and `Memory_Controller`
        - base classes in `CHI_config` seem reasonable enough


# Current Bugs:

- "Class ArmBoard has no parameter processor"
    - SOLVED
    - misleading error: issue was a missing return statement in a wrapper function
- "TypeError: wrong type '<class 'int'>' should be str" when assigning multiple parameters
    - SOLVED
    - wrong variable used accidentally, eliminated variable, converting to string directly
- "AttributeError: object 'RubySystem' has no attribute 'hnf'"
    - SOLVED
    - remove/comment out L3 code
- "AttributeError: Can't resolve proxy 'eventq_index' of type 'UInt32' from '<orphan CHI_SNF_ExtCtrl>'"
    - SOLVED
    - weird gem5ism - you can't append to the list of SNFs, you have to create them in the list comprehension
- `src/base/statistics.hh:1175: fatal: fatal condition (_x <= 0) || (_y <= 0) occurred: Storage sizes must be positive`
    - Very unhelpful message, maybe something with memory initialization?


