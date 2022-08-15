"""
Analyse the XML file generated by NS3 FlowMonitor
"""
from bs4 import BeautifulSoup as bs
from absl import app
from absl import flags
import matplotlib.pyplot as plt
from utils import drawCDF, roundList, getFlowMap
from collections import Counter, defaultdict
from math import ceil
import pandas as pd

FLAGS = flags.FLAGS
flags.DEFINE_string("input", "flow_monitor.xml", "The input XML file name.")
flags.DEFINE_string("map", None, "The file containing the mapping between the flow ID and the port number.")

time_unit = 1e6  # Transfer to ms from the original unit ns
size_unit = 1e3  # Transfer to KB from the original unit Bytes

def drawSizeAndDelay(fs):
    """Draw a plot with flow size as x axis and flow completion time as y axis

    Args:
        fs: a list of flow summary
"""
    x = [f['txBytes'] for f in fs]
    y = [f['delaySum'] for f in fs]
    plt.bar(x, y)
    plt.plot(x, y)
    plt.xlabel('Flow Size / KB')
    plt.ylabel('Total Delay / ms')
    plt.show()


def drawFlowBar(fs, y_field, y_label):
    """Draw a plot with flow ID as x axis

    Args:
        fs: a list of flow summary
"""
    x = range(1, len(fs) + 1)
    y = [f[y_field] for f in fs]
    plt.bar(x, y)
    plt.xlabel('Flow ID')
    plt.ylabel(y_label)
    plt.show()


def drawThroughput(fs, thd = 35, tw = 1e7):
    """Draw the flow throughput

    Args:
        fs: a list of flow summary
        thd: an int threshold. The flow with size less than thd won't be calculated.
             This is to filter out the ACK / NACK flow
        tw: an float for time window length in nano second
"""
    mn, mx = float('inf'), 0
    ct = Counter()
    time = dict()
    for f in fs:
        if f['txBytes'] < thd: continue
        t = f['timeFirstTxPacket'] * time_unit / tw
        mx = max(ceil(t), mx)
        t = int(t)
        mn = min(mn, t)

        ct[t] += f['txBytes']
        time.setdefault(t, [float('inf'), 0])
        time[t][0] = min(time[t][0], f['timeFirstTxPacket'])
        time[t][1] = max(time[t][1], f['timeLastRxPacket'])
        # time[t] = f['FCT']

    # y = [ct[t] * size_unit * 8 / (time[t] * time_unit) if t in time else 0 for t in range(mn, mx + 1)]
    # plt.plot(range(mn, mx + 1), y)
    # plt.xlabel('Time / %.2es' % (tw / 1e9))

    # Temporarily leave here for drawing throughput in ideal case experiment
    print(time)
    y = [ct[t] * size_unit * 8 / ((time[t][1] - time[t][0]) * time_unit) if t in time else 0 for t in range(mn, mx + 1, 1000)]
    print(y)
    plt.plot(range(mn//100, mx//100 + 1, 10), y, label = "Real Throughput")
    # #y = [ct[t] * size_unit * 8 / tw if t in time else 0 for t in range(mn, mx + 1, 1000)]
    #sr = [0.14, 0.2893333333333334, 0.40599999999999997, 0.5506666666666667, 0.714, 0.8166666666666665, 0.9566666666666667, 1.0686666666666669, 1.2553333333333334, 1.367333333333333]
    #y = [t * 6 for t in sr]
    #plt.plot(range(mn//100, mx//100 + 1, 10), y, '--r', label = "Aggregate Sending Rate")
    #plt.xticks(range(mn//100, mx//100 + 1, 10), roundList( sr, 2))
    #plt.xticks(rotation=45)

    plt.xlabel('Average Sending Rate (Gbps)')# % (tw / 1e9))
    plt.ylabel("Throughput (Gbps)")
    plt.legend(loc = 'best')
    plt.show()


def printThroughput(fs, ports = None):
    """Print a summary on the flow completion time of the flows

    Args:
        fs: a list of flow summary
        ports: a set or set-like data structure which support in-check (e.g., 12 in ports), only the flows with port in ports are calculated
    """
    print("Total flow size: %.4f GB" % sum([f['txBytes']/1e6 for f in fs if f['FCT'] > 0 and (not ports or int(f['destinationPort']) in ports)]))
    rates = [f['txBytes'] * 8 / 1e3 / f['FCT'] for f in fs if f['FCT'] > 0 and (not ports or int(f['destinationPort']) in ports)]
    ct = Counter(roundList(rates, 1))
    #print("Rate distribution:", sorted(ct.items()))
    print("Number of flows:", len(rates))
    print("Average rate: %.2f Gbps" % (sum(rates) / len(rates)))
    #print(sum([f['txBytes']/1e6 for f in fs]) * 8 / (max([f['timeLastRxPacket'] for f in fs]) - min([f['timeFirstTxPacket'] for f in fs])) * 1e3)


def main(argv):

    with open(FLAGS.input, 'r') as f:
        data = bs(f, 'xml')
    flows = data.FlowMonitor.FlowStats.findAll("Flow")
    ips = data.FlowMonitor.Ipv4FlowClassifier.findAll("Flow")

    # Extract the flow's identity information like source, destination address, port, etc
    flow_dic = {f['flowId']: f.attrs for f in flows}
    for ip in ips:
        flow_dic[ip['flowId']].update(ip.attrs)

    for f in flow_dic.values():
        # original format: "+123.1ns"
        f['timeFirstTxPacket'] = float(f['timeFirstTxPacket'][1:-2]) / time_unit
        f['timeLastRxPacket'] = float(f['timeLastRxPacket'][1:-2]) / time_unit
        f['delaySum'] = float(f['delaySum'][1:-2]) / time_unit
        f['jitterSum'] = float(f['jitterSum'][1:-2]) / time_unit
        f['txBytes'] = int(f['txBytes']) / size_unit     # The size unit is KB
        f['FCT'] = f['timeLastRxPacket'] - f['timeFirstTxPacket']

    fs = sorted([flow_dic[str(i)] for i in range(1,
                                                 len(flow_dic) + 1)],
                key=lambda f: f['txBytes'])
    # drawFlowBar(fs, 'txBytes', 'Flow Size / KB')
    # drawFlowBar(fs, 'delaySum', 'Total Delay / ms')
    # drawSizeAndDelay(fs)

    # Get the flow throughput summary
    #ports = None
    #if FLAGS.map:
    #    output = "flow_map.csv" # a temporary file
    #    getFlowMap(FLAGS.map, output)
    #    map_dt = pd.read_csv(output)  # Flow_ID,Port
    #    ports = set(map_dt.Port[:-1810])   # TODO: Why hard-coded 1810?
    #printThroughput(fs, ports)

    print("Port,FCT")
    for f in fs:
        print("%s,%d"%(f["destinationPort"], int(f["FCT"] * time_unit)))

    # drawCDF(fct, "FCT / ms")
    #small_fct = [f for f in fct if f < 0.2]
    #drawCDF(small_fct, "FCT < 0.2 ms (48,330 flows)", max_p=len(small_fct)/len(fct))

    #drawThroughput(fs)
    #senders = set([f['sourceAddress'] for f in fs if f['txBytes'] > 30])
    #for sender in senders:
    #    drawThroughput([f for f in fs if f['sourceAddress'] == sender])


if __name__ == '__main__':
    app.run(main)
