"""
Extract the queue length statistics from NS3-RDMA simulator output file
"""
from absl import app
from absl import flags
from bisect import insort, bisect
from collections import defaultdict
import matplotlib.pyplot as plt
plt.style.use('seaborn')

FLAGS = flags.FLAGS
flags.DEFINE_string("input", "queue.txt", "The input file name.")
flags.DEFINE_string("encoding", "utf16",
                    "The encoding schedme of the input file.")


def drawQLen(data, pause=None, label=None, show=True):
    """Draw a plot showing queue length change relative to the time

    Argument:
        data: a list containing (time, queue_length) tuple, sorted by time
        pause: a list, if not None, containing (pause_time, queue_length) tuple, sorted by time
        label: the label of the data
        show: call plt.show() or not
"""
    x = [d[0] / 1e6 for d in data]
    y = [d[1] / 1e3 for d in data]
    plt.plot(x, y, alpha=0.5, zorder=10, label=label)
    plt.xlabel("Time / ms")
    plt.ylabel("Queue Length / KB")
    if pause:
        x = [p[0] / 1e6 for p in pause]
        y = [p[1] / 1e3 for p in pause]
        plt.scatter(x, y, color='r', zorder=0, s=10)
    if show:
        if label:
            plt.legend(loc="best")
        plt.show()


def drawAllQLen(Q_dic):
    for node in sorted(Q_dic):
        drawQLen(Q_dic[node], label=str(node), show=False)
    plt.legend(loc="upper right", ncol=2)
    plt.show()


def main(argv):
    if not FLAGS.input:
        print("No input file\n")

    Q_dic = defaultdict(list)  # Queue length
    pr_dic = defaultdict(list)  # PAUSE receiver
    ps_dic = defaultdict(list)  # PAUSE sender

    with open(FLAGS.input, 'r', errors="ignore", encoding=FLAGS.encoding) as f:
        line = f.readline().strip()
        while line:
            arr = line.split(" ")
            if len(arr) == 3 and arr[-1] == "PAUSE_R":
                # Format: Time Node PAUSE_R
                insort(pr_dic[int(arr[1])], int(arr[0]))
            elif len(arr) == 4:
                if arr[2] == "Queue":
                    # Format: Time Node QUEUE Q_len
                    insort(Q_dic[int(arr[1])], (int(arr[0]), int(arr[-1])))
                elif arr[2] == "PAUSE_S":
                    # Format: Time Node PAUSE_S
                    insort(ps_dic[int(arr[1])], (int(arr[0]), int(arr[-1])))

            line = f.readline().strip()

    #for bottleneck in sorted(ps_dic):
    #    drawQLen(Q_dic[bottleneck], ps_dic[bottleneck], label = str(bottleneck))

    drawAllQLen(Q_dic)


if __name__ == '__main__':
    app.run(main)
