import os
import h5py
from pprint import pprint

def build_hdf5(name="default.h5", groups=[], path="."):
    hdf5_path = os.path.join(path, name) 


    # check that you want to overwrite the file if it already exists
    if os.path.exists(hdf5_path):
        print(f"A file with the name {name} already exists at location {path}")
        print("going a head will erase all previous content of such file!")
        answer = input("type \"y\" to overwrite the file: ") 
        if answer != "y":
            return
    


    with h5py.File(hdf5_path, "a") as f:
        # create an empty h5py folder with a group for each probe
        for gr in groups:
            f.create_group(gr)
        

def get_all_h5():
    return [file for file in os.listdir(".") if file[-3:]==".h5"]

def see_groups_and_datasets(filepath, subgroup=None):
    with h5py.File(filepath, "r") as f:
        if subgroup:
            f = f[subgroup]
        group_keys = [key for key, items in f.items() if isinstance(items, h5py.Group)]
        dataset_keys = [key for key, items in f.items() if isinstance(items, h5py.Dataset)]
    return dict(group_keys=group_keys, dataset_keys=dataset_keys)

def add_group(hdf5_path, group, **kargs):
    assert not group_exist(hdf5_path, group), "group already exists"
    # add the group to the library
    with h5py.File(hdf5_path, "a") as f:
        group = f.create_group(group)
        group.attrs.update(**kargs)
    
    print(see_groups_and_datasets(hdf5_path)["group_keys"])

def remove_group(hdf5_path, group):
    assert group_exist(hdf5_path, group), "group does not exist"
    with h5py.File(hdf5_path, "a") as f:
        del f[group] 


    
def group_exist(hdf5_path, group):
    assert(exists(hdf5_path))
    group_keys = see_groups_and_datasets(hdf5_path)["group_keys"]
    return (group in group_keys)
    
def exists(hdf5_path):
    return (hdf5_path in get_all_h5()) 

def explore_library(path, recursive=True):
    def printall(name, obj):
        print("NAME: {:^30}".format(name))
        print("Type: {:^20}".format(f"GROUP - Subgroups: {list(obj.keys())}" if isinstance(obj, h5py.Group) else "DATASET"))
        print("Parent Path: {:<10}".format(obj.parent.name))
        print("Attributes: ")
        pprint(dict(obj.attrs))
        if isinstance(obj, h5py.Dataset):
            print("shape: ", obj.shape, "____ dtype: ", obj.dtype) 
        print("\n\n\n")



    with h5py.File(path, "r") as f:
        if recursive:
            f.visititems(printall)
        else:
            for name, obj in f.items():
                printall(name, obj)

 