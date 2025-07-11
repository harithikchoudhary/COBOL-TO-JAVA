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

def get_enhanced_context_from_analysis():
    """Enhanced context retrieval with comprehensive analysis integration"""
    enhanced_context = ""
    
    try:
        # Get analysis manager from current app context
        if hasattr(current_app, 'comprehensive_analysis_data'):
            analysis_data = current_app.comprehensive_analysis_data
            analysis_manager = analysis_data.get('analysis_manager')
            
            if analysis_manager and hasattr(analysis_manager, 'conversion_context') and analysis_manager.conversion_context:
                logger.info("🔗 Using comprehensive analysis results for enhanced conversion")
                
                # Get conversion-ready context
                enhanced_context = analysis_manager.get_conversion_context_for_code()
                
                if enhanced_context:
                    logger.info(f"✅ Enhanced context generated ({len(enhanced_context)} characters)")
                else:
                    logger.warning("⚠️ No enhanced context available despite analysis manager presence")
                    
            else:
                logger.info("📋 No comprehensive analysis results available for enhancement")
        else:
            # Fallback: try to get from analysis manager directly
            from ..routes.analysis import analysis_manager
            
            if analysis_manager and hasattr(analysis_manager, 'conversion_context') and analysis_manager.conversion_context:
                logger.info("🔗 Using fallback analysis manager for enhanced conversion")
                enhanced_context = analysis_manager.get_conversion_context_for_code()
                
                if enhanced_context:
                    logger.info(f"✅ Fallback enhanced context generated ({len(enhanced_context)} characters)")
                
    except Exception as e:
        logger.warning(f"⚠️ Could not retrieve comprehensive analysis context: {e}")
        enhanced_context = ""
    
    return enhanced_context

def build_analysis_instructions(enhanced_context):
    """Build comprehensive analysis instructions"""
    analysis_instructions = ""
    
    if enhanced_context:
        analysis_instructions += f"\n\nENHANCED CONTEXT:\n{enhanced_context}\n"
    
    try:
        from ..routes.analysis import analysis_manager
        if analysis_manager and hasattr(analysis_manager, 'analysis_results'):
            full = analysis_manager.analysis_results
            full_json = json.dumps(full, indent=2)[:2000]  # Truncate to prevent token overflow
            
            # Get RAG contexts
            standards_ctx = getattr(analysis_manager, 'get_standards_context', lambda x, k: "")(enhanced_context[:200], k=3)
            project_ctx = getattr(analysis_manager, 'get_project_context', lambda x, k: "")(enhanced_context[:200], k=5)

            analysis_instructions += f"""
COMPREHENSIVE ANALYSIS RESULTS:
{full_json}

STANDARDS CONTEXT:
{standards_ctx}

PROJECT CONTEXT:
{project_ctx}

CRITICAL INSTRUCTIONS:
1. Honor ALL architecture recommendations from the analysis
2. Map COBOL structures to .NET entities as specified
3. Implement all identified business rules and CICS patterns
4. Follow the derived namespace and project conventions
5. Use the recommended technology stack and patterns
"""
    except Exception as e:
        logger.warning(f"⚠️ Could not build full analysis instructions: {e}")
        # Fallback to just enhanced context if available
        if not enhanced_context:
            analysis_instructions = "\n\nNo comprehensive analysis context available.\n"
    
    return analysis_instructions

def extract_project_name(converted_code):
    # Prefer namespace from Program.cs or any .cs file
    for key, info in converted_code.items():
        if isinstance(info, dict):
            file_name = info.get("FileName", "")
            if file_name.endswith(".cs"):
                content = info.get("content", "")
                match = re.search(r'namespace ([^\s{]+)', content)
                if match:
                    return match.group(1)
    # Fallback: Try Project.csproj
    proj = converted_code.get("ProjectFile") or converted_code.get("Project")
    if proj and isinstance(proj, dict):
        content = proj.get("content", "")
        match = re.search(r'<RootNamespace>(.*?)</RootNamespace>', content)
        if match:
            return match.group(1)
        # Fallback: use file name without extension
        file_name = proj.get("FileName")
        if file_name and file_name.endswith(".csproj"):
            return file_name[:-7]
    return "Project"

def flatten_converted_code(converted_code, unit_test_code=None):
    files = {}
    top_level_files = [
        "Program.cs",
        "Startup.cs",
        "appsettings.json",
        "appsettings.Development.json"
    ]
    project_name = extract_project_name(converted_code)
    # Find the relevant service or controller filename for the test file
    test_file_name = "UnitTests.cs"
    test_folder = "Services"
    if "ServiceImpl" in converted_code and isinstance(converted_code["ServiceImpl"], dict):
        service_file = converted_code["ServiceImpl"].get("FileName")
        if service_file and service_file.endswith(".cs"):
            test_file_name = service_file.replace(".cs", "Tests.cs")
            test_folder = "Services"
    elif "Controller" in converted_code and isinstance(converted_code["Controller"], dict):
        controller_file = converted_code["Controller"].get("FileName")
        if controller_file and controller_file.endswith(".cs"):
            test_file_name = controller_file.replace(".cs", "Tests.cs")
            test_folder = "Controllers"
    for section, info in converted_code.items():
        if isinstance(info, dict):
            file_name = info.get("FileName") or f"{section}.txt"
            if file_name == "Dependencies.txt":
                continue  # Skip Dependencies.txt
            file_path = info.get("Path") or ""
            # Place any .csproj file in the project_name/ directory, like Program.cs
            if file_name.lower().endswith(".csproj"):
                rel_path = f"{project_name}/{file_name}"
            elif file_name in top_level_files:
                rel_path = f"{project_name}/{file_name}"
            else:
                rel_path = os.path.join(project_name, file_path, file_name).replace("\\", "/")
            content = info.get("content", "")
            files[rel_path] = content
    # Add unit test code and test .csproj with the correct name and folder
    test_project_folder = f"{project_name}.Tests"
    test_csproj_name = f"{project_name}.Tests.csproj"
    test_csproj_content = f'''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
    <PackageReference Include="xunit" Version="2.4.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.4.5" />
    <PackageReference Include="Moq" Version="4.20.70" />
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="../{project_name}/{project_name}.csproj" />
  </ItemGroup>
</Project>'''
    if unit_test_code and unit_test_code.strip():
        files[f"{test_project_folder}/{test_folder}/{test_file_name}"] = unit_test_code
        files[f"{test_project_folder}/{test_csproj_name}"] = test_csproj_content
        # Add a minimal .sln file at the root referencing both projects
        sln_content = f"""
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31912.275
MinimumVisualStudioVersion = 10.0.40219.1
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}", "{project_name}/{project_name}.csproj", "{{11111111-1111-1111-1111-111111111111}}"
EndProject
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}.Tests", "{project_name}.Tests/{project_name}.Tests.csproj", "{{22222222-2222-2222-2222-222222222222}}"
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
EndGlobal
"""
        files[f"{project_name}.sln"] = sln_content.strip()
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
        business_requirements = data.get("businessRequirements", "")
        technical_requirements = data.get("technicalRequirements", "")
        vsam_definition = data.get("vsam_definition", "")

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

        # Get comprehensive enhanced context from analysis results
        log_processing_step("Retrieving comprehensive analysis context", {
            "has_analysis_manager": True
        }, 2)
        
        enhanced_context = get_enhanced_context_from_analysis()

        # Analyze the code to detect if it contains database operations
        log_processing_step("Analyzing source code for database operations", {
            "source_language": source_language,
            "code_preview": source_code[:200] + "..." if len(source_code) > 200 else source_code,
            "enhanced_context_available": bool(enhanced_context)
        }, 3)
        
        has_database = detect_database_usage(source_code, source_language)
        
        log_processing_step("Database detection completed", {
            "database_detected": has_database,
            "will_include_db_template": has_database
        }, 4)
        
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
        
        # Create base prompt for code conversion
        log_processing_step("Creating enhanced code conversion prompt", {
            "including_db_template": bool(db_setup_template),
            "business_req_length": len(str(business_requirements)),
            "technical_req_length": len(str(technical_requirements)),
            "enhanced_context_length": len(enhanced_context)
        }, 5)
        
        base_prompt = create_code_conversion_prompt(
            source_language, "C#", source_code,
            business_requirements, technical_requirements, db_setup_template
        )

        # Add database-specific instructions
        database_instruction = (
            "\n\nIMPORTANT: Only include database initialization code if the source COBOL code contains "
            "database or SQL operations. If the code is a simple algorithm (like sorting, calculation, etc.) "
            "without any database interaction, do NOT include any database setup code in the converted .NET 8 code."
        )

        # Build comprehensive analysis instructions
        analysis_instructions = build_analysis_instructions(enhanced_context)

        # Combine all prompt parts
        final_prompt = base_prompt + database_instruction + analysis_instructions

        # Create system message for code conversion
        system_message = (
            "You are an expert COBOL to .NET 8 code converter with comprehensive analysis capabilities. "
            "You have access to detailed business analysis, CICS patterns, RAG-enhanced context, and architectural recommendations. "
            "You convert legacy COBOL code to modern, domain-aware .NET 8 applications while maintaining all business logic. "
            "Only include database setup/initialization if the original COBOL code uses databases or SQL. "
            "For simple algorithms or calculations without database operations, do NOT add any database code. "
            "Generate a complete .NET 8 application structure following clean architecture, DDD principles, and best practices. "
            "Include Entity Framework Core models, repositories, services, controllers, and configuration files as needed. "
            "Please generate the database connection string for MySQL Server. Ensure the model definitions do not use precision attributes. "
            "The code should be compatible with .NET 8, and all necessary dependencies should be included in the .csproj file. "
            "Use the provided comprehensive analysis context to create more accurate entity relationships and service boundaries. "
            "Implement the recommended microservices patterns and technology stack from the analysis. "
            "Follow the architectural recommendations to ensure scalable, maintainable code. "
            "Return your response in JSON format always with the following structure:\n"
            "{\n"
            '  "convertedCode": {\n'
            '    "Entity": {"FileName": "","Path": "Models/", "content": ""},\n'
            '    "Repository": {"FileName": "","Path": "Repositories/Interfaces/", "content": ""},\n'
            '    "RepositoryImpl": {"FileName": "","Path": "Repositories/", "content": ""},\n'
            '    "Service": {"FileName": "","Path": "Services/Interfaces/", "content": ""},\n'
            '    "ServiceImpl": {"FileName": "","Path": "Services/", "content": ""},\n'
            '    "Controller": {"FileName": "","Path": "Controllers/", "content": ""},\n'
            '    "DbContext": {"FileName": "","Path": "Data/", "content": ""},\n'
            '    "Program": {"FileName": "","Path": "./", "content": ""},\n'
            '    "Startup": {"FileName": "","Path": "./", "content": ""},\n'
            '    "AppSettings": {"FileName": "","Path": "./", "content": ""},\n'
            '    "AppSettingsDev": {"FileName": "","Path": "./", "content": ""},\n'
            '    "ProjectFile": {"FileName": "","Path": "./", "content": ""},\n'
            '    "Dependencies": {"content": "NuGet packages and .NET dependencies needed"}\n'
            "  },\n"
            '  "databaseUsed": true/false,\n'
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
            "Implement the recommended microservices patterns, caching strategies, and security measures from the analysis."
        )

        # Build final messages for code conversion
        conversion_messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": final_prompt}
        ]

        # Call Azure OpenAI API for enhanced code conversion
        log_processing_step("Calling GPT for enhanced code conversion with comprehensive analysis", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "max_tokens": 4000,
            "prompt_length": len(final_prompt),
            "target_language": "C#",
            "analysis_enhanced": bool(enhanced_context)
        }, 6)

        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=conversion_messages,
            temperature=0.1,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )

        log_gpt_interaction("Enhanced Code Conversion with Comprehensive Analysis", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          conversion_messages, response, 6)

        # Parse the JSON response
        log_processing_step("Parsing enhanced code conversion response", {
            "response_length": len(response.choices[0].message.content)
        }, 7)
        
        conversion_content = response.choices[0].message.content.strip()
        try:
            conversion_json = json.loads(conversion_content)
            logger.info("✅ Enhanced code conversion JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("⚠️ Failed to parse enhanced code conversion JSON directly")
            conversion_json = extract_json_from_response(conversion_content)
        
        # Extract conversion results
        converted_code = conversion_json.get("convertedCode", {})
        conversion_notes = conversion_json.get("conversionNotes", "")
        potential_issues = conversion_json.get("potentialIssues", [])
        database_used = conversion_json.get("databaseUsed", False)
        analysis_enhanced = conversion_json.get("analysisEnhanced", bool(enhanced_context))
        architecture_recommendations = conversion_json.get("architectureRecommendations", [])
        technology_stack = conversion_json.get("technologyStack", {})

        # Save converted code to file (if original filename is provided)
        cobol_filename = data.get("cobolFilename") or data.get("sourceFilename")
        base_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else "ConvertedCode"
        # Use uuid for output folder
        converted_code_dir = os.path.join(output_dir, conversion_id)
        os.makedirs(converted_code_dir, exist_ok=True)
        
        # Save the full JSON response
        base_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else f"converted_{int(time.time())}"
        json_filename = f"{base_name}_llm_output.json"
        json_path = os.path.join(converted_code_dir, json_filename)
        # with open(json_path, 'w', encoding='utf-8') as f:
        #     json.dump(conversion_json, f, indent=2, ensure_ascii=False)
        
        # Extract and save each code section
        for section, info in converted_code.items():
            if isinstance(info, dict):
                file_name = info.get("FileName") or f"{section}.txt"
                file_path = info.get("Path") or ""
                content = info.get("content", "")
                # Compose full path
                section_dir = os.path.join(converted_code_dir, file_path)
                os.makedirs(section_dir, exist_ok=True)
                section_file_path = os.path.join(section_dir, file_name)
                with open(section_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
        
        log_processing_step("Enhanced code conversion completed", {
            "converted_code_length": len(str(converted_code)),
            "conversion_notes_length": len(conversion_notes),
            "potential_issues_count": len(potential_issues),
            "database_used": database_used,
            "analysis_enhanced": analysis_enhanced,
            "architecture_recommendations_count": len(architecture_recommendations)
        }, 8)
        
        # Generate unit test cases with enhanced context
        log_processing_step("Creating enhanced unit test prompt", {
            "target_language": "C#",
            "code_length": len(str(converted_code))
        }, 9)
        
        unit_test_prompt = create_unit_test_prompt(
            "C#",
            converted_code,
            business_requirements,
            technical_requirements
        )
        
        # Add analysis context to unit test prompt
        if enhanced_context:
            unit_test_prompt += f"\n\nAdditional Context from Analysis:\n{enhanced_context[:1000]}..."
        
        # Unit test system message
        unit_test_system = (
            "You are an expert test engineer specializing in writing comprehensive unit tests for .NET 8 applications. "
            "You create unit tests that verify all business logic, edge cases, and domain rules. "
            "Use the provided analysis context to create more accurate and business-aware tests. "
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
        
        log_processing_step("Calling GPT for enhanced unit test generation", {
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
        
        log_gpt_interaction("Enhanced Unit Test Generation", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          unit_test_messages, unit_test_response, 9)
        
        # Parse unit test response
        log_processing_step("Parsing enhanced unit test response", {
            "response_length": len(unit_test_response.choices[0].message.content)
        }, 10)
        
        unit_test_content = unit_test_response.choices[0].message.content.strip()
        try:
            unit_test_json = json.loads(unit_test_content)
            logger.info("✅ Enhanced unit test JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("⚠️ Failed to parse enhanced unit test JSON directly")
            unit_test_json = extract_json_from_response(unit_test_content)
        
        unit_test_code_raw = unit_test_json.get("unitTestCode", "")
        unit_test_code = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", unit_test_code_raw.strip())
        
        log_processing_step("Enhanced unit test generation completed", {
            "unit_test_code_length": len(unit_test_code),
            "test_description": unit_test_json.get("testDescription", "")[:100] + "..." if len(unit_test_json.get("testDescription", "")) > 100 else unit_test_json.get("testDescription", ""),
            "coverage_items": len(unit_test_json.get("coverage", [])),
            "business_rule_tests": len(unit_test_json.get("businessRuleTests", []))
        }, 11)
        
        # Generate functional test cases with enhanced context
        log_processing_step("Creating enhanced functional test prompt", {
            "target_language": "C#",
            "business_requirements_available": bool(business_requirements)
        }, 12)
        
        functional_test_prompt = create_functional_test_prompt(
            "C#",
            converted_code,
            business_requirements
        )
        
        # Add analysis context to functional test prompt
        if enhanced_context:
            functional_test_prompt += f"\n\nBusiness Domain Context from Analysis:\n{enhanced_context[:1000]}..."
        
        # Functional test system message
        functional_test_system = (
            "You are an expert QA engineer specializing in creating functional tests for .NET 8 applications. "
            "You create comprehensive test scenarios that verify the application meets all business requirements. "
            "Focus on user journey tests, acceptance criteria, and business domain validation. "
            "Use the provided analysis context to create domain-aware functional tests. "
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
        
        log_processing_step("Calling GPT for enhanced functional test generation", {
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
        
        log_gpt_interaction("Enhanced Functional Test Generation", AZURE_OPENAI_DEPLOYMENT_NAME, 
                          functional_test_messages, functional_test_response, 12)
        
        # Parse functional test response
        log_processing_step("Parsing enhanced functional test response", {
            "response_length": len(functional_test_response.choices[0].message.content)
        }, 13)
        
        functional_test_content = functional_test_response.choices[0].message.content.strip()
        try:
            functional_test_json = json.loads(functional_test_content)
            logger.info("✅ Enhanced functional test JSON parsed successfully")
        except json.JSONDecodeError:
            logger.warning("⚠️ Failed to parse enhanced functional test JSON directly")
            functional_test_json = extract_json_from_response(functional_test_content)
        
        log_processing_step("Enhanced functional test generation completed", {
            "functional_tests_count": len(functional_test_json.get("functionalTests", [])),
            "test_strategy_length": len(functional_test_json.get("testStrategy", "")),
            "domain_coverage": len(functional_test_json.get("domainCoverage", []))
        }, 14)
        
        # Build the enhanced response
        conversion_end_time = time.time()
        total_time = conversion_end_time - conversion_start_time
        
        log_processing_step("Building enhanced final response", {
            "total_conversion_time": f"{total_time:.2f} seconds",
            "converted_code_length": len(str(converted_code)),
            "unit_tests_length": len(unit_test_code),
            "functional_tests_count": len(functional_test_json.get("functionalTests", [])),
            "database_used": database_used,
            "analysis_enhanced": analysis_enhanced
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
            "analysisEnhanced": analysis_enhanced,
            "architectureRecommendations": architecture_recommendations,
            "technologyStack": technology_stack,
            "enhancementContext": {
                "enhanced_context_used": bool(enhanced_context),
                "context_length": len(enhanced_context),
                "analysis_available": True,
                "comprehensive_analysis": True
            },
            "technicalRequirements": technical_requirements
        }
        result["files"] = flatten_converted_code(converted_code, unit_test_code)
        # Save the full JSON response to output directory
        try:
            json_output_path = save_json_response(cobol_filename, result)
            logger.info(f"💾 Enhanced JSON response saved to: {json_output_path}")
        except Exception as save_json_exc:
            logger.warning(f"⚠️ Failed to save enhanced JSON response: {save_json_exc}")
        
        conversion_logger.info("="*80)
        conversion_logger.info("✅ ENHANCED CODE CONVERSION WITH COMPREHENSIVE ANALYSIS COMPLETED SUCCESSFULLY")
        conversion_logger.info(f"⏱️ Total Processing Time: {total_time:.2f} seconds")
        conversion_logger.info(f"📝 Converted Code Length: {len(str(converted_code))} characters")
        conversion_logger.info(f"🧪 Unit Tests Generated: {len(unit_test_code)} characters")
        conversion_logger.info(f"🔍 Functional Tests: {len(functional_test_json.get('functionalTests', []))} scenarios")
        conversion_logger.info(f"💾 Database Usage: {database_used}")
        conversion_logger.info(f"🚀 Analysis Enhanced: {analysis_enhanced}")
        conversion_logger.info(f"🏗️ Architecture Recommendations: {len(architecture_recommendations)}")
        conversion_logger.info("="*80)
        
        logger.info("=== ENHANCED CODE CONVERSION REQUEST COMPLETED SUCCESSFULLY ===")
        return jsonify(result)

    except Exception as e:
        conversion_end_time = time.time()
        total_time = conversion_end_time - conversion_start_time
        
        logger.error(f"❌ Error in enhanced code conversion or test generation: {str(e)}")
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        
        conversion_logger.error("="*80)
        conversion_logger.error("❌ ENHANCED CODE CONVERSION PROCESS FAILED")
        conversion_logger.error(f"⏱️ Time Before Failure: {total_time:.2f} seconds")
        conversion_logger.error(f"🚨 Error: {str(e)}")
        conversion_logger.error(f"📋 Traceback: {traceback.format_exc()}")
        conversion_logger.error("="*80)
        
        return jsonify({
            "status": "error",
            "message": f"Enhanced conversion failed: {str(e)}",
            "convertedCode": "",
            "conversionNotes": "",
            "potentialIssues": [],
            "unitTests": "",
            "unitTestDetails": {},
            "functionalTests": {},
            "sourceLanguage": source_language if 'source_language' in locals() else "",
            "targetLanguage": "C#" if 'target_language' in locals() else "",
            "databaseUsed": False,
            "analysisEnhanced": False
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