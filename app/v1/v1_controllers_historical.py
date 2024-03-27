import datetime
import glob
import json
import os

import hydrostats.data as hd
import pandas as pd
import xarray
from flask import jsonify, make_response

from .constants import PATH_TO_ERA_5, PATH_TO_ERA_INTERIM, M3_TO_FT3
from .v1_functions import handle_parameters, get_units_title, get_historical_dataframe

__all__ = ['historical', 'historical_averages', 'return_periods']


def historical(request):
    """
    Controller for retrieving simulated historic data
    """
    # handle the parameters from the user
    try:
        reach_id, region, units, return_format = handle_parameters(request)
        units_title, units_title_long = get_units_title(units)
        forcing = request.args.get('forcing', 'era_5')
        hist_df = get_historical_dataframe(reach_id, region, units, forcing)
    except Exception as e:
        raise e

    # if csv, return the dataframe as csv
    if return_format == 'csv':
        response = make_response(hist_df.to_csv())
        response.headers['content-type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=historic_streamflow_{forcing}_{reach_id}.csv'
        return response

    # if you wanted json out, create and return json
    #  era_interim or era_5
    if return_format == "json":
        return {
            'region': region,
            'simulation_forcing': forcing,
            'forcing_fullname': forcing.replace('era_', 'ERA ').title(),
            'comid': reach_id,
            'gendate': datetime.datetime.utcnow().isoformat() + 'Z',
            'startdate': hist_df.index[0],
            'enddate': hist_df.index[-1],
            'time_series': {
                'datetime': hist_df.index.tolist(),
                'flow': hist_df[f'streamflow_{units_title}^3/s'].tolist(),
            },
            'units': {
                'name': 'Streamflow',
                'short': f'{units_title}3/s',
                'long': f'Cubic {units_title_long} per Second'
            }
        }

    else:
        return jsonify({"error": "Invalid return_format."}), 422


def historical_averages(request, average_type):
    """
    Controller for retrieving averages
    """
    # handle the parameters from the user
    try:
        reach_id, region, units, return_format = handle_parameters(request)
        units_title, units_title_long = get_units_title(units)
        forcing = request.args.get('forcing', 'era_5')
        hist_df = get_historical_dataframe(reach_id, region, units, forcing)
    except Exception as e:
        raise e

    hist_df.index = pd.to_datetime(hist_df.index)
    if average_type == 'daily':
        hist_df = hd.daily_average(hist_df, rolling=True)
    else:
        hist_df = hd.monthly_average(hist_df)
    hist_df.index.name = 'datetime'

    if return_format == 'csv':
        response = make_response(hist_df.to_csv())
        response.headers['content-type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=seasonal_average_{forcing}_{reach_id}.csv'
        return response

    if return_format == "json":
        return jsonify({
            'region': region,
            'simulation_forcing': forcing,
            'forcing_fullname': forcing.replace('era_', 'ERA ').title(),
            'comid': reach_id,
            'gendate': datetime.datetime.utcnow().isoformat() + 'Z',
            'time_series': {
                'datetime': hist_df.index.tolist(),
                'flow': hist_df[f'streamflow_{units_title}^3/s'].tolist(),
            },
            'units': {
                'name': 'Streamflow',
                'short': f'{units_title}3/s',
                'long': f'Cubic {units_title_long} per Second'
            }
        })

    else:
        raise ValueError(f'Invalid return_format: {return_format}')


def return_periods(request):
    """
    Controller for retrieving seasonal averages
    """
    # handle the parameters from the user
    try:
        reach_id, region, units, return_format = handle_parameters(request)
    except Exception as e:
        raise e
    forcing = request.args.get('forcing', 'era_5')

    if forcing == 'era_interim':
        forcing_fullname = 'ERA Interim'
        historical_data_file = glob.glob(os.path.join(PATH_TO_ERA_INTERIM, region, '*return_periods*.nc*'))[0]
        startdate = '1980-01-01T00:00:00Z'
        enddate = '2014-12-31T00:00:00Z'
    elif forcing == 'era_5':
        forcing_fullname = 'ERA 5'
        historical_data_file = glob.glob(os.path.join(PATH_TO_ERA_5, region, '*return_periods*.nc*'))[0]
        startdate = '1979-01-01T00:00:00Z'
        enddate = '2018-12-31T00:00:00Z'
    else:
        return {"error": "Invalid forcing specified, choose era_interim or era_5"}, 422

    # handle the units
    units_title, units_title_long = get_units_title(units)

    # collect the data in a dataframe
    qout_nc = xarray.open_dataset(historical_data_file)
    qout_data = qout_nc.to_dataframe()
    try:
        del qout_data['lon'], qout_data['lat']
    except Exception:
        pass
    qout_data = qout_data[qout_data.index == reach_id]
    if units == 'english':
        for column in qout_data:
            qout_data[column] *= M3_TO_FT3

    # if csv, return the dataframe as csv
    if return_format == 'csv':
        response = make_response(qout_data.to_csv())
        response.headers['content-type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=return_periods_{forcing}_{reach_id}.csv'
        return response

    # create a json of the data
    json_output = {
        'return_periods': json.loads(qout_data.to_json(orient='records'))[0],
        'region': region,
        'comid': reach_id,
        'simulation_forcing': forcing,
        'forcing_fullname': forcing_fullname,
        'gendate': datetime.datetime.utcnow().isoformat() + 'Z',
        'startdate': startdate,
        'enddate': enddate,
        'units': {
            'name': 'Streamflow',
            'short': f'{units_title}3/s',
            'long': f'Cubic {units_title_long} per Second'
        }
    }

    # if you wanted json out, return json
    if return_format == "json":
        return jsonify(json_output)

    else:
        return jsonify({"error": "Invalid return_format."}), 422
