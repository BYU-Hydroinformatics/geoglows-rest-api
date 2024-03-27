import os

from flask import Flask
from flask_cors import CORS

from blueprint_pages import app as blueprint_pages
import v2
import v1

print("Launching Flask App")

api_path = os.getenv('API_PREFIX', '/api')

app = Flask(__name__)
app.url_map.strict_slashes = False
app.debug = False

cors = CORS(app)
app.config['CORS_HEADERS'] = '*'

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> HTML PAGES
app.register_blueprint(blueprint_pages)

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> REST API ENDPOINTS
app.register_blueprint(v2.V2BLUEPRINT)
app.register_blueprint(v1.V1BLUEPRINT)

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> __main__
if __name__ == '__main__':
    app.run()
