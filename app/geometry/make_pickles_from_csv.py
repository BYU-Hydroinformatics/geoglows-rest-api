import glob
import json
import os
import pickle

### to make the boundaries pickle
# 1 use arcgis/qgis/geopandas etc to make a geojson of the boundaries of the region. ideally, a simplified so there are fewer points
#   save them as region_name-geoglows.geojson all in the same directory

# 2 use this script to glob a list of them all
gjs = glob.glob('/path/to/geojsons/*.geojson')

# 3 then load them all into a single dictionary
boundaries_dictionary = {}
for gj in gjs:
    with open(gj, 'r') as f:
        boundaries_dictionary[os.path.splitext(os.path.basename(gj))[0]] = json.load(f)

# 4 dump it to pickle with protocol 4 (not 5 even though its better because we want maximum compatibility with python verisons)
picklepath = '/path/to/geometry/directory/in/api/code/direcotry/boundaries.pickle'
with open(picklepath, 'wb') as f:
    pickle.dump(json.dumps(boundaries_dictionary), f, protocol=4)


### to make the lat lon z csv files into pickle
import pandas as pd

# list all the csv files - where * indicates the region name
csv_files = glob.glob('/path/to/files/*/comid_lat_lon_z.pickle')
path_to_geometry_foler = ''
for csv_file in csv_files:
    df = pd.read_csv('', header=0, index_col=0)
    pickle_save_path = os.path.join(path_to_geometry_foler, f'{os.path.dirname(csv_file)}-comid_lat_lon_z.pickle')
    df.to_pickle(pickle_save_path, protocol=4)
