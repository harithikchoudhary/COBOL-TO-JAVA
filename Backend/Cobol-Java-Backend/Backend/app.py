from flask import Flask, request, jsonify
import os
from flask_cors import CORS
import openai
from openai import AzureOpenAI
import time
import json
import logging
import re
import traceback
from datetime import datetime

from dotenv import load_dotenv
from db_templates import get_db_template
from prompts import (
    create_business_requirements_prompt,
    create_technical_requirements_prompt,
    create_code_conversion_prompt,
    create_unit_test_prompt,
    create_functional_test_prompt
)
from db_usage import detect_database_usage

# Enhanced logging configuration
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

# Initialize logging
conversion_logger = setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://azure-openai-uk.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "NkHVD9xPtHLIvi2cgfcdfNdZnMdyZFpl02NvDHuW7fRf36cxrHerJQQJ99ALACmepeSXJ3w3AAABACOGrbaC")
AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

# Initialize OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# Ensure output directory exists at startup
output_dir = 'output'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def save_json_response(cobol_filename, json_obj):
    """Save the full JSON response to the output directory, using the COBOL filename as base."""
    base_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else f"converted_{int(time.time())}"
    output_filename = f"{base_name}_output.json"
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_obj, f, indent=2, ensure_ascii=False)
    return output_path

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

def extract_json_from_response(text):
    """
    Extract JSON content from the response text.
    Handle cases where the model might wrap JSON in markdown code blocks,
    add additional text, or return truncated/incomplete JSON.
    """
    logger.info("=== JSON EXTRACTION PROCESS ===")
    logger.info(f"Input text length: {len(text)} characters")
    logger.info(f"Input text preview: {text[:300]}...")
    
    try:
        # First, try to parse the whole text as JSON
        result = json.loads(text)
        logger.info(" Direct JSON parsing successful")
        return result
    except json.JSONDecodeError as e:
        logger.info(f" Direct JSON parsing failed: {str(e)}")
        logger.info("Trying alternative methods...")
        
        # Try to extract JSON from markdown code blocks
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, text)
        
        if matches:
            logger.info(f"Found {len(matches)} potential JSON blocks in markdown")
            # Try each potential JSON block
            for i, match in enumerate(matches):
                try:
                    result = json.loads(match)
                    logger.info(f" Successfully parsed JSON from markdown block {i+1}")
                    return result
                except json.JSONDecodeError:
                    logger.info(f" Failed to parse markdown block {i+1}")
                    continue
        
        # Look for JSON-like structures with repair attempt for truncated JSON
        try:
            # Find text between curly braces including nested braces
            if text.count('{') > text.count('}'):
                logger.info("Detected potentially truncated JSON, attempting repair")
                
                # Basic repair for common truncation issues
                if '"convertedCode"' in text and '"conversionNotes"' in text:
                    # Extract what we have between the main braces
                    main_content = re.search(r'{(.*)', text)
                    if main_content:
                        content = main_content.group(0)
                        
                        # Check if we have the convertedCode field but it's incomplete
                        code_match = re.search(r'"convertedCode"\s*:\s*"(.*?)(?<!\\)"', content)
                        if code_match:
                            code = code_match.group(1)
                        else:
                            code_start = re.search(r'"convertedCode"\s*:\s*"(.*)', content)
                            if code_start:
                                code = code_start.group(1)
                            else:
                                code = ""
                        
                        # Check for conversionNotes
                        notes_match = re.search(r'"conversionNotes"\s*:\s*"(.*?)(?<!\\)"', content)
                        if notes_match:
                            notes = notes_match.group(1)
                        else:
                            notes = "Truncated during processing"
                        
                        # Create a valid JSON object with what we could extract
                        result = {
                            "convertedCode": code.replace('\\n', '\n').replace('\\"', '"'),
                            "conversionNotes": notes,
                            "potentialIssues": ["Response was truncated - some content may be missing"]
                        }
                        logger.info(" Successfully repaired truncated JSON")
                        return result
            
            # If repair didn't work, try to find complete JSON objects
            brace_pattern = r'({[\s\S]*?})'
            potential_jsons = re.findall(brace_pattern, text)
            
            logger.info(f"Found {len(potential_jsons)} potential JSON objects")
            for i, potential_json in enumerate(potential_jsons):
                try:
                    if len(potential_json) > 20:  # Avoid tiny fragments
                        result = json.loads(potential_json)
                        logger.info(f" Successfully parsed JSON object {i+1}")
                        return result
                except json.JSONDecodeError:
                    logger.info(f" Failed to parse JSON object {i+1}")
                    continue
            
            logger.warning("Could not extract valid JSON from response")
            
            # Last resort: create a minimal valid response
            result = {
                "convertedCode": "Extraction failed - see raw response",
                "conversionNotes": "JSON parsing failed. The model response may have been truncated.",
                "potentialIssues": ["JSON extraction failed"],
                "raw_text": text[:1000] + "..." if len(text) > 1000 else text
            }
            logger.info("Created fallback JSON response")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting JSON: {str(e)}")
            return {
                "error": "JSON extraction failed",
                "raw_text": text[:1000] + "..." if len(text) > 1000 else text
            }

@app.route("/cobo/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    logger.info("Health check requested")
    return jsonify({"status": "healthy", "timestamp": time.time()})

def classify_uploaded_files(file_json):
    """Classify uploaded files by type"""
    logger.info("=== FILE CLASSIFICATION STARTED ===")
    logger.info(f"Number of files to classify: {len(file_json)}")
    
    # Define type-to-extension mappings
    type_extensions = {
        "COBOL Code": [".cob", ".cbl", ".cobol", ".pco", ".ccp"],
        "JCL": [".jcl", ".job", ".cntl", ".ctl"],
        "Copybooks": [".cpy", ".copybook", ".cblcpy", ".inc"],
        "VSAM Definitions": [".ctl", ".cntl", ".def", ".vsam"],
    }

    # Normalize extensions for quick lookup
    ext_to_type = {}
    for type_name, exts in type_extensions.items():
        for ext in exts:
            ext_to_type[ext] = type_name

    # Prepare result dictionary
    classified = {
        "COBOL Code": [],
        "JCL": [],
        "Copybooks": [],
        "VSAM Definitions": [],
        "Unknown": []
    }

    # Iterate over uploaded files
    for file_info in file_json.values():
        file_name = file_info["fileName"]
        lower_name = file_name.lower()
        matched_type = None

        for ext, type_name in ext_to_type.items():
            if lower_name.endswith(ext):
                matched_type = type_name
                break

        if matched_type:
            classified[matched_type].append(file_info)
            logger.info(f"Classified '{file_name}' as '{matched_type}'")
        else:
            classified["Unknown"].append(file_info)
            logger.info(f"Could not classify '{file_name}' - marked as Unknown")

    # Log classification summary
    for file_type, files in classified.items():
        if files:
            logger.info(f"{file_type}: {len(files)} files")
    
    logger.info("=== FILE CLASSIFICATION COMPLETED ===")
    return classified

@app.route("/cobo/analyze-requirements", methods=["POST"])
def analyze_requirements():
    """Endpoint to analyze COBOL code and extract business and technical requirements"""
    
    try:
        data = request.json
        log_request_details("ANALYZE REQUIREMENTS", data)
        
        if not data:
            logger.error("No data provided in request")
            return jsonify({"error": "No data provided"}), 400
        
        log_processing_step("Parsing request data", {
            "has_file_data": "file_data" in data,
            "source_language": data.get("sourceLanguage"),
            "target_language": data.get("targetLanguage")
        }, 1)
        
        file_data = data.get("file_data")
        # Ensure file_data is a dictionary
        if isinstance(file_data, str):
            try:
                file_data = json.loads(file_data)
                logger.info("Converted file_data from string to dictionary")
            except json.JSONDecodeError:
                logger.error("Invalid file_data format - JSON decode failed")
                return jsonify({"error": "Invalid file_data format"}), 400
        
        parse_file_data = classify_uploaded_files(file_data)

        source_language = data.get("sourceLanguage")
        target_language = data.get("targetLanguage")
        source_code = parse_file_data.get("COBOL Code", [])
        vsam_definition = parse_file_data.get("VSAM Definitions", [])
        jcl = parse_file_data.get("JCL", [])
        copybooks = parse_file_data.get("Copybooks", [])
        
        if not all([source_language, source_code]):
            logger.error("Missing required fields for analysis")
            return jsonify({"error": "Missing required fields"}), 400
        
        log_processing_step("Creating analysis prompts", {
            "source_language": source_language,
            "target_language": target_language,
            "cobol_files_count": len(source_code),
            "vsam_files_count": len(vsam_definition)
        }, 2)
        
        # Create prompts for business and technical requirements
        business_prompt = create_business_requirements_prompt(source_language, source_code, vsam_definition)
        technical_prompt = create_technical_requirements_prompt(source_language, target_language, source_code, vsam_definition)
        
        # Prepare messages for business requirements
        business_messages = [
            {
                "role": "system",
                "content": (
                    f"You are an expert in analyzing legacy code to extract business requirements. "
                    f"You understand {source_language} deeply and can identify business rules and processes in the code. "
                    f"Output your analysis in JSON format with the following structure:\n\n"
                    f"{{\n"
                    f'  "Overview": {{\n'
                    f'    "Purpose of the System": "Describe the system\'s primary function and how it fits into the business.",\n'
                    f'    "Context and Business Impact": "Explain the operational context and value the system provides."\n'
                    f'  }},\n'
                    f'  "Objectives": {{\n'
                    f'    "Primary Objective": "Clearly state the system\'s main goal.",\n'
                    f'    "Key Outcomes": "Outline expected results (e.g., improved processing speed, customer satisfaction)."\n'
                    f'  }},\n'
                    f'  "Business Rules & Requirements": {{\n'
                    f'    "Business Purpose": "Explain the business objective behind this specific module or logic.",\n'
                    f'    "Business Rules": "List the inferred rules/conditions the system enforces.",\n'
                    f'    "Impact on System": "Describe how this part affects the system\'s overall operation.",\n'
                    f'    "Constraints": "Note any business limitations or operational restrictions."\n'
                    f'  }},\n'
                    f'  "Assumptions & Recommendations": {{\n'
                    f'    "Assumptions": "Describe what is presumed about data, processes, or environment.",\n'
                    f'    "Recommendations": "Suggest enhancements or modernization directions."\n'
                    f'  }},\n'
                    f'  "Expected Output": {{\n'
                    f'    "Output": "Describe the main outputs (e.g., reports, logs, updates).",\n'
                    f'    "Business Significance": "Explain why these outputs matter for business processes."\n'
                    f'  }}\n'
                    f"}}"
                )
            },
            {
                "role": "user",
                "content": business_prompt
            }
        ]
        
        # Call Azure OpenAI API for business requirements
        log_processing_step("Calling GPT for business requirements analysis", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 2000
        }, 3)
        
        business_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=business_messages,
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        log_gpt_interaction("Business Requirements Analysis", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          business_messages, business_response, 3)
        
        # Prepare messages for technical requirements
        technical_messages = [
            {
                "role": "system", 
                "content": f"You are an expert in {source_language} to {target_language} migration. "
                          f"You deeply understand both languages and can identify technical challenges and requirements for migration. "
                          f"Output your analysis in JSON format with the following structure:\n"
                          f"{{\n"
                          f'  "technicalRequirements": [\n'
                          f'    {{"id": "TR1", "description": "First technical requirement", }},\n'
                          f'    {{"id": "TR2", "description": "Second technical requirement", "complexity": "High/Medium/Low"}}\n'
                          f'  ],\n'
                          f"}}"
            },
            {"role": "user", "content": technical_prompt}
        ]
        
        # Call Azure OpenAI API for technical requirements
        log_processing_step("Calling GPT for technical requirements analysis", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 2000
        }, 4)
        
        technical_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=technical_messages,
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        log_gpt_interaction("Technical Requirements Analysis", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          technical_messages, technical_response, 4)
        
        # Extract and parse JSON from responses
        log_processing_step("Parsing GPT responses", {
            "business_response_length": len(business_response.choices[0].message.content),
            "technical_response_length": len(technical_response.choices[0].message.content)
        }, 5)
        
        business_content = business_response.choices[0].message.content.strip()
        technical_content = technical_response.choices[0].message.content.strip()
        
        try:
            business_json = json.loads(business_content)
            logger.info(" Business requirements JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse business requirements JSON directly")
            business_json = extract_json_from_response(business_content)
            
        try:
            technical_json = json.loads(technical_content)
            logger.info(" Technical requirements JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse technical requirements JSON directly")
            technical_json = extract_json_from_response(technical_content)
        
        # Combine the results
        result = {
            "businessRequirements": business_json,
            "technicalRequirements": technical_json,
            "sourceLanguage": source_language,
            "targetLanguage": target_language,
        }
        
        log_processing_step("Analysis completed successfully", {
            "business_requirements_keys": list(business_json.keys()) if isinstance(business_json, dict) else "Not a dict",
            "technical_requirements_count": len(technical_json.get("technicalRequirements", [])) if isinstance(technical_json, dict) else "Not available"
        }, 6)
        
        logger.info("=== ANALYZE REQUIREMENTS REQUEST COMPLETED SUCCESSFULLY ===")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in requirements analysis: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route("/cobo/convert", methods=["POST"])
def convert_code():
    """Endpoint to convert code from one language to another"""
    
    conversion_start_time = time.time()
    conversion_logger.info("="*80)
    conversion_logger.info(" CODE CONVERSION PROCESS STARTED")
    conversion_logger.info("="*80)

    try:
        data = request.json
        log_request_details("CODE CONVERSION", data)
        
        if not data:
            logger.error("No data provided in conversion request")
            return jsonify({
                "status": "error",
                "message": "No data provided",
                "convertedCode": "", "conversionNotes": "", "potentialIssues": [],
                "unitTests": "", "unitTestDetails": {}, "functionalTests": {},
                "sourceLanguage": "", "targetLanguage": "", "databaseUsed": False
            }), 400

        source_language = data.get("sourceLanguage")
        target_language = data.get("targetLanguage")
        source_code = data.get("sourceCode")
        business_requirements = data.get("businessRequirements", "")
        technical_requirements = data.get("technicalRequirements", "")
        vsam_definition = data.get("vsam_definition", "")

        log_processing_step("Validating conversion request", {
            "source_language": source_language,
            "target_language": target_language,
            "source_code_length": len(source_code) if source_code else 0,
            "has_business_requirements": bool(business_requirements),
            "has_technical_requirements": bool(technical_requirements),
            "has_vsam_definition": bool(vsam_definition)
        }, 1)

        if not all([source_language, target_language, source_code]):
            logger.error("Missing required fields for conversion")
            return jsonify({
                "status": "error", "message": "Missing required fields",
                "convertedCode": "", "conversionNotes": "", "potentialIssues": [],
                "unitTests": "", "unitTestDetails": {}, "functionalTests": {},
                "sourceLanguage": source_language if source_language else "",
                "targetLanguage": target_language if target_language else "",
                "databaseUsed": False
            }), 400

        # Analyze the code to detect if it contains database operations
        log_processing_step("Analyzing source code for database operations", {
            "source_language": source_language,
            "code_preview": source_code[:200] + "..." if len(source_code) > 200 else source_code
        }, 2)
        
        has_database = detect_database_usage(source_code, source_language)
        
        log_processing_step("Database detection completed", {
            "database_detected": has_database,
            "will_include_db_template": has_database
        }, 3)
        
        # Only get DB template if database operations are detected
        if has_database:
            logger.info(f"Database operations detected in {source_language} code. Including DB setup in conversion.")
            db_setup_template = get_db_template(target_language)
            log_processing_step("Database template retrieved", {
                "target_language": target_language,
                "template_length": len(db_setup_template)
            })
        else:
            logger.info(f"No database operations detected in {source_language} code. Skipping DB setup.")
            db_setup_template = ""
        
        # Import the code converter module
        from code_converter import create_code_converter
        
        # Create a code converter instance
        converter = create_code_converter(client, AZURE_OPENAI_DEPLOYMENT_NAME)
        
        # Create a prompt for the Azure OpenAI model
        log_processing_step("Creating code conversion prompt", {
            "including_db_template": bool(db_setup_template),
            "business_req_length": len(str(business_requirements)),
            "technical_req_length": len(str(technical_requirements))
        }, 4)
        
        prompt = create_code_conversion_prompt(
            source_language, target_language, source_code, vsam_definition,
            business_requirements, technical_requirements, db_setup_template
        )

        # Add special instruction about database code
        prompt += f"\n\nIMPORTANT: Only include database initialization code if the source {source_language} code contains database or SQL operations. If the code is a simple algorithm (like sorting, calculation, etc.) without any database interaction, do NOT include any database setup code in the converted {target_language} code."

        # Conditional conversation messages based on target language
        if target_language.lower() in ['java', 'spring boot', 'springboot']:
            # Java/Spring Boot specific conversation messages
            conversion_messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are an expert Java/Spring Boot code converter assistant specializing in {source_language} to {target_language} migration. "
                        f"You convert legacy code to modern, idiomatic Java Spring Boot applications while maintaining all business logic. "
                        f"Only include database setup/initialization if the original code uses databases or SQL. "
                        f"For simple algorithms or calculations without database operations, don't add any database code. "
                        f"Generate a complete Spring Boot application structure with proper annotations, dependency injection, and best practices. "
                        f"Include JPA entities, repositories, services, controllers, and configuration files as needed. "
                        f"Return your response in JSON format always with the following structure:\n"
                        "{\n"
                        '  "convertedCode": {\n'
                        '    "Entity": {"FileName": "User.java","Path": "src/main/java/com/example/entity/", "content": ""},\n'
                        '    "Repository": {"FileName": "UserRepository.java","Path": "src/main/java/com/example/repository/", "content": ""},\n'
                        '    "Service": {"FileName": "UserService.java","Path": "src/main/java/com/example/service/", "content": ""},\n'
                        '    "Controller": {"FileName": "UserController.java","Path": "src/main/java/com/example/controller/", "content": ""},\n'
                        '    "MainApplication": {"FileName": "Application.java","Path": "src/main/java/com/example/", "content": ""},\n'
                        '    "ApplicationProperties": {"FileName": "application.properties","Path": "src/main/resources/", "content": ""},\n'
                        '    "ApplicationYml": {"FileName": "application.yml","Path": "src/main/resources/", "content": ""},\n'
                        '    "PomXml": {"FileName": "pom.xml","Path": "./", "content": ""},\n'
                        '    "DatabaseConfig": {"FileName": "DatabaseConfig.java","Path": "src/main/java/com/example/config/", "content": ""},\n'
                        '    "Dependencies": {"content": "Maven dependencies and Spring Boot starters needed"}\n'
                        "  },\n"
                        '  "databaseUsed": true/false,\n'
                        "}\n"
                        "IMPORTANT: Always return the response in this JSON format. Include proper Spring Boot annotations (@RestController, @Service, @Repository, @Entity, @Autowired, etc.). "
                        "Use JPA/Hibernate for database operations. Follow Spring Boot best practices and naming conventions."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        elif target_language.lower() in ['c#', 'csharp', '.net', 'dotnet', 'asp.net', 'asp.net core']:
            # C#/.NET specific conversation messages
            conversion_messages = [
            {
                "role": "system",
                "content": (
                    f"You are an expert C#/.NET code converter assistant specializing in {source_language} to {target_language} migration. "
                    f"You convert legacy code to modern, idiomatic C# .NET applications while maintaining all business logic. "
                    f"Only include database setup/initialization if the original code uses databases or SQL. "
                    f"For simple algorithms or calculations without database operations, don't add any database code. "
                    f"Generate a complete .NET application structure with proper design patterns, dependency injection, and best practices. "
                    f"Include Entity Framework models, repositories, services, controllers, and configuration files as needed. "
                    f"Please generate the database connection string for MySQL Server. Ensure the model definitions do not use precision attributes. "
                    f"The code should be compatible with .NET 8, and all necessary dependencies should be included in the .csproj file. "
                    f"Return your response in JSON format always with the following structure:\n"
                    "{\n"
                    '  "convertedCode": {\n'
                    '    "Entity": {"FileName": "User.cs","Path": "Models/", "content": ""},\n'
                    '    "Repository": {"FileName": "IUserRepository.cs","Path": "Repositories/Interfaces/", "content": ""},\n'
                    '    "RepositoryImpl": {"FileName": "UserRepository.cs","Path": "Repositories/", "content": ""},\n'
                    '    "Service": {"FileName": "IUserService.cs","Path": "Services/Interfaces/", "content": ""},\n'
                    '    "ServiceImpl": {"FileName": "UserService.cs","Path": "Services/", "content": ""},\n'
                    '    "Controller": {"FileName": "UserController.cs","Path": "Controllers/", "content": ""},\n'
                    '    "DbContext": {"FileName": "ApplicationDbContext.cs","Path": "Data/", "content": ""},\n'
                    '    "Program": {"FileName": "Program.cs","Path": "./", "content": ""},\n'
                    '    "Startup": {"FileName": "Startup.cs","Path": "./", "content": ""},\n'
                    '    "AppSettings": {"FileName": "appsettings.json","Path": "./", "content": ""},\n'
                    '    "AppSettingsDev": {"FileName": "appsettings.Development.json","Path": "./", "content": ""},\n'
                    '    "ProjectFile": {"FileName": "Project.csproj","Path": "./", "content": ""},\n'
                    '    "Dependencies": {"content": "NuGet packages and .NET dependencies needed"}\n'
                    "  },\n"
                    '  "databaseUsed": true/false,\n'
                    '  "conversionNotes": "Detailed notes about the conversion process",\n'
                    '  "potentialIssues": ["List of potential issues or considerations"]\n'
                    "}\n"
                    "IMPORTANT: Always return the response in this JSON format. Include proper .NET attributes ([ApiController], [Route], [HttpGet], etc.). "
                    "Use Entity Framework Core for database operations. Follow .NET best practices, SOLID principles, and naming conventions. "
                    "Implement proper dependency injection, async/await patterns, and error handling. Ensure everything is compatible with .NET 8."
                )
            },
        ]

        else:
            # Default conversation messages for other languages
            conversion_messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are an expert code converter assistant specializing in {source_language} to {target_language} migration. "
                        f"You convert legacy code to modern, idiomatic code while maintaining all business logic. "
                        f"Only include database setup/initialization if the original code uses databases or SQL. "
                        f"For simple algorithms or calculations without database operations, don't add any database code. "
                        f"Return your response in JSON format always with the following structure:\n"
                        "{\n"
                        '  "convertedCode": {\n'
                        '    "Entity": {"FileName": "","Path": "", "content": ""},\n'
                        '    "Repository": {"FileName": "","Path": "", "content": ""},\n'
                        '    "Service": {"FileName": "","Path": "", "content": ""},\n'
                        '    "Controller": {"FileName": "","Path":"", "content": ""},\n'
                        '    "application.properties": {"content": ""},\n'
                        '    "Dependencies": {"content": ""}\n'
                        "  },\n"
                        '  "databaseUsed": true/false\n'
                        "}\n"
                        "IMPORTANT: Always return the response in this JSON format. Do not ignore this requirement under any circumstances."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

        # Call Azure OpenAI API for code conversion
        log_processing_step("Calling GPT for code conversion", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 4000,
            "prompt_length": len(prompt),
            "target_language": target_language
        }, 5)

        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=conversion_messages,
            temperature=0.1,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )

        log_gpt_interaction("Code Conversion", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          conversion_messages, response, 5)

        # Parse the JSON response
        log_processing_step("Parsing code conversion response", {
            "response_length": len(response.choices[0].message.content)
        }, 6)
        
        conversion_content = response.choices[0].message.content.strip()
        try:
            conversion_json = json.loads(conversion_content)
            logger.info(" Code conversion JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse code conversion JSON directly")
            conversion_json = extract_json_from_response(conversion_content)
        
        # Extract conversion results
        converted_code = conversion_json.get("convertedCode", {})
        conversion_notes = conversion_json.get("conversionNotes", "")
        potential_issues = conversion_json.get("potentialIssues", [])
        database_used = conversion_json.get("databaseUsed", False)

        # Save converted code to file (if original filename is provided)
        cobol_filename = data.get("cobolFilename") or data.get("sourceFilename") or ""
        
        log_processing_step("Code conversion completed", {
            "converted_code_length": len(converted_code),
            "conversion_notes_length": len(conversion_notes),
            "potential_issues_count": len(potential_issues),
            "database_used": database_used
        }, 7)
        
        # Generate unit test cases
        log_processing_step("Creating unit test prompt", {
            "target_language": target_language,
            "code_length": len(converted_code)
        }, 8)
        
        unit_test_prompt = create_unit_test_prompt(
            target_language,
            converted_code,
            business_requirements,
            technical_requirements
        )
        
        # Prepare unit test messages
        unit_test_messages = [
            {
                "role": "system",
                "content": f"You are an expert test engineer specializing in writing unit tests for {target_language}. "
                          f"You create comprehensive unit tests that verify all business logic and edge cases. "
                          f"Return your response in JSON format with the following structure:\n"
                          f"{{\n"
                          f'  "unitTestCode": "The complete unit test code here",\n'
                          f'  "testDescription": "Description of the test strategy",\n'
                          f'  "coverage": ["List of functionalities covered by the tests"]\n'
                          f"}}"
            },
            {"role": "user", "content": unit_test_prompt}
        ]
        
        log_processing_step("Calling GPT for unit test generation", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 3000,
            "prompt_length": len(unit_test_prompt)
        }, 8)
        
        unit_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=unit_test_messages,
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        log_gpt_interaction("Unit Test Generation", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          unit_test_messages, unit_test_response, 8)
        
        # Parse the JSON response
        log_processing_step("Parsing unit test response", {
            "response_length": len(unit_test_response.choices[0].message.content)
        }, 9)
        
        unit_test_content = unit_test_response.choices[0].message.content.strip()
        try:
            unit_test_json = json.loads(unit_test_content)
            logger.info(" Unit test JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse unit test JSON directly")
            unit_test_json = extract_json_from_response(unit_test_content)
        
        unit_test_code_raw = unit_test_json.get("unitTestCode", "")
        unit_test_code = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", unit_test_code_raw.strip())
        
        log_processing_step("Unit test generation completed", {
            "unit_test_code_length": len(unit_test_code),
            "test_description": unit_test_json.get("testDescription", "")[:100] + "..." if len(unit_test_json.get("testDescription", "")) > 100 else unit_test_json.get("testDescription", ""),
            "coverage_items": len(unit_test_json.get("coverage", []))
        }, 10)
        
        # Generate functional test cases
        log_processing_step("Creating functional test prompt", {
            "target_language": target_language,
            "business_requirements_available": bool(business_requirements)
        }, 11)
        
        functional_test_prompt = create_functional_test_prompt(
            target_language,
            converted_code,
            business_requirements
        )
        
        # Prepare functional test messages
        functional_test_messages = [
            {
                "role": "system",
                "content": f"You are an expert QA engineer specializing in creating functional tests for {target_language} applications. "
                          f"You create comprehensive test scenarios that verify the application meets all business requirements. "
                          f"Focus on user journey tests and acceptance criteria. "
                          f"Return your response in JSON format with the following structure:\n"
                          f"{{\n"
                          f'  "functionalTests": [\n'
                          f'    {{"id": "FT1", "title": "Test scenario title", "steps": ["Step 1", "Step 2"], "expectedResult": "Expected outcome"}},\n'
                          f'    {{"id": "FT2", "title": "Another test scenario", "steps": ["Step 1", "Step 2"], "expectedResult": "Expected outcome"}}\n'
                          f'  ],\n'
                          f'  "testStrategy": "Description of the overall testing approach"\n'
                          f"}}"
            },
            {"role": "user", "content": functional_test_prompt}
        ]
        
        log_processing_step("Calling GPT for functional test generation", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 3000,
            "prompt_length": len(functional_test_prompt)
        }, 11)
        
        functional_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=functional_test_messages,
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        log_gpt_interaction("Functional Test Generation", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          functional_test_messages, functional_test_response, 11)
        
        # Parse the JSON response
        log_processing_step("Parsing functional test response", {
            "response_length": len(functional_test_response.choices[0].message.content)
        }, 12)
        
        functional_test_content = functional_test_response.choices[0].message.content.strip()
        try:
            functional_test_json = json.loads(functional_test_content)
            logger.info("✓ Functional test JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse functional test JSON directly")
            functional_test_json = extract_json_from_response(functional_test_content)
        
        log_processing_step("Functional test generation completed", {
            "functional_tests_count": len(functional_test_json.get("functionalTests", [])),
            "test_strategy_length": len(functional_test_json.get("testStrategy", ""))
        }, 13)
        
        # Build the complete response
        conversion_end_time = time.time()
        total_time = conversion_end_time - conversion_start_time
        
        log_processing_step("Building final response", {
            "total_conversion_time": f"{total_time:.2f} seconds",
            "converted_code_length": len(converted_code),
            "unit_tests_length": len(unit_test_code),
            "functional_tests_count": len(functional_test_json.get("functionalTests", [])),
            "database_used": database_used
        }, 14)
        
        result = {
            "status": "success",
            "convertedCode": converted_code,
            "conversionNotes": conversion_notes,
            "potentialIssues": potential_issues,
            "unitTests": unit_test_code,
            "unitTestDetails": unit_test_json,
            "functionalTests": functional_test_json,
            "sourceLanguage": source_language,
            "targetLanguage": target_language,
            "databaseUsed": database_used
        }
        
        # Save the full JSON response to output directory
        try:
            json_output_path = save_json_response(cobol_filename, result)
            logger.info(f"Full JSON response saved to: {json_output_path}")
        except Exception as save_json_exc:
            logger.warning(f"Failed to save JSON response: {save_json_exc}")
        
        conversion_logger.info("="*80)
        conversion_logger.info("✅ CODE CONVERSION PROCESS COMPLETED SUCCESSFULLY")
        conversion_logger.info(f"⏱️  Total Processing Time: {total_time:.2f} seconds")
        conversion_logger.info(f"📝 Converted Code Length: {len(converted_code)} characters")
        conversion_logger.info(f"🧪 Unit Tests Generated: {len(unit_test_code)} characters")
        conversion_logger.info(f"🔍 Functional Tests: {len(functional_test_json.get('functionalTests', []))} scenarios")
        conversion_logger.info(f"💾 Database Usage: {database_used}")
        conversion_logger.info("="*80)
        
        logger.info("=== CODE CONVERSION REQUEST COMPLETED SUCCESSFULLY ===")
        return jsonify(result)

    except Exception as e:
        conversion_end_time = time.time()
        total_time = conversion_end_time - conversion_start_time
        
        logger.error(f"Error in code conversion or test generation: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        conversion_logger.error("="*80)
        conversion_logger.error("❌ CODE CONVERSION PROCESS FAILED")
        conversion_logger.error(f"⏱️  Time Before Failure: {total_time:.2f} seconds")
        conversion_logger.error(f"🚨 Error: {str(e)}")
        conversion_logger.error(f"📋 Traceback: {traceback.format_exc()}")
        conversion_logger.error("="*80)
        
        return jsonify({
            "status": "error",
            "message": f"Conversion failed: {str(e)}",
            "convertedCode": "",
            "conversionNotes": "",
            "potentialIssues": [],
            "unitTests": "",
            "unitTestDetails": {},
            "functionalTests": {},
            "sourceLanguage": source_language if 'source_language' in locals() else "",
            "targetLanguage": target_language if 'target_language' in locals() else "",
            "databaseUsed": False
        }), 500


@app.route("/cobo/languages", methods=["GET"])
def get_languages():
    """Return supported languages"""
    
    logger.info("Languages endpoint requested")
    
    # This should match the languages in the frontend
    languages = [
        {"name": "COBOL", "icon": "📋"},
        {"name": "Java", "icon": "☕"},
        {"name": "C#", "icon": "🔷"}, 
    ]
    
    logger.info(f"Returning {len(languages)} supported languages")
    return jsonify({"languages": languages})

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 Error: {request.url} not found")
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 Error: {str(error)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({"error": "Internal server error"}), 500

@app.before_request
def log_request_info():
    """Log basic request information"""
    logger.debug(f"Request: {request.method} {request.path}")
    logger.debug(f"Remote Address: {request.remote_addr}")
    logger.debug(f"User Agent: {request.headers.get('User-Agent', 'Unknown')}")

@app.after_request
def log_response_info(response):
    """Log response information"""
    logger.debug(f"Response: {response.status_code} for {request.method} {request.path}")
    return response

if __name__ == "__main__":
    # Use environment variables for configuration in production
    port = int(os.environ.get("PORT", 8010))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    logger.info("="*80)
    logger.info("🚀 STARTING COBOL CONVERTER APPLICATION")
    logger.info("="*80)
    logger.info(f"🌐 Host: 0.0.0.0")
    logger.info(f"🔌 Port: {port}")
    logger.info(f"🐛 Debug Mode: {debug}")
    logger.info(f"🤖 Azure OpenAI Endpoint: {AZURE_OPENAI_ENDPOINT}")
    logger.info(f"📊 Azure OpenAI Deployment: {AZURE_OPENAI_DEPLOYMENT_NAME}")
    logger.info(f"📁 Log Directory: logs/")
    logger.info("="*80)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=debug  
    )