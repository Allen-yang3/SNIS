
import sys
import os
from collections import defaultdict
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

def parse_time_ns(tm):
    if tm.endswith('ns'):
        return float(tm[:-2])
    raise ValueError(tm)



class FiveTuple(object):
    __slots__ = ['sourceAddress', 'destinationAddress', 'protocol', 'sourcePort', 'destinationPort']
    def __init__(self, el):
        self.sourceAddress = el.get('sourceAddress')
        self.destinationAddress = el.get('destinationAddress')
        self.sourcePort = int(el.get('sourcePort'))
        self.destinationPort = int(el.get('destinationPort'))
        self.protocol = int(el.get('protocol'))
        
class Histogram(object):
    __slots__ = 'bins', 'nbins', 'number_of_flows'
    def __init__(self, el=None):
        self.bins = []
        if el is not None:
            #self.nbins = int(el.get('nBins'))
            for bin in el.findall('bin'):
                self.bins.append( (float(bin.get("start")), float(bin.get("width")), int(bin.get("count"))) )
class Flow(object):
    __slots__ = ['flowId', 'delayMean', 'packetLossRatio', 'rxBitrate', 'txBitrate',
                 'fiveTuple', 'packetSizeMean', 'probe_stats_unsorted',
                 'hopCount', 'flowInterruptionsHistogram', 'rx_duration',
                 'flowcompletiontime', 'throughput','delay',
                 'sentPackets', 'receivePackets', 'txBytes'
                ]
    def __init__(self, flow_el):
        self.flowId = int(flow_el.get('flowId'))
        rxPackets = int(flow_el.get('rxPackets'))
        txPackets = int(flow_el.get('txPackets'))
        tx_duration = float(float(flow_el.get('timeLastTxPacket')[:-2]) - float(flow_el.get('timeFirstTxPacket')[:-2]))*1e-9
        rx_duration = float(float(flow_el.get('timeLastRxPacket')[:-2]) - float(flow_el.get('timeFirstRxPacket')[:-2]))*1e-9
        # tx_duration = float(long(flow_el.get('timeLastTxPacket')[:-2]) - long(flow_el.get('timeFirstTxPacket')[:-2]))*1e-9
        # rx_duration = float(long(flow_el.get('timeLastRxPacket')[:-2]) - long(flow_el.get('timeFirstRxPacket')[:-2]))*1e-9
        self.flowcompletiontime = float(float(flow_el.get('timeLastRxPacket')[:-2]) - float(flow_el.get('timeFirstTxPacket')[:-2]))
        


        self.txBytes = int(flow_el.get('rxBytes'))
        rxBytes = float(flow_el.get('rxBytes'))
        self.delay = float(flow_el.get('delaySum')[:-2])
        self.rx_duration = rx_duration
        self.probe_stats_unsorted = []
        if rxPackets:
            self.hopCount = float(flow_el.get('timesForwarded')) / rxPackets + 1
        else:
            self.hopCount = -1000
        if rxPackets:
            self.delayMean = float(flow_el.get('delaySum')[:-2]) / rxPackets * 1e-9
            self.packetSizeMean = float(flow_el.get('rxBytes')) / rxPackets
        else:
            self.delayMean = None
            self.packetSizeMean = None
        if rx_duration > 0:
            self.rxBitrate = int(flow_el.get('rxBytes'))*8 / rx_duration
        else:
            self.rxBitrate = None
        if tx_duration > 0:
            self.txBitrate = int(flow_el.get('txBytes'))*8 / tx_duration
        else:
            self.txBitrate = None
        lost = float(flow_el.get('lostPackets'))
        #print "rxBytes: %s; txPackets: %s; rxPackets: %s; lostPackets: %s" % (flow_el.get('rxBytes'), txPackets, rxPackets, lost)
        if rxPackets == 0:
            self.packetLossRatio = None
        else:
            self.packetLossRatio = (lost / (rxPackets + lost))

        interrupt_hist_elem = flow_el.find("flowInterruptionsHistogram")
        if interrupt_hist_elem is None:
            self.flowInterruptionsHistogram = None
        else:
            self.flowInterruptionsHistogram = Histogram(interrupt_hist_elem)
            
        self.throughput = rxBytes * 8 / self.flowcompletiontime /1024 * 1e9
        
        
        self.sentPackets = txPackets
        self.receivePackets = rxPackets
        
        
       


class ProbeFlowStats(object):
    __slots__ = ['probeId', 'packets', 'bytes', 'delayFromFirstProbe']

class Simulation(object):
    def __init__(self, simulation_el):
        self.flows = []
        FlowClassifier_el, = simulation_el.findall("Ipv4FlowClassifier")
        flow_map = {}

        flow_map_new = {}
        for flow_el in simulation_el.findall("FlowStats/Flow"):

            flow = Flow(flow_el)
            flow_map[flow.flowId] = flow
            flow_map_new[flow.flowId] = flow
            # self.flows.append(flow)

        pair = defaultdict(list)
        for flow_cls in FlowClassifier_el.findall("Flow"):
            flowId = int(flow_cls.get('flowId'))

            tup = FiveTuple(flow_cls)
            flow_map[flowId].fiveTuple = tup

            key1 = (tup.sourceAddress, tup.destinationAddress, tup.sourcePort, tup.destinationPort)
            key2 = (tup.destinationAddress, tup.sourceAddress, tup.destinationPort, tup.sourcePort)
            if key2 in pair:
                pair[key2].append(flowId)
            else:
                pair[key1].append(flowId)




        print(len(flow_map))


        flow_bytes = {}

        for probe_elem in simulation_el.findall("FlowProbes/FlowProbe"):


            probeId = int(probe_elem.get('index'))


            for stats in probe_elem.findall("FlowStats"):
                flowId = int(stats.get('flowId'))
                s = ProbeFlowStats()
                s.packets = int(stats.get('packets'))
                s.bytes = int(stats.get('bytes'))

                flow_bytes[flowId] = s.bytes
                # if s.bytes <= 10000:
                #     # print(f'hello{flowId}')
                #     flow_map.pop(flowId, None)
                #     continue


                s.probeId = probeId
                if s.packets > 0:
                    s.delayFromFirstProbe =  parse_time_ns(stats.get('delayFromFirstProbeSum')) / float(s.packets)
                else:
                    s.delayFromFirstProbe = 0
                flow_map[flowId].probe_stats_unsorted.append(s)


        for id1, id2 in pair.values():
            if flow_bytes[id1] > flow_bytes[id2]:
                flow_map_new.pop(id2, None)
            else:
                flow_map_new.pop(id1, None)


        print(len(flow_map))

        self.flows = flow_map_new.values()

def main(argv):
    file_obj = open(argv[1])
    print("Reading XML file ", end=' ')
 
    sys.stdout.flush()        
    level = 0
    sim_list = []
    for event, elem in ElementTree.iterparse(file_obj, events=("start", "end")):
        if event == "start":
            level += 1
        if event == "end":
            level -= 1
            if level == 0 and elem.tag == 'FlowMonitor':
                sim = Simulation(elem)
                sim_list.append(sim)
                elem.clear() # won't need this any more
                sys.stdout.write(".")
                sys.stdout.flush()
    print(" done.")


    for sim in sim_list:
        throughput, count, total_rp, total_sp = 0.0, 0, 0, 0
        
        flow_ids, flow_cts, flow_txBytes = [], [], []
        for flow in sim.flows:



            flow_ids.append(flow.flowId)
            flow_cts.append(flow.flowcompletiontime * 1e-6)
            flow_txBytes.append(flow.txBytes / 1000)




            t = flow.fiveTuple
            proto = {6: 'TCP', 17: 'UDP'} [t.protocol]
            print("FlowID: %i (%s %s/%s --> %s/%i)" % \
                (flow.flowId, proto, t.sourceAddress, t.sourcePort, t.destinationAddress, t.destinationPort))
            print("\tTX bitrate: %.2f kbit/s" % (flow.txBitrate*1e-3,))
            print("\tRX bitrate: %.2f kbit/s" % (flow.rxBitrate*1e-3,))
#             print("\tMean Delay: %.2f ms" % (flow.delayMean*1e3,))
            
    
            print("\tSent packets %i packets" % (flow.sentPackets))
            print("\tReceive packets %i packets" % (flow.receivePackets))


            print("\tPacket Loss Ratio: %.2f %%" % (flow.packetLossRatio*100))
            print("\tflow completion time: %.2f ns" % (flow.flowcompletiontime))

#             print("\tflow completion time: %.2f ms" % (flow.flowcompletiontime *1e-6))
            print("\tThroughput is : %.2f kbit/s" % (flow.throughput))
            print("\tDelay time: %.2f ns" % (flow.delay))
            
            throughput += flow.throughput
            total_rp +=  flow.receivePackets
            total_sp += flow.sentPackets
            count += 1
        print(f'Average throughtput is {throughput / count} kbit/s')
        print(f'Total received packets is {total_rp}, sent is {total_sp}')
        



        print(len(flow_ids))

        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(24, 16))

        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312)
        ax3 = fig.add_subplot(313)

        bar_width = 0.5
        ax1.bar(flow_ids, flow_cts, width=bar_width)
        ax1.plot(flow_ids, flow_cts, color='purple')

        ax1.set(xlabel='Flow IDs', ylabel = 'Flow Completion Time (ms)')

        ax2.bar(flow_ids, flow_txBytes, width=bar_width)
        ax2.plot(flow_ids, flow_txBytes, color='purple')
        ax2.set(xlabel='Flow IDs', ylabel = 'txBytes (KBytes)')	
        

        ax3.scatter(flow_txBytes, flow_cts, color='purple',  marker='o')
        ax3.set(xlabel='Flow Size (KBytes)', ylabel = 'Flow Completion Time (ms)')  
        



        plt.savefig('1.png')
        plt.show()


        





if __name__ == '__main__':
    main(sys.argv)
