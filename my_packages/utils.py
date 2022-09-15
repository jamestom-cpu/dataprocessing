probes = ["xfb31", "XFE_04s", "XFR31"]
probes_walk = {
    probes[0]:dict(
        r18 = {}
    ),
    probes[1]:dict(
        r18 = {},
        r18_o = {}
    ),
    probes[2]:{

        "r18_o":{
            "along_x":{},
            "along_y":{}
        }
                
    }
}

class HandlePaths():
    def __init__(self, base_path="/NAS"):
        self.paths = []
        self.base_path = base_path
      
    def get_keys_(self, obj):
        if type(obj) is dict:
            return obj.keys()

    def get_paths(self, walk, path):
        keys = self.get_keys_(walk)
        
        if keys:
            for key in keys:
                new_path = path+f"/{key}"
                self.get_paths(walk[key], new_path)
        else:
            self.paths.append(path)
    
    def __call__(self, walk, path=None):
        if not path:
            path = self.base_path
        self.paths = []
        self.get_paths(walk, path)
        return self.paths




