import numpy as np

def getAverageThroughput(filename, excludeReads):
    throughputs = getThroughputs(filename,excludeReads)

    avg_throughput = 0
    for throughput in throughputs:
        avg_throughput += throughput
    avg_throughput = avg_throughput / len(throughputs)

    return avg_throughput

def getThroughputs(filename, excludeReads):
    file = open(filename, "r+")
    rawLines = file.readlines()
    lines = []
    throughputs = []
    tenthpercentile = []

    for line in rawLines:
        newline = line.split(" ")
        newline[-1] = newline[-1].strip()
        if(excludeReads):
            if(newline[0] != '0b008001'):
                lines.append(newline)
        else:
            lines.append(newline)

    for line in lines:
        throughputs.append((int(line[4]) * 8) / int(line[6]))

    return throughputs


def main():
    while(1):
        print("Select Mode:\n1. All Flows\n2. Write Flows Only\n3. Exit")
        selection = int(input())
        if(selection == 1):
            print("Please enter Filename: ")
            filename = input()
            print("Average Throughput: " + str(getAverageThroughput(filename, False) ))
            print('')
            print("10th Percentile: " + str (np.percentile(getThroughputs(filename,False), 10)))
            print('')
            print("90th Percentile: " + str (np.percentile(getThroughputs(filename,False), 90)))
            print('')
        elif(selection == 2):
            print("Please enter Filename: ")
            filename = input()
            print("Average Throughput: " + str(getAverageThroughput(filename, True)))
            print('')
            print("10th Percentile: " + str (np.percentile(getThroughputs(filename,True), 10)))
            print('')
            print("90th Percentile: " + str (np.percentile(getThroughputs(filename,True), 90)))
            print('')
        elif(selection == 3):
            exit()

main()
