#  https://gist.github.com/oseiskar/dbd51a3727fc96dcf5ed189fca491fb3
#  Copyright 2017 Otto Seiskari
#  Licensed under the Apache License, Version 2.0.
#  See http://www.apache.org/licenses/LICENSE-2.0 for the full text.
#
#  This file is based on
#  https://github.com/swagger-api/swagger-ui/blob/4f1772f6544699bc748299bd65f7ae2112777abc/dist/index.html
#  (Copyright 2017 SmartBear Software, Licensed under Apache 2.0)
#
"""
Usage:
    python swagger_yml_to_html.py < swagger_doc.yaml > index.html
"""
# pip install PyYAML
import json
import os
import sys
import yaml

TEMPLATE = """{% extends "base_template.html" %}
{% block title %}GEOGLOWS ECMWF Streamflow Service{% endblock %}

{% block body %}
  <div id="swagger-ui"></div>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.24.2/swagger-ui-bundle.js"> </script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.24.2/swagger-ui-standalone-preset.js"> </script>
  <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/js/bootstrap.min.js"></script>
  <script>
  window.onload = function() {
    const spec = SWAGGER_YAML_CONTENT;
    // Build a system
    const ui = SwaggerUIBundle({
      spec: spec,
      dom_id: '#swagger-ui',
      deepLinking: true,
      presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIStandalonePreset
      ],
      plugins: [
        SwaggerUIBundle.plugins.DownloadUrl
      ],
      layout: "StandaloneLayout"
    })
    window.ui = ui

    var elements = document.getElementsByClassName("topbar");
    while(elements.length > 0){
      elements[0].parentNode.removeChild(elements[0]);
    }
  }
  </script>
{% endblock %}

{% block stylesheets %}
  <link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700|Source+Code+Pro:300,600|Titillium+Web:400,600,700" rel="stylesheet">
  <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.24.2/swagger-ui.css" >
  <style>
    html
    {
      box-sizing: border-box;
      overflow-y: scroll;
    }
    *,
    *:before,
    *:after
    {
      box-sizing: inherit;
    }
    body {
      margin:0;
      background: #fafafa;
    }
  </style>
{% endblock %}
"""

spec = yaml.safe_load(sys.stdin)
sys.stdout.write(TEMPLATE.replace("SWAGGER_YAML_CONTENT", json.dumps(spec)))
with open('index.html', 'r') as idx:
    with open(os.path.join(os.path.pardir, 'app', 'templates', 'documentation.html'), 'w') as doc:
        doc.write(idx.read())
