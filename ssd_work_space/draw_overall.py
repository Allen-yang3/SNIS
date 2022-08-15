from absl import app
from absl import flags
import pandas as pd
import os
import numpy as np
from collections import Counter
from utils import readQueue, readFlows, readSummary
import matplotlib.pyplot as plt
#plt.style.use('seaborn')
plt.style.use('fivethirtyeight')

FLAGS = flags.FLAGS
flags.DEFINE_string("path", "test", "The directory containing log data")
flags.DEFINE_string("ssd", "net-ssd.csv", "The input file name")
flags.DEFINE_string("map", "flow_map.csv",
                    "Map from flow ID to destination port")
flags.DEFINE_string("fct", "fct.csv", "The flow completion time file")
flags.DEFINE_list(
    "trace",
    ['0.5us_16KB_10:1_x2_net-ssd', '5us_16KB_10:1_x2_net-ssd'],
    #['5us_V0_based_100:1_net-ssd', '10us_V0_based_50:1_net-ssd', '50us_V0_based_net-ssd'],
    "The trace going to be considered")


def readTraceFile(path):
    # The last field "Flow" is made up by "Src>Dst Port"
    names = "Time Node Src>Dst Protocol Port Seq Priority Flow".split(' ')
    data = pd.read_csv(path, sep=' ', names=names)

    # There are CNP and ECN packet in the trace file, which can't be decoded normaly
    tr = data.dropna(thresh=len(names) - 1)
    # The trace contains unknown lines containing header message
    # e.g., 6769360518 /134 1.134>1.11 type=3, code=3 1.11>1.134 org data=192 84 0 0 3 240 0 0
    tr = tr[pd.to_numeric(tr.Port, errors="coerce").notnull()]
    tr["Port"] = tr.Port.astype(int)
    tr["Seq"] = tr.Seq.astype(int)
    tr["Node"] = tr.Node.apply(lambda nd: int(nd[1:]))
    tr["Flow"] = tr['Src>Dst'] + tr.Port.apply(lambda i: ' ' + str(i))

    return tr


def drawPAUSEAndSendingRate(path):
    """Draw spine-level received PAUSE packet number and the accurate sendiing rate in each time window

    Args:
        path: A string for the path to the the directory containing all log files
    """
    tw = 1e6  # Time window (time unit)
    unit_dic = {1e3: "us", 1e6: "ms", 1e9: "s"}
    _, pause_data, _ = readQueue(os.path.join(path, "queue.txt"))

    # Count packets in read and write flows, respectively
    packet_data = readTraceFile(os.path.join(path, "mix.tr"))
    packet_data["tw"] = packet_data.Time // tw
    overall_data = readSummary(path)

    # Only consider about the ToR level switch since they are the closest switches to senders
    packet_data = packet_data[packet_data.Node.isin(range(256, 272))]

    # Map the unique port number to the IO type, 0 for read and 1 for write
    packet_data["IOType"] = packet_data["Port"].map(
        overall_data.set_index("Port")["IOType"])
    # Map the IO type to the ToR switches
    switch_dic = {1: set(range(256, 264)), 0: set(range(264, 272))}

    packet_count = [
        Counter(packet_data[(packet_data.IOType == i)
                            & (packet_data.Node.isin(switch_dic[i]))].tw)
        for i in range(2)
    ]

    min_t, max_t = int(packet_data.tw.min()), int(packet_data.tw.max())

    # Count PAUSE packet number
    nodes = range(280, 288)  # Only consider spine nodes
    mn, mx = float('inf'), 0
    pause_count = Counter()
    for p in pause_data:
        if nodes and p not in nodes:
            continue
        tmp = [t // tw for t in pause_data[p]]
        pause_count.update(tmp)
        mx = max(max(tmp), mx)
        mn = min(mn, min(tmp))

    key = range(min(min_t, int(mn)), max(max_t, int(mx)) + 1)

    # Draw
    x = range(len(key))
    fig, ax = plt.subplots(2, sharex=True, constrained_layout=True)

    fig.suptitle(os.path.normpath(path).split('/')[-2])
    ax[0].plot(x, [pause_count[k] for k in key],
               label="PAUSE",
               color="red",
               marker='o')
    ax[0].set_ylabel("PAUSE Number")

    ax[1].plot(x, [packet_count[1][k] * 8 * 1e3 / tw for k in key],
               label="Write",
               marker='d')
    ax[1].plot(x, [packet_count[0][k] * 8 * 1e3 / tw for k in key],
               label="Read",
               marker='o')
    ax[1].set_ylabel("Sending Rate (Gbs)")
    ax[1].set_xlabel("Time (%s)" %
                     (unit_dic[tw] if tw in unit_dic else "%.2es" %
                      (tw / 1e9)))
    ax[1].legend(loc='best')

    plt.show()


def scanLine(A):
    if not A:
        return None
    start, end = list(zip(*A))
    A = sorted([(t, 1) for t in start] + [(t + 1, -1) for t in end])
    ret = [0] * (A[-1][0] - A[0][0] + 1)
    ct = idx = 0
    for i in range(len(ret)):
        while idx < len(A) and A[0][0] + i >= A[idx][0]:
            ct += A[idx][1]
            idx += 1
        ret[i] = ct
    return A[0][0], A[-1][0], ret


def drawPAUSEAndFlow(path):
    """Draw spine-level received PAUSE packet number and the number of active flows in each time window

    Args:
        path: A string for the path to the the directory containing all log files
    """
    tw = 1e6  # Time window (time unit)
    unit_dic = {1e3: "us", 1e6: "ms", 1e9: "s"}
    # TODO: The file name is fixed, but should I?
    _, pause_data, _ = readQueue(os.path.join(path, "queue.txt"))
    flow_data = readFlows(os.path.join(path, "flow_monitor.xml"), time_unit=tw)
    overall_data = readSummary(path)
    id_io_dic = {
        overall_data.iloc[i].Port: overall_data.iloc[i].IOType
        for i in range(len(overall_data))
    }

    # Count flow number in each time window
    # Each element is a tuple containing  (min_t, max_t, flow_count)
    flow_count = [
        scanLine([[int(f['timeFirstTxPacket']),
                   int(f['timeLastRxPacket'])] for f in flow_data
                  if int(f['destinationPort']) in id_io_dic
                  and id_io_dic[int(f['destinationPort'])] == i])
        for i in range(2)
    ]
    mins = [flow_count[i][0] for i in range(len(flow_count))]
    maxs = [flow_count[i][1] for i in range(len(flow_count))]
    min_t, max_t = min(mins), max(maxs)
    flow_count = [flow_count[i][-1] for i in range(len(flow_count))]

    # Count PAUSE packet number
    nodes = range(280, 288)  # Only consider spine nodes
    mn, mx = float('inf'), 0
    ct = Counter()
    for p in pause_data:
        if nodes and p not in nodes:
            continue
        tmp = [t // tw for t in pause_data[p]]
        ct.update(tmp)
        mx = max(max(tmp), mx)
        mn = min(mn, min(tmp))
    min_t = min(min_t, int(mn))
    max_t = max(max_t, int(mx))
    x = range(min_t, max_t + 1)
    pause_count = [ct[t] if t in ct else 0 for t in x]

    # Draw
    flow_count = [[0] * int(mins[i] - min_t) + flow_count[i]
                  for i in range(len(flow_count))]
    flow_count = [
        flow_count[i] + [0] * int(max_t - maxs[i])
        for i in range(len(flow_count))
    ]
    x = range(len(x))
    fig, ax = plt.subplots(2, sharex=True, constrained_layout=True)
    fig.suptitle(os.path.normpath(path).split('/')[-2])
    ax[0].plot(x, pause_count, label="PAUSE", color="red", marker='o')
    #ax[0].set_xlabel("Time (%s)" % (unit_dic[tw] if tw in unit_dic else "%.2es" % (tw / 1e9)))
    ax[0].set_ylabel("PAUSE Number")

    # ax2 = ax.twinx()
    #ax[1].bar(x, flow_count, label = "Flow Count", width = 1, color = "blue")
    ax[1].stackplot(x, *flow_count[::-1], labels=["Write", "Read"])
    ax[1].set_ylabel("Flow Count")
    ax[1].set_xlabel("Time (%s)" %
                     (unit_dic[tw] if tw in unit_dic else "%.2es" %
                      (tw / 1e9)))
    ax[1].legend(loc='best')

    #fig.tight_layout()
    plt.show()


def drawTotalStats(trs):
    """Draw a plot containing both network stats and ssd stats

    Args:
        trs: A list containing the data directory pathes
    """
    dic, network_thr, ssd_thr = {}, {}, {}

    for tr in trs:
        dir_path = tr
        mx_itr = max([int(f) for f in os.listdir(dir_path) if f.isdigit()])
        last_itr_dir = os.path.join(dir_path, str(mx_itr - 1))
        ssd_dt = readSummary(last_itr_dir)

        tr = os.path.basename(os.path.normpath(tr)).replace('_net-ssd', '')

        # Record throughput
        dic[tr] = ssd_dt.Size / ssd_dt.TotalDelay
        ssd_thr[tr] = ssd_dt.Size / ssd_dt.DelayTime
        network_thr[tr] = ssd_dt.Size / ssd_dt.FCT

        # Draw CDF
        y = np.linspace(0, 1, len(ssd_dt), endpoint=False)
        x = sorted(ssd_dt.TotalDelay / 1e6)
        plt.plot(x, y, label=tr)

        # Draw ssd delay CDF
        y = np.linspace(0, 1, len(ssd_dt), endpoint=False)
        x = sorted(ssd_dt.DelayTime / 1e6)
        plt.plot(x, y, label=tr + "_ssd")

        # Draw network delay CDF
        y = np.linspace(0, 1, len(ssd_dt), endpoint=False)
        x = sorted(ssd_dt.FCT / 1e6)
        plt.plot(x, y, label=tr + "_network")

    #plt.xlim(0, 2)
    plt.xlabel('Delay (ms)')
    plt.ylabel("$p$")
    plt.title('Delay Distribution')
    plt.legend(loc='best')
    plt.show()

    mx = 0
    for tr in dic:
        x = sorted(dic[tr])
        mx = max(mx, sorted(ssd_thr[tr])[-len(x) // 10])
        y = np.linspace(0, 1, len(x), endpoint=False)
        plt.plot(x, y, label=tr)
        plt.plot(sorted(ssd_thr[tr])[:len(x)], y, label=tr + "_ssd")
        plt.plot(sorted(network_thr[tr])[:len(x)], y, label=tr + "_network")

    #plt.xlim(0, mx)
    plt.xlabel('Throughput (GB/s)')
    plt.ylabel("$p$")
    plt.title('Throughput Distribution')
    plt.legend(loc='best')
    plt.show()


def drawOverallCmp(trs):
    """Draw the comparison of overall delay and throughput

    Args:
        trs: A list containing the trace directory pathes
    """
    dic = {}
    print("trace\ttotal\tssd\tnet_throughput")
    for tr in trs:
        dir_path = tr
        # Use the data in the last iteration to compare
        mx_itr = max([int(f) for f in os.listdir(dir_path) if f.isdigit()])
        last_itr_dir = os.path.join(dir_path, str(mx_itr - 1))
        ssd_dt = readSummary(last_itr_dir)

        tr = os.path.basename(os.path.normpath(tr)).replace('_net-ssd', '')

        # Record throughput
        dic[tr] = ssd_dt.Size / ssd_dt.TotalDelay
        print(tr, dic[tr].mean(), (ssd_dt.Size / ssd_dt.DelayTime).mean(),
              (ssd_dt.Size / ssd_dt.FCT).mean())

        # Draw CDF
        y = np.linspace(0, 1, len(ssd_dt), endpoint=False)
        x = sorted(ssd_dt.TotalDelay / 1e6)
        plt.plot(x, y, label=tr)
    #plt.xlim(0, 10)
    plt.xlabel('Total Delay (ms)')
    plt.ylabel("$p$")
    plt.title('Total Delay Distribution')
    plt.legend(loc='best')
    plt.show()

    for tr in dic:
        tr = os.path.basename(os.path.normpath(tr)).replace('_net-ssd', '')
        y = np.linspace(0, 1, len(dic[tr]), endpoint=False)
        x = sorted(dic[tr])
        plt.plot(x, y, label=tr)
    plt.xlabel('Throughput (GB/s)')
    plt.ylabel("$p$")
    plt.title('Total Throughput Distribution')
    plt.legend(loc='best')
    plt.show()


def drawWorkloadDis(path, tw=1e6):
    """Draw the workload distribution"""
    unit_dic = {1e3: "us", 1e6: "ms", 1e9: "s"}
    data = pd.read_csv(path)
    w = data[data.IOType == 1]
    w['tw'] = w.ArrivalTime // tw
    r = data[data.IOType == 0]
    r['tw'] = r.FinishTime // tw
    ct_r, ct_w = Counter(), Counter()
    for i in range(len(w)):
        ct_w[w.iloc[i].tw] += w.iloc[i].Size
    for i in range(len(r)):
        ct_r[r.iloc[i].tw] += r.iloc[i].Size
    mn = int(min(min(ct_r), min(ct_w)))
    mx = int(max(max(ct_r), max(ct_w)))
    plt.plot(range(mx - mn + 1), [ct_w[i] * 8 / tw for i in range(mn, mx + 1)],
             label='Write',
             marker='o')
    plt.plot(range(mx - mn + 1), [ct_r[i] * 8 / tw for i in range(mn, mx + 1)],
             label='Read',
             marker='d')
    plt.legend(loc='best')
    plt.title(path.split('/')[-1].split('.csv')[0])
    plt.ylabel("Sending Rate (Gbs)")
    plt.xlabel("Time (%s)" % (unit_dic[tw] if tw in unit_dic else "%.2es" %
                              (tw / 1e9)))
    plt.tight_layout()
    plt.show()
    print(
        sum(ct_w.values()) / (data.FinishTime.max() - data.ArrivalTime.min()) *
        8)
    print(
        sum(ct_r.values()) / (data.FinishTime.max() - data.ArrivalTime.min()) *
        8)


def main(argv):
    #drawTotalStats(FLAGS.trace)
    #drawOverallCmp(FLAGS.trace)
    drawPAUSEAndFlow(FLAGS.path)
    drawPAUSEAndSendingRate(FLAGS.path)
    #drawWorkloadDis(FLAGS.path)


if __name__ == '__main__':
    app.run(main)
