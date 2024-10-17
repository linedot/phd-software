import math

def prepare_statdict(statmap):
    import _m5.stats
    statdict = {}
    statdict["mr"] = []
    statdict["nr"] = []
    statdict["simd_lat"] = []
    statdict["simd_count"] = []
    statdict["simd_width"] = []
    statdict["simd_phreg_count"] = []
    statdict["ld_count"] = []
    statdict["st_count"] = []
    statdict["l1_size"] = []
    statdict["cl_size"] = []
    statdict["assoc"] = []
    statdict["iq_size"] = []
    statdict["rob_size"] = []
    statdict["decode_width"] = []
    statdict["commit_width"] = []
    statdict["fetch_buf_size"] = []
    statdict["run"] = []
    for name,stat in statmap.items():
        stat.prepare()
        if isinstance(stat,_m5.stats.FormulaInfo):
            if len(stat.subnames) > 1:
                for sname in stat.subnames:
                    if sname == "":
                        continue
                    statdict[f"{name}::{sname}"] = []
            else:
                statdict[f"{name}"] = []
        elif isinstance(stat,_m5.stats.ScalarInfo):
            statdict[f"{name}"] = []
        elif isinstance(stat, _m5.stats.DistInfo):
            for i,v in enumerate(stat.values):
                bucket_start = stat.min_val+i*stat.bucket_size
                if bucket_start.is_integer():
                    bucket_start = int(bucket_start)
                bucket_end = stat.min_val+(i+1)*stat.bucket_size-1
                if bucket_end.is_integer():
                    bucket_end = int(bucket_end)
                bucket = f"{bucket_start}-{bucket_end}"
                if bucket_end == bucket_start:
                    bucket = f"{bucket_start}"
                statdict[f"{name}::{bucket}"] = []
            statdict[f"{name}::min_value"] = []
            statdict[f"{name}::max_value"] = []
            statdict[f"{name}::mean"] = []
            statdict[f"{name}::stddev"] = []
            statdict[f"{name}::samples"] = []
            statdict[f"{name}::total"] = []
            statdict[f"{name}::overflows"] = []
        elif isinstance(stat, _m5.stats.VectorInfo):
            for sname,sval in zip(stat.subnames,stat.value):
                if sname == "":
                    continue
                statdict[f"{name}::{sname}"] = []
    return statdict


def append_stats(statmap, statdict):
    import _m5.stats
    import m5
    import functools
    for name,stat in statmap.items():
        if isinstance(stat,_m5.stats.FormulaInfo):
            if len(stat.subnames) > 1:
                for sname,sval in zip(stat.subnames,stat.value):
                    if sname == "":
                        continue
                    statdict[f"{name}::{sname}"].append(sval)
            else:
                val = stat.result
                statdict[f"{name}"].append(val[0])
        elif isinstance(stat,_m5.stats.ScalarInfo):
            statdict[f"{name}"].append(stat.result)
        elif isinstance(stat, _m5.stats.DistInfo):
            for i,v in enumerate(stat.values):
                bucket_start = stat.min_val+i*stat.bucket_size
                if bucket_start.is_integer():
                    bucket_start = int(bucket_start)
                bucket_end = stat.min_val+(i+1)*stat.bucket_size-1
                if bucket_end.is_integer():
                    bucket_end = int(bucket_end)
                bucket = f"{bucket_start}-{bucket_end}"
                if bucket_end == bucket_start:
                    bucket = f"{bucket_start}"
                # Sometimes the bucket doesn't exist.
                # In this case initialize the value list with as many
                # zeroes as there are elements in the min_val list, as
                # min_val should have been recorded every time
                must_len = len(statdict[f"{name}::min_value"])
                if f"{name}::{bucket}" not in statdict:
                    statdict[f"{name}::{bucket}"] = [0]*must_len
                # Also if the bucket exists, but the len is too small, 
                # fill the missing values with zeroes
                bucket_vlist_len = len(statdict[f"{name}::{bucket}"])
                if must_len > bucket_vlist_len:
                    statdict[f"{name}::{bucket}"].extend([0]*(must_len-bucket_vlist_len))
                statdict[f"{name}::{bucket}"].append(v)
            statdict[f"{name}::min_value"].append(stat.min_val)
            statdict[f"{name}::max_value"].append(stat.max_val)
            count = functools.reduce(lambda a,b : a+b, stat.values, 0)
            statdict[f"{name}::mean"].append(stat.sum/max(1.0,count))
            stddev = math.sqrt(
                              max(0.0,(stat.squares*count - stat.sum*stat.sum))/
                              max(1.0,(count*(count-1.0))))
            statdict[f"{name}::stddev"].append(stddev)
            statdict[f"{name}::samples"].append(count)
            statdict[f"{name}::total"].append(stat.sum)
            statdict[f"{name}::overflows"].append(stat.overflow)
        elif isinstance(stat, _m5.stats.VectorInfo):
            for sname,sval in zip(stat.subnames,stat.value):
                if sname == "":
                    continue
                statdict[f"{name}::{sname}"].append(sval)
        elif isinstance(stat, _m5.stats.Info):
            pass
            # I'm not sure what to do with a _m5.stats.Info object?
            #print(f"{name}{stat.name}/unit = {stat.unit}")
            #print(f"{name}{stat.name}/flags = {stat.flags}")
            #print(f"{name}{stat.name}/desc = {stat.desc}")
        else:
            print("%s is a %s and has %s" %(f"{name}{stat.name}",type(stat),dir(stat)))


def build_stat_tree(statmap : dict, name: str, groups):
    for key in groups:
        group = groups[key]
        subgroups = group.getStatGroups()
        if 0 != len(subgroups):
            build_stat_tree(statmap, f"{name}{key}.", subgroups)
        stats = group.getStats()
        statmap.update({f"{name}{key}.{stat.name}" : stat for stat in stats if f"{name}{stat.name}" not in statmap })

def prepare_stats(groups):
    for key in groups:
        group = groups[key]
        group.preDumpStats()
        subgroups = group.getStatGroups()
        if 0 != len(subgroups):
            prepare_stats(subgroups)
        stats = group.getStats()
        for stat in stats:
            stat.prepare()
