from flask import Blueprint, jsonify, request
from flask_cors import cross_origin

from .analytics import log_request
from .v1_controllers_forecasts import (forecast_stats,
                                       forecast_ensembles,
                                       forecast_warnings,
                                       forecast_records,
                                       available_dates)
from .v1_controllers_historical import (historical,
                                        historical_averages,
                                        return_periods)
from .v1_utilities import (get_available_data_handler,
                           get_region_handler,
                           get_reach_id_from_latlon_handler)

app = Blueprint('rest-endpoints-v1', __name__)


@app.route(f'/api/<product>', methods=['GET'])
@app.route(f'/api/v1/<product>', methods=['GET'])
@cross_origin()
def rest_endpoints_v1(product: str):
    log_request(version="v1",
                product=product,
                reach_id=request.args.get('reach_id', 0),
                return_format=request.args.get('return_format', 'csv'),
                source=request.args.get('source', 'other'), )

    # forecast data products
    if product == 'ForecastStats':
        return forecast_stats(request)
    elif product == 'ForecastEnsembles':
        return forecast_ensembles(request)
    elif product == 'ForecastWarnings':
        return forecast_warnings(request)
    elif product == 'ForecastRecords':
        return forecast_records(request)

    # historical data products
    elif product == 'HistoricSimulation':
        return historical(request)
    elif product == 'ReturnPeriods':
        return return_periods(request)
    elif product == 'DailyAverages':
        return historical_averages(request, 'daily')
    elif product == 'MonthlyAverages':
        return historical_averages(request, 'monthly')

    elif product == 'AvailableData':
        return get_available_data_handler()
    elif product == 'AvailableRegions':
        return get_region_handler()
    elif product == 'AvailableDates':
        return available_dates(request)
    elif product == 'GetReachID':
        return get_reach_id_from_latlon_handler(request)

    else:
        return jsonify({'status': f'data product "{product}" not available'}), 201
