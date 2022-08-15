"""
Parse the simulated csv trace file to flow configuration file for NS3-RDMA simulator.
"""
from absl import app
from absl import flags
import pandas as pd
from math import ceil

FLAGS = flags.FLAGS
flags.DEFINE_string("input", "100initiator_90hosts.csv",
                    "The input file name.")
flags.DEFINE_string("output", "flow.txt", "The output file name.")
flags.DEFINE_integer("payload", 1000, "The data size in each packet.")
flags.DEFINE_integer("n_init", 128, "The number of initiators.")
flags.DEFINE_integer("n_target", 128, "The number of targets.")


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
    with open(FLAGS.output, 'w') as f:
        f.write(str(len(data)) + '\n')
        for i in range(len_data):
            item = data.iloc[i]
            if not item["IOType"]:  # Read flow
                f.write("%d %d %d %d %.6f %.6f\n" %
                        (item["TargetID"] + num_initor, item["InitiatorID"], 3,
                         ceil(item["Size"] / FLAGS.payload),
                         item["FinishTime"], item["FinishTime"] + 10))
            else:  # Write flow
                f.write("%d %d %d %d %.6f %.6f\n" % (
                    item["InitiatorID"],
                    item["TargetID"] + num_initor,
                    3,
                    ceil(item["Size"] / FLAGS.payload),
                    # In the IO trace the write operation only record the time
                    # when data arrives at the node, here I assume it starts transmitting at that time
                    max(item["ArrivalTime"], 0),
                    item["ArrivalTime"] + 10))


if __name__ == '__main__':
    app.run(main)
