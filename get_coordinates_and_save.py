from my_packages import signal_elaboration as s
from my_packages.utils import probes, probes_walk, HandlePaths
from my_packages.directory_data import  GetCoordinates, make_generator
from my_packages.my_hdf5 import explore_library


import os
import pandas
import numpy as np
from datetime import datetime
import scipy.signal
import scipy.io
import pickle
import h5py

from pprint import pprint


# exploring the NAS
# you can explore the NAS using cmd line tools:

print("we have the following probes", probes)
print("the structure in which the files are saved is: ")
pprint(probes_walk)

# obtain all possible paths from the json-like structure
data_paths = HandlePaths()(probes_walk)
probe_paths = {probe: HandlePaths(base_path="/NAS/"+probe)(probes_walk[probe]) for probe in probes}
all_paths = HandlePaths()(probes_walk) 
pprint(probe_paths)  
pprint(all_paths)


path = "measurements.h5"

data_handlers = dict()
for probe in probes:
    data_handlers[probe] = []
    for measurement in probe_paths[probe]:
        print("current measurement path:", measurement)
        dh = GetCoordinates(measurement)
        data_handlers[probe].append(dh)

        dh.save_to_hdf5(path) 