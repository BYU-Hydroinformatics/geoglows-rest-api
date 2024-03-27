import os
from glob import glob

import natsort
import pandas as pd
import xarray as xr
import s3fs

from .constants import PATH_TO_FORECASTS, M3_TO_FT3, ODP_S3_BUCKET_REGION, ODP_RETROSPECTIVE_S3_BUCKET_URI

__all__ = [
    'get_forecast_dataset',
    'get_return_periods_dataframe',
    'find_available_dates',
    'get_forecast_warnings_dataframe',
    'latlon_to_reach',
]


def get_forecast_dataset(reach_id: int, date: str) -> xr.Dataset:
    """
    Opens the forecast dataset for a given date, selects the reach_id and Qout variable
    """
    if date == "latest":
        date = find_available_dates()[0]

    if len(date) == 8:
        date = f"{date}00"

    forecast_file = os.path.join(PATH_TO_FORECASTS, f'Qout_{date}.zarr')

    if not os.path.exists(forecast_file):
        raise ValueError(f'Data not found for date {date}. Use YYYYMMDD format and the AvailableDates endpoint.')

    try:
        forecast_dataset = xr.open_zarr(forecast_file)
    except Exception as e:
        print(e)
        raise ValueError('Error while reading data from the zarr files')
    try:
        return forecast_dataset.sel(rivid=reach_id).Qout
    except Exception as e:
        print(e)
        raise ValueError(f'Unable to get data for reach_id {reach_id} in the forecast dataset')


def get_return_periods_dataframe(reach_id: int, units: str) -> pd.DataFrame:
    s3 = s3fs.S3FileSystem(anon=True, client_kwargs=dict(region_name=ODP_S3_BUCKET_REGION))
    s3store = s3fs.S3Map(root=f'{ODP_RETROSPECTIVE_S3_BUCKET_URI}/return-periods.zarr', s3=s3, check=False)
    df = xr.open_zarr(s3store).sel(rivid=reach_id).to_dataframe()
    if units == 'cfs':
        for column in df:
            df[column] *= M3_TO_FT3
    return df


def find_available_dates() -> list:
    forecast_zarrs = glob(os.path.join(PATH_TO_FORECASTS, "Qout*.zarr"))
    forecast_zarrs = natsort.natsorted(forecast_zarrs, reverse=True)
    dates = [os.path.basename(d).replace('.zarr', '').split('_')[1] for d in forecast_zarrs]
    return dates


def get_forecast_warnings_dataframe(date) -> pd.DataFrame:
    # todo
    # if date == 'latest':
    #     date = find_available_dates()[-1]

    # find the warnings combined file using the date

    # check that it exists and raise an error if not

    # read and return the dataframe with pandas

    # return

    raise NotImplementedError("This function is not yet implemented")


def latlon_to_reach(lat: float, lon: float) -> list:
    """
    Finds the reach ID nearest to a given lat/lon
    Uses the ModelMasterTable to find the locations
    """
    df = pd.read_parquet('/mnt/configs/geoglows-v2-geographic-properties-table.parquet',
                         columns=['LINKNO', 'lat', 'lon'])
    df['distance'] = ((df['lat'] - lat) ** 2 + (df['lon'] - lon) ** 2) ** 0.5
    return df.sort_values('distance').reset_index(drop=True).iloc[0][['TDXHydroLinkNo', 'distance']].values.flatten()
