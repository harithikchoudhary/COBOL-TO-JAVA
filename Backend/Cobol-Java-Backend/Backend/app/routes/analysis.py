from flask import Blueprint, request, jsonify
from ..config import logger, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME
from ..utils.file_classifier import classify_uploaded_files
from openai import AzureOpenAI
import json
from ..utils.prompts import create_business_requirements_prompt, create_technical_requirements_prompt
from ..utils.logs import log_request_details, log_processing_step, log_gpt_interaction
from ..utils.response import extract_json_from_response
import traceback


bp = Blueprint('analysis', __name__, url_prefix='/cobo')

# Initialize OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

@bp.route("/analyze-requirements", methods=["POST"])
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
        business_prompt = create_business_requirements_prompt(source_language, source_code)
        technical_prompt = create_technical_requirements_prompt(source_language, target_language, source_code)
        
        # Prepare messages for business requirements
        business_messages = [
            {
                "role": "system",
                "content": (
                    f"You are an expert in analyzing COBOL code to extract business requirements. "
                    f"You understand COBOL deeply and can identify business rules and processes in the code. "
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
                "content": f"You are an expert in COBOL to .NET 8 migration. "
                          f"You deeply understand both COBOL and .NET 8 and can identify technical challenges and requirements for migration. "
                          f"Output your analysis in JSON format with the following structure:\n"
                          f"{{\n"
                          f'  "technicalRequirements": [\n'
                          f'    {{"id": "TR1", "description": "First technical requirement", "complexity": "High/Medium/Low"}},\n'
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
            logger.info("Business requirements JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse business requirements JSON directly")
            business_json = extract_json_from_response(business_content)
            
        try:
            technical_json = json.loads(technical_content)
            logger.info("Technical requirements JSON parsed successfully")
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