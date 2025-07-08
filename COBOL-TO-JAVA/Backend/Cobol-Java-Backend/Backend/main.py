from app import create_app
from app.config import logger
import os

if __name__ == "__main__":
    app = create_app()
    
    # Use environment variables for configuration
    port = int(os.environ.get("PORT", 8010))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    logger.info("=" * 80)
    logger.info("STARTING COBOL CONVERTER APPLICATION")
    logger.info("=" * 80)
    logger.info("Host: 0.0.0.0")
    logger.info(f"Port: {port}")
    logger.info(f"Debug Mode: {debug}")
    logger.info(f"Azure OpenAI Endpoint: {app.config.get('AZURE_OPENAI_ENDPOINT')}")
    logger.info(f"Azure OpenAI Deployment: {app.config.get('AZURE_OPENAI_DEPLOYMENT_NAME')}")
    logger.info("Log Directory: logs/")
    logger.info("=" * 80)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=debug
    )
