import numpy as np
from pprint import pprint
import os 

from my_packages.directory_data import make_all_generators, measurements2dataset

filename = "measurements.h5"
generators = make_all_generators(filename, return_fullpaths=True)

archive_path = "/NAS/full_measurement_data.h5"

for key, generator in generators.items():
    measurements2dataset(archive_path, generator, key, compression_level=5)

