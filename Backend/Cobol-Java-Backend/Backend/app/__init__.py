from flask import Flask
from flask_cors import CORS
from .config import setup_logging, logger, output_dir
import os
from flask import request
import traceback
from flask import jsonify


def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Register blueprints
    from .routes import analysis, conversion, misc
    app.register_blueprint(analysis.bp)
    app.register_blueprint(conversion.bp)
    app.register_blueprint(misc.bp)

    # Setup logging for requests and responses
    @app.before_request
    def log_request_info():
        logger.debug(f"Request: {request.method} {request.path}")
        logger.debug(f"Remote Address: {request.remote_addr}")
        logger.debug(f"User Agent: {request.headers.get('User-Agent', 'Unknown')}")

    @app.after_request
    def log_response_info(response):
        logger.debug(f"Response: {response.status_code} for {request.method} {request.path}")
        return response

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"404 Error: {request.url} not found")
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 Error: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500

    return app