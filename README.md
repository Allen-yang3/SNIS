 # SNIS Linux Convergence Test Readme

SNIS is an iterative storage-network simulator which evaluates dis-aggregated storage systems. SNIS integrates storage and network simulations to model the end-to-end performance of disaggregated storage systems and conducts multiple rounds of simulations to update arrival times of read/write requests.

## Getting Started 

To run the MQSim Linux Simulator, ensure that the correct versions of Linux, Python, GCC and G++ are used
For this project, we use:

- Ubuntu Linux 22.04.
- GCC/G++ 5 and python 2 NS3 Simulator.
- Python 3 for MQSim and SNIS.
- All setup for NS3 should be done under ssd_work_space/simulation.



### Installing/configuring GCC and G++ 5

1. Add both of these to the sources.list file. (sudo nano /etc/apt/sources.list)

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

&nbsp;

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
$ update-alternatives --install /usr/bin/python python /usr/bin/python3.10 2
```

The path in both commands should be modified accordingly based on where python is installed. In most cases it will be installed in the listed path above.

```bash
$ python --version
Python 3.10.4
```
---

Now, we can again list all python alternatives:

```
$ update-alternatives --list python
/usr/bin/python2.7
/usr/bin/python3.10
```

From now on, we can anytime switch between the above listed python alternative versions using below command and entering a selection number:

```bash
update-alternatives --config python
```

After this command, select python2.7 for auto mode and python3 for manual mode.

> For more documentation on installing python please refer to [this](https://linuxconfig.org/how-to-change-from-default-to-alternative-python-version-on-debian-linux) page

&nbsp;

## Running The Simulation

In this section we will explain how to configure and run experiments on the NS3 and SNIS simulators.

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

The configuration file has different settings within that can be adjusted based on your needs. We have provided a base [config.txt](https://github.com/Allen-yang3/SNIS/blob/master/ssd_work_space/simulation/mix/config.txt) file to run the simulation. Also included is [config_doc.txt](https://github.com/Allen-yang3/SNIS/blob/master/ssd_work_space/simulation/mix/config_doc.txt) which goes into further detail on configuring the simulator. 

&nbsp;

### Starting MQSim 

#### Python Libraries Required for MQSim
For our script we use both Pandas and absl. Please find the commands below for installation.

```
$ sudo pip3 install pandas
$ sudo pip3 install absl
```

#### Compile MQSim
```
$ git submodule init
$ git submodule update
$ cd SSD_Sim/MQSim
$ make
$ chmod +x ./MQSim
$ cp ./MQSim $PATH_TO_SNIS/ssd_work_space
```


#### Execute MQSim

To run MQSim, path under `/ssd_work_space`. To actually start it run

```
./MQSim -i ssdconfig.test.xml -w workload-trace.xml
```

Refer to [MQSim Readme](https://github.com/DanlinJia/SSD_Sim/blob/8e3b61709aba95ecfdb8d2189259addfa474e690/MQSim/README.md) for more documentation on compiling

&nbsp;

The workload file as well as other configurations can be added to this command as arguments. Examples:

```
flags.DEFINE_string("workload", "Fujitsu_V0_based_50_to_1_net-ssd.csv", "The workload input file")
flags.DEFINE_float("conv", 0.05, "converge criteria, if set to 0, SNIS will finish all iterations specified by 'num'")
flags.DEFINE_string("map_mod", "sequential", "The defualt initiator_target mapping is sequential")
flags.DEFINE_integer("rack_num", 2, "The default rack number is 2") 
flags.DEFINE_integer("ssd_per_target", 1, "The number of ssds each target has")
```

Refer to [Linux_converge_test.py](https://github.com/Allen-yang3/SNIS/blob/master/ssd_work_space/Linux_converge_test.py) for all arguments.

> Please use Python 3.8+ to ensure compatibility

&nbsp;

Here's an example of starting simulator with command line arguments:
```
$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W.trace -map_mod random -rack_num 4
```

## Experiments

*Workload: 1us; 40_to_4; Random distribution; 5W and 10W requests; one SSD device per target*

```
python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W.trace -map_mod random -rack_num 4
python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-5W.trace -map_mod random -rack_num 4
```

---

*Workload: 1us; 40_to_4; Random distribution; 5W and 10W requests; multiple (5) SSD devices per target with 3 patterns*

```
$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_20-10W-Linux.trace -map_mod random -rack_num 4
$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_20-10W-Linux.trace -map_mod sequential -rack_num 4
$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_20-10W-Linux.trace -map_mod even -rack_num 4

$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod random -rack_num 4
$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod sequential -rack_num 4
$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod even -rack_num 4

$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod random -rack_num 4 -ssd_per_target 5
$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod sequential -rack_num 4 -ssd_per_target 5
$ python3 Linux_converge_test.py -workload V0_MAP_InterArrival_1_256_MEAN_40_to_4-10W-Linux.trace -map_mod even -rack_num 4 -ssd_per_target 5
```

Output files can be found under `ssd_work_space/test/{workflow name}`. Each iteration will be labeled by their iteration number. 

If error message `MQSim does not have permissions` occurs run the following command:
> $ sudo chmod u+x MQSim

&nbsp;

#### Simulation outputs:


NS3 Simulation Output: 
```
fct.txt, pfc.txt, mix.tr
```

MQSim Simulation output:

```
test.txt
```

SNIS Simulation Output:

```
test.txt
```

## References

D. Jia et al., "SNIS: Storage-Network Iterative Simulation for Disaggregated Storage Systems," 2021 IEEE International Performance, Computing, and Communications Conference (IPCCC), 2021, pp. 1-6, doi: 10.1109/IPCCC51483.2021.9679397.
