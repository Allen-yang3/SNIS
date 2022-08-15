file = open("topology-test.txt", "r+")
lines = file.readlines()
file.close()

for line in lines:
    newLine = line.split(" ")
    if(len(newLine) == 5):
        continue
    else:
        data.append(newLine)
for line in replacedLine
    line.replace(4,"1000ns")

with open('replacement_topology.txt','w') as f:
    f.writelines(replacedLine)