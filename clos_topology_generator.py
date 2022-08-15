"""
Generate a 3-tier CLOS topology configuration file for NS3-RDMA simulator.

For the definition of CLOS, I refer to below links:
    https://packetpushers.net/demystifying-dcn-topologies-clos-fat-trees-part2/
    https://www.oreilly.com/library/view/bgp-in-the/9781491983416/ch01.html
"""

from sys import stderr
from absl import app
from absl import flags

DEBUG = False

FLAGS = flags.FLAGS
flags.DEFINE_list(
    "hosts", ['64'] * 4,
    "The number of servers in each pod. The length stands for the number of pods."
)
flags.DEFINE_list(
    "leaves", ['2', '2', '2', '2'],
    "The number of leaf switches in each pod. The length should be the same as the number o pods"
)
flags.DEFINE_list(
    "rates", ['10', '40', '40'],
    "The link rate in each layer, the unit is Gbps. ATTENTION: the length must be 3!"
)
flags.DEFINE_integer("delay", 1, "The delay time, the unit is microsecond.")
flags.DEFINE_integer("rack", 16, "The number of servers in a rack.")
flags.DEFINE_integer("spine", 8, "The total number of spine switches.")
flags.DEFINE_string("output", "topology.txt", "The output file name.")


def main(argv):
    if len(FLAGS.rates) != 3:
        print("The length of the rates must be 3!\n", file=stderr)
    if len(FLAGS.hosts) != len(FLAGS.leaves):
        print("The length of the hosts and leaves must be the same!\n",
              file=stderr)

    hosts = [int(h) for h in FLAGS.hosts]
    leaves = [int(l) for l in FLAGS.leaves]
    rates = [int(r) for r in FLAGS.rates]
    spine = FLAGS.spine
    rack = FLAGS.rack
    n = len(hosts)  # The number of pods

    with open(FLAGS.output, 'w') as f:
        # First line: total node #, switch node #, link #
        tors = [(h + rack - 1) // rack for h in hosts]  # Top of Racks
        switch = spine + sum(leaves) + sum(tors)
        sh = sum(hosts)
        nodes = sh + switch
        link = sh + sum(t * l
                        for t, l in zip(tors, leaves)) + len(leaves) * spine
        f.write("%d %d %d\n" % (nodes, switch, link))

        # The ID from 0 to (sh - 1) will be hosts, the following IDs will be switches.
        # Second line: switch node IDs...
        for i in range(sh, sh + switch):
            f.write("%d " % i)
        f.write("\n")

        delay = FLAGS.delay / 1000

        dp_host = [0] * (n + 1)
        dp_tor = [sh] * (n + 1)
        dp_leaf = [sh + sum(tors)] * (n + 1)
        for i in range(n):
            dp_host[i + 1] = dp_host[i] + hosts[i]
            dp_tor[i + 1] = dp_tor[i] + tors[i]
            dp_leaf[i + 1] = dp_leaf[i] + leaves[i]

        # Connect switches in each pod
        for i in range(n):
            if DEBUG: f.write("Pod %d\n" % i)
            # Connect hosts to ToR switches
            for j in range(dp_host[i], dp_host[i + 1]):
                f.write("%d %d %dGbps %.3fms 0\n" %
                        (j, sh + j // FLAGS.rack, rates[0], delay))

            if DEBUG: f.write("Leaf\n")
            # Connect ToR switches to leaf switches
            for j in range(dp_tor[i], dp_tor[i + 1]):
                for k in range(dp_leaf[i], dp_leaf[i + 1]):
                    f.write("%d %d %dGbps %.3fms 0\n" %
                            (j, k, rates[1], delay))

            if DEBUG: f.write("Spine\n")
            # Connect leaf switches to spine switches
            for j in range(dp_leaf[i], dp_leaf[i + 1]):
                for k in range(nodes - spine + j - dp_leaf[i], nodes,
                               leaves[i]):
                    f.write("%d %d %dGbps %.3fms 0\n" %
                            (j, k, rates[2], delay))


if __name__ == '__main__':
    app.run(main)
