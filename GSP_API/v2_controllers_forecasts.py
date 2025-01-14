import datetime
import json
import os

import numpy as np
import pandas as pd
import xarray
from flask import jsonify

import v2_utilities
from constants import PATH_TO_FORECAST_RECORDS, M3_TO_FT3
from model_utilities import reach_to_region
from v2_controllers_historical import historical_averages

__all__ = ['hydroviewer', 'forecast', 'forecast_stats', 'forecast_ensembles', 'forecast_records', 'forecast_anomalies',
           'forecast_warnings', 'forecast_dates']


def hydroviewer(reach_id: int, start_date: str, date: str, units: str, return_format: str) -> jsonify:
    if date == 'latest':
        date = v2_utilities.get_most_recent_date()
    stats_df = forecast_stats(reach_id, date, units, "df")
    stats_df = stats_df.replace(np.nan, '')
    records_df = forecast_records(reach_id, start_date, date, units, "df")

    if return_format == 'csv':
        return v2_utilities.dataframe_to_csv_flask_response(pd.concat([records_df, stats_df], join='outer'),
                                                            f'hydroviewer_data_{reach_id}')
    if return_format == 'json':
        records_df.columns = [f'{records_df.columns[0]}_rec', ]
        rp_df = v2_utilities.get_return_periods_dataframe(reach_id, units)

        # add the columns from the dataframe
        json_template = v2_utilities.new_json_template(reach_id, units, start_date=records_df.index[0],
                                                       end_date=stats_df.index[-1])
        json_template['datetime_stats'] = stats_df.index.tolist()
        json_template['datetime_rec'] = records_df.index.tolist()
        json_template.update(stats_df.to_dict(orient='list'))
        json_template.update(records_df.to_dict(orient='list'))
        json_template.update(json.loads(rp_df.to_json(orient='records'))[0])
        json_template['metadata']['series'] = ['datetime_stats', 'datetime_rec', ] + stats_df.columns.tolist() + \
                                              records_df.columns.tolist() + list(rp_df.keys())
        return jsonify(json_template), 200


def forecast(reach_id: int, date: str, units: str, return_format: str) -> pd.DataFrame:
    forecast_xarray_dataset = v2_utilities.get_forecast_dataset(reach_id, date)

    # get an array of all the ensembles, delete the high res before doing averages
    merged_array = forecast_xarray_dataset.data
    merged_array = np.delete(merged_array, list(forecast_xarray_dataset.ensemble.data).index(52), axis=0)

    # replace any values that went negative because of the routing
    merged_array[merged_array <= 0] = 0

    # load all the series into a dataframe
    df = pd.DataFrame({
        f'flow_avg_{units}': np.mean(merged_array, axis=0),
    }, index=forecast_xarray_dataset.time.data)
    df.dropna(inplace=True)
    df.index = df.index.strftime('%Y-%m-%dT%X+00:00')
    df.index.name = 'datetime'
    df = df.astype(np.float64).round(v2_utilities.NUM_DECIMALS)

    # handle units conversion
    if units == 'cfs':
        for column in df.columns:
            df[column] *= M3_TO_FT3

    if return_format == 'csv':
        return v2_utilities.dataframe_to_csv_flask_response(df, f'forecast_{reach_id}_{units}')
    if return_format == 'json':
        return v2_utilities.dataframe_to_jsonify_response(df=df, reach_id=reach_id, units=units)
    return df


def forecast_stats(reach_id: int, date: str, units: str, return_format: str) -> pd.DataFrame:
    forecast_xarray_dataset = v2_utilities.get_forecast_dataset(reach_id, date)

    # get an array of all the ensembles, delete the high res before doing averages
    merged_array = forecast_xarray_dataset.data
    merged_array = np.delete(merged_array, list(forecast_xarray_dataset.ensemble.data).index(52), axis=0)

    # replace any values that went negative because of the routing
    merged_array[merged_array <= 0] = 0

    # load all the series into a dataframe
    df = pd.DataFrame({
        f'flow_max_{units}': np.amax(merged_array, axis=0),
        f'flow_75p_{units}': np.percentile(merged_array, 75, axis=0),
        f'flow_avg_{units}': np.mean(merged_array, axis=0),
        f'flow_med_{units}': np.median(merged_array, axis=0),
        f'flow_25p_{units}': np.percentile(merged_array, 25, axis=0),
        f'flow_min_{units}': np.min(merged_array, axis=0),
        f'high_res_{units}': forecast_xarray_dataset.sel(ensemble=52).data,
    }, index=forecast_xarray_dataset.time.data)
    df.index = df.index.strftime('%Y-%m-%dT%X+00:00')
    df.index.name = 'datetime'
    df = df.astype(np.float64).round(v2_utilities.NUM_DECIMALS)

    # handle units conversion
    if units == 'cfs':
        for column in df.columns:
            df[column] *= M3_TO_FT3

    if return_format == 'csv':
        return v2_utilities.dataframe_to_csv_flask_response(df, f'forecast_stats_{reach_id}_{units}')
    if return_format == 'json':
        return v2_utilities.dataframe_to_jsonify_response(df=df, reach_id=reach_id, units=units)
    if return_format == "df":
        return df


def forecast_ensembles(reach_id: int, date: datetime.datetime, units: str, return_format: str, ensemble: str):
    forecast_xarray_dataset = v2_utilities.get_forecast_dataset(reach_id, date)

    # make a list column names (with zero padded numbers) for the pandas DataFrame
    ensemble_column_names = []
    for i in range(1, 53):
        ensemble_column_names.append(f'ensemble_{i:02}_{units}')

    # make the data into a pandas dataframe
    df = pd.DataFrame(data=np.transpose(forecast_xarray_dataset.data).round(v2_utilities.NUM_DECIMALS),
                      columns=ensemble_column_names,
                      index=forecast_xarray_dataset.time.data)
    df.index = df.index.strftime('%Y-%m-%dT%X+00:00')
    df.index.name = 'datetime'
    df = df.astype(np.float64).round(v2_utilities.NUM_DECIMALS)

    # handle units conversion
    if units == 'cfs':
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
                    requested_ensembles.append(f'ensemble_{int(i):02}_{units}')
            else:
                requested_ensembles.append(f'ensemble_{int(ens):02}_{units}')
        # make a list of columns to remove from the dataframe deleting the requested ens from all ens columns
        for ens in requested_ensembles:
            if ens in ensemble_column_names:
                ensemble_column_names.remove(ens)
        # delete the dataframe columns we aren't interested
        for ens in ensemble_column_names:
            del df[ens]

    if return_format == 'csv':
        return v2_utilities.dataframe_to_csv_flask_response(df, f'forecast_ensembles_{reach_id}_{units}')
    if return_format == 'json':
        return v2_utilities.dataframe_to_jsonify_response(df=df, reach_id=reach_id, units=units)
    if return_format == "df":
        return df


def forecast_records(reach_id: int, start_date: str, end_date: str, units: str, return_format: str) -> pd.DataFrame:
    region = reach_to_region(reach_id)
    try:
        start_date = datetime.datetime.strptime(start_date, '%Y%m%d')
        end_date = datetime.datetime.strptime(end_date, '%Y%m%d')
    except Exception:
        raise ValueError(f'Unrecognized start_date "{start_date}" or end_date "{end_date}". Use YYYYMMDD format')

    # open and read the forecast record netcdf
    record_path = os.path.join(PATH_TO_FORECAST_RECORDS, region,
                               # f'forecast_record-{datetime.datetime.utcnow().year}-{region}.nc')
                               f'forecast_record-{2021}-{region}.nc')
    forecast_record = xarray.open_dataset(record_path)
    times = pd.to_datetime(pd.Series(forecast_record['time'].data, name='datetime'), unit='s', origin='unix')
    record_flows = forecast_record.sel(rivid=reach_id)['Qout']
    forecast_record.close()

    # create a dataframe and filter by date
    df = times.to_frame().join(pd.Series(record_flows, name=f'flow_avg_{units}').round(v2_utilities.NUM_DECIMALS))
    df = df[df['datetime'].between(start_date, end_date)]
    df = df.set_index('datetime')
    df.index = df.index.strftime('%Y-%m-%dT%H:%M:%SZ')
    df.index.name = 'datetime'
    df.dropna(inplace=True)
    df = df.astype(np.float64).round(v2_utilities.NUM_DECIMALS)

    if units == 'cfs':
        df[f'flow_avg_{units}'] *= M3_TO_FT3

    # create the http response
    if return_format == 'csv':
        return v2_utilities.dataframe_to_csv_flask_response(df, f'forecast_records_{reach_id}')
    if return_format == 'json':
        return v2_utilities.dataframe_to_jsonify_response(df=df, reach_id=reach_id, units=units)
    if return_format == "df":
        return df


def forecast_anomalies(reach_id: int, date: datetime.datetime, units: str, return_format: str) -> pd.DataFrame:
    df = forecast(reach_id, date, units, "df")
    df = df.dropna()
    avg_df = historical_averages(reach_id, units, 'daily', 'df')

    df['datetime'] = df.index
    df.index = pd.to_datetime(df.index).strftime("%m/%d")
    df = df.join(avg_df, how="inner")
    df[f'anomaly_{units}'] = df[f'flow_avg_{units}'] - df[f'flow_{units}']
    df.index = df['datetime']
    df = df.rename(columns={f'flow_{units}': f'daily_avg_{units}'})
    del df['datetime']
    df = df.astype(np.float64).round(v2_utilities.NUM_DECIMALS)

    # create the response
    if return_format == 'csv':
        return v2_utilities.dataframe_to_csv_flask_response(df, f'forecast_anomalies_{reach_id}')
    if return_format == 'json':
        return v2_utilities.dataframe_to_jsonify_response(df=df, reach_id=reach_id, units=units)
    return df


def forecast_warnings(date: str, return_format: str):
    warnings_df = v2_utilities.find_forecast_warnings(date)
    if return_format == 'csv':
        return v2_utilities.dataframe_to_csv_flask_response(warnings_df, f'forecast_warnings_{date}')
    if return_format == 'json':
        return jsonify(warnings_df.to_dict(orient='index'))
    return warnings_df


def forecast_dates():
    return v2_utilities.find_available_dates()
