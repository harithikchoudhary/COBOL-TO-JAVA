from flask import Blueprint, request, jsonify
from ..config import logger, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME
from ..utils.file_classifier import classify_uploaded_files
from openai import AzureOpenAI
import json
import traceback

bp = Blueprint('analysis', __name__, url_prefix='/cobo')

# Initialize OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def create_business_requirements_prompt(source_language, source_code):
    """
    Creates a prompt for extracting business requirements from COBOL code.
    """
    return f"""
    Analyze the following {source_language} code to extract business requirements for conversion to .NET 8 using Onion Architecture.

    Source Code:
    {source_code}

    Return JSON with:
    {{
      "Overview": {{
        "Purpose of the System": "Primary function and business fit",
        "Context and Business Impact": "Operational context and value"
      }},
      "Objectives": {{
        "Primary Objective": "Main goal",
        "Key Outcomes": "Expected results"
      }},
      "Business Rules & Requirements": {{
        "Business Purpose": "Objective of the module",
        "Business Rules": "List of inferred rules",
        "Impact on System": "Effect on overall operation",
        "Constraints": "Business limitations"
      }},
      "Assumptions & Recommendations": {{
        "Assumptions": "Presumptions about data/processes",
        "Recommendations": "Modernization suggestions"
      }},
      "Expected Output": {{
        "Output": "Main outputs (e.g., reports, updates)",
        "Business Significance": "Importance to business"
      }}
    }}
    """

def create_technical_requirements_prompt(source_language, target_language, source_code):
    """
    Creates a prompt for extracting technical requirements for .NET 8 migration.
    """
    return f"""
    Analyze the following {source_language} code to extract technical requirements for migration to {target_language} using Onion Architecture.

    Source Code:
    {source_code}

    Ensure requirements support:
    - Domain Layer: Entities, interfaces, exceptions (no dependencies)
    - Application Layer: Services, DTOs (depends on Domain)
    - Infrastructure Layer: Repositories, DbContext (implements Application interfaces)
    - Presentation Layer: Controllers (depends on Application)
    - Dependency Injection: Configured in Program.cs
    - Namespace: Company.Project.[Layer]
    - Entity Framework Core for database operations if detected

    Return JSON with:
    {{
      "technicalRequirements": [
        {{"id": "TR1", "description": "Requirement description", "complexity": "High/Medium/Low"}}
      ]
    }}
    """

@bp.route("/analyze-requirements", methods=["POST"])
def analyze_requirements():
    """Endpoint to analyze COBOL code and extract requirements for .NET 8 Onion Architecture."""
    try:
        data = request.json
        logger.info(f"Received request data: {data}")
        
        if not data:
            logger.error("No data provided")
            return jsonify({"error": "No data provided"}), 400
        
        file_data = data.get("file_data")
        if isinstance(file_data, str):
            try:
                file_data = json.loads(file_data)
                logger.info("Converted file_data to dictionary")
            except json.JSONDecodeError:
                logger.error("Invalid file_data format")
                return jsonify({"error": "Invalid file_data format"}), 400
        
        if not isinstance(file_data, dict):
            logger.error(f"file_data is not a dict: {type(file_data)}")
            return jsonify({"error": "Invalid file_data format"}), 400
        
        parse_file_data = classify_uploaded_files(file_data)
        source_language = data.get("sourceLanguage")
        target_language = data.get("targetLanguage")
        source_code_infos = parse_file_data.get("COBOL Code", [])
        source_code = [f["content"] for f in source_code_infos if isinstance(f, dict) and "content" in f]
        vsam_definition = parse_file_data.get("VSAM Definitions", [])
        
        if not all([source_language, source_code]):
            logger.error("Missing required fields")
            return jsonify({"error": "Missing required fields"}), 400
        
        source_code_str = "\n".join(source_code) if isinstance(source_code, list) else source_code
        
        business_prompt = create_business_requirements_prompt(source_language, source_code_str)
        technical_prompt = create_technical_requirements_prompt(source_language, target_language, source_code_str)
        
        business_messages = [
            {"role": "system", "content": "You are an expert in analyzing COBOL code for business requirements."},
            {"role": "user", "content": business_prompt}
        ]
        
        logger.info("Calling Azure OpenAI for business requirements")
        business_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=business_messages,
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        technical_messages = [
            {
                "role": "system",
                "content": f"You are an expert in COBOL to .NET 8 migration using Onion Architecture. "
                          f"Extract technical requirements ensuring proper layer separation and dependency inversion."
            },
            {"role": "user", "content": technical_prompt}
        ]
        
        logger.info("Calling Azure OpenAI for technical requirements")
        technical_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=technical_messages,
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        business_content = business_response.choices[0].message.content.strip()
        technical_content = technical_response.choices[0].message.content.strip()
        
        try:
            business_json = json.loads(business_content)
            logger.info("Business requirements parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse business JSON")
            business_json = {"error": "Failed to parse business requirements"}
        
        try:
            technical_json = json.loads(technical_content)
            logger.info("Technical requirements parsed successfully")
        except json.JSONDecodeError:
            logger.warning("Failed to parse technical JSON")
            technical_json = {"technicalRequirements": []}
        
        db_indicators = ['EXEC SQL', 'INTO', 'FROM', 'WHERE', 'SELECT', 'FILE SECTION', 'VSAM']
        has_database = any(indicator in source_code_str.upper() for indicator in db_indicators) or len(vsam_definition) > 0
        technical_requirements = technical_json.get("technicalRequirements", [])
        
        required_keywords = [
            "Domain Layer", "Application Layer", "Infrastructure Layer", "Presentation Layer",
            "Dependency Injection", "Namespace", "Dependency Inversion"
        ]
        requirements_text = json.dumps(technical_requirements).lower()
        if has_database and "Entity Framework Core" not in requirements_text:
            technical_requirements.append({
                "id": f"TR{len(technical_requirements) + 1}",
                "description": "Implement database operations using Entity Framework Core in the Infrastructure Layer.",
                "complexity": "High"
            })
        
        for kw in required_keywords:
            if kw.lower() not in requirements_text:
                requirement_id = len(technical_requirements) + 1
                if kw == "Domain Layer":
                    technical_requirements.append({
                        "id": f"TR{requirement_id}",
                        "description": "Implement Domain Layer with entities, interfaces, and exceptions.",
                        "complexity": "Medium"
                    })
                elif kw == "Application Layer":
                    technical_requirements.append({
                        "id": f"TR{requirement_id}",
                        "description": "Implement Application Layer with services and DTOs, depending on Domain.",
                        "complexity": "Medium"
                    })
                elif kw == "Infrastructure Layer":
                    technical_requirements.append({
                        "id": f"TR{requirement_id}",
                        "description": "Implement Infrastructure Layer with repositories and DbContext.",
                        "complexity": "High"
                    })
                elif kw == "Presentation Layer":
                    technical_requirements.append({
                        "id": f"TR{requirement_id}",
                        "description": "Implement Presentation Layer with controllers depending on Application.",
                        "complexity": "Medium"
                    })
                elif kw == "Dependency Injection":
                    technical_requirements.append({
                        "id": f"TR{requirement_id}",
                        "description": "Configure dependency injection in Program.cs.",
                        "complexity": "Medium"
                    })
                elif kw == "Namespace":
                    technical_requirements.append({
                        "id": f"TR{requirement_id}",
                        "description": "Use consistent namespace structure (Company.Project.[Layer]).",
                        "complexity": "Low"
                    })
                elif kw == "Dependency Inversion":
                    technical_requirements.append({
                        "id": f"TR{requirement_id}",
                        "description": "Enforce dependency inversion with interfaces.",
                        "complexity": "Medium"
                    })
        
        technical_json["technicalRequirements"] = technical_requirements
        
        result = {
            "businessRequirements": business_json,
            "technicalRequirements": technical_json,
            "sourceLanguage": source_language,
            "targetLanguage": target_language,
        }
        
        logger.info("Analysis completed successfully")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500