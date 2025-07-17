from flask import Blueprint, request, jsonify, current_app
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
import uuid

bp = Blueprint('conversion', __name__, url_prefix='/cobo')

# Initialize OpenAI.
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def save_json_response(cobol_filename, json_obj):
    """Save the full JSON response to the json_output directory, using the COBOL filename as base."""
    base_dir = os.path.dirname(output_dir)
    json_output_dir = os.path.join(base_dir, "json_output")
    os.makedirs(json_output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else f"converted_{int(time.time())}"
    output_filename = f"{base_name}_output.json"
    output_path = os.path.join(json_output_dir, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_obj, f, indent=2, ensure_ascii=False)
    return output_path



def build_conversion_instructions():
    """Build basic conversion instructions"""
    return """
BASIC CONVERSION INSTRUCTIONS:
1. Convert COBOL code to modern .NET 8 patterns
2. Use standard .NET conventions and best practices
3. Ensure proper error handling and validation
4. Follow SOLID principles and clean architecture
"""

def extract_project_name(converted_code, cobol_filename=None):
    import re
    def to_pascal_case(text):
        if not text:
            return ''
        parts = re.split(r"[\s._-]+", text)
        return ''.join(p.capitalize() for p in parts if p)

    # 1. Try to use the input COBOL file name if available and not generic
    if cobol_filename:
        base = os.path.splitext(os.path.basename(cobol_filename))[0]
        if base and len(base) > 2 and base.lower() not in ["input", "project", "yourprojectname"]:
            return to_pascal_case(base)

    # 2. Fallback: use the .csproj file name if present
    for key, info in converted_code.items():
        if isinstance(info, dict):
            file_name = info.get("FileName", "")
            if file_name.endswith(".csproj"):
                return to_pascal_case(file_name[:-7])
        elif isinstance(info, list):
            for file_obj in info:
                if isinstance(file_obj, dict):
                    file_name = file_obj.get("FileName", "")
                    if file_name.endswith(".csproj"):
                        return to_pascal_case(file_name[:-7])
    # 3. Fallback: 'Project'
    return "Project"

def flatten_converted_code(converted_code, unit_test_code=None):
    files = {}
    project_name = extract_project_name(converted_code)
    
    # Standard .NET project structure mapping
    folder_mapping = {
        "Entities": "Models",
        "Repositories": "Repositories/Interfaces", 
        "RepositoryImpls": "Repositories",
        "Services": "Services/Interfaces",
        "ServiceImpls": "Services",
        "Controllers": "Controllers",
        "DbContexts": "Data",
        "Programs": "",  # Root level
        "Startups": "",  # Root level
        "AppSettings": "",  # Root level
        "AppSettingsDevs": "",  # Root level
        "ProjectFiles": ""  # Root level
    }
    
    # Process each section of the converted code
    for section, info in converted_code.items():
        if section == "Dependencies":
            continue  # Skip Dependencies.txt
            
        folder_path = folder_mapping.get(section, section)
        
        if isinstance(info, list):
            # Handle array of file objects
            for file_obj in info:
                if isinstance(file_obj, dict):
                    file_name = file_obj.get("FileName") or f"{section}.cs"
                    content = file_obj.get("content", "")
                    file_path = file_obj.get("Path", "")
                    # Use Path property if present
                    if file_path:
                        rel_path = os.path.join(project_name, file_path, file_name).replace("\\", "/")
                    elif folder_path:
                        rel_path = f"{project_name}/{folder_path}/{file_name}"
                    else:
                        rel_path = f"{project_name}/{file_name}"
                    files[rel_path] = content
                        
        elif isinstance(info, dict):
            # Handle single file object
            file_name = info.get("FileName") or f"{section}.cs"
            content = info.get("content", "")
            file_path = info.get("Path", "")
            if file_path:
                rel_path = os.path.join(project_name, file_path, file_name).replace("\\", "/")
            elif folder_path:
                rel_path = f"{project_name}/{folder_path}/{file_name}"
            else:
                rel_path = f"{project_name}/{file_name}"
            files[rel_path] = content
    
    # Add unit test project structure if unit tests are provided
    if unit_test_code and unit_test_code.strip():
        test_project_folder = f"{project_name}.Tests"
        test_csproj_name = f"{project_name}.Tests.csproj"
        
        # Create test project file
        test_csproj_content = f'''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
    <IsTestProject>true</IsTestProject>
  </PropertyGroup>
  
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
    <PackageReference Include="xunit" Version="2.4.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.4.5" />
    <PackageReference Include="Moq" Version="4.20.70" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.InMemory" Version="8.0.0" />
  </ItemGroup>
  
  <ItemGroup>
    <ProjectReference Include="../{project_name}/{project_name}.csproj" />
  </ItemGroup>
</Project>'''
        
        # Add test files
        files[f"{test_project_folder}/UnitTests.cs"] = unit_test_code
        files[f"{test_project_folder}/{test_csproj_name}"] = test_csproj_content
        
        # Add solution file at the root
        sln_content = f'''Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31912.275
MinimumVisualStudioVersion = 10.0.40219.1

Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}", "{project_name}\\{project_name}.csproj", "{{11111111-1111-1111-1111-111111111111}}"
EndProject

Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}.Tests", "{project_name}.Tests\\{project_name}.Tests.csproj", "{{22222222-2222-2222-2222-222222222222}}"
EndProject

Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Debug|Any CPU = Debug|Any CPU
		Release|Any CPU = Release|Any CPU
	EndGlobalSection
	
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		{{11111111-1111-1111-1111-111111111111}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{11111111-1111-1111-1111-111111111111}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{11111111-1111-1111-1111-111111111111}}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{{11111111-1111-1111-1111-111111111111}}.Release|Any CPU.Build.0 = Release|Any CPU
		{{22222222-2222-2222-2222-222222222222}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{22222222-2222-2222-2222-222222222222}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{22222222-2222-2222-2222-222222222222}}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{{22222222-2222-2222-2222-222222222222}}.Release|Any CPU.Build.0 = Release|Any CPU
	EndGlobalSection
EndGlobal'''
        
        files[f"{project_name}.sln"] = sln_content
    
    return files

@bp.route("/convert", methods=["POST"])
def convert_code():
    """Enhanced endpoint to convert COBOL code to .NET 8 using comprehensive analysis results"""
    
    conversion_start_time = time.time()
    conversion_logger = logging.getLogger('conversion')
    logger.info("Starting code conversion process")

    try:
        conversion_id = str(uuid.uuid4())
        data = request.json
        log_request_details("ENHANCED CODE CONVERSION", data)
        
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

        logger.info(f"Converting {source_language} to {target_language} - {len(source_code) if source_code else 0} characters")

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
            logger.info(f"📊 Database operations detected in COBOL code. Including DB setup in conversion.")
            db_setup_template = get_db_template("C#")
            log_processing_step("Database template retrieved", {
                "target_language": "C#",
                "template_length": len(db_setup_template)
            })
        else:
            logger.info(f"📋 No database operations detected in COBOL code. Skipping DB setup.")
            db_setup_template = ""
        
        # Create a code converter instance
        converter = create_code_converter(client, AZURE_OPENAI_DEPLOYMENT_NAME)
    
        base_prompt = create_code_conversion_prompt(
            source_language, "C#", source_code,
            db_setup_template
        )

        # Add database-specific instructions
        database_instruction = (
            "\n\nIMPORTANT: Only include database initialization code if the source COBOL code contains "
            "database or SQL operations. If the code is a simple algorithm (like sorting, calculation, etc.) "
            "without any database interaction, do NOT include any database setup code in the converted .NET 8 code."
        )

        # Build conversion instructions
        conversion_instructions = build_conversion_instructions()

        # Combine all prompt parts
        final_prompt = base_prompt + database_instruction + conversion_instructions

        # Create system message for code conversion
        system_message = (
            "You are an expert COBOL to .NET 8 code converter. "
            "You convert legacy COBOL code to modern .NET 8 applications while maintaining all business logic. "
            "Only include database setup/initialization if the original COBOL code uses databases or SQL. "
            "For simple algorithms or calculations without database operations, do NOT add any database code. "
            "Generate a complete .NET 8 application structure following clean architecture, DDD principles, and best practices. "
            "Include Entity Framework Core models, repositories, services, controllers, and configuration files as needed. "
            "Please generate the database connection string for MySQL Server. Ensure the model definitions do not use precision attributes. "
            "The code should be compatible with .NET 8, and all necessary dependencies should be included in the .csproj file. "
            "Follow standard .NET patterns and conventions to ensure scalable, maintainable code. "
            "IMPORTANT: Use standard .NET folder structure - do NOT create separate folders for each file. "
            "Return your response in JSON format always with the following structure:\n"
            "{\n"
            '  "convertedCode": {\n'
            '    "Entities": [\n'
            '      {\n'
            '        "FileName": "EntityName.cs",\n'
            '        "content": "// Entity content here"\n'
            '      }\n'
            '    ],\n'
            '    "Repositories": [\n'
            '      {\n'
            '        "FileName": "IRepositoryName.cs",\n'
            '        "content": "// Repository interface content here"\n'
            '      }\n'
            '    ],\n'
            '    "RepositoryImpls": [\n'
            '      {\n'
            '        "FileName": "RepositoryName.cs",\n'
            '        "content": "// Repository implementation content here"\n'
            '      }\n'
            '    ],\n'
            '    "Services": [\n'
            '      {\n'
            '        "FileName": "IServiceName.cs",\n'
            '        "content": "// Service interface content here"\n'
            '      }\n'
            '    ],\n'
            '    "ServiceImpls": [\n'
            '      {\n'
            '        "FileName": "ServiceName.cs",\n'
            '        "content": "// Service implementation content here"\n'
            '      }\n'
            '    ],\n'
            '    "Controllers": [\n'
            '      {\n'
            '        "FileName": "ControllerName.cs",\n'
            '        "content": "// Controller content here"\n'
            '      }\n'
            '    ],\n'
            '    "DbContexts": [\n'
            '      {\n'
            '        "FileName": "ApplicationDbContext.cs",\n'
            '        "content": "// DbContext content here"\n'
            '      }\n'
            '    ],\n'
            '    "Programs": [\n'
            '      {\n'
            '        "FileName": "Program.cs",\n'
            '        "content": "// Program.cs content here"\n'
            '      }\n'
            '    ],\n'
            '    "Startups": [\n'
            '      {\n'
            '        "FileName": "Startup.cs",\n'
            '        "content": "// Startup.cs content here (if needed)"\n'
            '      }\n'
            '    ],\n'
            '    "AppSettings": [\n'
            '      {\n'
            '        "FileName": "appsettings.json",\n'
            '        "content": "// appsettings.json content here"\n'
            '      }\n'
            '    ],\n'
            '    "AppSettingsDevs": [\n'
            '      {\n'
            '        "FileName": "appsettings.Development.json",\n'
            '        "content": "// appsettings.Development.json content here"\n'
            '      }\n'
            '    ],\n'
            '    "ProjectFiles": [\n'
            '      {\n'
            '        "FileName": "ProjectName.csproj",\n'
            '        "content": "// .csproj content here"\n'
            '      }\n'
            '    ],\n'
            '    "Dependencies": {\n'
            '      "content": "NuGet packages and .NET dependencies needed"\n'
            '    }\n'
            '  },\n'
            '  "databaseUsed": true,\n'
            '  "conversionNotes": "Detailed notes about the conversion process including comprehensive analysis insights",\n'
            '  "potentialIssues": ["List of potential issues or considerations"],\n'
            '  "analysisEnhanced": true/false,\n'
            '  "architectureRecommendations": ["List of implemented architecture patterns"],\n'
            '  "technologyStack": {"database": "", "caching": "", "messaging": ""}\n'
            "}\n"
            "IMPORTANT: Always return the response in this JSON format. Include proper .NET attributes ([ApiController], [Route], [HttpGet], etc.). "
            "Use Entity Framework Core for database operations. Follow .NET best practices, SOLID principles, and naming conventions. "
            "Implement proper dependency injection, async/await patterns, and error handling. Ensure everything is compatible with .NET 8. "
            "Leverage the provided comprehensive analysis context to create more accurate business domain models and relationships. "
            "Implement the recommended microservices patterns, caching strategies, and security measures from the analysis. "
            "DO NOT include Path property in the JSON response - the folder structure will be handled by the application logic."
        )

        # Build final messages for code conversion
        conversion_messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": final_prompt}
        ]

        # Call Azure OpenAI API for code conversion
        log_processing_step("Calling GPT for code conversion", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 10000,
            "prompt_length": len(final_prompt),
            "target_language": "C#"
        }, 5)

        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=conversion_messages,
            temperature=0.1,
            max_tokens=10000,
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
            logger.info("✅ Code conversion JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("⚠️ Failed to parse code conversion JSON directly")
            conversion_json = extract_json_from_response(conversion_content)
        
        # Extract conversion results
        converted_code = conversion_json.get("convertedCode", {})
        conversion_notes = conversion_json.get("conversionNotes", "")
        potential_issues = conversion_json.get("potentialIssues", [])
        database_used = conversion_json.get("databaseUsed", False)

        # Save converted code to file (if original filename is provided)
        cobol_filename = data.get("cobolFilename") or data.get("sourceFilename")
        base_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else "ConvertedCode"
        # Use uuid for output folder
        converted_code_dir = os.path.join(output_dir, conversion_id)
        os.makedirs(converted_code_dir, exist_ok=True)
        
        # Add this before the file saving loop
        logger.info(f"🔍 Converted code structure: {list(converted_code.keys())}")
        logger.info(f"📊 Converted code content preview: {str(converted_code)[:500]}...")
        # Save the full JSON response
        base_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else f"converted_{int(time.time())}"
        json_filename = f"{base_name}_llm_output.json"
        json_path = os.path.join(converted_code_dir, json_filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(conversion_json, f, indent=2, ensure_ascii=False)
        
        # Extract and save each code section
        for section, section_data in converted_code.items():
            if isinstance(section_data, list):
                # Handle array of file objects
                for file_obj in section_data:
                    if isinstance(file_obj, dict):
                        file_name = file_obj.get("FileName") or f"{section}.txt"
                        file_path = file_obj.get("Path") or ""
                        content = file_obj.get("content", "")
                        
                        if content:  # Only save if there's actual content
                            # Compose full path
                            section_dir = os.path.join(converted_code_dir, file_path)
                            os.makedirs(section_dir, exist_ok=True)
                            section_file_path = os.path.join(section_dir, file_name)
                            
                            try:
                                with open(section_file_path, 'w', encoding='utf-8') as f:
                                    f.write(content)
                                logger.info(f"✅ Saved file: {section_file_path}")
                            except Exception as e:
                                logger.error(f"❌ Failed to save file {section_file_path}: {e}")
            elif isinstance(section_data, dict):
                # Handle single file object
                file_name = section_data.get("FileName") or f"{section}.txt"
                file_path = section_data.get("Path") or ""
                content = section_data.get("content", "")
                
                if content:  # Only save if there's actual content
                    # Compose full path
                    section_dir = os.path.join(converted_code_dir, file_path)
                    os.makedirs(section_dir, exist_ok=True)
                    section_file_path = os.path.join(section_dir, file_name)
                    
                    try:
                        with open(section_file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"✅ Saved file: {section_file_path}")
                    except Exception as e:
                        logger.error(f"❌ Failed to save file {section_file_path}: {e}")
        
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
        
        # Only keep Controllers and Services for unit test generation
        controllers = converted_code.get("Controllers", [])
        services = converted_code.get("Services", [])
        print("Below is controller for unit test case generation");
        print(controllers)
        print(services)

        # Compose a minimal dict to pass to the unit test prompt
        unit_test_input = {
            "Controllers": controllers,
            "Services": services
        }
      


        unit_test_prompt = create_unit_test_prompt(
            "C#",
            unit_test_input,
        )
        
        # Unit test system message
        unit_test_system = (
            "You are an expert test engineer specializing in writing comprehensive unit tests for .NET 8 applications. "
            "You create unit tests that verify all business logic, edge cases, and domain rules. "
            "Return your response in JSON format with the following structure:\n"
            "{\n"
            '  "unitTestCode": "The complete unit test code here",\n'
            '  "testDescription": "Description of the test strategy",\n'
            '  "coverage": ["List of functionalities covered by the tests"],\n'
            '  "businessRuleTests": ["List of business rules being tested"]\n'
            "}"
        )
        
        # Prepare unit test messages
        unit_test_messages = [
            {"role": "system", "content": unit_test_system},
            {"role": "user", "content": unit_test_prompt}
        ]
        
        log_processing_step("Calling GPT for unit test generation", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 3000,
            "prompt_length": len(unit_test_prompt)
        }, 9)
        
        unit_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=unit_test_messages,
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        log_gpt_interaction("Unit Test Generation", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          unit_test_messages, unit_test_response, 9)
        
        # Parse unit test response
        log_processing_step("Parsing unit test response", {
            "response_length": len(unit_test_response.choices[0].message.content)
        }, 10)
        
        unit_test_content = unit_test_response.choices[0].message.content.strip()
        try:
            unit_test_json = json.loads(unit_test_content)
            logger.info("✅ Unit test JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("⚠️ Failed to parse unit test JSON directly")
            unit_test_json = extract_json_from_response(unit_test_content)
        
        unit_test_code_raw = unit_test_json.get("unitTestCode", "")
        unit_test_code = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", unit_test_code_raw.strip())
        
        log_processing_step("Unit test generation completed", {
            "unit_test_code_length": len(unit_test_code),
            "test_description": unit_test_json.get("testDescription", "")[:100] + "..." if len(unit_test_json.get("testDescription", "")) > 100 else unit_test_json.get("testDescription", ""),
            "coverage_items": len(unit_test_json.get("coverage", [])),
            "business_rule_tests": len(unit_test_json.get("businessRuleTests", []))
        }, 11)
        
        # Generate functional test cases
        log_processing_step("Creating functional test prompt", {
            "target_language": "C#",
        }, 12)
        
        functional_test_prompt = create_functional_test_prompt(
            "C#",
            unit_test_input
        )
        
        # Functional test system message
        functional_test_system = (
            "You are an expert QA engineer specializing in creating functional tests for .NET 8 applications. "
            "You create comprehensive test scenarios that verify the application meets all business requirements. "
            "Focus on user journey tests, acceptance criteria, and business domain validation. "
            "Return your response in JSON format with the following structure:\n"
            "{\n"
            '  "functionalTests": [\n'
            '    {"id": "FT1", "title": "Test scenario title", "steps": ["Step 1", "Step 2"], "expectedResult": "Expected outcome", "businessRule": "Related business rule"},\n'
            '    {"id": "FT2", "title": "Another test scenario", "steps": ["Step 1", "Step 2"], "expectedResult": "Expected outcome", "businessRule": "Related business rule"}\n'
            '  ],\n'
            '  "testStrategy": "Description of the overall testing approach",\n'
            '  "domainCoverage": ["List of business domain areas covered"]\n'
            "}"
        )
        
        # Prepare functional test messages
        functional_test_messages = [
            {"role": "system", "content": functional_test_system},
            {"role": "user", "content": functional_test_prompt}
        ]
        
        log_processing_step("Calling GPT for functional test generation", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 3000,
            "prompt_length": len(functional_test_prompt)
        }, 12)
        
        functional_test_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=functional_test_messages,
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        log_gpt_interaction("Functional Test Generation", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          functional_test_messages, functional_test_response, 12)
        
        # Parse functional test response
        log_processing_step("Parsing functional test response", {
            "response_length": len(functional_test_response.choices[0].message.content)
        }, 13)
        
        functional_test_content = functional_test_response.choices[0].message.content.strip()
        try:
            functional_test_json = json.loads(functional_test_content)
            logger.info("✅ Functional test JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("⚠️ Failed to parse functional test JSON directly")
            functional_test_json = extract_json_from_response(functional_test_content)
        
        log_processing_step("Functional test generation completed", {
            "functional_tests_count": len(functional_test_json.get("functionalTests", [])),
            "test_strategy_length": len(functional_test_json.get("testStrategy", "")),
            "domain_coverage": len(functional_test_json.get("domainCoverage", []))
        }, 14)
        
        # Build the final response
        conversion_end_time = time.time()
        total_time = conversion_end_time - conversion_start_time
        
        log_processing_step("Building final response", {
            "total_conversion_time": f"{total_time:.2f} seconds",
            "converted_code_length": len(str(converted_code)),
            "unit_tests_length": len(unit_test_code),
            "functional_tests_count": len(functional_test_json.get("functionalTests", [])),
            "database_used": database_used
        }, 15)
        
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
            "databaseUsed": database_used,
        }
        result["files"] = flatten_converted_code(converted_code, unit_test_code)
        # Save the full JSON response to output directory
        try:
            json_output_path = save_json_response(cobol_filename, result)
            logger.info(f"💾 JSON response saved to: {json_output_path}")
        except Exception as save_json_exc:
            logger.warning(f"⚠️ Failed to save JSON response: {save_json_exc}")
        
        conversion_logger.info("="*80)
        conversion_logger.info("✅ CODE CONVERSION COMPLETED SUCCESSFULLY")
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
        
        logger.error(f"❌ Error in code conversion or test generation: {str(e)}")
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        
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

@bp.route("/converted-files/<base_name>", methods=["GET"])
def get_converted_files(base_name):
    """Return the file tree and contents for a given conversion (by base_name) from ConvertedCode."""
    import os
    from flask import jsonify
    
    converted_code_dir = os.path.join(output_dir, "ConvertedCode")
    base_dir = os.path.join(converted_code_dir, base_name)
    if not os.path.exists(base_dir):
        # Fallback: try to find files with base_name as prefix (for flat structure)
        files = [f for f in os.listdir(converted_code_dir) if f.startswith(base_name)]
        file_tree = {"files": {}}
        for file in files:
            file_path = os.path.join(converted_code_dir, file)
            if os.path.isfile(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    file_tree["files"][file] = f.read()
        return jsonify(file_tree)
    # Recursively walk the directory
    file_tree = {"files": {}}
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, base_dir)
            with open(file_path, "r", encoding="utf-8") as f:
                file_tree["files"][rel_path] = f.read()
    return jsonify(file_tree)