"""
Extract the trace of the flow from NS3-RDMA simulator output file
"""
from absl import app
from absl import flags
import pandas as pd
from math import ceil
from collections import Counter, defaultdict
import utils
import matplotlib.pyplot as plt
plt.style.use('seaborn')

FLAGS = flags.FLAGS
flags.DEFINE_string("input", "mix.tr", "The input file name.")
flags.DEFINE_string("output", "network_result.txt", "The output file name.")


def drawNodeThroughtput(tr, time_window=1e6, packet_size=1e3):
    """Draw a plot with time as x axis and throughtput as y axis

    Args:
        tr: a Dataframe containing the network trace
"""
    #dic = extractNodeDic(tr)
    gps = tr.groupby(tr.Node)
    ns = set(tr.Node)
    mx, mn = ceil(tr.Time.max() / time_window), tr.Time.min() // time_window
    x = list(range(int(mn), int(mx + 1)))
    bins = [t * time_window for t in x]
    scale = 1e9 / time_window
    for n in ns:
        gp = gps.get_group(n)
        # get the number of packets in each time window
        y = list(gp.groupby(pd.cut(gp.Time, bins)).count().Time)
        y = [v * scale * packet_size // 1e9 for v in y]
        plt.plot(x[:-1], y, label=n, alpha=0.3)
    # The position to place legend:
    # https://stackoverflow.com/questions/4700614/how-to-put-the-legend-out-of-the-plot
    #plt.legend(loc="upper left", ncol=2, fancybox=True, shadow=True)
    plt.xlabel("Time / ms")
    plt.ylabel("Throughput / GBps")
    plt.show()


def drawFlowSize(tr):
    fs = set(tr.Flow)
    dic = {f: len(set(tr[tr.Flow == f].Seq)) for f in fs}
    # plt.title("Max=%d    Min=%d    Most common=%d" % (x[-1], x[0], num_ct.most_common(1)11111]))
    utils.drawCDF(dic.values(), "Flow Size / Number of Packet")


def drawQueuingDelay(tr, link_delay=1e-6):
    #dic = extractFlowDic(tr)
    gps = tr.groupby(tr.Flow)
    qd = defaultdict(int)  # Queueing delay
    for f in gps.groups:
        flow = gps.get_group(f)
        flow.sort_values(['Seq', 'Time'], inplace=True)
        delay = [
            1e3 * max((a - b - link_delay), 0)
            for a, b in zip(flow[1:].Time, flow.Time)
        ]
        same_packet = [a == b for a, b in zip(flow[1:].Seq, flow.Seq)]
        qd[f] = sum(delay[i] for i in range(len(same_packet))
                    if same_packet[i])
    x = sorted([(len(set(gps.get_group(f).Seq)), f) for f in gps.groups])
    y = [qd[f] for _, f in x]
    x = [s for s, _ in x]
    plt.bar(x, y)
    plt.plot(x, y)
    plt.xlabel("Flow Size / Number of Packet")
    plt.ylabel("Queueing Dealy / ms")
    plt.show()


def drawFCT(tr, link_delay=1e-6):
    #dic = extractFlowDic(tr)
    gps = tr.groupby(tr.Flow)
    x = list(range(len(gps)))
    y = sorted(
        [1e-6 * (f.Time.max() - f.Time.min() + link_delay) for _, f in gps])
    plt.bar(x, y)
    plt.plot(x, y)
    plt.xlabel("Flow ID")
    plt.ylabel("Flow Completion Time / ms")
    plt.show()

    ct = Counter(y)
    x = sorted([(len(set(f.Seq)), key) for key, f in gps])
    y = [
        1e-6 * (gps.get_group(f).Time.max() - gps.get_group(f).Time.min() +
                link_delay) for _, f in x
    ]
    x = [s for s, _ in x]
    plt.bar(x, y)
    plt.plot(x, y)
    plt.xlabel("Flow Size / Number of Packet")
    plt.ylabel("Flow Completion Time / ms")
    plt.show()


def extractNodeDic(tr):
    nodes = set(tr.Node)
    dic = dict()
    for n in nodes:
        dic[n] = tr[tr.Node == n]
    return dic


def extractFlowDic(tr):
    flows = set(tr.Flow)
    dic = dict()
    print("flow numbers:", len(flows))
    for f in flows:
        dic[f] = tr[tr.Flow == f]
    return dic


def main(argv):
    if not FLAGS.input:
        print("No input file\n")

    # The last field "Flow" is made up by "Src>Dst Port"
    names = "Time Node Src>Dst Protocol Port Seq Priority Flow".split(' ')
    data = pd.read_csv(FLAGS.input, sep=' ', names=names)

    # There are CNP and ECN packet in the trace file, which can't be decoded normaly
    tr = data.dropna(thresh=len(names) - 1)
    # The trace contains unknown lines containing header message
    # e.g., 6769360518 /134 1.134>1.11 type=3, code=3 1.11>1.134 org data=192 84 0 0 3 240 0 0
    tr = tr[pd.to_numeric(tr.Port, errors="coerce").notnull()]
    tr.Port = tr.Port.astype(int)
    tr.Seq = tr.Seq.astype(int)
    tr.Flow = tr['Src>Dst'] + tr.Port.apply(lambda i: ' ' + str(i))

    # drawFlowSize(tr)
    # drawFCT(tr)
    # drawQueuingDelay(tr)
    drawNodeThroughtput(tr)


if __name__ == '__main__':
    app.run(main)
