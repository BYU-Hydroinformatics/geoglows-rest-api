import os
from datetime import datetime as dt

import numpy as np
import pandas as pd
import xarray
from flask import jsonify, make_response

from .constants import PATH_TO_FORECASTS, PATH_TO_FORECAST_RECORDS, M3_TO_FT3
from .v1_functions import get_units_title, ecmwf_find_most_current_files, handle_parameters

__all__ = ['forecast_stats', 'forecast_ensembles', 'forecast_warnings', 'forecast_records', 'available_dates']


def forecast_stats(request):
    """
    Controller that will retrieve forecast statistics data in different formats
    """
    # handle the parameters from the user
    try:
        reach_id, region, units, return_format = handle_parameters(request)
    except Exception as e:
        raise e
    forecast_folder = request.args.get('date', 'most_recent')

    # handle the units
    units_title, units_title_long = get_units_title(units)

    # find/check current output datasets
    path_to_output_files = os.path.join(PATH_TO_FORECASTS, region)
    forecast_nc_list, start_date = ecmwf_find_most_current_files(path_to_output_files, forecast_folder)
    forecast_nc_list = sorted(forecast_nc_list)
    if not forecast_nc_list or not start_date:
        raise ValueError(f'ECMWF forecast for region "{region}" and date "{start_date}" not found')

    try:
        # combine 52 ensembles
        qout_datasets = []
        ensemble_index_list = []
        for forecast_nc in forecast_nc_list:
            ensemble_index_list.append(int(os.path.basename(forecast_nc)[:-3].split("_")[-1]))
            qout_datasets.append(xarray.open_dataset(forecast_nc).sel(rivid=reach_id).Qout)
        merged_ds = xarray.concat(qout_datasets, pd.Index(ensemble_index_list, name='ensemble'))

        # get an array of all the ensembles, delete the high res before doing averages
        merged_array = merged_ds.data
        merged_array = np.delete(merged_array, list(merged_ds.ensemble.data).index(52), axis=0)
    except:
        raise ValueError('Error while reading data from the netCDF files')

    # replace any values that went negative because of the muskingham routing
    merged_array[merged_array <= 0] = 0

    # load all the series into a dataframe
    df = pd.DataFrame({
        f'flow_max_{units_title}^3/s': np.amax(merged_array, axis=0),
        f'flow_75%_{units_title}^3/s': np.percentile(merged_array, 75, axis=0),
        f'flow_avg_{units_title}^3/s': np.mean(merged_array, axis=0),
        f'flow_25%_{units_title}^3/s': np.percentile(merged_array, 25, axis=0),
        f'flow_min_{units_title}^3/s': np.min(merged_array, axis=0),
        f'high_res_{units_title}^3/s': merged_ds.sel(ensemble=52).data
    }, index=merged_ds.time.data)
    df.index = df.index.strftime('%Y-%m-%dT%H:%M:%SZ')
    df.index.name = 'datetime'

    # handle units conversion
    if units_title == 'ft':
        for column in df.columns:
            df[column] *= M3_TO_FT3

    if return_format == 'csv':
        response = make_response(df.to_csv())
        response.headers['content-type'] = 'text/csv'
        response.headers['Content-Disposition'] = \
            f'attachment; filename=forecasted_streamflow_{region}_{reach_id}_{units_title}^3/s.csv'
        return response

    # split the df so that we can use dropna to lists of dates and values without na entries
    high_res_data = df[f'high_res_{units_title}^3/s'].dropna()
    del df[f'high_res_{units_title}^3/s']
    df.dropna(inplace=True)

    # create a dictionary with the metadata and series of values
    context = {
        'region': region,
        'comid': reach_id,
        'gendate': dt.utcnow().isoformat() + 'Z',
        'startdate': df.index[0],
        'enddate': df.index[-1],
        'units': {
            'name': 'Streamflow',
            'short': f'{units_title}^3/s',
            'long': f'Cubic {units_title_long} per Second',
        },
        'time_series': {
            'datetime': df.index.tolist(),
            'datetime_high_res': high_res_data.index.tolist(),
            'high_res': high_res_data.to_list(),
        }
    }
    context['time_series'].update(df.to_dict(orient='list'))

    if return_format == "json":
        return jsonify(context)

    else:
        raise ValueError('Invalid return_format')


def forecast_ensembles(request):
    """
    Controller that will retrieve forecast ensemble data in different formats
    """
    # handle the parameters from the user
    try:
        reach_id, region, units, return_format = handle_parameters(request)
    except Exception as e:
        raise ValueError(e)
    ensemble = request.args.get('ensemble', 'all')
    forecast_folder = request.args.get('date', 'most_recent')

    # handle the units
    units_title, units_title_long = get_units_title(units)

    # find/check current output datasets
    path_to_output_files = os.path.join(PATH_TO_FORECASTS, region)
    forecast_nc_list, start_date = ecmwf_find_most_current_files(path_to_output_files, forecast_folder)
    forecast_nc_list = sorted(forecast_nc_list)
    if not forecast_nc_list or not start_date:
        raise ValueError(f'ECMWF forecast for region "{region}" and date "{start_date}" not found')

    try:
        # combine 52 ensembles with xarray
        qout_datasets = []
        ensemble_index_list = []
        for forecast_nc in forecast_nc_list:
            ensemble_index_list.append(int(os.path.basename(forecast_nc)[:-3].split("_")[-1]))
            qout_datasets.append(xarray.open_dataset(forecast_nc).sel(rivid=reach_id).Qout)
        merged_ds = xarray.concat(qout_datasets, pd.Index(ensemble_index_list, name='ensemble'))
    except:
        raise ValueError('Error while reading data from the netCDF files')

    # make a list column names (with zero padded numbers) for the pandas DataFrame
    ensemble_column_names = []
    for i in ensemble_index_list:
        ensemble_column_names.append(f'ensemble_{i:02}_{units_title}^3/s')

    # make the data into a pandas dataframe
    df = pd.DataFrame(data=np.transpose(merged_ds.data), columns=ensemble_column_names, index=merged_ds.time.data)
    df.index = df.index.strftime('%Y-%m-%dT%H:%M:%SZ')
    df.index.name = 'datetime'

    # handle units conversion
    if units_title == 'ft':
        for column in df.columns:
            df[column] *= M3_TO_FT3

    # filtering which ensembles you want to get out of the dataframe of them all
    if ensemble != 'all':
        requested_ensembles = []
        for ens in ensemble.split(','):
            # if there was a range requested with a '-', generate a list of numbers between the 2
            if '-' in ens:
                start, end = ens.split('-')
                for i in range(int(start), int(end) + 1):
                    requested_ensembles.append(f'ensemble_{int(i):02}_{units_title}^3/s')
            else:
                requested_ensembles.append(f'ensemble_{int(ens):02}_{units_title}^3/s')
        # make a list of columns to remove from the dataframe deleting the requested ens from all ens columns
        for ens in requested_ensembles:
            if ens in ensemble_column_names:
                ensemble_column_names.remove(ens)
        # delete the dataframe columns we aren't interested
        for ens in ensemble_column_names:
            del df[ens]

    if return_format == 'csv':
        response = make_response(df.to_csv())
        response.headers['content-type'] = 'text/csv'
        response.headers['Content-Disposition'] = \
            f'attachment; filename=forecasted_ensembles_{region}_{reach_id}_{units_title}^3/s.csv'
        return response

    # for any column in the dataframe (e.g. each ensemble)
    ensemble_ts_dict = {
        'datetime': df[f'ensemble_01_{units_title}^3/s'].dropna(inplace=False).index.tolist(),
        'datetime_high_res': df[f'ensemble_52_{units_title}^3/s'].dropna(inplace=False).index.tolist(),
    }
    for column in df.columns:
        ensemble_ts_dict[column] = df[column].dropna(inplace=False).tolist()

    context = {
        'region': region,
        'comid': reach_id,
        'startdate': df.index[0],
        'enddate': df.index[-1],
        'gendate': dt.utcnow().isoformat() + 'Z',
        'time_series': ensemble_ts_dict,
        'units': {
            'name': 'Streamflow',
            'short': f'{units_title}3/s',
            'long': f'Cubic {units_title_long} per Second'
        }
    }

    if return_format == 'json':
        return jsonify(context)

    else:
        raise ValueError('Invalid return_format')


def forecast_warnings(request):
    region = request.args.get('region', 'all')
    forecast_date = request.args.get('forecast_date', 'most_recent')
    return_format = request.args.get('return_format', 'csv')

    warnings = None

    if region == 'all':
        for reg in os.listdir(PATH_TO_FORECASTS):
            # find/check current output datasets
            path_to_region_forecasts = os.path.join(PATH_TO_FORECASTS, reg)
            if not os.path.isdir(path_to_region_forecasts):
                continue
            if forecast_date == 'most_recent':
                date_folders = sorted([d for d in os.listdir(path_to_region_forecasts)
                                       if os.path.isdir(os.path.join(path_to_region_forecasts, d))],
                                      reverse=True)
                folder = os.path.join(path_to_region_forecasts, date_folders[0])
            else:
                folder = os.path.join(path_to_region_forecasts, forecast_date)
                if not os.path.isdir(folder):
                    raise ValueError(f'Forecast date {forecast_date} was not found')
            # locate the forecast warning csv
            summary_file = os.path.join(folder, 'forecasted_return_periods_summary.csv')
            if not os.path.isfile(summary_file):
                continue
            if warnings is None:
                warnings = pd.read_csv(summary_file)
                continue
            warnings = pd.concat([warnings, pd.read_csv(summary_file)], axis=0)
    else:
        path_to_region_forecasts = os.path.join(PATH_TO_FORECASTS, region)
        if not os.path.isdir(path_to_region_forecasts):
            raise ValueError(f'No region data found for region "{region}"')
        if forecast_date == 'most_recent':
            date_folders = sorted([d for d in os.listdir(path_to_region_forecasts)
                                   if os.path.isdir(os.path.join(path_to_region_forecasts, d))],
                                  reverse=True)
            folder = os.path.join(path_to_region_forecasts, date_folders[0])
        else:
            folder = os.path.join(path_to_region_forecasts, forecast_date)
            if not os.path.isdir(folder):
                raise ValueError(f'Forecast date {forecast_date} was not found. Use YYYYMMDD format.')
        # locate the forecast warning csv
        summary_file = os.path.join(folder, 'forecasted_return_periods_summary.csv')
        if not os.path.isfile(summary_file):
            raise ValueError(f'ForecastWarnings tables not found for region: "{region}"')
        warnings = pd.read_csv(summary_file)

    if warnings is None:
        raise ValueError('Unable to find any warnings csv files for any region')

    if return_format == 'csv':
        response = make_response(warnings.to_csv(index=False))
        response.headers['content-type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=ForecastWarnings-{region}.csv'
        return response

    elif return_format == 'json':
        return jsonify(warnings.to_dict(orient='index'))
    else:
        raise ValueError('Invalid return_format')


def forecast_records(request):
    # handle the parameters from the user
    try:
        reach_id, region, units, return_format = handle_parameters(request)
    except Exception as e:
        raise ValueError(e)
    year = dt.utcnow().year
    start_date = request.args.get('start_date', dt(year=year, month=1, day=1).strftime('%Y%m%d'))
    end_date = request.args.get('end_date', dt(year=year, month=12, day=31).strftime('%Y%m%d'))

    try:
        start_date = dt.strptime(start_date, '%Y%m%d')
        end_date = dt.strptime(end_date, '%Y%m%d')
    except:
        raise ValueError(f'Unrecognized start_date "{start_date}" or end_date "{end_date}". Use YYYYMMDD format')

    # handle the units
    units_title, units_title_long = get_units_title(units)

    # open and read the forecast record netcdf
    record_path = os.path.join(PATH_TO_FORECAST_RECORDS, region, f'forecast_record-{year}-{region}.nc')
    forecast_record = xarray.open_dataset(record_path)
    times = pd.to_datetime(pd.Series(forecast_record['time'].data, name='datetime'), unit='s', origin='unix')
    record_flows = forecast_record.sel(rivid=reach_id)['Qout']
    forecast_record.close()

    # create a dataframe and filter by date
    df = times.to_frame().join(pd.Series(record_flows, name=f'streamflow_{units_title}^3/s'))
    df = df[df['datetime'].between(start_date, end_date)]
    df.index = df['datetime']
    del df['datetime']
    df.index = df.index.strftime('%Y-%m-%dT%H:%M:%SZ')
    df.index.name = 'datetime'
    df[df[f'streamflow_{units_title}^3/s'] > 1000000000] = np.nan
    df.dropna(inplace=True)
    if units == 'english':
        df[f'streamflow_{units_title}^3/s'] *= M3_TO_FT3

    # create the http response
    if return_format == 'csv':
        response = make_response(df.to_csv())
        response.headers['content-type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=forecast_record_{reach_id}.csv'
        return response

    elif return_format == 'json':
        return {
            'region': region,
            'comid': reach_id,
            'gendate': dt.utcnow().isoformat() + 'Z',
            'startdate': df.index[0],
            'enddate': df.index[-1],
            'units': {
                'name': 'Streamflow',
                'short': f'{units_title}^3/s',
                'long': f'Cubic {units_title_long} per Second',
            },
            'time_series': {
                'datetime': df.index.tolist(),
                'flow': df[f'streamflow_{units_title}^3/s'].tolist(),
            }
        }

    else:
        raise ValueError(f'Invalid return_format "{return_format}"')


def available_dates(request):
    """
    Controller that returns available dates.
    """
    region = request.args.get('region', None)
    if region is None:
        raise ValueError('region is a required parameter')

    region_path = os.path.join(PATH_TO_FORECASTS, region)

    if not os.path.exists(region_path):
        raise ValueError(f'Region "{region}" does not exist.')

    dates = [d for d in os.listdir(region_path) if d.split('.')[0].isdigit()]

    if len(dates) > 0:
        return jsonify({"available_dates": dates})
    else:
        return jsonify({"message": "No dates available."}), 204
