import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from .config import config
from .core.collector import system_monitor
from .core.preprocessor import data_scaler

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Enable CORS for all routes
    CORS(app)

    # Start System Monitor
    system_monitor.start()

    # Basic Health Check Route
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'CRASH SENSE Agent',
            'version': '0.1.0'
        })
    
    @app.route('/api/metrics/current', methods=['GET'])
    def get_current_metrics():
        metrics = system_monitor.get_latest_metrics()
        if not metrics:
            return jsonify({})
            
        normalized = request.args.get('normalized', 'false').lower() == 'true'
        if normalized:
            return jsonify(data_scaler.normalize_metrics(metrics))
            
        return jsonify(metrics)

    # Register blueprints (placeholders for now)
    # from .api import api_bp
    # app.register_blueprint(api_bp, url_prefix='/api')

    return app

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_CONFIG', 'default'))
    try:
        app.run(host='0.0.0.0', port=5000)
    finally:
        system_monitor.stop()
