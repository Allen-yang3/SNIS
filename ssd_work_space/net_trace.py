from matplotlib import colors
from numpy.core.fromnumeric import size
import pandas as pd
import os
import shutil
import numpy as np
from numpy import random
import math
import multiprocessing
import matplotlib.pyplot as plt
from datetime import datetime
from subprocess import check_output
from xml.etree import ElementTree as et
from sklearn.metrics import pairwise

def get_df(path, columns=[]):
    if os.path.exists(path):
        if len(columns)==0:
            df = pd.read_csv(path, header=0)
        else:
            df = pd.read_csv(path, names=columns)
        return df
    else:
        print("Path {} not found !".format(path))

def calculate_distance(new_array, old_array):
    dist = np.linalg.norm((new_array - old_array)/old_array, ord=1)
    return dist/len(new_array)

def calculate_throughput(ssd_df):
    # unit: GB/s
    return (ssd_df.Size/ssd_df.DelayTime).mean()

def calculate_overall_throughput(ssd_df):
    # unit: GB/s
    return ssd_df.Size.sum()/(ssd_df["FinishTime"].iloc[-1] - ssd_df["ArrivalTime"].iloc[0])

def calculate_tpt_distance(tpt1, tpt2):
    def relative_distance(val1, val2):
        #return abs(val1 - val2)/max(val1, val2)*100
        return (val1 - val2)/max(val1, val2)*100
    return relative_distance(tpt1.mean(), tpt2.mean()), relative_distance(tpt1.median(), tpt2.median()), relative_distance(np.percentile(tpt1, 90), np.percentile(tpt2, 90))

# euclidian, consin_similarity, shoribishofe (5us)
def calculate_tpt_hist_distance(tpt1, tpt2):
    range = (min(tpt1.min(), tpt2.min()), max(tpt1.max(), tpt2.max()))
    # each bin contains 10MB/s
    unit = 0.01
    bins = int((range[1] - range[0])/unit)
    count1, _ = np.histogram(tpt1, bins=bins, range=range)
    count2, _ = np.histogram(tpt2, bins=bins, range=range)
    similarity = pairwise.cosine_similarity(count1.reshape(1,-1), count2.reshape(1,-1))
    max_idx = np.argmax(abs(count2-count1))
    return (1-similarity[0][0]), max(abs(count2-count1)), abs(count2-count1)[max_idx]/max(count2[max_idx], count1[max_idx])*100

def plot_cdf_across_iter(dfs, column, unit, fig_path):
    # integer/ scale
    fig, axs = plt.subplots()
    axs.set_title(column + " CDF across iterations")
    axs.set_xlabel(column+"({})".format(unit))
    axs.grid(True)
    for i in range(1, len(dfs)):
        if "tpt" in column:
            x = dfs[i][0].loc[dfs[i][0][column]<np.percentile(dfs[i][0][column],95), column]
        else:
            x = dfs[i][0][column]
        # x = dfs[i][0][column]
        n, bins, patches = axs.hist(x, 100, density=True, histtype='step', cumulative=True, label='{}'.format(i))
    axs.legend(loc="right")
    plt.savefig(fig_path)

def plot_metric_across_iter(metric, column, fig_path):
    fig, axs = plt.subplots()
    axs.set_title(column + " across iterations")
    axs.set_xlabel("iteration")
    axs.set_ylabel(column)
    #axs.set_ylim([1, 4.0])
    if "%" in column and column != "Relative_max_difference(%)":
        axs.set_ylim(0, 100)
    # if column == "Relative_max_difference(%)":
    #     axs.set_ylim(0.99, 1.0)
    axs.grid(True)
    axs.plot(range(0, len(metric), 1), metric[column])
    axs.set_xticks(range(0, len(metric), 1))
    plt.savefig(fig_path)

def plot_metric_across_iter_for_paper(metric, fig_path):
    bar_metric = ["Relative_Distance_Throughput_Median(%)", "Relative_Distance_Throughput_90th(%)", "Relative_max_difference(%)"]
    bar_metric = ["Relative_Distance_Throughput_Median(%)", "Relative_Distance_Throughput_90th(%)", "Relative_Distance_Throughput_Mean(%)"]
    scatter_metric = ["new_metric"]
    # metric["new_metric"] = metric[bar_metric].mean(axis=1)
    fig, axs = plt.subplots()
    markers=['gx-', 'b+-', 'rv-']
    for i, column in enumerate(bar_metric):
        axs.plot(range(0, len(metric), 1), metric[column], markers[i], label=column)
    ax1 = axs.twinx()
    for column in scatter_metric:
        ax1.scatter(range(0, len(metric), 1), metric[column])
    # axs.set_title(column + " across iterations")
    axs.set_xlabel("iteration")
    axs.set_ylabel("Relative distance (%)")
    ax1.set_ylabel("Convergency Criteria (%)")
    # axs.set_ylabel(column)
    # #axs.set_ylim([1, 4.0])
    # if "%" in column and column != "Relative_max_difference(%)":
    #     axs.set_ylim(0, 100)
    # if column == "Relative_max_difference(%)":
    #     axs.set_ylim(0.99, 1.0)
    axs.grid(True)
    axs.legend(loc="upper right")
    # axs.plot(range(0, len(metric), 1), metric[column])
    axs.set_xticks(range(0, len(metric), 1))
    plt.savefig(fig_path)


def plot_run_time(df, attri, fig_path):
    attri_df = df[["ArrivalTime","IOType", attri]]
    fig, axs = plt.subplots()
    write = attri_df[attri_df["IOType"]==1]
    read = attri_df[attri_df["IOType"]==0]
    axs.plot(write["ArrivalTime"], write[attri], label="WR")
    axs.plot(read["ArrivalTime"], read[attri], label="RD")
    axs.set_title(attri+" for R/W")
    axs.set_xlabel("Time(us)")
    axs.set_ylabel(attri)
    axs.legend()
    axs.grid(True)
    plt.savefig(fig_path)


def trace_stats_plot(ssd_folder = "/home/labuser/ssd-net-sim/traces/2021-03-31/test1", \
                         net_folder = "/home/labuser/ssd-net-sim/traces/2021-03-31/test1", \
                         trace_name = 'ssd_Fujitsu_V0_based_50_to_1_net-ssd', \
                         iterations = []):
    # get path to net-ssd.csv and result.csv
    dirs = os.listdir(ssd_folder)
    ssd_path = os.path.join(ssd_folder, trace_name)
    net_path = os.path.join(net_folder, trace_name)
    # each element of dfs is a pair of (ssd_df, net_df) for i-th iteration 
    dfs = []
    for iteration in iterations:
        iteration = str(iteration)
        if not  os.path.isdir(os.path.join(ssd_path, iteration)):
            continue
        ssd_iter_path = os.path.join(ssd_path, iteration, "net-ssd.csv")
        net_iter_path = os.path.join(net_path, iteration, "{}.csv".format(iteration))
        ssd_df = get_df(ssd_iter_path)
        ssd_df["Ave_tpt"] = ssd_df.Size/ssd_df.DelayTime
        net_df = get_df(net_iter_path)
        net_df["Ave_tpt"] = net_df.Size/net_df.TotalDelay
        dfs.append([ssd_df, net_df])

    # initialize metric columns
    metric = pd.DataFrame(columns=["Relative_Distance(%)", "Average_Delay(ns)" ,"Overall_Throughput(GB/s)", \
                                    "Average_Throughput(GB/s)", "Relative_Distance_Throughput_Mean(%)", \
                                    "Relative_Distance_Throughput_Median(%)", "Relative_Distance_Throughput_90th(%)", \
                                    "Cosine_Similarity difference", "Max_difference", "Relative_max_difference(%)"])
    # calculate values of each column for each iteration
    for i in range(1, len(dfs)):
        dist = calculate_distance(dfs[i][0]["DelayTime"].values,  dfs[i-1][0]["DelayTime"].values)
        over_tpt = calculate_overall_throughput(dfs[i][0])
        ave_tpt = calculate_throughput(dfs[i][0])
        delay = dfs[i][0]["DelayTime"].mean()
        dist_tpt_mean, dist_tpt_median, dist_tpt_95th = calculate_tpt_distance(dfs[i][0]["Ave_tpt"], dfs[i-1][0]["Ave_tpt"])
        dist_tpt_hist_cosin_simi, max_diff, rela_max_diff = calculate_tpt_hist_distance(dfs[i][0]["Ave_tpt"], dfs[i-1][0]["Ave_tpt"])
        new_metric = (dist_tpt_median + dist_tpt_mean + rela_max_diff)/3
        metric.loc[i,:] = [dist, delay, over_tpt, ave_tpt, dist_tpt_mean, dist_tpt_median, dist_tpt_95th, dist_tpt_hist_cosin_simi, max_diff, rela_max_diff]
    metric["new_metric"] = metric[["Relative_Distance_Throughput_Median(%)", "Relative_Distance_Throughput_90th(%)", "Relative_Distance_Throughput_Mean(%)"]].mean(axis=1)

    # initialize metric columns
    overall_metric = pd.DataFrame(columns=["Relative_Distance(%)", "Average_Delay(ns)" ,"Overall_Throughput(GB/s)", \
                                    "Average_Throughput(GB/s)", "Relative_Distance_Throughput_Mean(%)", \
                                    "Relative_Distance_Throughput_Median(%)", "Relative_Distance_Throughput_90th(%)", \
                                    "Cosine_Similarity difference", "Max_difference", "Relative_max_difference(%)", \
                                    "Mean_tpt", "Median_tpt", "90th_tpt"])
    # calculate values of each column for each iteration
    for i in range(1, len(dfs)):
        dist = calculate_distance(dfs[i][1]["TotalDelay"].values,  dfs[i-1][1]["TotalDelay"].values)
        over_tpt = calculate_overall_throughput(dfs[i][1])
        ave_tpt = calculate_throughput(dfs[i][1])
        delay = dfs[i][1]["TotalDelay"].mean()
        mean, median, perc = dfs[i][1]["Ave_tpt"].mean(), dfs[i][1]["Ave_tpt"].median(), np.percentile(dfs[i][1]["Ave_tpt"], 90)
        dist_tpt_mean, dist_tpt_median, dist_tpt_95th = calculate_tpt_distance(dfs[i][1]["Ave_tpt"], dfs[i-1][1]["Ave_tpt"])
        dist_tpt_hist_cosin_simi, max_diff, rela_max_diff = calculate_tpt_hist_distance(dfs[i][1]["Ave_tpt"], dfs[i-1][1]["Ave_tpt"])
        new_metric = (dist_tpt_median + dist_tpt_mean + rela_max_diff)/3
        overall_metric.loc[i,:] = [dist, delay, over_tpt, ave_tpt, dist_tpt_mean, dist_tpt_median, dist_tpt_95th, dist_tpt_hist_cosin_simi, max_diff, rela_max_diff, mean, median, perc]
    overall_metric["new_metric"] = overall_metric[["Relative_Distance_Throughput_Median(%)", "Relative_Distance_Throughput_90th(%)", "Relative_Distance_Throughput_Mean(%)"]].mean(axis=1)

    # plot CDF of delaytime and throughput
    plot_cdf_across_iter(dfs, "DelayTime", "ns", os.path.join(ssd_path, "delay_cdf.pdf"))
    plot_cdf_across_iter(dfs, "Ave_tpt", "GB/s", os.path.join(ssd_path, "ave_tpt_cdf.pdf"))
    # plot metric across iteration
    for column in metric.keys():
        plot_metric_across_iter(metric, column, os.path.join(ssd_path, column.split("(")[0]+".pdf"))
    plot_metric_across_iter_for_paper(metric, os.path.join(ssd_path, "ssd_paper_fig.pdf"))
    plot_metric_across_iter_for_paper(overall_metric, os.path.join(ssd_path, "overall_paper_fig.pdf"))

    print(trace_name)
    print(overall_metric)
    return metric, overall_metric

def preprocess_df_and_plot_active_stats(path, time_unit, attri, unit, fig_path, window=0, active=True):
    net_ssd_df = get_df(path)
    net_ssd_df = net_ssd_df[["ArrivalTime","DelayTime", "FinishTime", "IOType", "Size"]]
    init_time = net_ssd_df["ArrivalTime"].iloc[0]
    net_ssd_df["ArrivalTime"] = net_ssd_df["ArrivalTime"].apply(lambda x: x - init_time)
    net_ssd_df["FinishTime"] = net_ssd_df["FinishTime"].apply(lambda x: x - init_time)
    net_ssd_df["Throughput"] = net_ssd_df["Size"]/net_ssd_df["DelayTime"]
    net_ssd_df["Rate"] = np.array([1]*len(net_ssd_df))
    new_column = "Time({})".format(time_unit)
    if time_unit=="us":
        net_ssd_df[new_column] = (net_ssd_df["ArrivalTime"]/1e3).astype(int)
        net_ssd_df["FinishTime"] = (net_ssd_df["FinishTime"]/1e3).astype(int)
    elif time_unit=="ms":
        net_ssd_df[new_column] = (net_ssd_df["ArrivalTime"]/1e6).astype(int)
        net_ssd_df["FinishTime"] = (net_ssd_df["FinishTime"]/1e6).astype(int)
    elif time_unit=="s":
        net_ssd_df[new_column] = (net_ssd_df["ArrivalTime"]/1e9).astype(int)
        net_ssd_df["FinishTime"] = (net_ssd_df["FinishTime"]/1e9).astype(int)
    if "KB" in unit:
        net_ssd_df["Size"] = net_ssd_df["Size"].apply(lambda x: x/1024)
    elif "MB" in unit:
        net_ssd_df["Size"] = net_ssd_df["Size"].apply(lambda x: x/1024/1024)
    elif "GB" in unit:
        net_ssd_df["Size"] = net_ssd_df["Size"].apply(lambda x: x/1024/1024/1024)
    write = net_ssd_df[net_ssd_df["IOType"]==1]
    read = net_ssd_df[net_ssd_df["IOType"]==0]
    if active:
        def get_active_stat(df, time_column):
            df = df.reset_index()
            stat_df = pd.DataFrame(columns=[time_column, "Throughput", "Rate", "Size"])
            short_df = df[df[time_column]==df["FinishTime"]]
            long_df = df.loc[~df.index.isin(short_df.index), :]
            stat_df = short_df.groupby([time_column]).sum()
            stat_df = stat_df[["Throughput", "Rate", "Size"]]
            for i in long_df.index.values:
                for time_stample in range(long_df.loc[i, time_column], long_df.loc[i, "FinishTime"]+1):
                    if time_stample not in stat_df.index.values:
                        stat_df.loc[time_stample, :] = np.array(df[["Throughput", "Rate", "Size"]].iloc[i].values)
                    else:
                        for column in ["Throughput", "Rate", "Size"]:
                            # use time_stample==stat_df.index to select the correct index of stat_df as stat_df.index is unsorted.
                            stat_df.loc[time_stample==stat_df.index, column] += df.loc[i, column]
            stat_df = stat_df.sort_index()
            stat_df[time_column] = stat_df.index
            stat_df.index.names = ["index"]
            return stat_df
        processed_wr_df = get_active_stat(write, new_column)
        processed_rd_df = get_active_stat(read, new_column)
    else:
        processed_wr_df = write.groupby([new_column], as_index=False).sum()
        processed_rd_df = read.groupby([new_column], as_index=False).sum()
    if window!=0:
        processed_wr_df[new_column] = processed_wr_df[new_column].apply(lambda x: x/window).astype(int)*window
        processed_rd_df[new_column] = processed_rd_df[new_column].apply(lambda x: x/window).astype(int)*window
        processed_wr_df = processed_wr_df.groupby([new_column], as_index=False).mean()
        processed_rd_df = processed_rd_df.groupby([new_column], as_index=False).mean()
    fig, (ax1, ax2) = plt.subplots(2,1)
    ax1.bar(processed_wr_df[new_column], processed_wr_df[attri], label="WR", color="b")
    ax2.bar(processed_rd_df[new_column], processed_rd_df[attri], label="RD", color="r")
    ax2.set_xlabel(new_column)
    ax1.set_ylabel(attri+" ({}) of WR".format(unit))
    ax2.set_ylabel(attri+" ({}) of RD".format(unit))
    ax1.grid(True)
    ax2.grid(True)
    ax1.set_title("{} of {}".format("active stats" if active else "stats", attri))
    # if attri=="Throughput":
    #     ax1.set_yscale("log")
    #     ax2.set_yscale("log")
    plt.savefig(fig_path)
    plt.clf()

# def preprocess_df_and_plot_ave_run_time(path, time_unit, attri, unit, fig_path):
#     net_ssd_df = get_df(path)
#     net_ssd_df = net_ssd_df[["ArrivalTime","DelayTime", "FinishTime", "IOType", "Size"]]
#     net_ssd_df["ArrivalTime"] = net_ssd_df["ArrivalTime"].apply(lambda x: x - net_ssd_df["ArrivalTime"].iloc[0])
#     net_ssd_df["Throughput"] = net_ssd_df["Size"]/net_ssd_df["DelayTime"]
#     net_ssd_df["Rate"] = np.array([1]*len(net_ssd_df))
#     new_column = "Time({})".format(time_unit)
#     if time_unit=="us":
#         net_ssd_df[new_column] = (net_ssd_df["ArrivalTime"]/1e3).astype(int)
#     elif time_unit=="ms":
#         net_ssd_df[new_column] = (net_ssd_df["ArrivalTime"]/1e6).astype(int)
#     elif time_unit=="s":
#         net_ssd_df[new_column] = (net_ssd_df["ArrivalTime"]/1e9).astype(int)
#     write = net_ssd_df[net_ssd_df["IOType"]==1]
#     read = net_ssd_df[net_ssd_df["IOType"]==0]
#     processed_wr_df = write.groupby([new_column], as_index=False).sum()
#     processed_rd_df = read.groupby([new_column], as_index=False).sum()
#     fig, axs = plt.subplots()
#     axs.plot(processed_wr_df[new_column], processed_wr_df[attri], label="WR")
#     axs.plot(processed_rd_df[new_column], processed_rd_df[attri], label="RD")
#     axs.set_title(attri+" for R/W")
#     axs.set_xlabel(new_column)
#     axs.set_ylabel(attri+" ({})".format(unit))
#     axs.legend()
#     axs.grid(True)
#     plt.savefig(fig_path)

def plot_waiting_time(path, time_unit, fig_path, attri, unit, window=0, active=True):
    transaction_size = 16384
    waiting_df = pd.read_csv(path, delimiter=" ", names=["ArrivalTime", "IOType", "ExecutionTime", "TransferTime", "WaitingTime", "DelayTime"])
    # preprocessing waiting_df
    waiting_df["Size"] = np.array([transaction_size]*len(waiting_df))
    waiting_df["ArrivalTime"] = waiting_df["ArrivalTime"].apply(lambda x: x-waiting_df["ArrivalTime"].iloc[0])
    waiting_df["ServiceTime"] = waiting_df["ArrivalTime"] + waiting_df["WaitingTime"] + waiting_df["TransferTime"]
    waiting_df["FinishTime"] = waiting_df["ArrivalTime"] + waiting_df["DelayTime"]
    waiting_df["WaitingPercent"] = (waiting_df["WaitingTime"]/waiting_df["DelayTime"]) * 100
    if time_unit=="us":
        scale = 1e3
    elif time_unit=="ms":
        scale = 1e6
    elif time_unit=="s":
        scale = 1e9
    else:
        scale = 1

    scale = int(scale)
    if attri == "Throughput":
        # creat time windows in time_unit
        waiting_df["start"] = waiting_df["ServiceTime"].apply(lambda x: x/scale).astype(int) * scale
        waiting_df["end"] = waiting_df["FinishTime"].apply(lambda x: x/scale).astype(int) * scale
        # filter out transactions finished within a time window
        short_df = waiting_df.loc[waiting_df["start"] == waiting_df["end"], ["ServiceTime", "FinishTime", "IOType", "Size" , "start", "end"]]
        # filter out transactions finished across multiple time windows
        long_df = waiting_df.loc[~waiting_df.index.isin(short_df.index), ["ServiceTime", "FinishTime", "IOType", "Size" , "start", "end"]]
        # generate ascendingly increasing index
        short_df = short_df.reset_index(drop=True)
        long_df = long_df.reset_index(drop=True)
        for i in long_df.index.values:
            finish = long_df.loc[i, "FinishTime"]
            start = long_df.loc[i, "ServiceTime"]
            ave_size = long_df.loc[i, "Size"]/(finish-start)
            # time_stamp is the end of current time window
            for time_stample in range(int(long_df.loc[i, "start"]+scale), int(long_df.loc[i, "end"]+scale*2), scale):
                if time_stample == int(long_df.loc[i, "end"]+scale):
                    short_df.loc[len(short_df), :] = np.array([start, finish, long_df.loc[i, "IOType"], ave_size*(finish - start) , time_stample, time_stample+scale])
                else:
                    short_df.loc[len(short_df), :] = np.array([start, finish, long_df.loc[i, "IOType"], ave_size*(time_stample - start) , time_stample, time_stample+scale])
                start = time_stample
            assert(start>finish)
        # filter out write/read transactions, which is opposite to workload
        write = short_df[short_df["IOType"]==0]
        read = short_df[short_df["IOType"]==1]
        # sum up Size in a time window
        processed_wr_df = write.groupby(["end"], as_index=False).sum()
        processed_rd_df = read.groupby(["end"], as_index=False).sum()
        # compute throughput as GB/s (from Byte/time_unit)
        processed_wr_df["Throughput"] = processed_wr_df["Size"].apply(lambda x: x/scale)
        processed_rd_df["Throughput"] = processed_rd_df["Size"].apply(lambda x: x/scale)
        new_column = "Time({})".format(time_unit)
        processed_wr_df[new_column] = processed_wr_df["end"].apply(lambda x: x/scale).astype(int)
        processed_rd_df[new_column] = processed_rd_df["end"].apply(lambda x: x/scale).astype(int)
    elif attri == "WaitingTime" or attri == "QueueLength" :
        # creat time windows in time_unit
        waiting_df["start"] = waiting_df["ArrivalTime"].apply(lambda x: x/scale).astype(int) * scale
        waiting_df["end"] = waiting_df["ServiceTime"].apply(lambda x: x/scale).astype(int) * scale
        # filter out transactions finished within a time window
        short_df = waiting_df.loc[waiting_df["start"] == waiting_df["end"], ["ArrivalTime", "ServiceTime", "IOType", "WaitingTime" , "start", "end"]]
        short_df["QueueLength"] = np.array([1]*len(short_df))
        # filter out transactions finished across multiple time windows
        long_df = waiting_df.loc[~waiting_df.index.isin(short_df.index), ["ArrivalTime", "ServiceTime", "IOType", "WaitingTime" , "start", "end"]]
        # generate ascendingly increasing index
        short_df = short_df.reset_index(drop=True)
        long_df = long_df.reset_index(drop=True)
        for i in long_df.index.values:
            finish = long_df.loc[i, "ServiceTime"]
            start = long_df.loc[i, "ArrivalTime"]
            # time_stamp is the end of current time window
            for time_stample in range(int(long_df.loc[i, "start"]+scale), int(long_df.loc[i, "end"]+scale*2), scale):
                short_df.loc[len(short_df), :] = np.array([start, finish, long_df.loc[i, "IOType"], (finish - start) , time_stample, time_stample+scale, 1])
                start = time_stample
            assert(start>finish)
        # filter out write/read transactions
        write = short_df[short_df["IOType"]==0]
        read = short_df[short_df["IOType"]==1]
        if attri=="WaitingTime":
            # average waiting time in a time window
            processed_wr_df = write.groupby(["start"], as_index=False).mean()
            processed_rd_df = read.groupby(["start"], as_index=False).mean()
            if unit=="us":
                processed_wr_df.loc[:, "WaitingTime"] = processed_wr_df["WaitingTime"]/1e3
                processed_rd_df.loc[:, "WaitingTime"] = processed_rd_df["WaitingTime"]/1e3
            elif unit=="ms":
                processed_wr_df.loc[:, "WaitingTime"] = processed_wr_df["WaitingTime"]/1e6
                processed_rd_df.loc[:, "WaitingTime"] = processed_rd_df["WaitingTime"]/1e6
            elif unit=="s":
                processed_wr_df.loc[:, "WaitingTime"] = processed_wr_df["WaitingTime"]/1e9
                processed_rd_df.loc[:, "WaitingTime"] = processed_rd_df["WaitingTime"]/1e9
        else:
            # sum queue length in a time window
            processed_wr_df = write.groupby(["start"], as_index=False).sum()
            processed_rd_df = read.groupby(["start"], as_index=False).sum()
        new_column = "Time({})".format(time_unit)
        processed_wr_df[new_column] = processed_wr_df["start"].apply(lambda x: x/scale).astype(int)
        processed_rd_df[new_column] = processed_rd_df["start"].apply(lambda x: x/scale).astype(int)
        
    if window!=0:
        processed_wr_df[new_column] = processed_wr_df[new_column].apply(lambda x: x/window).astype(int)*window
        processed_rd_df[new_column] = processed_rd_df[new_column].apply(lambda x: x/window).astype(int)*window
        processed_wr_df = processed_wr_df.groupby([new_column], as_index=False).mean()
        processed_rd_df = processed_rd_df.groupby([new_column], as_index=False).mean()
    fig, (ax1, ax2) = plt.subplots(2,1)
    ax1.bar(processed_wr_df[new_column], processed_wr_df[attri], label="WR", color="b")
    ax2.bar(processed_rd_df[new_column], processed_rd_df[attri], label="RD", color="r")
    ax2.set_xlabel(new_column)
    ax1.set_ylabel(attri+" ({}) of WR".format(unit))
    ax2.set_ylabel(attri+" ({}) of RD".format(unit))
    ax1.grid(True)
    ax2.grid(True)
    ax1.set_title(attri)
    plt.savefig(fig_path)
    plt.clf()

def plot_for_trace(folder, trace_name, window=0):
    path = os.path.join(folder, trace_name)
    fig_path = os.path.join(folder, "size_active.pdf")
    preprocess_df_and_plot_active_stats(path, "ms", "Size", "KB/ms", fig_path, window)
    fig_path = os.path.join(folder, "rate_active.pdf")
    preprocess_df_and_plot_active_stats(path, "ms", "Rate", "num/ms", fig_path, window)
    waiting_path = os.path.join(folder, "waiting")
    fig_path = os.path.join(folder, "tpt.pdf")
    plot_waiting_time(waiting_path, "ms", fig_path, "Throughput", "GB/s", window, False)
    fig_path = os.path.join(folder, "waiting_ave.pdf")
    plot_waiting_time(waiting_path, "ms", fig_path, "WaitingTime" ,"us", window, False)
    fig_path = os.path.join(folder, "queue.pdf")
    plot_waiting_time(waiting_path, "ms", fig_path, "QueueLength" ,"#", window, False)
    # fig_path = os.path.join(folder, "delay_ave.pdf")
    # plot_waiting_time(waiting_path, "ms", fig_path, "DelayTime" ,"us", window, False)
    fig_path = os.path.join(folder, "size_ave.pdf")
    preprocess_df_and_plot_active_stats(path, "ms", "Size", "KB/ms", fig_path, window, False)
    fig_path = os.path.join(folder, "rate_ave.pdf")
    preprocess_df_and_plot_active_stats(path, "ms", "Rate", "num/ms", fig_path, window, False)

def plot():
    trace_name="net-ssd.csv"
    for folder in ["/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_Tencent1125_10_to_1_net-ssd/6/", \
        "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_Tencent1125_20_to_1_net-ssd/6/", \
            "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_Tencent1125_30_to_1_net-ssd/6/", \
                "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_Tencent1125_40_to_1_net-ssd/6/", \
                    "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_Tencent1125_50_to_1_net-ssd/6/", \
                        "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_Tencent1125_100_to_1_net-ssd/6/" 
                # "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_Fujitsu_V0_based_10_to_1_net-ssd/6/", \
                # "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_Fujitsu_V0_based_40_to_1_net-ssd/6/", \
                # "/home/labuser/ssd-net-sim/traces/2021-03-31/test/ssd_Fujitsu_V0_based_50_to_1_net-ssd/6/", \
                # "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_Fujitsu_V0_based_100_to_1_net-ssd/6/", \
                # "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_50us_V0_based_10_to_1_40KB_net-ssd/6/", \
                # "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_50us_V0_based_10_to_1_60KB_net-ssd/6/", \
                # "/home/labuser/ssd-net-sim/traces/2021-03-31/test1/ssd_50us_V0_based_10_to_1_80KB_net-ssd/6/", \
                ]:
        plot_for_trace(folder, trace_name, window=5)

if __name__ == "__main__":
    trace_df = {}
    #trace_folder = "/home/labuser/ssd-net-sim/traces/2021-03-31/test"
    trace_folder = "/home/labuser/ssd-net-sim/Congest/ssd_work_space/test"
    #trace_folder = "/home/labuser/ssd-net-sim/Congest/ssd_work_space/test7"
    #trace_folder = "/home/labuser/ssd-net-sim/Congest/ssd_work_space/test_ssd_config"
for folder in os.listdir(trace_folder):
    ssd_metric, overall_metric = trace_stats_plot(ssd_folder = trace_folder, \
                        net_folder = trace_folder, \
                        trace_name = folder, \
                        iterations=list(range(13)))
    trace_df[folder] = [ssd_metric, overall_metric]
    ssd_metric.to_csv(os.path.join(trace_folder, folder, "ssd_metric.csv"), index=False)
    overall_metric.to_csv(os.path.join(trace_folder, folder, "overall_metric.csv"), index=False)
        # iter_folder = os.path.join(trace_folder, folder, "6")
        # trace_name="net-ssd.csv"
        # plot_for_trace(iter_folder, trace_name, window=5)
                        #  trace_name = 'ssd_Fujitsu_V0_based_50_to_1_net-ssd')


# odd_cov = []
# even_cov = []
# absolute = []
# even = overall_metric[(overall_metric.index%2)==0]    
# odd = overall_metric[(overall_metric.index%2)==1]
# def get_points(df):
#     x = []
#     y = []
#     for i in df.index.values[1:]:
#         absolute = abs(df.loc[i, ["Mean_tpt", "Median_tpt", "90th_tpt"]] - df.loc[i-2, ["Mean_tpt", "Median_tpt", "90th_tpt"]]).values
#         maxi = [max(a,b) for a,b in zip(df.loc[i, ["Mean_tpt", "Median_tpt", "90th_tpt"]].values, df.loc[i-2, ["Mean_tpt", "Median_tpt", "90th_tpt"]].values)]
#         x.append(i)
#         y.append( (absolute/maxi).mean())
#     return x,y

# even_x, even_y = get_points(even)
# odd_x,odd_y = get_points(odd)
# fig, ax = plt.subplots(figsize=(10, 6))
# markers=['gx-', 'b+-', 'rv-']
# plt.plot(range(len(overall_metric)), overall_metric.Mean_tpt*8,  markers[0], label="Mean", ms=10) 
# plt.plot(range(len(overall_metric)), overall_metric.Median_tpt*8,  markers[1], label="Median", ms=10) 
# plt.plot(range(len(overall_metric)), overall_metric["90th_tpt"]*8,  markers[2], label="90th", ms=10) 
# # ax.legend(loc='center right',fontsize=20)
# ax.legend(loc='lower right', bbox_to_anchor=[1.0, 0.05], fontsize=20)
# ax.set_xlabel("Iteration", fontsize=22)
# ax.set_ylabel("Throughput (GBps)",fontsize=22)
# ax.tick_params(labelsize=20)
# # ax.legend(loc='upper right', bbox_to_anchor=[1.0, 1.0],fontsize=20)
# ax.set_xlabel("iteration", size=20)
# ax.set_ylabel("Metric of throughput (Gbps)", size=20)
# # axs2 = axs.twinx()
# # axs2.scatter(even_x, even_y, c = "r", label="even")
# # axs2.scatter(odd_x, odd_y, c = "g", label="odd")
# # axs2.set_ylabel("Cov_C avg. (%)" , size=15)
# # axs2.legend(loc='upper right',fontsize=15)
# # fig = plt.gcf()
# # fig.set_size_inches(10, 5.3)
# plt.savefig("test.png")


# line1 = plt.plot(mean, 'ro-', label = 'mean')
# line2 = plt.plot(median, 'g+-', label = 'meadian')
# line3 = plt.plot(ninety_percentile, 'b^-', label = '90th')

# ax.legend(loc='lower right', bbox_to_anchor=[1.0, 0.6], fontsize=20)

# ax.set_xlabel("Iteration", fontsize=22)
# ax.set_ylabel("Throughput (GBps)",fontsize=22)

# ax.tick_params(labelsize=20)

# plt.ylim(0, 0.01)

# plt.savefig("ssd_Fujitsu-1W_V0_based_10us_10_to_1_net-ssd_throughput" + ".png")

# plt.show()
