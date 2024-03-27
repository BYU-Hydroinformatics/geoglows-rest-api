import json
import pickle
from collections import OrderedDict

import pandas as pd
from shapely.geometry import Point, MultiPoint, shape
from shapely.ops import nearest_points


def reach_to_region(reach_id=None):
    # Indonesia 1M's
    # ------australia 2M (currently 200k's)
    # Japan 3M's
    # East Asia 4M's
    # South Asia 5M's
    # ------middle_east 6M (currently 600k's)
    # Africa 7M's
    # Central Asia 8M's
    # South America 9M's
    # West Asia 10M's
    # -------central_america 11M (currently 900k's)
    # Europe 12M's
    # North America 13M's
    print(reach_id)
    lookup = OrderedDict([
        ('australia-geoglows', 300000),
        ('middle_east-geoglows', 700000),
        ('central_america-geoglows', 1000000),
        ('islands-geoglows', 2000000),
        ('japan-geoglows', 4000000),
        ('east_asia-geoglows', 5000000),
        ('south_asia-geoglows', 6000000),
        ('africa-geoglows', 8000000),
        ('central_asia-geoglows', 9000000),
        ('south_america-geoglows', 10000000),
        ('west_asia-geoglows', 11000000),
        ('europe-geoglows', 13000000),
        ('north_america-geoglows', 14000000)
    ])

    for region, threshold in lookup.items():
        if reach_id < threshold:
            if region == 'error':
                raise ValueError(f'Unable to determine a region paired with reach_id "{reach_id}"')
            print("FINISH")
            return region
    raise ValueError(f'Unable to determine a region paired with reach_id "{reach_id}"')


def latlon_to_reach(lat: float, lon: float) -> tuple:
    if lat is None or lon is None:
        raise ValueError('please provide a "lat" and "lon" argument')
    # determine the region that the point is in
    region = latlon_to_region(lat, lon)

    # switch the point because the csv's are lat/lon, backwards from what shapely expects (lon then lat)
    point = Point(float(lat), float(lon))

    # open the region csv
    df = pd.read_pickle(f'/app/GSP_API/geometry/{region}-comid_lat_lon_z.pickle')
    points_df = df.loc[:, "Lat":"Lon"].apply(Point, axis=1)

    # determine which point is closest
    multi_pt = MultiPoint(points_df.tolist())
    nearest_pt = nearest_points(point, multi_pt)
    reach_id = int(points_df[points_df == nearest_pt[1]].index[0])
    distance = nearest_pt[0].distance(nearest_pt[1])

    # if the nearest stream if more than .1 degrees away, you probably didn't find the right stream
    if distance > 0.11:
        raise ValueError('This lat/lon pair is too far from a delineated stream. Try again or use the web interface.')
    else:
        return reach_id, region, distance


def latlon_to_region(lat, lon):
    # create a shapely point for the querying
    point = Point(float(lon), float(lat))

    # read the boundaries pickle
    bounds_pickle = '/app/GSP_API/geometry/boundaries.pickle'
    with open(bounds_pickle, 'rb') as f:
        region_bounds = json.loads(pickle.load(f))
    for region in region_bounds:
        for polygon in region_bounds[region]['features']:
            if shape(polygon['geometry']).contains(point):
                return f'{region}-geoglows'
    # if there weren't any regions, return that there was an error
    raise ValueError('This lat/lon point is not within any of the supported delineation regions.')
