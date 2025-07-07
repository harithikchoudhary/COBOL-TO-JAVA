from flask import Blueprint, request, jsonify
from ..config import logger, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, output_dir
from openai import AzureOpenAI
import logging
import os
import json
import re
import time
import traceback
from ..utils.code_converter import create_code_converter, extract_cobol_program_name
from ..utils.prompts import create_code_conversion_prompt, create_unit_test_prompt, create_functional_test_prompt
from ..utils.logs import log_request_details, log_processing_step, log_gpt_interaction
from ..utils.response import extract_json_from_response
from ..utils.db_usage import detect_database_usage
from ..utils.db_templates import get_db_template

bp = Blueprint('conversion', __name__, url_prefix='/cobo')

# Initialize OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def save_json_response(cobol_filename, json_obj):
    """Save the full JSON response to the output directory."""
    base_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else f"converted_{int(time.time())}"
    output_filename = f"{base_name}_output.json"
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_obj, f, indent=2, ensure_ascii=False)
    return output_path

@bp.route("/convert", methods=["POST"])
def convert_code():
    """Endpoint to convert COBOL code to .NET 8 with Onion Architecture."""
    conversion_start_time = time.time()
    conversion_logger = logging.getLogger('conversion')
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
                "convertedCode": {}, "conversionNotes": "", "potentialIssues": [],
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
                "convertedCode": {}, "conversionNotes": "", "potentialIssues": [],
                "unitTests": "", "unitTestDetails": {}, "functionalTests": {},
                "sourceLanguage": source_language if source_language else "",
                "targetLanguage": target_language if target_language else "",
                "databaseUsed": False
            }), 400

        if source_language.lower() != "cobol" or target_language.lower() not in ["c#", ".net", ".net 8"]:
            logger.error("Invalid language pair for conversion")
            return jsonify({
                "status": "error", "message": "Conversion only supported from COBOL to .NET 8",
                "convertedCode": {}, "conversionNotes": "", "potentialIssues": [],
                "unitTests": "", "unitTestDetails": {}, "functionalTests": {},
                "sourceLanguage": source_language if source_language else "",
                "targetLanguage": target_language if target_language else "",
                "databaseUsed": False
            }), 400

        log_processing_step("Analyzing source code for database operations", {
            "source_language": source_language,
            "code_preview": source_code[:200] + "..." if len(source_code) > 200 else source_code
        }, 2)
        
        has_database = detect_database_usage(source_code, source_language)
        
        log_processing_step("Database detection completed", {
            "database_detected": has_database,
            "will_include_db_template": has_database
        }, 3)
        
        db_setup_template = get_db_template("C#") if has_database else ""
        if has_database:
            logger.info("Database operations detected. Including EF Core setup.")
        else:
            logger.info("No database operations detected. Skipping EF Core setup.")

        converter = create_code_converter(client, AZURE_OPENAI_DEPLOYMENT_NAME)
        
        log_processing_step("Creating code conversion prompt", {
            "including_db_template": bool(db_setup_template),
            "business_req_length": len(str(business_requirements)),
            "technical_req_length": len(str(technical_requirements))
        }, 4)
        
        cobol_filename = data.get("cobolFilename", "")
        # Extract project name from COBOL code or filename
        fallback_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else "TaskManagementSystem"
        project_name = extract_cobol_program_name(source_code, fallback=fallback_name)
        
        prompt = create_code_conversion_prompt(
            source_language, "C#", source_code,
            business_requirements, technical_requirements, db_setup_template
        )

        prompt += """
        IMPORTANT: Ensure the output follows .NET 8 Onion Architecture:
        - Use consistent namespaces (Company.Project.[Layer])
        - Include all necessary using statements
        - Implement dependency injection in Program.cs
        - Use Entity Framework Core for database operations only if detected
        - Generate complete, executable code with no placeholders
        """

        conversion_messages = [
            {
                "role": "system",
                "content": (
                    f"You are an expert COBOL to .NET 8 converter specializing in Onion Architecture. "
                    f"Convert COBOL code to idiomatic .NET 8, maintaining all business logic. "
                    f"Include database setup only if COBOL code uses databases (EXEC SQL, FILE SECTION, VSAM). "
                    f"Generate a complete .NET 8 application with: "
                    f"1. Domain: Entities, interfaces, exceptions (no dependencies). "
                    f"2. Application: Services, DTOs (depends on Domain). "
                    f"3. Infrastructure: Repositories, DbContext (implements Application interfaces). "
                    f"4. Presentation: Controllers (depends on Application). "
                    f"Use dependency injection, proper namespaces (Company.Project.[Layer]), and Entity Framework Core for database operations. "
                    f"Return JSON with the structure specified in the prompt."
                )
            },
            {"role": "user", "content": prompt}
        ]

        log_processing_step("Calling Azure OpenAI for conversion", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 4000,
            "prompt_length": len(prompt)
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

        log_processing_step("Parsing conversion response", {
            "response_length": len(response.choices[0].message.content)
        }, 6)
        
        conversion_content = response.choices[0].message.content.strip()
        try:
            conversion_json = json.loads(conversion_content)
            logger.info("Conversion JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse conversion JSON")
            conversion_json = extract_json_from_response(conversion_content)

        converted_code = conversion_json.get("convertedCode", {})
        conversion_notes = conversion_json.get("conversionNotes", "")
        potential_issues = conversion_json.get("potentialIssues", [])
        database_used = conversion_json.get("databaseUsed", False)

        cobol_filename = data.get("cobolFilename", "")
        
        log_processing_step("Generating unit tests", {
            "target_language": "C#",
            "code_length": len(str(converted_code))
        }, 7)
        
        unit_test_prompt = create_unit_test_prompt(
            "C#", converted_code, business_requirements, technical_requirements
        )
        
        unit_test_messages = [
            {
                "role": "system",
                "content": f"You are an expert in writing unit tests for .NET 8 applications using Onion Architecture. "
                          f"Generate xUnit tests with Moq for Application and Domain layers. "
                          f"Return JSON with unitTestCode, testDescription, and coverage."
            },
            {"role": "user", "content": unit_test_prompt}
        ]
        
        unit_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=unit_test_messages,
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        log_gpt_interaction("Unit Test Generation", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          unit_test_messages, unit_test_response, 7)
        
        unit_test_content = unit_test_response.choices[0].message.content.strip()
        try:
            unit_test_json = json.loads(unit_test_content)
            logger.info("Unit test JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse unit test JSON")
            unit_test_json = extract_json_from_response(unit_test_content)
        
        unit_test_code_raw = unit_test_json.get("unitTestCode", "")
        if isinstance(unit_test_code_raw, list):
            unit_test_code_raw = "\n".join(str(item) for item in unit_test_code_raw)
        elif not isinstance(unit_test_code_raw, str):
            unit_test_code_raw = str(unit_test_code_raw)
        unit_test_code = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", unit_test_code_raw.strip())
        
        log_processing_step("Generating functional tests", {
            "target_language": "C#",
            "business_requirements_available": bool(business_requirements)
        }, 8)
        
        functional_test_prompt = create_functional_test_prompt(
            "C#", converted_code, business_requirements
        )
        
        functional_test_messages = [
            {
                "role": "system",
                "content": f"You are a QA engineer creating functional tests for .NET 8 applications. "
                          f"Generate SpecFlow test scenarios for user journeys. "
                          f"Return JSON with functionalTests and testStrategy."
            },
            {"role": "user", "content": functional_test_prompt}
        ]
        
        functional_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=functional_test_messages,
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        log_gpt_interaction("Functional Test Generation", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          functional_test_messages, functional_test_response, 8)
        
        functional_test_content = functional_test_response.choices[0].message.content.strip()
        try:
            functional_test_json = json.loads(functional_test_content)
            logger.info("Functional test JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse functional test JSON")
            functional_test_json = extract_json_from_response(functional_test_content)
        
        conversion_end_time = time.time()
        total_time = conversion_end_time - conversion_start_time
        
        log_processing_step("Building final response", {
            "total_conversion_time": f"{total_time:.2f} seconds",
            "converted_code_length": len(str(converted_code)),
            "unit_tests_length": len(unit_test_code),
            "functional_tests_count": len(functional_test_json.get("functionalTests", [])),
            "database_used": database_used
        }, 9)
        
        result = {
            "status": "success",
            "convertedCode": converted_code,
            "conversionNotes": conversion_notes,
            "potentialIssues": potential_issues,
            "unitTests": unit_test_code,
            "unitTestDetails": unit_test_json,
            "functionalTests": functional_test_json,
            "sourceLanguage": source_language,
            "targetLanguage": "C#",
            "databaseUsed": database_used
        }
        
        try:
            json_output_path = save_json_response(cobol_filename, result)
            logger.info(f"JSON response saved to: {json_output_path}")
        except Exception as save_json_exc:
            logger.warning(f"Failed to save JSON response: {save_json_exc}")
        
        conversion_logger.info("="*80)
        conversion_logger.info("✅ CODE CONVERSION COMPLETED")
        conversion_logger.info(f"⏱️ Total Time: {total_time:.2f} seconds")
        conversion_logger.info("="*80)
        
        return jsonify(result)

    except Exception as e:
        conversion_end_time = time.time()
        total_time = conversion_end_time - conversion_start_time
        
        logger.error(f"Conversion error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        conversion_logger.error("="*80)
        conversion_logger.error("❌ CONVERSION FAILED")
        conversion_logger.error(f"Error: {str(e)}")
        conversion_logger.error("="*80)
        
        return jsonify({
            "status": "error",
            "message": f"Conversion failed: {str(e)}",
            "convertedCode": {},
            "conversionNotes": "",
            "potentialIssues": [],
            "unitTests": "",
            "unitTestDetails": {},
            "functionalTests": {},
            "sourceLanguage": source_language if 'source_language' in locals() else "",
            "targetLanguage": "C#" if 'target_language' in locals() else "",
            "databaseUsed": False
        }), 500