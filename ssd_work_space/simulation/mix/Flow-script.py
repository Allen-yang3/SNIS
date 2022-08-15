file = open("1k_analysisflow.txt", "r+")
lines = file.readlines()
file.close()

totalFlows = 0
data = []

# Get all lines except first line into new list
for line in lines:
    newLine = line.split(" ")
    if(len(newLine) != 1):
        newLine.pop(5)
    else:
        totalFlows = line
        continue
    data.append(newLine)

# Sort the new list
sortedLines = sorted(data, key=lambda x: x[4])

for line in sortedLines:
    line.insert(3,"100")
    
# Process each row into a string
for i in range(0,len(sortedLines)):
    s = ""
    for word in sortedLines[i]:
        s = s + word + " "
    s = s.rstrip(s[-1])
    sortedLines[i] = s + "\n"

# Add back the first line
sortedLines.insert(0, totalFlows)

# Write to File
with open('1k_analysisflow_sorted.txt', 'w') as f:
    f.writelines(sortedLines)

