SNIS=$(pwd)

# initialize submodule
echo "initialize submodule:"
git submodule init
git submodule update
cd SSD_Sim && git pull https://github.com/DanlinJia/SSD_Sim.git main

# compile MQSim and copy it to workspace
echo "compile MQSim and copy it to workspace:"
cd MQSim && make
cd $SNIS
cp SSD_Sim/MQSim/MQSim ssd_work_space/
chmod +x ssd_work_space/MQSim

echo "copy necessary files"
# copy MQSim configuration files
cp SSD_Sim/MQSim/ssdconfig.test.xml ssd_work_space/
cp SSD_Sim/MQSim/workload-trace.xml ssd_work_space/

# copy MQSim python wrapper
cp SSD_Sim/io_sim/io_sim.py ssd_work_space/
