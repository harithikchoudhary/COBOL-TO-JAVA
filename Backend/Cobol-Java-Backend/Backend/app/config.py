import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://azure-openai-uk.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "NkHVD9xPtHLIvi2cgfcdfNdZnMdyZFpl02NvDHuW7fRf36cxrHerJQQJ99ALACmepeSXJ3w3AAABACOGrbaC")
AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

# NEW: Azure configuration for RAG and CICS analysis
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

# NEW: Directory configurations
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "cics_analysis"
DOCUMENTS_DIR = "documents"
API_OUTPUT_DIR = "rag_storage"

# Output directory
output_dir = 'output'

# Logging setup
def setup_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler('logs/app.log', maxBytes=10000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logging()