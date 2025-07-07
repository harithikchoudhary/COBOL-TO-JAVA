from app import create_app
from app.config import logger
import os

if __name__ == "__main__":
    app = create_app()
    
    # Use environment variables for configuration
    port = int(os.environ.get("PORT", 8010))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    logger.info("Starting COBOL Converter Application")
    logger.info(f"Server: 0.0.0.0:{port} | Debug: {debug}")
    logger.info(f"Azure OpenAI: {app.config['AZURE_OPENAI_DEPLOYMENT_NAME']}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=debug
    )
