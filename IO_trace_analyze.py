"""
Analyze the IO trace provided by Danlin (jia.da@northeastern.edu)
"""
from absl import app
from absl import flags
import pandas as pd
import numpy as np
import scipy.stats as st
from math import ceil
from utils import drawCDF
from collections import Counter
import matplotlib.pyplot as plt
plt.style.use('seaborn')

FLAGS = flags.FLAGS
flags.DEFINE_string("input", "100initiator_90hosts.csv",
                    "The input file name.")
flags.DEFINE_integer("time_window", int(1e9),
                     "The time window length, the unit is ns.")


def drawFlowSize(data, time=None):
    """Draw a plot with flow size as x axis, the number of the flows with that size as y axis
Then draw a histogram and PDF distribution for the flow size.

    Args:
        data: DataFrame containing the IO trace
        time: a tuple containing (start_time, end_time)
"""
    tmp = data
    if time:
        tmp = data[(data.ArrivalTime >= time[0]) & (data.FinishTime < time[1])]

    # Draw flow size bar
    ct = Counter(tmp.Size / 1024)
    plt.bar(list(ct.keys()), list(ct.values()))
    plt.xlabel('Flow Size / KB')
    plt.ylabel('Number')
    plt.show()

    # Draw flow size histogram and PDF
    x = tmp.Size / 1024
    plt.hist(x, density=True, bins=100, stacked=True, label="Flow Size")
    mn, mx = plt.xlim()
    plt.xlim(mn, mx)
    kde_xs = np.linspace(mn, mx, 300)
    kde = st.gaussian_kde(x)

    plt.plot(kde_xs, kde.pdf(kde_xs), label="PDF")
    plt.xlabel('Flow Size / KB')
    plt.ylabel('Probability Density')
    plt.legend(loc="upper center", ncol=1, fancybox=True, shadow=True)
    plt.show()


def findBusiestTimeWindow(data, window_length):
    mx = ceil(max(data.FinishTime) / window_length) * window_length
    mn = min(data.ArrivalTime) // window_length * window_length
    tw = [(len(data[(data.ArrivalTime >= i)
                    & (data.FinishTime < i + window_length)]), i)
          for i in range(mn, mx, window_length)]
    return max(tw)


def drawDataSizeCDF(data, time=None, label=None):
    """Draw data size CDF plot in the time interval

    Arguments:
        data: DataFrame containing the IO trace
        time: a tuple containing (start_time, end_time)
"""
    tmp = data
    if time:
        tmp = data[(data.ArrivalTime >= time[0]) & (data.FinishTime < time[1])]
    label = label if label else "Size / KB"
    drawCDF(tmp.Size // 1024, label)


def main(argv):
    if not FLAGS.input:
        print("No input file\n")
    data = pd.read_csv(FLAGS.input)
    #r_data = data[data.IOType == 0]
    n, time = findBusiestTimeWindow(data, FLAGS.time_window)
    print((n, time))
    #drawDataSizeCDF(data, (time, time + FLAGS.time_window))

    # Draw the CDF of which the size of flows is less than 100 KB
    #drawDataSizeCDF(data[data.Size <= 102400], (time, time + FLAGS.time_window), "Flow Size < 100 / KB (48,784 flows)")

    #drawDataSizeCDF(data[data.IOType == 0], (time, time + FLAGS.time_window), "Read Flow Size / KB")
    #drawDataSizeCDF(data[data.IOType == 1], (time, time + FLAGS.time_window), "Write Flow Size / KB")

    drawFlowSize(data, (time, time + FLAGS.time_window))


if __name__ == '__main__':
    app.run(main)
