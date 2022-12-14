from ssd_simulator import *
from datetime import datetime
import shutil
import subprocess

class ssd_simulator:
    def __init__(self, ssd_in_trace, net_out_trace, output_folder, output_name):
        #ssd_simulator = ssd_simulator("/home/labuser/ssd-net-sim/Congest/ssd_work_space/ssd_tmp/tmp.trace","/home/labuser/ssd-net-sim/Congest/ssd_work_space/ssd_tmp","net-ssd.csv")
        self.distances = {"DelayTime":[], "FinishTime":[]}
        self.ssd_in_trace = ssd_in_trace
        self.net_out_trace = net_out_trace
        self.output_folder = output_folder
        #added 13
        self.output_name = output_name
        self.output_path = "{}/{}".format(output_folder, output_name)
    #15-20 added
    def set_output_folder(self, output_folder):
        self.output_folder = output_folder
        self.output_path = os.path.join(output_folder, self.output_name)
    
    def set_net_out_trace(self, net_out_trace):
        self.net_out_trace = net_out_trace

    def read_trace_df(self, path):
        df = pd.read_csv(path, names=["ArrivalTime", "VolumeID", "Offset", "Size", "IOType"], sep=" ")
        return df

    def calculate_distance(self, old_array, new_array):
        dist = np.linalg.norm(new_array-old_array)
        dist = np.linalg.norm((new_array - old_array), ord=1)
        return dist

    def generate_output(self, trace_df, response_df, output_file):
        #ToDo: check correctness
        output_df = pd.concat([trace_df, response_df], axis=1, sort=False)
        output_df["FinishTime"] = output_df["ArrivalTime"] + output_df["DelayTime"]
        output_df.loc[:, "Size"] = output_df["Size"].apply(lambda x: x*512)
        return output_df

    def run_MQSim(self, MQSim_input_trace, MQSim_output_folder, targetid):
        # modify input of the workload trace
        workload = "workload-trace.xml"
        tree = et.parse(workload)
        tree.find('IO_Scenario/IO_Flow_Parameter_Set_Trace_Based/File_Path').text = MQSim_input_trace
        tree.write(workload)
        # execute MQSim
        cmd = ["./MQSim", "-i", "ssdconfig.test.xml",  "-w", workload]
        # os.system("./MQSim -i ssdconfig.test.xml -w {}".format(workload))
        temp = subprocess.Popen(cmd, stdout = subprocess.PIPE)
        output = str(temp.communicate())
        # copy statistics to the output_folder
        trace_statistic = os.path.join("{}".format(MQSim_output_folder),"statistic_target{}_{}".format(targetid, os.path.basename(MQSim_input_trace)))
        shutil.copyfile("workload-trace_scenario_1.xml", "{}".format(trace_statistic))
        with open("{}".format(trace_statistic), "w") as file:
            # TODO: extract info from the statistic file
            pass

    # def run_SSD_sim(self, input_path, output_folder, output_file, trace_df=pd.DataFrame([]), old_df=pd.DataFrame([])):
    #     run_MQSim(input_path, output_folder)
    #     response_df = get_response_df(0)
    #     if len(trace_df)==0:
    #         trace_df = self.read_trace_df(input_path)
    #     output_df = self.generate_output(trace_df, response_df, output_file)
    #     distance = None
    #     if len(old_df)>0:
    #         distance = {}
    #         for column in ["DelayTime", "FinishTime"]:
    #             x1 = output_df.sort_values(by=["RequestID"])[output_df.IOType==1][column]
    #             x2 = old_df.sort_values(by=["RequestID"])[output_df.IOType==1][column]
    #             distance[column] = self.calculate_distance(x1, x2)
    #     return output_df, distance

    def get_response_df(self, response_file = "response"):
        df_res = pd.read_csv(response_file, delimiter=" ", names=["ArrivalTime", "DelayTime"])
        df_res = df_res.sort_values(by=["ArrivalTime"])
        df_res = df_res.reset_index(drop=True)
        os.remove("{}".format(response_file))
        return df_res

    def initialize_SSD_trace(self, snis_in_trace):
        if os.path.exists("response"):
            raise Exception('response file should not exist!')
        trace_df = pd.read_csv(snis_in_trace, header=0)
        response_df_list = []
        for targetid in trace_df.TargetID.drop_duplicates().values:
            print("start ssd simulation for target {}".format(targetid))
            target_df = trace_df.loc[trace_df["TargetID"]==targetid, :]
            ssd_input_df = target_df[["ArrivalTime", "VolumeID", "Offset", "Size", "IOType"]].copy()
            ssd_input_df.loc[:, "IOType"] = ssd_input_df.IOType.apply(lambda x: x^1)
            ssd_input_df.to_csv(path_or_buf=self.ssd_in_trace, sep=" ", header=False, index=False)
            # run MQSim
            self.run_MQSim(self.ssd_in_trace, self.output_folder, targetid)
            # get the response_df with two columns: [ArrivalTime, DelayTime], sorted by ArrivalTime
            response_df_list.append(self.get_response_df(response_file = "response"))
  
        # copy("waiting", os.path.join(work_dir, "waiting"))
        # os.remove("waiting")
        response_df = pd.concat(response_df_list).sort_values(by=["ArrivalTime"])
        assert(int((response_df.ArrivalTime.values - trace_df.ArrivalTime.values).mean())==0)
        new_df = trace_df.merge(response_df, left_on='ArrivalTime', right_on='ArrivalTime')
        new_df["FinishTime"] = new_df["ArrivalTime"] + new_df["DelayTime"]
        new_df["Size"] = new_df.Size.apply(lambda x: x*512)
        names = ["RequestID", "ArrivalTime", "DelayTime", "FinishTime", "InitiatorID", "TargetID", "IOType", "Size", "VolumeID", "Offset"]
        new_df = new_df[names].sort_values(by=["ArrivalTime"])
        new_df = new_df.reset_index(drop=True)
        new_df["RequestID"] = new_df.index
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

if __name__=="__main__":
    workload = "Tencent1125-8K_18us_40_to_4_net-ssd.csv"
    ori = pd.read_csv(workload)
    init_arrival = ori.ArrivalTime
    ssd_output = "net-ssd.csv"
    ssd_sim = ssd_simulator("./tmp",
                            "test/test/{}".format(workload), ".",
                            ssd_output)
    ssd_sim.ssd_simulation_iter(init_arrival)

    # def ssd_simulation_iter(self, arrival_time):
    #     intermedia_file = self.net_out_trace
    #     intermedia_path = self.ssd_in_trace
    #     now = datetime.now()
    #     time = now.strftime("%H:%M:%S")
    #     os.system("cp {} {}".format(intermedia_file, intermedia_file+"_"+time))
    #     net_df = pd.read_csv(intermedia_file, header=0)
    #     trace_df = net_df[["RequestID","ArrivalTime", "InitiatorID", "Offset", "Size", "IOType"]]
    #     trace_df = trace_df.sort_values(by=["ArrivalTime"])
    #     trace_df.loc[:, "Size"] = trace_df.Size.apply(lambda x: int(x/512))
    #     trace_df.drop(["RequestID"], axis=1).to_csv(path_or_buf=intermedia_path, sep=" ", header=False, index=False)
    #     new_df, distance = self.run_SSD_sim(intermedia_path, self.output_folder, self.output_path, trace_df = trace_df, old_df = net_df)
    #     new_df = net_df[["RequestID", "InitiatorID", "TargetID"]].merge(new_df, left_on="RequestID", right_on="RequestID")
    #     self.distances["DelayTime"].append(distance["DelayTime"])
    #     self.distances["FinishTime"].append(distance["FinishTime"])
    #     new_df.loc[:, "ArrivalTime"] = arrival_time
    #     new_df.to_csv(path_or_buf=self.output_path, sep=",", header=True, index=False)
    #     names = ["RequestID", "ArrivalTime", "DelayTime", "FinishTime", "InitiatorID", "TargetID", "IOType", "Size", "InitiatorID", "Offset"]
    #     return new_df[names]