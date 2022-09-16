import os
import re
import numpy as np
from datetime import datetime
from copy import copy
from my_packages import my_hdf5
from my_packages.utils import probes
from my_packages.my_hdf5 import *
from tqdm import tqdm

class Batch_Generator():
    # this class defines a generator that loads filenames in an array until the numbering
    # returns to 1. Therefore all the measurements of the same point should be grouped in one batch. 
    # The batch generator expects a generator as input, that returns one at a time the filenames. 
    # In particular such a generator is defined as os.scandir(<directory_path>)
    def __init__(self, parsed):
        self.parsed = parsed
        self.coordinate_gen = iter(parsed)
        self.current_batch = []
        self.number_of_batches_done = 0
        self.batch_size = 50

    def __len__(self):
        return len(self.parsed)    
    
    def __iter__(self):
        return self
    
    def __next__(self):
        current_coordinates = next(self.coordinate_gen)
        current_name = "x"+current_coordinates[0]+"y"+current_coordinates[1]
        batch = [current_name+str(ii+1)+".csv" for ii in range(self.batch_size)]

        self.current_batch=batch
        self.number_of_batches_done += 1

        return self.current_batch




class RootBatchGen(Batch_Generator):
    def __init__(self, parsed, root):
        Batch_Generator.__init__(self, parsed)
        self.local_gen = Batch_Generator(self.parsed)
        self.root = root
        self.default_next = lambda : copy(Batch_Generator.__next__)(self)

    def add_root(func):
        def inner(self):
            batch = [os.path.join(self.root, string) for string in func(self)]
            self.current_batch_fullpath = batch
            return batch
        return inner
    

    @add_root
    def __next__(self):
        return self.default_next()
        



class GetCoordinates():
    def __init__(
        self, 
        path = "",
        file_contents = None,
        ):
        self.path = path
        if not file_contents:
            resp = input("type \"y\" to look through the directory contents: ")
            if resp == "y":
                print("looking through content . . .")
                print("\n")
                self.file_contents = os.listdir(path)
            else:
                raise Exception("must give the list of contents")
        else:
            self.file_contents=file_contents
        
        coordinates = self.get_coordinates()

    
    @staticmethod
    def _parse_strings(contents):
        reg_expr = "[1-9]([0-9]|)\.csv"

        parsing1 = lambda x: list(filter(None, re.split(reg_expr, x)))[0]
        parsing2 = lambda x: x[1:].split("y")
        parsed_strings = list(map(parsing2, set(map(parsing1, contents))))
        
        return parsed_strings
    
    
    def get_coordinates(self):
        # using regular expressions split the string where it finds a number between 1 and 9; followed by a number 
        # between 0 and 9 or nothing; followed by ".csv". 

        parsed_strings = self._parse_strings(self.file_contents)
        self.parsed_strings = parsed_strings

        coordinates = np.array(parsed_strings, dtype=np.float32)
        self.points = coordinates

        point_table = np.rec.fromarrays(
            [coordinates[:,0]/1e3, coordinates[:,1]/1e3], 
            dtype=[("x", "float16"), ("y", "float16")]
            )
        self.point_table = point_table
        x = np.unique(coordinates[:,0]); y = np.unique(coordinates[:,1])
        # the coordinate are expressed in micron!
        # transform to mm
        x = x/1e3; y=y/1e3



        # create a grid that can be useful in plotting on the measurement plane. No need to be conscious of memory:
        # the number of points is very small
        grid = np.meshgrid(x,y, indexing="xy", sparse=False, copy=True) 
        self.coordinates = dict(x=x, y=y, grid=grid)

        return x, y, grid
    
    def save_to_hdf5(self, library_path):
        info = dict(description = \
        "These coordinates were obtained as the coordinates that appear atleast once among the \
        measurement points as found in the names of the csv files")


        probe = get_probe_from_path(probes, self.path)
        save_measurement_info(
            library=library_path, 
            dh=self,
            probes=probes,
            measurement_info=info,
            group_info=dict(READ="info on the probe")
            )


def make_all_generators(file, return_fullpaths=False):
    coordinates_dict = make_coord_dict(file)
    generators = {}
    for k in coordinates_dict.keys():
        with h5py.File(file, "r") as f:
            path = f[k].attrs["measurement_path"] 
        generators[k] = make_generator(
            coordinates_dict[k]["x"], 
            coordinates_dict[k]["y"],
            include_file_location = path if return_fullpaths else False
        )
    return generators
    

def make_coord_dict(file):
    with h5py.File(file, "r") as f:
        return {
            group: dict(
                x=np.array(f[group]["coordinates"]["x_coordinates"]),
                y=np.array(f[group]["coordinates"]["y_coordinates"])
            )

            for group in see_groups_and_datasets(file)["group_keys"]
        }   
    
def make_generator(xcoordinates, ycoordinates, include_file_location=False):
    # WARNING: the assumption is that every xcoordinate has an associated y coordinate
    # get the coordinates from the parsed strings
    parsed_strings = arrays_2_parsed_strings(xcoordinates, ycoordinates)
    batch_generator = RootBatchGen(parsed_strings, include_file_location) if include_file_location else Batch_Generator(parsed_strings) 

    return batch_generator

def arrays_2_parsed_strings(x, y):   
    xgrid, ygrid = np.meshgrid(x, y, indexing="xy", sparse=False, copy=True)
    points = grid_2_points(xgrid, ygrid)
    parsed = [[str(a)+'0' for a in elem] for elem in points*1e3]
    return parsed


def grid_2_points(xgrid, ygrid):
    # Change this function if the assumption is no longer true!!!
    points = np.stack((xgrid.flatten(), ygrid.flatten()), axis=1)
    return points



##################################################################################
## save information in hdf5 format
###################################################################################


def save_measurement_info(library, dh, probes, measurement_info={}, group_info={}):
    path = dh.path
    probe = get_probe_from_path(probes, dh.path)

    group_name = get_group_name(probe, path, probes)


    xcoord = dh.coordinates["x"]; ycoord = dh.coordinates["y"] 
    if not exists(library):
        build_hdf5(name=library, groups=[probe])
    
    if not group_exist(library, group_name):
        add_group(library, group_name, **group_info)

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    # open the group
    with h5py.File(library, "a") as f:
        g = f[group_name]
        
        g.attrs["creation date"]= dt_string
        g.attrs["measurement_path"] = path
        g.attrs["probe"] = probe

        
        #check if the coordinate group already exists
        group_keys = [key for key, items in g.items() if isinstance(items, h5py.Group)]

        print("the probe contains the following groups: ", group_keys)

        if "coordinates" in group_keys:
            res = input("type y to overwrite")

            if res != "y":
                return 
            else:
                del g["coordinates"]

       

        coord_gr = g.create_group("coordinates")
        coord_gr.attrs.update(measurement_info)

        # create the dataset
        # require_dataset is the same as create_dataset. However, if the dataset already exists it does not overwirte.

        x_ds=coord_gr.require_dataset("x_coordinates", shape=xcoord.shape, dtype=np.float32, data=xcoord)
        y_ds=coord_gr.require_dataset("y_coordinates", shape=ycoord.shape, dtype=np.float32, data=ycoord)
        points_table = coord_gr.require_dataset("measurement_points", shape=dh.point_table.shape, 
        dtype=dh.point_table.dtype, data=dh.point_table)

    
def get_probe_from_path(probes, path):
    probe_ = [p for p in probes if p in path]
    # check there is one element in the probe list
    try:
        probe = (lambda x: x)(*probe_)
    except:
        raise("probe length is ", len(probe_))
    return probe


def get_group_name(probe, path, probes):
    # this function is necessary because of the poor choice in naming the folders

    if probe == probes[0]:
        return probe
    if probe  == probes[1]:
        if path.split("/")[-1]=="r18":         
            return "/".join([probe, "incomplete"])
        else:
            return probe
    if probe == probes[2]:
        return probe + "_" + path.split("/")[-1]
    return

    ######################################################################################################
    ######################################################################################################

    # create an h5 file with all the measurements compressed

def measurements2dataset(library, batch_generator, dataset_name, compression_level=4):
    number_of_batches = len(batch_generator)
    datapoints = int(100e3)
    batch_size = batch_generator.batch_size
    # batch_size = batch_generator.batch_size

    dataset_shape = (batch_size, number_of_batches, 2, datapoints)

    dataset_attr = dict(
        observation_interval = "10us",
        number_of_points = datapoints,
        max_frequency_resolution = 1/datapoints, 
        structure_of_numpy_array = ("batch_size", "number_of_batches", "time, amplitude", "datapoints") 
    )

    if not exists(library):
        build_hdf5(name=library)

    with h5py.File(library, "a") as f:
        dataset = f.require_dataset(
            dataset_name, 
            shape=dataset_shape, 
            dtype="float64", 
            chunks=(batch_size, 1, 2, datapoints), 
            compression=compression_level
            )
        for batch in tqdm(batch_generator):
            dataset[:, batch_generator.number_of_batches_done, :, : ] = get_numpy_from_batch(batch)
    

def get_numpy_from_batch(batch):
    readings = [list(read_csv(csv_file_path)) for csv_file_path in batch]

    # I must transpose so that the shape has the number of points in the last position and 2 - ie time and amplitude - in 
    # second to last place
    
    return np.array(readings).transpose(0,2,1)

def read_csv(filename):
    for row in open(filename):
        yield list(map(lambda x: float(x),row.split(",")[-2:]))