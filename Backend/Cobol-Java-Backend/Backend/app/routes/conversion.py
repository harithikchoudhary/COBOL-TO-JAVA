from flask import Blueprint, request, jsonify
from ..config import logger, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, output_dir
from openai import AzureOpenAI
import logging
import os
from ..config import logger, output_dir
from ..utils.code_converter import create_code_converter
from ..utils.prompts import create_code_conversion_prompt, create_unit_test_prompt, create_functional_test_prompt, create_business_requirements_prompt, create_technical_requirements_prompt
from ..utils.logs import log_request_details, log_processing_step, log_gpt_interaction
from ..utils.response import extract_json_from_response
from ..utils.db_usage import detect_database_usage
from ..utils.db_templates import get_db_template
import json
import re
import time
import traceback

bp = Blueprint('conversion', __name__, url_prefix='/cobo')

# Initialize OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def save_json_response(cobol_filename, json_obj):
    """Save the full JSON response to the output directory, using the COBOL filename as base."""
    base_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else f"converted_{int(time.time())}"
    output_filename = f"{base_name}_output.json"
    output_path = os.path.join(output_dir, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_obj, f, indent=2, ensure_ascii=False)
    return output_path

@bp.route("/convert", methods=["POST"])
def convert_code():
    """Endpoint to convert COBOL code to .NET 8"""
    
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

        # Validate that source is COBOL and target is .NET 8
        if source_language.lower() != "cobol" or target_language.lower() not in ["c#", ".net", ".net 8"]:
            logger.error("Invalid language pair for conversion")
            return jsonify({
                "status": "error", "message": "Conversion only supported from COBOL to .NET 8",
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
            logger.info(f"Database operations detected in COBOL code. Including DB setup in conversion.")
            db_setup_template = get_db_template("C#")
            log_processing_step("Database template retrieved", {
                "target_language": "C#",
                "template_length": len(db_setup_template)
            })
        else:
            logger.info(f"No database operations detected in COBOL code. Skipping DB setup.")
            db_setup_template = ""
        
        # Create a code converter instance
        converter = create_code_converter(client, AZURE_OPENAI_DEPLOYMENT_NAME)
        
        # Create a prompt for the Azure OpenAI model
        log_processing_step("Creating code conversion prompt", {
            "including_db_template": bool(db_setup_template),
            "business_req_length": len(str(business_requirements)),
            "technical_req_length": len(str(technical_requirements))
        }, 4)
        
        prompt = create_code_conversion_prompt(
            source_language, "C#", source_code,
            business_requirements, technical_requirements, db_setup_template
        )

        # Add special instruction about database code
        prompt += f"\n\nIMPORTANT: Only include database initialization code if the source COBOL code contains database or SQL operations. If the code is a simple algorithm (like sorting, calculation, etc.) without any database interaction, do NOT include any database setup code in the converted .NET 8 code."

        # Conversion messages for COBOL to .NET 8
        conversion_messages = [
            {
                "role": "system",
                "content": (
                    f"You are an expert COBOL to .NET 8 code converter assistant. "
                    f"You convert legacy COBOL code to modern, idiomatic .NET 8 applications while maintaining all business logic. "
                    f"Only include database setup/initialization if the original COBOL code uses databases or SQL. "
                    f"For simple algorithms or calculations without database operations, do NOT add any database code. "
                    f"Generate a complete .NET 8 application structure with proper design patterns, dependency injection, and best practices. "
                    f"Include Entity Framework Core models, repositories, services, controllers, and configuration files as needed. "
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
            {"role": "user", "content": prompt}
        ]

        # Call Azure OpenAI API for code conversion
        log_processing_step("Calling GPT for code conversion", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 4000,
            "prompt_length": len(prompt),
            "target_language": "C#"
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
            logger.info("Code conversion JSON parsed successfully")
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
            "converted_code_length": len(str(converted_code)),
            "conversion_notes_length": len(conversion_notes),
            "potential_issues_count": len(potential_issues),
            "database_used": database_used
        }, 7)
        
        # Generate unit test cases
        log_processing_step("Creating unit test prompt", {
            "target_language": "C#",
            "code_length": len(str(converted_code))
        }, 8)
        
        unit_test_prompt = create_unit_test_prompt(
            "C#",
            converted_code,
            business_requirements,
            technical_requirements
        )
        
        # Prepare unit test messages
        unit_test_messages = [
            {
                "role": "system",
                "content": f"You are an expert test engineer specializing in writing unit tests for .NET 8 applications. "
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
            logger.info("Unit test JSON parsed successfully")
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
            "target_language": "C#",
            "business_requirements_available": bool(business_requirements)
        }, 11)
        
        functional_test_prompt = create_functional_test_prompt(
            "C#",
            converted_code,
            business_requirements
        )
        
        # Prepare functional test messages
        functional_test_messages = [
            {
                "role": "system",
                "content": f"You are an expert QA engineer specializing in creating functional tests for .NET 8 applications. "
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
            logger.info("Functional test JSON parsed successfully")
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
            "converted_code_length": len(str(converted_code)),
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
            "targetLanguage": "C#",
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
        conversion_logger.info(f"⏱️ Total Processing Time: {total_time:.2f} seconds")
        conversion_logger.info(f"📝 Converted Code Length: {len(str(converted_code))} characters")
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
        conversion_logger.error(f"⏱️ Time Before Failure: {total_time:.2f} seconds")
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
            "targetLanguage": "C#" if 'target_language' in locals() else "",
            "databaseUsed": False
        }), 500