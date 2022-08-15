"""ATTENTION: Please refer to windows_converge_test.py for running the converge experiment!!!

June 1, 2021
This script is originally created to generate NS3 network simulation necessary configuration files in each iteration in the converge experiment.
Currently, the windows_converge_test.py can work independently to finish the converge experiment.
As a result, this file will only serve to analyze the converge experiment results.
"""
from absl import app
from absl import flags
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import ceil
import os
from scipy import spatial
from io_sim import ssd_simulator
from shutil import copyfile
from utils import readSummary

plt.style.use('fivethirtyeight')

FLAGS = flags.FLAGS
flags.DEFINE_string("path", "test", "The directory containing log data")
flags.DEFINE_integer("write", 6, "The number of directories holding traces")


def extractWriteFlowFCT(path, itr_num=6):
    """Extract write request FCT from the directory"""

    root_dir = path
    data = pd.DataFrame()
    for i in range(1, itr_num + 1):
        t = readSummary(os.path.join(root_dir, str(i)))
        #t = t.sort_values("RequestID").set_index("RequestID")
        t = t[t.IOType == 1].sort_values("FCT").reset_index()
        data[str(i)] = t.FCT
    data.to_csv('write.csv', index=False)
    return data


def extractThroughput(path, itr_num=6):
    """Extract throughput from the directory"""

    root_dir = path
    data = pd.DataFrame()
    for i in range(1, itr_num + 1):
        t = readSummary(os.path.join(root_dir, str(i)))
        #t = t[t.IOType == 1].sort_values("FCT").reset_index()
        t["Throughput"] = t.Size / t.TotalDelay * 1e9  # Byte/s
        data[str(i)] = t.Throughput
    data.to_csv('write.csv', index=False)
    return data


def computeCosDistance(arr_1, arr_2, bin_size=1000):
    mx = max(max(arr_1), max(arr_2))
    mn = min(min(arr_1), min(arr_2))
    bin_num = ceil((mx - mn) / bin_size)  # set the size of bin around 1us
    print(mn, mx, bin_num)
    ct1, _ = np.histogram(arr_1, bins=max(10, bin_num), range=(mn, mx))
    ct2, _ = np.histogram(arr_2, bins=max(10, bin_num), range=(mn, mx))
    return spatial.distance.cosine(ct1, ct2)


def computePercentileRelativeDistance(arr_1, arr_2, percentile=0.9):
    return abs(arr_1.quantile(percentile) - arr_2.quantile(percentile)) / max(
        arr_1.quantile(percentile), arr_2.quantile(percentile))


def computeMeanRelativeDistance(arr_1, arr_2):
    return abs(arr_1.mean() - arr_2.mean()) / max(arr_1.mean(), arr_2.mean())


def drawDistanceTrend(path, itr_num=6, cmp_func=computeCosDistance):
    """Draw the cosine similarity distance of write requests"""
    #data = extractWriteFlowFCT(path, itr_num)
    data = extractThroughput(path, itr_num)

    # Cosine distance
    y = [
        computeCosDistance(data[str(i + 1)], data[str(i)], bin_size=5e3)
        for i in range(1, itr_num)
    ]
    print(y)
    plt.plot(range(itr_num - 1), y, marker='x', label="Cosine")

    # Mean Normalized Absolute
    y = [
        computeMeanRelativeDistance(data[str(i + 1)], data[str(i)])
        for i in range(1, itr_num)
    ]
    plt.plot(range(itr_num - 1), y, marker='x', label="Mean Relative")

    # 90%-ile Normalized Absolute
    y = [
        computePercentileRelativeDistance(data[str(i + 1)], data[str(i)])
        for i in range(1, itr_num)
    ]
    plt.plot(range(itr_num - 1), y, marker='x', label="90%-ile Relative")

    # Median Normalized Absolute
    y = [
        computePercentileRelativeDistance(data[str(i + 1)], data[str(i)], 0.5)
        for i in range(1, itr_num)
    ]
    plt.plot(range(itr_num - 1), y, marker='x', label="Median Relative")

    plt.legend(loc='best')
    plt.xlabel('Iteration')
    plt.ylabel("Distance")
    plt.title(os.path.normpath(path).split('/')[-1])
    plt.ylim([0, 1])
    plt.tight_layout()
    plt.show()


def drawDistanceCDF(path, itr_num=6):
    #data = extractWriteFlowFCT(path, itr_num)
    data = extractThroughput(path, itr_num)

    def drawCDF(data, label, color):
        y = np.linspace(0, 1, len(data), endpoint=False)
        x = sorted(data)
        plt.plot(x, y, label=label, color=color)

    cmap = plt.get_cmap('gnuplot')
    colors = [cmap(i) for i in np.linspace(0, 1, itr_num)]
    for i in range(1, itr_num):
        name = 'dif_%d_%d' % (i, i + 1)
        data[name] = abs(data[str(i)] - data[str(i + 1)]) / pd.concat(
            [data[str(i)], data[str(i + 1)]], axis=1).max(axis=1)
        print(data[name].mean())
        drawCDF(data[name], label=name, color=colors[i - 1])
    #print(data.mean())
    plt.legend(loc='best')
    plt.ylabel("$p$")
    plt.xlabel("Normalized Absolute Distance")
    plt.title(os.path.normpath(path).split('/')[-1])
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def main(argv):
    drawDistanceCDF(FLAGS.path, FLAGS.write)
    drawDistanceTrend(FLAGS.path, FLAGS.write, cmp_func=computeCosDistance)


if __name__ == '__main__':
    app.run(main)
