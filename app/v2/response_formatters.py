import datetime

import numpy as np
import pandas as pd
from flask import make_response, jsonify

__all__ = ['df_to_csv_flask_response', 'df_to_jsonify_response', 'new_json_template', ]


def df_to_csv_flask_response(df: pd.DataFrame, csv_name: str, *, index: bool = True):
    response = make_response(df.to_csv(index=index))
    response.headers['content-type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={csv_name}.csv'
    return response


def df_to_jsonify_response(df: pd.DataFrame, reach_id: int, units: str):
    # if the dataframe index type is datetime, convert it to a string
    if isinstance(df.index, pd.DatetimeIndex):
        df.index = df.index.strftime('%Y-%m-%dT%X+00:00')
    json_template = new_json_template(reach_id, units, start_date=df.index[0], end_date=df.index[-1])
    # add the columns from the dataframe to the json template
    json_template['datetime'] = df.index.tolist()
    json_template.update(df.replace(np.nan, '').to_dict(orient='list'))
    json_template['metadata']['series'] = ['datetime', ] + df.columns.tolist()
    return jsonify(json_template)


def new_json_template(reach_id, units, start_date, end_date):
    return {
        'metadata': {
            'reach_id': reach_id,
            'gen_date': datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dY%X+00:00'),
            'start_date': start_date,
            'end_date': end_date,
            'series': [],
            'units': {
                'name': 'streamflow',
                'short': f'{units}',
                'long': f'Cubic {"Meters" if units == "cms" else "Feet"} per Second',
            },
        }
    }
