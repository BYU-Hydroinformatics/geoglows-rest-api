import logging
from os import getenv

from controllers_deprecated import (seasonal_average_handler,
                                    deprecated_forecast_stats_handler,
                                    deprecated_historic_data_handler)
from flask import Flask, render_template, request, jsonify, url_for, redirect, make_response
from flask_cors import CORS, cross_origin
from flask_restful import Api
from controllers_forecasts import (forecast_stats_handler,
                                   forecast_ensembles_handler,
                                   forecast_warnings_handler,
                                   forecast_records_handler,
                                   available_dates_handler, )
from controllers_historical import (historic_data_handler,
                                    historic_averages_handler,
                                    return_periods_handler, )
from controllers_utilities import (get_available_data_handler,
                                   get_region_handler,
                                   get_reach_id_from_latlon_handler, )
from controllers_water_one_flow import (wof_get_sites, wof_get_values, )

print("Creating Application")

api_path = getenv('API_PREFIX')
wof_path = 'wof'

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = '*'
api = Api(app)


# create logger function
def init_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler('/app/api.log', 'a')
    formatter = logging.Formatter('%(asctime)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> HTML PAGES
@app.route('/')
@cross_origin()
def home():
    return render_template('home.html')


@app.route('/documentation')
@cross_origin()
def documentation():
    return render_template('documentation.html')


@app.route('/publications')
@cross_origin()
def publications():
    return render_template('publications.html')


@app.route('/about')
@cross_origin()
def about():
    return render_template('about.html')


@app.route('/training')
@cross_origin()
def training():
    return render_template('training.html')


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> WATERONEFLOW ENDPOINTS
@app.route(f'{api_path}/{wof_path}/GetSites', methods=['GET'])
@api.representation('application/xml')
@cross_origin()
def get_sites():
    """
    WaterOneFlow GetValues
    """
    return make_response(wof_get_sites(), 200, {})


@app.route(f'{api_path}/{wof_path}/GetValues', methods=['GET'])
@api.representation('application/xml')
@cross_origin()
def get_values():
    """
    WaterOneFlow GetValues
    """
    return wof_get_values(request.args.get('location'), request.args.get('variable'),
                          request.args.get('startDate'), request.args.get('endDate'))


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> REST API ENDPOINTS
@app.route(f'{api_path}/ForecastStats/', methods=['GET'])
@cross_origin()
def forecast_stats():
    return forecast_stats_handler(request)


@app.route(f'{api_path}/ForecastEnsembles/', methods=['GET'])
@cross_origin()
def forecast_ensembles():
    return forecast_ensembles_handler(request)


@app.route(f'{api_path}/ForecastWarnings/', methods=['GET'])
@cross_origin()
def forecast_warnings():
    return forecast_warnings_handler(request)


@app.route(f'{api_path}/ForecastRecords/', methods=['GET'])
@cross_origin()
def forecast_records():
    return forecast_records_handler(request)


@app.route(f'{api_path}/HistoricSimulation/', methods=['GET'])
@cross_origin()
def historic_simulation():
    return historic_data_handler(request)


@app.route(f'{api_path}/ReturnPeriods/', methods=['GET'])
@cross_origin()
def return_periods():
    return return_periods_handler(request)


@app.route(f'{api_path}/DailyAverages/', methods=['GET'])
@cross_origin()
def daily_averages():
    return historic_averages_handler(request, 'daily')


@app.route(f'{api_path}/MonthlyAverages/', methods=['GET'])
@cross_origin()
def monthly_averages():
    return historic_averages_handler(request, 'monthly')


@app.route(f'{api_path}/AvailableData/', methods=['GET'])
@cross_origin()
def available_data():
    return get_available_data_handler()


@app.route(f'{api_path}/AvailableRegions/', methods=['GET'])
@cross_origin()
def regions():
    return get_region_handler()


@app.route(f'{api_path}/AvailableDates/', methods=['GET'])
@cross_origin()
def dates():
    return available_dates_handler(request)


@app.route(f'{api_path}/GetReachID/', methods=['GET'])
@cross_origin()
def determine_reach_id():
    return get_reach_id_from_latlon_handler(request)


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> DEPRECATED
# GET, API SeasonalAverage endpoint
@app.route(f'{api_path}/SeasonalAverage/', methods=['GET'])
@cross_origin()
def seasonal_average():
    # ensure you have enough information provided to return a response
    if request.args.get('reach_id', '') == '':
        if request.args.get('lat', '') == '' or request.args.get('lon', '') == '':
            logging.error("Either reach_id or lat and lon parameters are required as input.")
            return jsonify({"error": "Either reach_id or lat and lon parameters are required as input."}), 422

    return seasonal_average_handler(request)


@app.route(f'{api_path}/DeprecatedForecastStats/', methods=['GET'])
@cross_origin()
def deprecated_forecast_stats():
    # ensure you have enough information provided to return a response
    if request.args.get('reach_id', '') == '':
        if request.args.get('lat', '') == '' or request.args.get('lon', '') == '':
            logging.error("Either reach_id or lat and lon parameters are required as input.")
            return jsonify({"error": "Either reach_id or lat and lon parameters are required as input."}), 422

    return deprecated_forecast_stats_handler(request)


@app.route(f'{api_path}/DeprecatedHistoricSimulation/', methods=['GET'])
@cross_origin()
def deprecated_historic_simulation():
    # ensure you have enough information provided to return a response
    if request.args.get('reach_id', '') == '':
        if request.args.get('lat', '') == '' or request.args.get('lon', '') == '':
            logging.error("Either reach_id or lat and lon parameters are required as input.")
            return jsonify({"error": "Either reach_id or lat and lon parameters are required as input."}), 422

    return deprecated_historic_data_handler(request)


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ERROR HANDLERS
@app.errorhandler(404)
def errors_404(e):
    if request.path.startswith(f'{api_path}'):
        return jsonify({"error": f'API Endpoint not found: {request.path} -> Check spelling and the API docs'}), 404
    return redirect(url_for('home')), 404, {'Refresh': f'1; url={url_for("home")}'}


@app.errorhandler(ValueError)
def error_valueerror(e):
    return jsonify({"error": str(e)}), 422


# @app.errorhandler(Exception)
# def error_generalexception(e):
#     return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


if __name__ == '__main__':
    app.debug = False
    app.run()
