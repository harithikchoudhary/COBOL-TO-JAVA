import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import sys

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

# Azure configuration for RAG and CICS analysis
AZURE_CONFIG = {
    "AZURE_OPENAI_EMBED_API_ENDPOINT": "https://azure-openai-uk.openai.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2023-05-15",
    "AZURE_OPENAI_EMBED_API_KEY": "NkHVD9xPtHLIvi2cgfcdfNdZnMdyZFpl02NvDHuW7fRf36cxrHerJQQJ99ALACmepeSXJ3w3AAABACOGrbaC",
    "AZURE_OPENAI_EMBED_VERSION": "2023-05-15",
    "AZURE_OPENAI_EMBED_MODEL": "text-embedding-3-large",
    "AZURE_OPENAI_ENDPOINT": "https://azure-openai-uk.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview",
    "AZURE_OPENAI_API_KEY": "NkHVD9xPtHLIvi2cgfcdfNdZnMdyZFpl02NvDHuW7fRf36cxrHerJQQJ99ALACmepeSXJ3w3AAABACOGrbaC",
    "AZURE_OPENAI_API_VERSION": "2023-05-15",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o"
}

# Directory configurations
UPLOAD_DIR = "uploads"

# Output directory
output_dir = 'output'

# Logging setup
def setup_logging():
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Set to INFO to reduce verbosity

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler with UTF-8 encoding
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10000000, backupCount=5, encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Optional: Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.stream.reconfigure(encoding='utf-8')  # Ensure UTF-8 for console
    logger.addHandler(console_handler)

    # Suppress verbose logs from external libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('faiss').setLevel(logging.WARNING)

    return logger

logger = setup_logging()
 