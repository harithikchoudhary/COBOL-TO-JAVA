from flask import Blueprint, jsonify
from ..config import logger
import time

bp = Blueprint('misc', __name__, url_prefix='/cobo')

@bp.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    logger.info("Health check requested")
    return jsonify({"status": "healthy", "timestamp": time.time()})

@bp.route("/languages", methods=["GET"])
def get_languages():
    """Return supported languages"""
    logger.info("Languages endpoint requested")
    
    # Only support COBOL to .NET 8
    languages = [
        {"name": "COBOL", "icon": "📋"},
        {"name": "C#", "icon": "🔷"}, 
    ]
    
    logger.info(f"Returning {len(languages)} supported languages")
    return jsonify({"languages": languages})