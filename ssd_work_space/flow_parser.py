"""
Parse the simulated csv trace file to flow configuration file for NS3-RDMA simulator.
"""
from absl import app
from absl import flags
import pandas as pd
from math import ceil
import numpy as np

FLAGS = flags.FLAGS
flags.DEFINE_string("input", "100initiator_90hosts.csv",
                    "The input file name.")
flags.DEFINE_string("output", "flow.txt", "The output file name.")
flags.DEFINE_integer("payload", 1000, "The data size in each packet.")
flags.DEFINE_integer("n_init", 128, "The number of initiators.")
flags.DEFINE_integer("n_target", 128, "The number of targets.")
flags.DEFINE_integer("rack_size", 16, "The number of nodes in each rack")
flags.DEFINE_string("map_mod", 'sequential', "Mapping mod from ssd to network id")
flags.DEFINE_integer("rack_num", 2, "racks to spread over")

def id_map_ssd2network(ssd_ids: list, start_id: int, end_id: int, rack_size: int, mod='random', rack_num=10):
    """
    Map intiator/target id from trace to network topology.
    Return a mapping dictionary from trace/ssd id to network id.
    Assumption: 1. ssd_ids are contineous integers.
                2. rack_num is used in 'even' mod to specify how many racks ssd_ids spreading on.
    """
    id_len = len(ssd_ids)
    ret_dict = {}
    if mod == 'random':
        np.random.seed(123)
        rnd_array = np.random.choice(range(start_id, end_id + 1), size=id_len, replace=False, p=None)
        # rnd_array = np.random.randint(low=start_id, high=end_id, size=id_len)
        for i, ssd_id in enumerate(ssd_ids):
            ret_dict[ssd_id] = rnd_array[i]    
    elif mod == 'sequential': 
        for i, ssd_id in enumerate(ssd_ids):
            ret_dict[ssd_id] = ssd_id + start_id
            if ret_dict[ssd_id]>end_id:
                raise Exception("node id out of range") 
    elif mod == 'even':
        if rack_num*rack_size<id_len:
            raise Exception(f"node id out of range in nodes of {rack_num} rack")
        # select racks in round-robin
        # e.g., ssd_ids = [0,1,2,3,4,5,6,7,8,9], rack_num=4
        # ret_dict = {0: 0, 6: 33, 5: 17, 8: 2, 4: 1, 3: 48, 2: 32, 9: 18, 1: 16, 7: 49}
        for i, ssd_id in enumerate(ssd_ids):
            # mapped_id = rack offset + node offset 
            rack_idx = ssd_id % rack_num
            ret_dict[ssd_id] = start_id + rack_idx * rack_size + (ssd_id // rack_num)
    else:
        raise Exception("unrecognized mod!")
    
#     print(f"SSD to network topology mapping: {ret_dict}")
    return ret_dict


def main(argv):
    if not FLAGS.input:
        print("No input file\n")
    data = pd.read_csv(FLAGS.input)
    data = data[(data.InitiatorID.isin(range(FLAGS.n_init)))
                & (data.TargetID.isin(range(FLAGS.n_target)))
                ]
                #& (data.ArrivalTime >= 6e9)  # The busiest time window
                #& (data.FinishTime < 7e9)]
    data.ArrivalTime /= 1e9
    data.FinishTime /= 1e9
    data.DelayTime /= 1e9
    len_data = data.shape[0]
    num_initor = max(len(set(data.InitiatorID)),
                     data.InitiatorID.max() + 1, FLAGS.n_init)
    
    initor_id = list(data.InitiatorID.drop_duplicates().values)
    target_id = list(data.TargetID.drop_duplicates().values)
    initor_map_dict = id_map_ssd2network(ssd_ids=initor_id, start_id=0, \
                                            end_id=num_initor-1, rack_size=FLAGS.rack_size, \
                                            mod=FLAGS.map_mod, rack_num=FLAGS.rack_num)
    target_map_dict = id_map_ssd2network(ssd_ids=target_id, start_id=num_initor, \
                                            end_id=num_initor+FLAGS.n_target, rack_size=FLAGS.rack_size, \
                                            mod=FLAGS.map_mod, rack_num=FLAGS.rack_num)
    
    print("initor map: {}\n target_map: {}".format(initor_map_dict, target_map_dict))

    with open(FLAGS.output, 'w') as f:
        f.write(str(len(data)) + '\n')
        for i in range(len_data):
            item = data.iloc[i]
            #edit by allen
            if not item["IOType"]:  # Read flow
                f.write("%d %d %d %d %d %.6f\n" %
                        (target_map_dict[int(item["TargetID"])], 
                        initor_map_dict[int(item["InitiatorID"])], 3,
                         100, ceil(item["Size"]),
                         item["FinishTime"]))
            else:  # Write flow
                f.write("%d %d %d %d %d %.6f\n" % (
                    initor_map_dict[int(item["InitiatorID"])],
                    #(item["InitiatorID"] + 1) // 10 * 12,	# Merge 100 nodes into 10 nodes
                    target_map_dict[int(item["TargetID"])],
                    3, 100,
                    ceil(item["Size"]),
                    # In the IO trace the write operation only record the time
                    # when data arrives at the node, here I assume it starts transmitting at that time
                    (item["ArrivalTime"])
                    ))

            #if not item["IOType"]:  # Read flow
            #    f.write("%d %d %d %d %.6f %.6f\n" %
            #            (item["TargetID"] + num_initor, item["InitiatorID"], 3,
            #             ceil(item["Size"] / FLAGS.payload),
            #             item["FinishTime"], item["FinishTime"] + 10))
            #else:  # Write flow
            #    f.write("%d %d %d %d %.6f %.6f\n" % (
            #        item["InitiatorID"],
            #        #(item["InitiatorID"] + 1) // 10 * 12,	# Merge 100 nodes into 10 nodes
            #        item["TargetID"] + num_initor,
            #        3,
            #        ceil(item["Size"] / FLAGS.payload),
            #        # In the IO trace the write operation only record the time
            #        # when data arrives at the node, here I assume it starts transmitting at that time
            #        max(item["ArrivalTime"], 0),
            #        item["ArrivalTime"] + 10))


if __name__ == '__main__':
    app.run(main)
