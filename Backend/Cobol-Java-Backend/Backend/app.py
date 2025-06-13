from flask import Flask, request, jsonify
import os
from flask_cors import CORS
import openai
from openai import AzureOpenAI
import time
import json
import logging
import re

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "your-azure-openai-endpoint")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "your-azure-openai-key")
AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "your-deployment-name")

# Initialize OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)


def extract_json_from_response(text):
    """
    Extract JSON content from the response text.
    Handle cases where the model might wrap JSON in markdown code blocks,
    add additional text, or return truncated/incomplete JSON.
    """
    import json
    import re
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # First, try to parse the whole text as JSON
        return json.loads(text)
    except json.JSONDecodeError:
        logger.info("Direct JSON parsing failed, trying alternative methods")
        
        # Try to extract JSON from markdown code blocks
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, text)
        
        if matches:
            # Try each potential JSON block
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # Look for JSON-like structures with repair attempt for truncated JSON
        try:
            # Find text between curly braces including nested braces
            # First, check if we have an opening brace but incomplete JSON
            if text.count('{') > text.count('}'):
                logger.info("Detected potentially truncated JSON, attempting repair")
                
                # Basic repair for common truncation issues
                # This won't handle all cases but covers many scenarios
                if '"convertedCode"' in text and '"conversionNotes"' in text:
                    # Extract what we have between the main braces
                    main_content = re.search(r'{(.*)', text)
                    if main_content:
                        content = main_content.group(0)
                        
                        # Check if we have the convertedCode field but it's incomplete
                        code_match = re.search(r'"convertedCode"\s*:\s*"(.*?)(?<!\\)"', content)
                        if code_match:
                            # We have complete convertedCode
                            code = code_match.group(1)
                        else:
                            # Truncated in the middle of convertedCode
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
                        return {
                            "convertedCode": code.replace('\\n', '\n').replace('\\"', '"'),
                            "conversionNotes": notes,
                            "potentialIssues": ["Response was truncated - some content may be missing"]
                        }
            
            # If repair didn't work, try to find complete JSON objects
            brace_pattern = r'({[\s\S]*?})'
            potential_jsons = re.findall(brace_pattern, text)
            
            for potential_json in potential_jsons:
                try:
                    if len(potential_json) > 20:  # Avoid tiny fragments
                        return json.loads(potential_json)
                except json.JSONDecodeError:
                    continue
            
            logger.warning("Could not extract valid JSON from response")
            
            # Last resort: create a minimal valid response with whatever we got
            return {
                "convertedCode": "Extraction failed - see raw response",
                "conversionNotes": "JSON parsing failed. The model response may have been truncated.",
                "potentialIssues": ["JSON extraction failed"],
                "raw_text": text[:1000] + "..." if len(text) > 1000 else text  # Include part of raw text
            }
            
        except Exception as e:
            logger.error(f"Error extracting JSON: {str(e)}")
            return {
                "error": "JSON extraction failed",
                "raw_text": text[:1000] + "..." if len(text) > 1000 else text
            }


@app.route("/cobo/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": time.time()})

def classify_uploaded_files(file_json):
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
        else:
            classified["Unknown"].append(file_info)

    return classified


@app.route("/cobo/analyze-requirements", methods=["POST"])
def analyze_requirements():
    """Endpoint to analyze COBOL code and extract business and technical requirements"""
    
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    file_data = data.get("file_data")
    parse_file_data = classify_uploaded_files(file_data)

    source_language = data.get("sourceLanguage")
    target_language = data.get("targetLanguage")
    source_code = parse_file_data.get("COBOL Code", [])
    vsam_definition = parse_file_data.get("VSAM Definitions", [])
    jcl = parse_file_data.get("JCL", [])
    copybooks = parse_file_data.get("Copybooks", [])
    
    if not all([source_language, source_code]):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        # Create prompts for business and technical requirements
        business_prompt = create_business_requirements_prompt(source_language, source_code, vsam_definition)
        technical_prompt = create_technical_requirements_prompt(source_language, target_language, source_code, vsam_definition)
        
        # Call Azure OpenAI API for business requirements with JSON response format
        business_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages =[
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
            ],

            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Log the complete raw business response
        logger.info("=== RAW BUSINESS REQUIREMENTS RESPONSE ===")
        logger.info(json.dumps(business_response.model_dump(), indent=2))
        
        # Call Azure OpenAI API for technical requirements with JSON response format
        technical_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
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
            ],
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Log the complete raw technical response
        logger.info("=== RAW TECHNICAL REQUIREMENTS RESPONSE ===")
        logger.info(json.dumps(technical_response.model_dump(), indent=2))
        
        # Extract and parse JSON from responses
        business_content = business_response.choices[0].message.content.strip()
        technical_content = technical_response.choices[0].message.content.strip()
        
        try:
            business_json = json.loads(business_content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse business requirements JSON directly")
            business_json = extract_json_from_response(business_content)
            
        try:
            technical_json = json.loads(technical_content)
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
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in requirements analysis: {str(e)}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/cobo/convert", methods=["POST"])
def convert_code():
    """Endpoint to convert code from one language to another"""

    data = request.json
    if not data:
        return jsonify({
            "status": "error",
            "message": "No data provided",
            "convertedCode": "",
            "conversionNotes": "",
            "potentialIssues": [],
            "unitTests": "",
            "unitTestDetails": {},
            "functionalTests": {},
            "sourceLanguage": "",
            "targetLanguage": "",
            "databaseUsed": False
        }), 400

    source_language = data.get("sourceLanguage")
    target_language = data.get("targetLanguage")
    source_code = data.get("sourceCode")
    business_requirements = data.get("businessRequirements", "")
    technical_requirements = data.get("technicalRequirements", "")
    vsam_definition = data.get("vsam_definition", "")

    if not all([source_language, target_language, source_code]):
        return jsonify({
            "status": "error",
            "message": "Missing required fields",
            "convertedCode": "",
            "conversionNotes": "",
            "potentialIssues": [],
            "unitTests": "",
            "unitTestDetails": {},
            "functionalTests": {},
            "sourceLanguage": source_language if source_language else "",
            "targetLanguage": target_language if target_language else "",

            "databaseUsed": False
        }), 400

    try:
        # Analyze the code to detect if it contains database operations
        has_database = detect_database_usage(source_code, source_language)
        
        # Only get DB template if database operations are detected
        if has_database:
            logger.info(f"Database operations detected in {source_language} code. Including DB setup in conversion.")
            db_setup_template = get_db_template(target_language)
        else:
            logger.info(f"No database operations detected in {source_language} code. Skipping DB setup.")
            db_setup_template = ""  # Empty string if no database operations
        
        # Import the code converter module
        from code_converter import create_code_converter, should_chunk_code
        
        # Create a code converter instance
        converter = create_code_converter(client, AZURE_OPENAI_DEPLOYMENT_NAME)
        
        # Check if code should be chunked
        if should_chunk_code(source_code):
            logger.info(f"Source code is large ({len(source_code)} chars). Using chunking approach.")
            
            # Split the code into manageable chunks
            code_chunks = converter.chunk_code(
                source_code=source_code,
                source_language=source_language,
                chunk_size=23500,  # Adjust as needed based on model capabilities
                chunk_overlap=2000  # Ensure context overlap between chunks
            )
            
            # Convert the chunked code
            conversion_json = converter.convert_code_chunks(
                chunks=code_chunks,
                source_language=source_language,
                target_language=target_language,
                vsam_definition = vsam_definition,
                business_requirements=business_requirements,
                technical_requirements=technical_requirements,
                db_setup_template=db_setup_template
            )
        else:
            logger.info(f"Source code is small enough ({len(source_code)} chars) for direct conversion.")
            
            # Create a prompt for the Azure OpenAI model
            prompt = create_code_conversion_prompt(
                source_language,
                target_language,
                source_code,
                vsam_definition,
                business_requirements,
                technical_requirements,
                db_setup_template
            )

            # Add special instruction about database code
            prompt += f"\n\nIMPORTANT: Only include database initialization code if the source {source_language} code contains database or SQL operations. If the code is a simple algorithm (like sorting, calculation, etc.) without any database interaction, do NOT include any database setup code in the converted {target_language} code."

            # Call Azure OpenAI API with JSON response format
            response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert code converter assistant specializing in {source_language} to {target_language} migration. "
                                  f"You convert legacy code to modern, idiomatic code while maintaining all business logic. "
                                  f"Only include database setup/initialization if the original code uses databases or SQL. "
                                  f"For simple algorithms or calculations without database operations, don't add any database code. "
                                  f"Return your response in JSON format always with the following structure:\n"
                                  f"{{\n"
                                  f'  "convertedCode": "The complete converted code here",\n'
                                  f'  "conversionNotes": "Notes about the conversion process",\n'
                                  f'  "potentialIssues": ["List of any potential issues or limitations"],\n'
                                  f'  "databaseUsed": true/false\n'
                                  f"}}"
                                  f"IMPORTANT: Always return the response in JSON format. Do not ignore this requirement under any circumstances."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )

            # Log the complete raw conversion response
            logger.info("=== RAW CODE CONVERSION RESPONSE ===")
            logger.info(json.dumps(response.model_dump(), indent=2))

            # Parse the JSON response
            conversion_content = response.choices[0].message.content.strip()
            try:
                conversion_json = json.loads(conversion_content)
            except json.JSONDecodeError:
                logger.warning("Failed to parse code conversion JSON directly")
                conversion_json = extract_json_from_response(conversion_content)
        
        # Extract conversion results
        converted_code = conversion_json.get("convertedCode", "")
        conversion_notes = conversion_json.get("conversionNotes", "")
        potential_issues = conversion_json.get("potentialIssues", [])
        database_used = conversion_json.get("databaseUsed", False)
        
        # Generate unit test cases based on the converted code and requirements
        unit_test_prompt = create_unit_test_prompt(
            target_language,
            converted_code,
            business_requirements,
            technical_requirements
        )
        
        unit_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
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
            ],
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        # Log the complete raw unit test response
        logger.info("=== RAW UNIT TEST RESPONSE ===")
        logger.info(json.dumps(unit_test_response.model_dump(), indent=2))
        
        # Parse the JSON response
        unit_test_content = unit_test_response.choices[0].message.content.strip()
        try:
            unit_test_json = json.loads(unit_test_content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse unit test JSON directly")
            unit_test_json = extract_json_from_response(unit_test_content)
        
        unit_test_code_raw= unit_test_json.get("unitTestCode", "")
        unit_test_code = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", unit_test_code_raw.strip())
        
        # Generate functional test cases based on business requirements
        functional_test_prompt = create_functional_test_prompt(
            target_language,
            converted_code,
            business_requirements
        )
        
        functional_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
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
            ],
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        # Log the complete raw functional test response
        logger.info("=== RAW FUNCTIONAL TEST RESPONSE ===")
        logger.info(json.dumps(functional_test_response.model_dump(), indent=2))
        
        # Parse the JSON response
        functional_test_content = functional_test_response.choices[0].message.content.strip()
        try:
            functional_test_json = json.loads(functional_test_content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse functional test JSON directly")
            functional_test_json = extract_json_from_response(functional_test_content)
        
        # Build the complete response
        return jsonify({
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
        })

    except Exception as e:
        logger.error(f"Error in code conversion or test generation: {str(e)}")
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
    
    # This should match the languages in the frontend
    languages = [
        {"name": "COBOL", "icon": "📋"},
        {"name": "Java", "icon": "☕"},
        {"name": "C#", "icon": "🔷"}, 
    ]
    
    return jsonify({"languages": languages})


@app.route("/cobo/generate-tests", methods=["POST"])
def generate_tests():
    """Endpoint to generate test cases for already converted code"""
    
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    target_language = data.get("targetLanguage")
    converted_code = data.get("convertedCode")
    business_requirements = data.get("businessRequirements", "")
    technical_requirements = data.get("technicalRequirements", "")
    
    if not all([target_language, converted_code]):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        # Generate unit test cases
        unit_test_prompt = create_unit_test_prompt(
            target_language,
            converted_code,
            business_requirements,
            technical_requirements
        )
        
        unit_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert test engineer specializing in writing unit tests for {target_language}. "
                              f"You create comprehensive unit tests that verify all business logic and edge cases. "
                              f"Return your response in JSON format with the following structure:\n"
                              f"{{\n"
                              f'  "unitTestCode": "The complete unit test code here",\n'
                              f'  "testCases": [\n'
                              f'    {{"id": "TC1", "description": "Test case description", "expectedResult": "Expected outcome"}},\n'
                              f'    {{"id": "TC2", "description": "Another test case", "expectedResult": "Expected outcome"}}\n'
                              f'  ]\n'
                              f"}}"
                },
                {"role": "user", "content": unit_test_prompt}
            ],
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        # Generate functional test cases
        functional_test_prompt = create_functional_test_prompt(
            target_language,
            converted_code,
            business_requirements
        )
        
        functional_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert QA engineer specializing in creating functional tests for {target_language} applications. "
                              f"You create comprehensive test scenarios that verify the application meets all business requirements. "
                              f"Focus on user journey tests and acceptance criteria. "
                              f"Please Donot respond in # format1 Please genrate in numeric and bullet points format in json"
                              f"Return your response in JSON format with the following structure:\n"
                              f"{{\n"
                              f'  "functionalTests": [\n'
                              f'    {{"id": "FT1", "title": "Test scenario title", "steps": ["Step 1", "Step 2"], "expectedResult": "Expected outcome"}},\n'
                              f'    {{"id": "FT2", "title": "Another test scenario", "steps": ["Step 1", "Step 2"], "expectedResult": "Expected outcome"}}\n'
                              f'  ]\n'
                              f"}}"
                },
                {"role": "user", "content": functional_test_prompt}
            ],
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON responses
        unit_test_content = unit_test_response.choices[0].message.content.strip()
        functional_test_content = functional_test_response.choices[0].message.content.strip()
        
        try:
            unit_test_json = json.loads(unit_test_content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse unit test JSON directly")
            unit_test_json = extract_json_from_response(unit_test_content)
            
        try:
            functional_test_json = json.loads(functional_test_content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse functional test JSON directly")
            functional_test_json = extract_json_from_response(functional_test_content)
        
        # Extract the unit test code
        unit_test_code = unit_test_json.get("unitTestCode", "")
        
        return jsonify({
            "unitTests": unit_test_code,
            "unitTestDetails": unit_test_json,
            "functionalTests": functional_test_json,
            "targetLanguage": target_language
        })
        
    except Exception as e:
        logger.error(f"Error in test generation: {str(e)}")
        return jsonify({"error": f"Test generation failed: {str(e)}"}), 500


if __name__ == "__main__":
    # Use environment variables for configuration in production
    port = int(os.environ.get("PORT", 8010))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    logger.info(f"Starting Flask app on port {port}, debug mode: {debug}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=debug  
    )