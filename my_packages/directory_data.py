import os
import re
import numpy as np
from datetime import datetime
from my_packages import my_hdf5
from my_packages.utils import probes
from my_packages.my_hdf5 import *

class Batch_Generator():
    # this class defines a generator that loads filenames in an array until the numbering
    # returns to 1. Therefore all the measurements of the same point should be grouped in one batch. 
    # The batch generator expects a generator as input, that returns one at a time the filenames. 
    # In particular such a generator is defined as os.scandir(<directory_path>)
    def __init__(self, coordinates):
        self.coordinate_gen = iter(coordinates)
        self.current_batch = []
        self.number_of_batches_done = 0
    
    
    def __iter__(self):
        return self
    
    def __next__(self):
        current_coordinates = next(self.coordinate_gen)
        current_name = "x"+current_coordinates[0]+"y"+current_coordinates[1]
        batch = [current_name+str(ii+1)+".csv" for ii in range(50)]

        self.current_batch=batch
        self.number_of_batches_done += 1

        return self.current_batch



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


    
    
def make_generator(xcoordinates, ycoordinates):
    # WARNING: the assumption is that every xcoordinate has an associated y coordinate
    # get the coordinates from the parsed strings
    parsed_strings = arrays_2_parsed_strings(xcoordinates, ycoordinates)
    batch_generator = Batch_Generator(parsed_strings)

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
        # create the dataset
        # require_dataset is the same as create_dataset. However, if the dataset already exists it does not overwirte.

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
        coord_gr.attrs["creation date"]= dt_string
        coord_gr.attrs["measurement_path"] = path
        coord_gr.attrs["probe"] = probe
        coord_gr.attrs.update(measurement_info)

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