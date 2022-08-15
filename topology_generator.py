"""
Generate topology configuration file for NS3-RDMA simulator.
"""
from absl import app
from absl import flags

FLAGS = flags.FLAGS
flags.DEFINE_integer(
    "ni",
    10,
    "The total number of the devices connected to the ingress switches.",
    lower_bound=1)
flags.DEFINE_integer(
    "ne",
    10,
    "The total number of the devices connected to the egress switches.",
    lower_bound=1)
flags.DEFINE_integer("rate", 40, "The line rate, the unit is Gbps.")
flags.DEFINE_integer("delay", 1, "The delay time, the unit is microsecond.")
flags.DEFINE_integer(
    "ingress", -1,
    "The number of ingress switches, if not specified, will be calculated as the number of senders divide by 2."
)
flags.DEFINE_integer(
    "middle", -1,
    "The number of middle (spine) switches, if not specified, will be calculated as the number of leaves switches divide by 2."
)
flags.DEFINE_integer(
    "egress", -1,
    "The number of egress switches, if not specified, will be calculated as the number of receivers divide by 2."
)
flags.DEFINE_string("output", "topology.txt", "The output file name.")


def main(argv):
    i_host = FLAGS.ni
    e_host = FLAGS.ne
    if not (i_host | e_host):
        return
    ig = max(
        (i_host + 1) >> 1,
        1) if FLAGS.ingress <= 0 else FLAGS.ingress  # number of ingress switch
    eg = max(
        (e_host + 1) >> 1,
        1) if FLAGS.egress <= 0 else FLAGS.egress  # number of egress switch
    middle = max(1, max(ig, eg) >> 1) if FLAGS.middle <= 0 else FLAGS.middle

    ratio_ig, ratio_eg = i_host // ig + (i_host % ig >
                                         0), e_host // eg + (e_host % eg > 0)

    with open(FLAGS.output, 'w') as f:
        # First line: total node #, switch node #, link #
        switch = eg + ig + middle
        link = i_host + e_host + (ig + eg) * middle
        f.write("%d %d %d\n" % (i_host + e_host + switch, switch, link))

        # The ID from 0 to (ig + eg) will be hosts, the following IDs will be switches.
        # Second line: switch node IDs...
        start = i_host + e_host
        f.write(str(start))
        for i in range(start + 1, start + switch):
            f.write(" %d" % i)
        f.write("\n")

        delay = FLAGS.delay / 1000

        # Connect i_host and ingress switch, ingress swtich and spine switch
        for i in range(start, start + ig):
            for j in range((i - start) * ratio_ig,
                           min((i - start + 1) * ratio_ig, i_host)):
                f.write("%d %d %dGbps %.3fms 0\n" % (i, j, FLAGS.rate, delay))
            for j in range(start + ig, start + ig + middle):
                f.write("%d %d %dGbps %.3fms 0\n" % (i, j, FLAGS.rate, delay))

        # Connect e_host and egress switch, egress swtich and spine switch
        start = start + ig + middle
        for i in range(start, start + eg):
            for j in range(i_host + (i - start) * ratio_eg, i_host + min(
                (i - start + 1) * ratio_eg, e_host)):
                f.write("%d %d %dGbps %.3fms 0\n" % (i, j, FLAGS.rate, delay))
            for j in range(start - middle, start):
                f.write("%d %d %dGbps %.3fms 0\n" % (i, j, FLAGS.rate, delay))


if __name__ == '__main__':
    app.run(main)
