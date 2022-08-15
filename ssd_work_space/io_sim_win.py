import pandas as pd
import os
import shutil
import numpy as np
from numpy import random
import subprocess
import multiprocessing
from datetime import datetime
from subprocess import check_output
from xml.etree import ElementTree as et

class ssd_simulator:
    def __init__(self, ssd_in_trace, net_out_trace, output_folder, output_name):
        """
        Description:
            A wrapper on MQSim to provide APIs for network simulator to use.
                1. initializes SNIS
                2. runs ssd simulator in each iteration
        Parameters:
            ssd_in_trace: the input trace for ssd simulator (MQSim)
            net_out_trace: the output trace of network simulator (NS3)
            output_folder: workspace 
            output_name: the name of output of ssd simulator
        """
        self.distances = {"DelayTime":[], "FinishTime":[]}
        self.ssd_in_trace = ssd_in_trace
        self.net_out_trace = net_out_trace
        self.output_folder = output_folder
        self.output_name = output_name
        self.output_path = os.path.join(output_folder, output_name)

    def set_output_folder(self, output_folder):
        self.output_folder = output_folder
        self.output_path = os.path.join(output_folder, self.output_name)
    
    def set_net_out_trace(self, net_out_trace):
        self.net_out_trace = net_out_trace

    def read_trace_df(self, path):
        """
        read input workload trace for MQSim
        """
        df = pd.read_csv(path, names=["ArrivalTime", "VolumeID", "Offset", "Size", "IOType"], sep=" ")
        return df

    def get_response_df(self, response_file = "response"):
        """
        MQSim will generate a text file to record response time of each request.
        Read the response file and return as a dataframe with ArrivalTime and DelayTime columns.
        """
        df_res = pd.read_csv(response_file, delimiter=" ", names=["ArrivalTime", "DelayTime"])
        df_res = df_res.sort_values(by=["ArrivalTime"])
        df_res = df_res.reset_index(drop=True)
        os.remove("{}".format(response_file))
        return df_res

    def reallocate_wait_file(self, from_path="waiting", to_path=""):
        """
        MQSim will generate a text file to record waiting time of each transaction.
        Move the file if necessary.
        """
        shutil.copyfile(from_path, to_path)
        os.remove(from_path)

    def run_MQSim(self, MQSim_input_trace, MQSim_output_folder, targetid):
        """
        a wrapper of MQSim for windows OS.
        Parameters:
            MQSim_input_trace: MQSim's input trace path, by default is self.ssd_in_trace
            MQSim_output_folder: MQSim's output folder, by default is self.output_folder
            targetid: used for track statistics generated for each target 
        """
        # modify input of the workload trace
        workload = "workload-trace.xml"
        tree = et.parse(workload)
        tree.find('IO_Scenario/IO_Flow_Parameter_Set_Trace_Based/File_Path').text = MQSim_input_trace
        tree.write(workload)
        # execute MQSim
        # deprecated: os.system("./MQSim -i ssdconfig.test.xml -w {}".format(workload))
        cmd = [".\\MQSim.exe", "-i", "ssdconfig.test.xml",  "-w", workload]
        temp = subprocess.Popen(cmd, stdout = subprocess.PIPE)
        output = str(temp.communicate())
        # copy statistics to the output_folder
        trace_statistic = os.path.join("{}".format(MQSim_output_folder),"statistic_target{}_{}".format(targetid, os.path.basename(MQSim_input_trace)))
        shutil.copyfile("workload-trace_scenario_1.xml", "{}".format(trace_statistic))
        with open("{}".format(trace_statistic), "w") as file:
            # TODO: extract info from the statistic file
            pass 

    def initialize_SSD_trace(self, snis_in_trace):
        """
        initialize SNIS by reading a .trace input and start SSD simulation.
        Input:
            snis_in_trace: a .trace file.
        Output:
            new_df: a .csv file containing all information the network simulator needs.
        """
        if os.path.exists("response"):
            raise Exception('response file should not exist!')
        trace_df = pd.read_csv(snis_in_trace, header=0)
        # start simulation for each target
        response_df_list = []
        for targetid in trace_df.TargetID.drop_duplicates().values:
            print("start ssd simulation for target {}".format(targetid))
            target_df = trace_df[trace_df["TargetID"]==targetid]
            ssd_input_df = target_df[["ArrivalTime", "VolumeID", "Offset", "Size", "IOType"]]
            # The IOType in sample generator is oppsite to that in MQSim
            ssd_input_df.loc[:, "IOType"] = ssd_input_df.IOType.apply(lambda x: x^1)
            # Save the input trace to self.ssd_in_trace
            ssd_input_df.to_csv(path_or_buf=self.ssd_in_trace, sep=" ", header=False, index=False)
            # run MQSim
            self.run_MQSim(self.ssd_in_trace, self.output_folder, targetid)
            # get the response_df with two columns: [ArrivalTime, DelayTime], sorted by ArrivalTime
            response_df_list.append(self.get_response_df(response_file = "response"))
            # mv waiting file to output_folder
            self.reallocate_wait_file(to_path= os.path.join(self.output_folder, "waiting_{}".format(targetid)))
        
        response_df = pd.concat(response_df_list).sort_values(by=["ArrivalTime"])
        assert(int((response_df.ArrivalTime.values - trace_df.ArrivalTime.values).mean())==0)
        # append response time to the original .trace file
        new_df = trace_df.merge(response_df, left_on='ArrivalTime', right_on='ArrivalTime')
        new_df["FinishTime"] = new_df["ArrivalTime"] + new_df["DelayTime"]
        new_df["Size"] = new_df.Size.apply(lambda x: x*512)
        names = ["RequestID", "ArrivalTime", "DelayTime", "FinishTime", "InitiatorID", "TargetID", "IOType", "Size", "VolumeID", "Offset"]
        new_df = new_df[names].sort_values(by=["ArrivalTime"])
        new_df = new_df.reset_index(drop=True)
        new_df["RequestID"] = new_df.index
        # save the output of ssd simulator, net-ssd.csv file
        new_df[names].to_csv(path_or_buf=self.output_path, sep=",", header=True, index=False)
        return new_df[names]

    def ssd_simulation_iter(self, arrival_time):
        if os.path.exists("response"):
            raise Exception('response file should not exist!')
        # ssd_in_trace is the temp input file of MQSim
        intermedia_path = self.ssd_in_trace
        # read the output of network simulator
        net_df = pd.read_csv(self.net_out_trace, header=0)
        trace_df = net_df.loc[:, ["RequestID","ArrivalTime", "VolumeID", "Offset", "Size", "IOType", "TargetID"]]
        trace_df = trace_df.sort_values(by=["ArrivalTime"])
        trace_df.loc[:, "Size"] = trace_df.Size.apply(lambda x: int(x/512))
        # change IOType to the opposite for MQSim
        trace_df.loc[:, "IOType"] = trace_df.IOType.apply(lambda x: x^1)
        # ArrivalTime is integer with ns unit
        trace_df.loc[:, "ArrivalTime"] = trace_df["ArrivalTime"].astype(np.int64)
        response_df_list = []
        for targetid in trace_df.TargetID.drop_duplicates().values:
            print("start ssd simulation for target {}".format(targetid))
            target_df = trace_df[trace_df["TargetID"]==targetid]
            target_df.drop(["RequestID", "TargetID"], axis=1).to_csv(path_or_buf=intermedia_path, sep=" ", header=False, index=False)
            # run MQSim
            self.run_MQSim(intermedia_path, self.output_folder, targetid)
            # get the response_df with two columns: [ArrivalTime, DelayTime], sorted by ArrivalTime
            response_df_list.append(self.get_response_df(response_file = "response"))
        
        response_df = pd.concat(response_df_list).sort_values(by=["ArrivalTime"])
        # return response_df, trace_df
        assert(int((response_df.ArrivalTime.values - trace_df.ArrivalTime.values).mean())==0)
        ssd_df = net_df.loc[:, ["RequestID", "ArrivalTime", "DelayTime", "FinishTime", "InitiatorID", "TargetID", "IOType", "Size", "VolumeID", "Offset"]]
        ssd_df = ssd_df.sort_values(by=["ArrivalTime"])
        ssd_df.loc[:, "DelayTime"] = response_df["DelayTime"].values
        ssd_df.loc[:, "FinishTime"] = ssd_df["DelayTime"] + ssd_df["ArrivalTime"]
        ssd_df.loc[:, "ArrivalTime"] = arrival_time
        ssd_df.to_csv(path_or_buf=self.output_path, sep=",", header=True, index=False)
        # print("Throuput(GB/s): {}, Distance(ns): {}, Ave_latency(ns): {}".format((ssd_df.Size.sum()/(ssd_df["FinishTime"].iloc[-1] - ssd_df["ArrivalTime"].iloc[0])*1e9/1024/1024/1024), distance["FinishTime"]/len(ssd_df), ssd_df.DelayTime.mean()))
        names = ["RequestID", "ArrivalTime", "DelayTime", "FinishTime", "InitiatorID", "TargetID", "IOType", "Size", "VolumeID", "Offset"]
        return ssd_df[names]
