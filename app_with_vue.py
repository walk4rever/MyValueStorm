import os
import json
import time
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify
import threading
import sys

from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from knowledge_storm.result_manager import ResultManager
from api.research_api import research_api

# Create Flask app
app = Flask(__name__, 
            static_folder='frontend/vue-ui/dist',
            static_url_path='')

# Register API blueprint
app.register_blueprint(research_api, url_prefix='/api/research')

# Serve Vue.js frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Health check endpoint
@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Run Flask in the main thread
    app.run(host='0.0.0.0', port=5000, debug=True)
