"""This script creates summary csv files in the network-ssd iteration experiment"""
from absl import app
from absl import flags
from utils import readSummary
import pandas as pd
import os
import numpy as np

FLAGS = flags.FLAGS
flags.DEFINE_string("path", "test", "The directory containing log data")


# def main():
#     root = "test/ssd_Fujitsu-1W_V0_based_10us_10_to_1_net-ssd"
#     for f in os.listdir(root):
#         # result.csv is the output file in each iteration, which is used as an indicator of the completion of an iteration here
#         if f.isdigit() and os.path.isfile(os.path.join(root, f, "result.csv")):
#             dt = readSummary(os.path.join(root, f))
#             dt.to_csv(os.path.join(root, f + ".csv"), index=False)

def main(argv):
    folder = FLAGS.path
    for trace in os.listdir(folder):
        root = os.path.join(folder, trace)
        for f in os.listdir(root):
            # result.csv is the output file in each iteration, which is used as an indicator of the completion of an iteration here
            if f.isdigit() and os.path.isfile(os.path.join(root, f, "result.csv")):
                dt = readSummary(os.path.join(root, f))
                dt.to_csv(os.path.join(root, f, f + ".csv"), index=False)

            
if __name__ == '__main__':
    app.run(main)
    
    
'''
if __name__ == '__main__':
    """
    create merged stats for each iteration.
    """
    folder = FLAGS.path

    for trace in os.listdir(folder):
        root = os.path.join(folder, trace)
        for f in os.listdir(root):
            # result.csv is the output file in each iteration, which is used as an indicator of the completion of an iteration here
            if f.isdigit() and os.path.isfile(os.path.join(root, f, "result.csv")):
                dt = readSummary(os.path.join(root, f))
                dt.to_csv(os.path.join(root, f, f + ".csv"), index=False)
'''

