from absl import app
from absl import flags
import pandas as pd
from math import ceil
import os
from io_sim import ssd_simulator
from shutil import copyfile, copy
from utils import *
import subprocess
from pathlib import Path

FLAGS = flags.FLAGS
flags.DEFINE_string("workload", "Fujitsu_V0_based_50_to_1_net-ssd.csv",
                    "The workload input file")
flags.DEFINE_string("input", "net-ssd.csv", "The input file name of network simulator")
flags.DEFINE_string("output", "result.csv", "The output file name of network simulator")
flags.DEFINE_string("map", "flow_map.csv",
                    "Map from flow ID to destination port")
flags.DEFINE_string("fct", "fct.csv", "The flow completion time file")
flags.DEFINE_integer("num", 30, "The number of iterations")
flags.DEFINE_integer("start_itr", 0, "The start iteration, used when not run from scratch. Set to 1 to start from scratch")
flags.DEFINE_boolean("qcn", False, "Enable QCN")
flags.DEFINE_float("conv", 0.05, "converge criteria, if set to 0, SNIS will finish all iterations specified by 'num'")
flags.DEFINE_string("map_mod", "sequential", "The defualt initiator_target mapping is sequential")
flags.DEFINE_integer("rack_num", 2, "The default rack number is 2") 
flags.DEFINE_integer("ssd_per_target", 1, "The number of ssds each target has")


def getFlowMap(log_file, output):
    """Copy the flow-port mapping to a csv file"""
    with open(output, 'w') as of:
        with open(log_file, 'r') as f:
            line = f.readline().strip()
            while line and not line.startswith("Flow_ID,Src,Dst,Port"):
                line = f.readline().strip()
            of.write("Flow_ID,Src,Dst,Port\n")
            while line:
                line = f.readline().strip()
                of.write(line + "\n")
                


def makeupWindowsPath(*p):
    #return os.path.join('c:', os.sep, *p)
    return os.path.join(*p)

def runNS3NetworkSimulation(work_dir):
    """
        Perform Network simulation using NS3.
    
    Input:
        work_dir: the dir of each iteration
    
    Output (Unsure):
        queue.txt
    """
    work_dir = os.path.abspath(work_dir)
    #edit 54
    #net_files = ["queue.txt", "flow_monitor.xml", "mix.tr"]
    #net_files = ["queue.txt", "mix/mix.tr", "mix/fct.txt"] #modified by bo 5/3, mix.tr is under "mix" directory
    net_files = ["queue.txt", "mix/fct.txt"] #modified by bo 5/3, mix.tr is under "mix" directory
    #network_dir = "network_simulation"
    network_dir = "simulation"
    path = os.getcwd()

    
    # Copy flow.txt to destination directory
    copy(makeupWindowsPath(work_dir, "flow.txt"), network_dir)

    #print(makeupWindowsPath(*network_dir))

    #os.chdir(network_dir) #edit 

    # TODO: figure out why the command runs extremely slow when use absolute path
    #cmd = "%s %s > %s" % ("MQSim.exe", "config.txt", "queue.txt")
    #print(cmd)
    #os.system("./MQSim config.txt > queue.txt") replace with format regarding to 65
    #Network simulation, not MQSim. 
    
    #print(work_dir)

    #path = Path(work_dir)
    #changedir = "%s/simulation" % (path.parent.parent.parent.absolute())

    os.chdir(network_dir)
    #print("network_dir:",network_dir)
    cmd="./waf --run 'scratch/third mix/config.txt' > queue.txt"
    os.system(cmd)

    # Copy back intermediate files
    for net_file in net_files:
        #print(net_file)
        copy(net_file, work_dir)

    # Return to the original working directory
    os.chdir(path)


def main(argv):
    if not FLAGS.input:
        print("No input file\n")
        return

    if FLAGS.conv !=0 :
        is_last_converged = False

    FLAGS.workload = os.path.basename(FLAGS.workload)
    # Create test directory if not existed
    parent_dir = "test/QCN/%s" % (FLAGS.workload.split(
        ".")[0]) if FLAGS.qcn else "test/%s" % (FLAGS.workload.split(".")[0])
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    parent_dir = os.path.abspath(parent_dir)

    # Prepare the log folder
    log_dir = parent_dir + "/log_%s" % FLAGS.workload.split(".")[0]
    # Create the directories for copying files for statistic analysis, including net and ssd info
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # initialize ssd simulator object
    ssd_output = "net-ssd.csv"
    ssd_sim = ssd_simulator("./tmp",
                            makeupWindowsPath(parent_dir, FLAGS.output), ".",
                            ssd_output,  workload_path="workload-trace.xml", ssdconfig_path="ssdconfig.test.xml", ssd_per_target=FLAGS.ssd_per_target)

    for i in range(FLAGS.start_itr, FLAGS.num + 1):
        print("Running iteration %d ..." % i)
        work_dir = parent_dir + "/%d" % i   
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        ############################ SSD Simulation ###############################
        
        # output folder will be work_dir: test/workload_name/iter/
        ssd_sim.set_output_folder(work_dir)
        #ssd_sim.__init__(work_dir) 
        # SNIS starts from SSD simulation, reading .trace or .csv input file.
        # if input is in .trace format, SNIS calls initializa_SSD_trace to start SSD simulation.
        # Otherwise, it means SSD simulation is completed in sample generator, SNIS reads .csv
        # input and starts Network simulation.
        if i == 0:
            if "trace" in FLAGS.workload:
                new_df = ssd_sim.initialize_SSD_trace(FLAGS.workload)
                # copy("waiting", os.path.join(work_dir, "waiting"))
                # os.remove("waiting")
                # os.system("python flow_parser.py -input %s -output %s" %
                #         (ssd_sim.output_path, work_dir + "/flow.txt"))
                #copy(FLAGS.workload, work_dir + "/" + FLAGS.input)
        
            elif "csv" in FLAGS.workload:
                copy(FLAGS.workload, ssd_sim.output_path)
                # os.system("python flow_parser.py -input %s -output %s" %
                #         (FLAGS.workload, work_dir + "/flow.txt"))
            else:
                raise  Exception("workload should be .trace or .csv")

        else:
            # network output trace path will be: test/workload_name/iter-1/result.csv
            ssd_sim.set_net_out_trace(os.path.join(parent_dir, str(i-1) , FLAGS.output))
            # The original ArrivalTime
            # Assume the original workload file is under current directory
            
            #print("Directory Path: ", Path().absolute(), "\n Wokload:", FLAGS.workload)
            ori = pd.read_csv(FLAGS.workload)
            #os.chdir('../../..')
            #ori = pd.read_csv(ssd_output) #edit 5/4
            #os.chdir(work_dir)
            init_arrival = ori.ArrivalTime

            #print("init_arrival:", init_arrival)
            # start ssd simulation of next iteration
            ssd_sim.ssd_simulation_iter(init_arrival)

            # Prepare for the next iter, copy necessary files to the next iteration directory
            # next_dir = parent_dir + "/%d" % (i + 1)
            # next_dir = os.path.abspath(next_dir)
            # if not os.path.exists(next_dir):
            #     os.makedirs(next_dir)

            # # copy the output of ssd simulation in current iter to next iter
            # ssd_file_path = makeupWindowsPath(next_dir, ssd_output)
            # # Overwrite to use the latest result
            # # if not os.path.exists(ssd_file_path):
            # copyfile(ssd_output, ssd_file_path)


        ############################ Network Simulation ###############################
        # Get latest flow.txt
        os.system("python3 flow_parser.py -input %s -output %s -map_mod %s -rack_num %s" %
                (ssd_sim.output_path, makeupWindowsPath(work_dir, "flow.txt"), FLAGS.map_mod, FLAGS.rack_num))
        # Start NS3 simulation
        runNS3NetworkSimulation(work_dir)
        work_dir = os.path.abspath(work_dir)

        print(FLAGS.map)
        getFlowMap(makeupWindowsPath(work_dir, "queue.txt"),
                   makeupWindowsPath(work_dir, FLAGS.map))
        print("done")
        '''
        map_dt = pd.read_csv(makeupWindowsPath(work_dir,
                                               FLAGS.map), sep = " ", names =  ["Flow_ID", "Src", "Dst", "Port"], on_bad_lines= 'skip')  # Flow_ID,Port
        #os.system("echo 'Port FCT' > fct.csv")

        #os.system("awk '{print $3, $7}' simulation/mix/fct.txt > fct.csv") #edit 
        os.system("awk '{print $1, $2, $3, $7}' %s > %s" % ("simulation/mix/fct.txt",makeupWindowsPath(work_dir, FLAGS.fct)))
        #output as fct.csv
        
        #os.system("python fm_xml_parser.py -input %s > %s" %
                  #(makeupWindowsPath(work_dir, "flow_monitor.xml"),
                   #makeupWindowsPath(work_dir, FLAGS.fct)))
        fct_dt = pd.read_csv(makeupWindowsPath(work_dir,
                                               FLAGS.fct),sep = ' ', names = ["Src", "Dst", "Port", "FCT"] )  # Port,FCT
                                     

        map_dt = pd.merge(map_dt, fct_dt, how='left', left_on=["Src", "Dst", "Port"], right_on=["Src", "Dst", "Port"])
        '''
        
        map_dt = pd.read_csv(makeupWindowsPath(work_dir, FLAGS.map))
        os.system("echo 'Src,Dst,Port,FCT' > %s" % (makeupWindowsPath(work_dir, FLAGS.fct)))         
        os.system("awk '{print %s}' %s >> %s" % ('$1","$2","$3","$7',"simulation/mix/fct.txt",makeupWindowsPath(work_dir, FLAGS.fct)))               
        fct_dt = pd.read_csv(makeupWindowsPath(work_dir, FLAGS.fct))
        map_dt = pd.merge(map_dt, fct_dt, how='inner', on=['Src', 'Dst', 'Port'])

        
        

        data = pd.read_csv(makeupWindowsPath(work_dir, FLAGS.input))
        cols = data.columns
        data.RequestID -= data.RequestID.min()  # In case that the RequestID doesn't not start from 0
        for col in map_dt.columns:
            data[col] = map_dt[col]

        # Update write flow's arrival time with the network delay
        data.loc[data.IOType == 1,
                 ['ArrivalTime']] = data.ArrivalTime + data.FCT

        # Save new result
        data.to_csv(makeupWindowsPath(work_dir, FLAGS.output),
                    index=False,
                    columns=cols)

        ############################ Check Convergency #################################
        # generate aggregated stats (ssd+network)        
        df_aggre = readSummary(work_dir)
        df_aggre.to_csv(os.path.join(work_dir, "{}.csv".format(i)), index=False)

        # return if converged
        if FLAGS.conv!=0:
            tpt1 = df_aggre.Size/df_aggre.TotalDelay     #throughput of current iteration
            inx_gap = 2
            pre_inx = i - inx_gap
            if pre_inx >= 0:
                pre_df = pd.read_csv(os.path.join(parent_dir, str(pre_inx), "{}.csv".format(pre_inx)), header=0)
                tpt2 = pre_df.Size/pre_df.TotalDelay      #throughput of the previous one/two iteration
                cc = calculate_convergency_criteria(tpt1, tpt2)   #calculate converge criteria
                with open(os.path.join(parent_dir,"cc.txt"), "a") as cc_txt:
                    cc_txt.write("iteration {}: cc between {} and {} is {}\n".format(i, i, pre_inx, cc))
                if cc< FLAGS.conv:
                    if is_last_converged:
                        print("Converged at iteration {}, as cc between {} and {} is less than {}".format(
                                i, i, pre_inx,FLAGS.conv))
                        return
                    is_last_converged = True
                else:
                    is_last_converged = False     #evaluate if the previous iteration is converged

        
        ############################ Generate log ###############################
        # Copy files to ssd directory for further analysis
        log_dir_iter = log_dir + "/%d" % i
        if not os.path.exists(log_dir_iter):
            os.makedirs(log_dir_iter)
        copy(makeupWindowsPath(work_dir, FLAGS.input), log_dir_iter)
        copy(makeupWindowsPath(work_dir, FLAGS.output), log_dir_iter)
        # Copy network intermediate files as well for convenience
        copy(makeupWindowsPath(work_dir, FLAGS.fct), log_dir_iter)
        copy(makeupWindowsPath(work_dir, FLAGS.map), log_dir_iter)
        copy(makeupWindowsPath(work_dir, "{}.csv".format(i)), log_dir_iter)

        # The first iteration doesn't have "waiting" file
        w_path = makeupWindowsPath(work_dir, "waiting")
        if os.path.exists(w_path):
            copy(w_path, log_dir_iter)


if __name__ == '__main__':
    app.run(main)
