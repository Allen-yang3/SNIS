"""
Generate flow configuration file for NS3-RDMA N-to-1 simulation.
"""
from absl import app
from absl import flags
import pandas as pd
from math import ceil
import numpy as np
from collections import defaultdict

FLAGS = flags.FLAGS
flags.DEFINE_integer("incast", 2, "Incast ratio")
flags.DEFINE_multi_integer("target", list(range(128, 256, 13)),
                           "The target node ID")
flags.DEFINE_float("tw", 1e7, "Time window in nano second")
flags.DEFINE_float("size", 35, "Flow size")
# flags.DEFINE_multi_integer("lambda", [1e-3, 5e-3, 1e-3], "lambda")
# On average 744264ns between two different flows of the same node, obtained from 20 most busy nodes
flags.DEFINE_float(
    "lam_start", 5e-3,
    "The mean value of number of flows in one microsecond. There will be a group of data using range(lam_start, lam_end + 1, lam_gap)"
)
flags.DEFINE_float(
    "lam_end", 6e-3,
    "The mean value of number of flows in one microsecond. There will be a group of data using range(lam_start, lam_end + 1, lam_gap)"
)
flags.DEFINE_float(
    "lam_gap", 5e-4,
    "The mean value of number of flows in one microsecond. There will be a group of data using range(lam_start, lam_end + 1, lam_gap)"
)


def main(argv):
    tw = FLAGS.tw
    lam_start, lam_end, lam_gap = FLAGS.lam_start, FLAGS.lam_end, FLAGS.lam_gap
    total = FLAGS.incast * len(FLAGS.target)
    if total <= 128 // 2:
        senders = list(range(0, 128 // total * total, 128 // total))
    else:
        import random
        senders = random.sample(range(128), k=total)

    # The distribution of the most common 20 flow sizes
    # The other frequencies are added to the last flow item
    # Obtained from 100initiators_90hosts.csv (Tencent workload)
    dist = [[4.0, 0.4813935971772176], [8.0, 0.1003169564096472],
            [16.0, 0.05636768965569536], [64.0, 0.0485858284593492],
            [12.0, 0.04596525106284027], [32.0, 0.035670992169609596],
            [1.0, 0.0333668656701328], [512.0, 0.019236777053771376],
            [20.0, 0.01743310804321122], [24.0, 0.014283764451341883],
            [28.0, 0.01254682310597061], [128.0, 0.01095749144419899],
            [36.0, 0.008529008841415638], [48.0, 0.008027540327268866],
            [40.0, 0.0073835172556731155], [2.0, 0.007259161152366557],
            [44.0, 0.006454385069179402], [60.0, 0.006295654108048266],
            [3.0, 0.005908431444906707], [56.0, 0.0740171570981556]]
    """
    # Obtained from the write flows in Fujisu workload
    dist = [[5, 0.5696552687036689], [1, 0.08829239985514392],
            [9, 0.06223575763657702], [33, 0.04805120575235718],
            [2, 0.04619469180995929], [2, 0.030749193910808794],
            [17, 0.027140881266007253], [132, 0.02713433656350761],
            [13, 0.02119392826133433], [66, 0.007576583927083287],
            [4, 0.005785517009681797], [62, 0.0056197178796909145],
            [21, 0.005486642262198234], [3, 0.005189949082214553],
            [3, 0.003911550527284865], [25, 0.003813379989790264],
            [4, 0.003656307129798903], [29, 0.0024499003023652553],
            [50, 0.00161435994991121], [41, 0.034248428180616325]]

    # Obtained from the write flows in K5cloud workload
    dist = [[5, 0.5884031303427957], [66, 0.0725968361337808],
            [9, 0.04669812902048282], [1, 0.0384886150728762],
            [3, 0.035562144356828286], [17, 0.024580119119898387],
            [2, 0.02408595902444354], [4, 0.01878180845212421],
            [33, 0.0165046988665358], [3, 0.014308293819149819],
            [2, 0.01305426945631215], [13, 0.013019504424471105],
            [20, 0.012087056606163096], [4, 0.0115146751890659],
            [25, 0.007688038469990948], [29, 0.006871060221726406],
            [21, 0.006021800158180895], [5, 0.005209788343036503],
            [6, 0.003989287403759838], [17, 0.04053478551837762]]
    """

    packet_num, prob = zip(*dist)
    dic = defaultdict(list)
    with open('flow.txt', 'w') as f:
        for ti, tg in enumerate(FLAGS.target):
            for idx in range(ti, len(senders), len(FLAGS.target)):
                nd = senders[idx]
                for lam in range(int(lam_start * 1e6),
                                 int(lam_end * 1e6) + 1, int(lam_gap * 1e6)):
                    lam /= 1e6
                    target = lam * FLAGS.tw / 1e3
                    # The flow sending follows poisson
                    poisson = np.random.poisson(lam, int(FLAGS.tw / 1e3))
                    while abs(sum(poisson) - target) > target * 0.1:
                        poisson = np.random.poisson(lam, int(FLAGS.tw / 1e3))
                    #poisson = np.random.binomial(1, lam, int(FLAGS.tw / 1e3))
                    size = 0
                    for i, n in enumerate(poisson):
                        time = (lam - lam_start) / lam_gap * 10 + i / 1e6
                        for j in range(n):
                            packet = np.random.choice(
                                packet_num,
                                p=prob) if FLAGS.size <= 0 else FLAGS.size
                            f.write("%d %d 3 %d %.6f %.6f\n" %
                                    (nd, tg, packet, time, time + 10))
                            size += packet

                    # One packet is 1030 Bytes, here it uses 1e3 Bytes to stand for the packet size
                    rate = size * 8 * 1e3 / FLAGS.tw
                    time = (lam - lam_start) / lam_gap * 10
                    dic[time].append(rate)
                    print(
                        "lambda=%f sum_poisson=%d Node %d rate %fGbps at %ds" %
                        (lam, sum(poisson), nd, rate, time))

    print('\n')
    for t in sorted(dic):
        print("Average rate at %ds:\t%fGbps" % (t, sum(dic[t]) / len(dic[t])))
    print([sum(dic[t]) / len(dic[t]) for t in sorted(dic)])


if __name__ == '__main__':
    app.run(main)
