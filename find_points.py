from my_packages.utils import HandlePaths, probes_walk

probe_paths = HandlePaths()(probes_walk)
print(probe_paths)
