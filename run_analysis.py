from my_packages import signal_elaboration as s
from my_packages import probes, probes_walk, Handle_Paths

import os
import scipy.signal
import scipy.io
import pickle




# parameters
probes = ["xfb31", "XFE_04s", "XFR31"]
directory = os.path.join("/home/pignari/poliNAS", probes[0], "r18")
T = 10e-6
N= int(100e3)


# load coordinates
with open("/share/data_processing/point_coordinates", "rb") as handle:
    coordinates = pickle.load(handle)

#load the FIR filter from MATLAB
mat = scipy.io.loadmat('/share/data_processing/FIR_matlab.mat')
FIR_m = mat["b"][-1]

# window properties
kaiser_beta = 14

# create post processing class
post_processing = s.ElaborateBatches(directory=directory, coordinates=coordinates, observation_time=T, record_length=N)

# define the processing functions
FIR_filter_func = lambda x: post_processing.apply_conv_FIR_filter(x, FIR_m)
window_func = lambda x: post_processing.apply_window(
    x, window = scipy.signal.windows.kaiser(x.shape[0], kaiser_beta),
    coherence="amplitude"
)

post_processing.run_average_spectrum(
    archive_name=("xfb31", "windowed_and_FIR"),
    signal_postprocessing= lambda x: FIR_filter_func(window_func(x)),
    #number_of_batches=2,
    save_location=r"/share/data_processing/",
    restart_generator=True,
    default_overwrite=True
)