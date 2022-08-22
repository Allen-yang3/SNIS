 # MQSim Linux Convergence Test Readme

INTRO HERE TODO

## Getting Started 

To run the MQSim Linux Simulator, ensure that the correct versions of python, GCC and G++ are used
For this project, we use:

- GCC/G++ 5 for the linux simulator and python 2.
- MQSim runs in Python 3 however python 2 can be used and is recommended.
- All setup should be done under ssd_work_space/simulation


### Installing/configuring GCC and G++ 5

1. Add both of these to the sources.list file. (sudo gedit /etc/apt/sources.list)

```
deb [trusted=yes] http://dk.archive.ubuntu.com/ubuntu/ xenial main
deb [trusted=yes] http://dk.archive.ubuntu.com/ubuntu/ xenial universe 
```

2. Update and install using the following 2 commands:

```
$ sudo apt update
$ sudo apt install g++-5 gcc-5
```

> See [here](https://askubuntu.com/questions/1235819/ubuntu-20-04-gcc-version-lower-than-gcc-7 ) for a more complete documentation on the instructions to install and set up GCC 5

### Installing/Configuring Python2

There are multiple ways to set python 2 as the default version. If you already have python3 configured to python, then you can either create a new virtual environment or update alternative for python. For our testing, we used "update alternative".

To change python version system-wide we can use update-alternatives python command. Logged in as a root user, first list all available python alternatives:

```
$ update-alternatives --list python
```

You may recieve an error message looking something like this:

> update-alternatives: error: no alternatives for python

This means that no python alternatives has been recognized by update-alternatives command. For this reason we need to update our alternatives table and include both python2.7 and python3.4:

```
$ update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
$ update-alternatives --install /usr/bin/python python /usr/bin/python3.4 2
```

The path in both commands should be modified accordingly based on where python is installed. In most cases it will be installed in the listed path above.

```bash
$ python --version
Python 3.4.2
```
---

Now, we can again list all python alternatives:

```
$ update-alternatives --list python
/usr/bin/python2.7
/usr/bin/python3.4
```

From now on, we can anytime switch between the above listed python alternative versions using below command and entering a selection number:

```bash
update-alternatives --config python
```

After this command, select python2.7 for auto mode and python3 for manual mode.

> For more documentation on installing python please refer to [this](https://linuxconfig.org/how-to-change-from-default-to-alternative-python-version-on-debian-linux) page

## Running The Simulation

INTRO TODO

### Starting the Network Simulator

After changing the default version and configuring python, please run the following command under the `/Simulation` directory to ensure that the GCC and G++ version are correctly assigned.

```
$ CC='gcc-5' CXX='g++-5' ./waf configure
```

This command will also build the simulator and prepare it for tests to be run.

All Simulator files can be found under `ssd-work-space/simulation`. Under simulation, the configuration files as well as output and flow files will be found under `simulation/mix`.

To run the simulation: 
```
$ ./waf --run 'scratch/third mix/config.txt'
```

Where config.txt can be replaced with a configuration file of your choice. 

The configuration file has different settings within that can be adjusted based on your needs. We have provided a base `config.txt` file to run the simulation.

Also included is `config_doc.txt` which goes into further detail on configuring the simulator. 

### Starting MQSim 

#### Compile MQSim
```
git submodule init
cd SSD_Sim/MQSim
make
cp ./MQSim SNIS/ssd_work_space
```

#### Execute MQSim

To run MQSim, path under `/ssd_work_space`. To actually start it run

```
./MQSim -i ssdconfig.test.xml -w workload-trace.xml
```

Check SSD_Sim/MQSim/README.md for details about running MQSim.

The workload file as well as other configurations can be added to this command as arguments. Refer to `Linux_converge_test.py` for all arguments.

> Please use Python 3.8+ to ensure compatibility

Here's an example of starting simulator with command line arguments:
```
$ python3.8 ./Linux_converge_test.py -workload $.trace -map_mod random -rack_num 4
```

## Experiments

*Workload: 1us; 40_to_4; Random distribution; 5W and 10W requests; one SSD device per target*

```
python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W.trace -map_mod random -rack_num 4
python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-5W.trace -map_mod random -rack_num 4
```

---

*Workload: 1us; 40_to_4; Random distribution; 5W and 10W requests; multiple (5) SSD devices per target with 3 patterns*

```
$ python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_20-10W-Linux.trace -map_mod random -rack_num 4
$ python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_20-10W-Linux.trace -map_mod sequential -rack_num 4
$ python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_20-10W-Linux.trace -map_mod even -rack_num 4

$ python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod random -rack_num 4
$ python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod sequential -rack_num 4
$ python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod even -rack_num 4

$ python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod random -rack_num 4 -ssd_per_target 5
$ python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod sequential -rack_num 4 -ssd_per_target 5
$ python3.8 ./Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod even -rack_num 4 -ssd_per_target 5
```

Output files can be found under `ssd_work_space/test/{workflow name}`. Each iteration will be labeled by their iteration number. 

