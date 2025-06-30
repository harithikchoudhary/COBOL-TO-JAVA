import logging
import os
import json
from datetime import datetime
from flask import request

# === Setup Logging ===

# Create logs directory if it doesn't exist
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'{log_dir}/app.log', encoding='utf-8'),
        logging.FileHandler(f'{log_dir}/conversion_details.log', encoding='utf-8')
    ]
)

# Main application logger
logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)

# Conversion-specific logger
conversion_logger = logging.getLogger('conversion_logger')
conversion_logger.setLevel(logging.DEBUG)

# Add a detailed formatter for conversion logs
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - STEP: %(message)s'
)

# Separate handler for conversion steps
conversion_handler = logging.FileHandler(
    f'{log_dir}/step_by_step_conversion.log', encoding='utf-8'
)
conversion_handler.setFormatter(detailed_formatter)
conversion_logger.addHandler(conversion_handler)


def setup_logging():
    """Configure comprehensive logging with multiple levels and formats"""
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            # Console handler for INFO and above
            logging.StreamHandler(),
            # File handler for all logs
            logging.FileHandler(f'{log_dir}/app.log', encoding='utf-8'),
            # Separate file for conversion process details
            logging.FileHandler(f'{log_dir}/conversion_details.log', encoding='utf-8')
        ]
    )
    
    # Create specialized loggers
    conversion_logger = logging.getLogger('conversion')
    conversion_logger.setLevel(logging.DEBUG)
    
    # Add a detailed formatter for conversion logs
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - STEP: %(message)s'
    )
    
    # Create separate handler for conversion details
    conversion_handler = logging.FileHandler(f'{log_dir}/step_by_step_conversion.log', encoding='utf-8')
    conversion_handler.setFormatter(detailed_formatter)
    conversion_logger.addHandler(conversion_handler)
    
    return conversion_logger


def log_request_details(endpoint_name, request_data):
    """Log detailed request information"""
    logger.info(f"=== {endpoint_name.upper()} REQUEST STARTED ===")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Request Method: {request.method}")
    logger.info(f"Request Headers: {dict(request.headers)}")
    logger.info(f"Request Data Keys: {list(request_data.keys()) if request_data else 'No data'}")
    
    # Log request data with sensitive info masked
    safe_data = request_data.copy() if request_data else {}
    if 'sourceCode' in safe_data:
        code_preview = safe_data['sourceCode'][:200] + "..." if len(safe_data['sourceCode']) > 200 else safe_data['sourceCode']
        logger.info(f"Source Code Preview: {code_preview}")
        logger.info(f"Source Code Length: {len(safe_data['sourceCode'])} characters")
    
    logger.info(f"Full Request Data: {json.dumps(safe_data, indent=2, default=str)}")


def log_gpt_interaction(step_name, model_name, messages, response, step_number=None):
    """Log detailed GPT interaction"""
    step_prefix = f"STEP {step_number}: " if step_number else ""
    
    conversion_logger.info(f"=== {step_prefix}{step_name.upper()} - GPT INTERACTION ===")
    conversion_logger.info(f"Model: {model_name}")
    conversion_logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Log the messages sent to GPT
    conversion_logger.info("INPUT TO GPT:")
    for i, message in enumerate(messages):
        conversion_logger.info(f"  Message {i+1} ({message['role']}):")
        content = message['content']
        if len(content) > 1000:
            conversion_logger.info(f"    Content Preview (first 500 chars): {content[:500]}...")
            conversion_logger.info(f"    Content Preview (last 500 chars): ...{content[-500:]}")
            conversion_logger.info(f"    Total Content Length: {len(content)} characters")
        else:
            conversion_logger.info(f"    Content: {content}")
    
    # Log response details
    if response:
        conversion_logger.info("RESPONSE FROM GPT:")
        conversion_logger.info(f"  Response ID: {getattr(response, 'id', 'N/A')}")
        conversion_logger.info(f"  Model Used: {getattr(response, 'model', 'N/A')}")
        conversion_logger.info(f"  Usage: {getattr(response, 'usage', 'N/A')}")
        
        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            content = choice.message.content
            conversion_logger.info(f"  Finish Reason: {choice.finish_reason}")
            conversion_logger.info(f"  Response Length: {len(content)} characters")
            
            if len(content) > 2000:
                conversion_logger.info(f"  Response Preview (first 1000 chars): {content[:1000]}...")
                conversion_logger.info(f"  Response Preview (last 1000 chars): ...{content[-1000:]}")
            else:
                conversion_logger.info(f"  Full Response: {content}")
    
    conversion_logger.info(f"=== END {step_prefix}{step_name.upper()} ===\n")


def log_processing_step(step_name, details, step_number=None):
    """Log processing steps with details"""
    step_prefix = f"STEP {step_number}: " if step_number else ""
    conversion_logger.info(f"{step_prefix}{step_name}")
    if isinstance(details, dict):
        for key, value in details.items():
            conversion_logger.info(f"  {key}: {value}")
    else:
        conversion_logger.info(f"  Details: {details}")




