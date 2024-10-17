#import pandas as pd
import os
from simsetup import setup_cpu, setup_system
from stats import build_stat_tree, prepare_statdict, append_stats


def simrun(isa,db,combo):
    import m5
    from m5.objects import Root
    import resource

    # Should be inherited from parent process, but isn't
    # Suppress file creation
    m5.options.outdir="/dev/null"
    m5.options.dump_config=False
    m5.options.json_config=False
    m5.options.dot_config=False
    m5.options.dot_dvfs_config=False
    m5.core.setOutputDir("/dev/null")

    # Let's see if we can stop memuse explosions with this
    softlimit = 12*1024*1024*1024
    hardlimit = 16*1024*1024*1024
    resource.setrlimit(resource.RLIMIT_AS, (softlimit,hardlimit))


    mr,nr,simd_lat,simd_count,simd_width,simd_phreg_count,ld_count,st_count,l1_size,iq_size,rob_size,assoc,decode_width,commit_width,fetch_buf_size = combo
    cpu = setup_cpu(isa=isa,
                    simd_lat=simd_lat, simd_count=simd_count, 
                    simd_width=simd_width, simd_phreg_count=simd_phreg_count,
                    ld_count=ld_count, st_count=st_count,
                    iq_size=iq_size,
                    rob_size=rob_size,
                    assoc=assoc, l1_size=l1_size,
                    decode_width=decode_width,
                    commit_width=commit_width,
                    fetch_buf_size=fetch_buf_size)
    system = setup_system(isa=isa, mr=mr, nr=nr, simd_width=simd_width, cpu=cpu)

    #m5.options.outdir=os.path.join(base_out_dir,f"gemm_m5_M{mr}_N{nr}_lat{simd_lat}_vl{simd_width}_nfu{simd_count}_dw{decode_width}_cw{commit_width}_fbs{fetch_buf_size}_l1as{assoc}_st{st_count}_ld{ld_count}_l1d{l1_size}_phr{simd_phreg_count}_rob{rob_size}")
    #print(f"gem5 output directory: {m5.options.outdir}")
    #if os.path.exists(m5.options.outdir):
    #    print(f"Path exists, removing")
    #    shutil.rmtree(m5.options.outdir)
    #os.makedirs(m5.options.outdir,exist_ok=True)
    #print(f"created output dir")
    #m5.core.setOutputDir(m5.options.outdir)

    root = Root(full_system=False, system=system)
    m5.instantiate()

    statgroups = root.getStatGroups()
    statmap = {}
    build_stat_tree(statmap, name="", groups=statgroups)

    #stat_df = pd.DataFrame(columns=[name for name in statmap.keys()])
    #stat_df.reset_index(drop=True,inplace=True)
    statdict = prepare_statdict(statmap)


    run = 0
    noexit=True
    print("starting workload loop")
    while noexit:
        exit_event = m5.simulate()
        if "workbegin" == exit_event.getCause():
            print("workbegin event detected, resetting statistics")
            m5.stats.reset()
        elif "workend" == exit_event.getCause():
            print("workend event detected, dumping statistics")
            #m5.stats.dump()
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
            statdict["iq_size"].append(iq_size)
            statdict["rob_size"].append(rob_size)
            statdict["assoc"].append(assoc)
            statdict["decode_width"].append(decode_width)
            statdict["commit_width"].append(commit_width)
            statdict["fetch_buf_size"].append(fetch_buf_size)
            statdict["run"].append(run)
            run = run+1
            cycle_value = statdict["system.cpu.numCycles"][run-1]
            print(f"Cycles: {cycle_value}")
        else:
            print("exit event neither workbegin nor workend, ending simulation")
            noexit=False

    print("Exiting @ tick %i because %s" % (m5.curTick(), exit_event.getCause()))


    reference_key = "system.cpu.numCycles"
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
    
    conn = db.connect()
    cursor = conn.cursor()
    db.add_rows(cursor, statdict)
    conn.close()
    #simrun.q.put(pd.DataFrame(statdict))
    # TODO: This print prevents a race condition, figure out where it is
    print("exiting sim worker")

#def simrun_init(result_queues):
#
#    from gem5.utils.multiprocessing.context import gem5Context
#    
#    queue_id = int(gem5Context().current_process().name.split('-')[1])%len(result_queues)
#    simrun.q = result_queues[queue_id]
