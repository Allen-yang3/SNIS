def getAverageThroughput(filename, excludeReads):
    file = open(filename, "r+")
    rawLines = file.readlines()
    lines = []
    throughputs = []

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

    avg_throughput = 0
    for throughput in throughputs:
        avg_throughput += throughput
    avg_throughput = avg_throughput / len(throughputs)

    return avg_throughput

def main():
    while(1):
        print("Select Mode:\n1. All Flows\n2. Write Flows Only\n3. Exit")
        selection = int(input())
        if(selection == 1):
            print("Please enter Filename: ")
            filename = input()
            print("Average Throughput: " + str(getAverageThroughput(filename, False)))
            print('')
        elif(selection == 2):
            print("Please enter Filename: ")
            filename = input()
            print("Average Throughput: " + str(getAverageThroughput(filename, True)))
            print('')
        elif(selection == 3):
            exit()

main()
