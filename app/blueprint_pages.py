import logging
import traceback

from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_cors import cross_origin

app = Blueprint('pages', __name__)

logger = logging.getLogger("DEBUG")


@app.route('/')
@cross_origin()
def home():
    return render_template('home.html')


@app.route('/documentation')
@cross_origin()
def documentation():
    return render_template('documentation.html')


@app.route('/license')
@cross_origin()
def license():
    return render_template('license.html')


@app.route('/publications')
@cross_origin()
def publications():
    return render_template('publications.html')


@app.route('/about')
@cross_origin()
def about():
    return render_template('about.html')


@app.route('/resources')
@cross_origin()
def resources():
    return render_template('resources.html')


@app.errorhandler(404)
def errors_404(e):
    logger.debug(traceback.format_exc())
    if request.path.startswith(f'/api'):
        return jsonify({"error": f'API Endpoint not found: {request.path} -> Check spelling and the API docs'}), 404
    return redirect(url_for('pages.home')), 404, {'Refresh': f'1; url={url_for("home")}'}
