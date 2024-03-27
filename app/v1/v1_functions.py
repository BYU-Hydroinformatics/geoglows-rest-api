import datetime
import glob
import os

import netCDF4 as nc
import pandas as pd
from pytz import utc

from .constants import PATH_TO_ERA_INTERIM, PATH_TO_ERA_5, M3_TO_FT3
from .model_utilities import latlon_to_reach, reach_to_region


def handle_parameters(request):
    reach_id = int(request.args.get('reach_id', False))
    region = request.args.get('region', False)
    if not reach_id:
        lat = request.args.get('lat', False)
        lon = request.args.get('lon', False)
        if not lat or not lon:
            raise ValueError('Insufficient information. Provide a reach_id or both a latitude and longitude')
        try:
            reach_id, region, distance = latlon_to_reach(lat, lon)
        except Exception:
            raise ValueError('This lat/lon pair is too far from a delineated stream')
    if not region:
        region = reach_to_region(reach_id)
    units = request.args.get('units', 'metric')
    return_format = request.args.get('return_format', 'csv')
    return reach_id, region, units, return_format


def find_historical_files(region, forcing):
    if forcing == 'era_interim':
        path = glob.glob(os.path.join(PATH_TO_ERA_INTERIM, region, 'Qout*.nc*'))[0]
        template = os.path.join(PATH_TO_ERA_INTERIM, 'erainterim_pandas_dataframe_template.pickle')
    elif forcing in ['era5', 'era-5', 'era_5']:
        path = glob.glob(os.path.join(PATH_TO_ERA_5, region, 'Qout*.nc*'))[0]
        template = os.path.join(PATH_TO_ERA_5, 'era5_pandas_dataframe_template.pickle')
    else:
        raise ValueError("Invalid forcing specified, choose era_interim or era_5")

    return path, template


def get_historical_dataframe(reach_id, region, units, forcing):
    historical_data_file, template = find_historical_files(region, forcing)

    # handle the units
    units_title, units_title_long = get_units_title(units)

    # collect the data in a dataframe
    df = pd.read_pickle(template)
    qout_nc = nc.Dataset(historical_data_file)
    try:
        df['flow'] = qout_nc['Qout'][:, list(qout_nc['rivid'][:]).index(reach_id)]
        qout_nc.close()
    except Exception as e:
        qout_nc.close()
        raise e
    if units == 'english':
        df['flow'] = df['flow'].values * M3_TO_FT3
    df.rename(columns={'flow': f'streamflow_{units_title}^3/s'}, inplace=True)
    return df


def ecmwf_find_most_current_files(path_to_watershed_files, forecast_folder):
    """
    Finds the current output from downscaled ECMWF forecasts
    """
    if forecast_folder == "most_recent":
        if not os.path.exists(path_to_watershed_files):
            return None, None
        directories = \
            sorted(
                [d for d in os.listdir(path_to_watershed_files)
                 if os.path.isdir(os.path.join(path_to_watershed_files, d))],
                reverse=True
            )
    else:
        directories = [forecast_folder]
    for directory in directories:
        try:
            date = datetime.datetime.strptime(directory.split(".")[0], "%Y%m%d")
            time = directory.split(".")[-1]
            path_to_files = os.path.join(path_to_watershed_files, directory)
            if not path_to_files.endswith(".00") and not path_to_files.endswith(".12"):
                time = "00"
                path_to_files += ".00"

            if os.path.exists(path_to_files):
                basin_files = sorted(glob.glob(os.path.join(path_to_files, "Qout*.nc")),
                                     reverse=True)
                if len(basin_files) > 0:
                    seconds = int(int(time) / 100) * 60 * 60
                    forecast_datetime_utc = (date + datetime.timedelta(0, seconds)).replace(tzinfo=utc)
                    return basin_files, forecast_datetime_utc
        except Exception as ex:
            print(ex)
            pass

    # there are no files found
    return None, None


def get_ecmwf_valid_forecast_folder_list(main_watershed_forecast_folder, file_extension):
    """
    Retrieves a list of valid forecast folders for the watershed
    """
    directories = sorted(
        [d for d in os.listdir(main_watershed_forecast_folder)
         if os.path.isdir(os.path.join(main_watershed_forecast_folder, d))],
        reverse=True
    )
    output_directories = []
    directory_count = 0
    for directory in directories:
        date = datetime.datetime.strptime(directory.split(".")[0], "%Y%m%d")
        hour = int(directory.split(".")[-1]) / 100
        path_to_files = os.path.join(main_watershed_forecast_folder, directory)
        if os.path.exists(path_to_files):
            basin_files = glob.glob(os.path.join(path_to_files, "*{0}".format(file_extension)))
            # only add directory to the list if valid
            if len(basin_files) > 0:
                output_directories.append({
                    'id': directory,
                    'text': str(date + datetime.timedelta(hours=int(hour)))
                })
                directory_count += 1
            # limit number of directories
            if directory_count > 64:
                break
    return output_directories


def get_units_title(unit_type):
    """
    Get the title for units
    """
    if unit_type == 'metric':
        return 'm', 'meters'
    elif unit_type == 'english':
        return 'ft', 'feet'
