from flask import Blueprint, request, jsonify, current_app
from ..config import logger, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, output_dir
from openai import AzureOpenAI
import logging
import os
from ..utils.prompts import  create_unit_test_prompt, create_functional_test_prompt, get_conversion_instructions
from ..utils.logs import log_request_details, log_processing_step, log_gpt_interaction
from ..utils.response import extract_json_from_response
from ..utils.db_usage import detect_database_usage
from ..utils.db_templates import get_db_template
from ..utils.rag_indexer import load_vector_store, query_vector_store
from ..utils.prompts import  create_cobol_to_dotnet_conversion_prompt
import json
import re
import time
import traceback
import uuid
from pathlib import Path

bp = Blueprint('conversion', __name__, url_prefix='/cobo')

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


def extract_project_name(target_structure):
    """Extract project name from target structure"""
    if isinstance(target_structure, dict):
        return target_structure.get("project_name", "BankingSystem")
    return "BankingSystem"

def flatten_converted_code(converted_code, unit_test_code=None, project_id=None, target_structure=None):
    """Create a standard .NET 8 folder structure and save it to the filesystem."""
    files = {}
    
    # Extract project name from target structure
    project_name = extract_project_name(target_structure) if target_structure else "BankingSystem"
    test_project_name = f"{project_name}.Tests"

    # Process each file in converted_code
    if isinstance(converted_code, list):
        for file_info in converted_code:
            if isinstance(file_info, dict):
                file_name = file_info.get("file_name", "")
                content = file_info.get("content", "")
                path = file_info.get("path", "")

                # Create proper file path based on target structure
                if path:
                    if not path.startswith(project_name):
                        file_path = f"{project_name}/{path}/{file_name}"
                    else:
                        file_path = f"{path}/{file_name}"
                else:
                    file_path = f"{project_name}/{file_name}"

                files[file_path] = content

    # Add main project file if not exists
    if not any(f.endswith(".csproj") for f in files.keys()):
        csproj_content = f'''<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Tools" Version="8.0.0" />
    <PackageReference Include="Microsoft.AspNetCore.Authentication.JwtBearer" Version="8.0.0" />
    <PackageReference Include="Swashbuckle.AspNetCore" Version="6.4.0" />
    <PackageReference Include="Serilog.Extensions.Hosting" Version="8.0.0" />
    <PackageReference Include="Serilog.Sinks.Console" Version="5.0.0" />
    <PackageReference Include="Serilog.Sinks.File" Version="5.0.0" />
  </ItemGroup>
</Project>'''
        files[f"{project_name}/{project_name}.csproj"] = csproj_content

    # Add appsettings.json if not exists
    if not any("appsettings.json" in f for f in files.keys()):
        appsettings_content = '''{
  "ConnectionStrings": {
    "DefaultConnection": "Server=localhost;Database=BankingSystem;Trusted_Connection=true;TrustServerCertificate=true;"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "AllowedHosts": "*"
}'''
        files[f"{project_name}/appsettings.json"] = appsettings_content

    # Add test project csproj file first
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
    files[f"{test_project_name}/{test_project_name}.csproj"] = test_csproj_content

    # Add unit test files if unit_test_code is provided
    if unit_test_code:
        logger.info(f"Processing unit test code: {type(unit_test_code)}")
        
        # Handle different formats of unit_test_code
        if isinstance(unit_test_code, list):
            # Format: [{"fileName": "...", "content": "..."}]
            for test_file in unit_test_code:
                if isinstance(test_file, dict):
                    file_name = test_file.get("fileName")
                    content = test_file.get("content", "")
                    if file_name and content:
                        files[f"{test_project_name}/Tests/{file_name}"] = content
                        logger.info(f"Added unit test file: {file_name}")
        
        elif isinstance(unit_test_code, dict):
            # Handle different dict formats
            if "unitTestFiles" in unit_test_code:
                # Format: {"unitTestFiles": [{"fileName": "...", "content": "..."}]}
                for test_file in unit_test_code["unitTestFiles"]:
                    if isinstance(test_file, dict):
                        file_name = test_file.get("fileName")
                        content = test_file.get("content", "")
                        if file_name and content:
                            files[f"{test_project_name}/{file_name}"] = content
                            logger.info(f"Added unit test file: {file_name}")
            else:
                # Direct content mapping
                for file_name, content in unit_test_code.items():
                    if content:
                        files[f"{test_project_name}/{file_name}"] = content
                        logger.info(f"Added unit test file: {file_name}")
        
        elif isinstance(unit_test_code, str):
            # Single string content - create default file
            if unit_test_code.strip():
                files[f"{test_project_name}/UnitTests.cs"] = unit_test_code
                logger.info("Added single unit test file: UnitTests.cs")
        
        # Add solution file
        sln_content = f'''
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31912.275
MinimumVisualStudioVersion = 10.0.40219.1
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}", "{project_name}/{project_name}.csproj", "{{11111111-1111-1111-1111-111111111111}}"
EndProject
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{test_project_name}", "{test_project_name}/{test_project_name}.csproj", "{{22222222-2222-2222-2222-222222222222}}"
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
'''.strip()
        files[f"{project_name}.sln"] = sln_content

    # Save files to the filesystem
    if project_id:
        output_dir_path = os.path.join("output", "converted", project_id)
        os.makedirs(output_dir_path, exist_ok=True)
        for file_path, content in files.items():
            full_path = os.path.join(output_dir_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Saved file: {full_path}")

    # --- POST-PROCESSING: Ensure appsettings.json and Program.cs are correct ---
    # 1. Move any appsettings.json to the project root
    appsettings_keys = [k for k in files if k.lower().endswith("appsettings.json") and k != f"{project_name}/appsettings.json"]
    for key in appsettings_keys:
        files[f"{project_name}/appsettings.json"] = files[key]
        del files[key]

    # 2. Ensure Program.cs exists in the project root
    program_cs_path = f"{project_name}/Program.cs"
    if not any(k.lower() == program_cs_path.lower() for k in files):
        # Standard .NET 8 minimal hosting model template
        files[program_cs_path] = '''
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllers();
// Add other services, e.g., DbContext, repositories, etc.

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
'''

    return files

def get_source_code_from_project(project_id):
    """Get source code from uploaded project files"""
    try:
        # Load from comprehensive analysis data if available
        if hasattr(current_app, 'comprehensive_analysis_data') and current_app.comprehensive_analysis_data:
            project_data = current_app.comprehensive_analysis_data
            if project_data.get('project_id') == project_id:
                cobol_files = project_data.get('cobol_files', {})
                if cobol_files:
                    logger.info(f"Found {len(cobol_files)} COBOL files in analysis data")
                    return cobol_files
        
        # Fallback: Load from uploads directory
        uploads_dir = Path("uploads") / project_id
        if uploads_dir.exists():
            source_code = {}
            for file_path in uploads_dir.glob("**/*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.cbl', '.cpy', '.jcl']:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        source_code[file_path.name] = f.read()
            
            if source_code:
                logger.info(f"Loaded {len(source_code)} files from uploads directory")
                return source_code
        
        logger.warning(f"No source code found for project {project_id}")
        return {}
        
    except Exception as e:
        logger.error(f"Error getting source code for project {project_id}: {str(e)}")
        return {}

def load_analysis_data(project_id):
    """Load analysis data including cobol_analysis.json, target_structure.json, and business_requirements.json"""
    analysis_data = {}
    
    # Load COBOL analysis
    cobol_analysis_path = os.path.join("output", "analysis", project_id, "cobol_analysis.json")
    if os.path.exists(cobol_analysis_path):
        with open(cobol_analysis_path, "r", encoding="utf-8") as f:
            analysis_data["cobol_analysis"] = json.load(f)
        logger.info(f"Loaded COBOL analysis for project: {project_id}")
    else:
        logger.warning(f"COBOL analysis not found for project: {project_id}")
    
    # Load target structure
    target_structure_path = os.path.join("output", "analysis", project_id, "target_structure.json")
    if os.path.exists(target_structure_path):
        with open(target_structure_path, "r", encoding="utf-8") as f:
            analysis_data["target_structure"] = json.load(f)
        logger.info(f"Loaded target structure for project: {project_id}")
    else:
        logger.warning(f"Target structure not found for project: {project_id}")
    
    # Load business requirements - NEW
    business_requirements_path = os.path.join("output", "analysis", project_id, "business_requirements.json")
    if os.path.exists(business_requirements_path):
        with open(business_requirements_path, "r", encoding="utf-8") as f:
            analysis_data["business_requirements"] = json.load(f)
        logger.info(f"Loaded business requirements for project: {project_id}")
    else:
        logger.warning(f"Business requirements not found for project: {project_id}")
    
    # Load technical requirements - NEW
    technical_requirements_path = os.path.join("output", "analysis", project_id, "technical_requirements.json")
    if os.path.exists(technical_requirements_path):
        with open(technical_requirements_path, "r", encoding="utf-8") as f:
            analysis_data["technical_requirements"] = json.load(f)
        logger.info(f"Loaded technical requirements for project: {project_id}")
    else:
        logger.warning(f"Technical requirements not found for project: {project_id}")
    
    return analysis_data


@bp.route("/convert", methods=["POST"])
def convert_cobol_to_csharp():
    try:
        data = request.json
        project_id = data.get("projectId")
        
        if not project_id:
            logger.error("Project ID is missing in request")
            return jsonify({"error": "Project ID is missing. Please upload files first.", "files": {}}), 400

        logger.info(f"Starting conversion for project: {project_id}")

        # Load analysis data (cobol_analysis.json, target_structure.json, business_requirements.json, technical_requirements.json)
        analysis_data = load_analysis_data(project_id)
        
        if not analysis_data.get("cobol_analysis"):
            logger.error(f"No COBOL analysis data found for project: {project_id}")
            return jsonify({"error": "No analysis data found. Please run analysis first.", "files": {}}), 400
        
        cobol_json = analysis_data["cobol_analysis"]
        target_structure = analysis_data.get("target_structure", {})
        business_requirements = analysis_data.get("business_requirements", {})
        technical_requirements = analysis_data.get("technical_requirements", {})
        
        logger.info(f"Loaded analysis data for project: {project_id}")

        # Get source code - try multiple sources
        source_code = {}
        
        # First try: from request data
        request_source_code = data.get("sourceCode", {})
        if request_source_code:
            logger.info("Using source code from request")
            if isinstance(request_source_code, str):
                try:
                    request_source_code = json.loads(request_source_code)
                except json.JSONDecodeError:
                    logger.error("Failed to parse sourceCode from request")
                    request_source_code = {}
            
            # Extract content from file objects
            for file_name, file_data in request_source_code.items():
                if isinstance(file_data, dict) and 'content' in file_data:
                    source_code[file_name] = file_data['content']
                elif isinstance(file_data, str):
                    source_code[file_name] = file_data
        
        # Second try: from project files
        if not source_code:
            logger.info("Getting source code from project files")
            source_code = get_source_code_from_project(project_id)
        
        # Validate source code
        if not source_code:
            logger.error(f"No source code found for project: {project_id}")
            return jsonify({"error": "No source code found. Please upload COBOL files first.", "files": {}}), 400
        
        # Filter only COBOL-related files
        cobol_code_list = []
        for file_name, content in source_code.items():
            if isinstance(content, str) and content.strip():
                # Check if it's a COBOL file
                if (file_name.lower().endswith(('.cbl', '.cpy', '.jcl')) or 
                    any(keyword in content.upper() for keyword in ['IDENTIFICATION DIVISION', 'PROGRAM-ID', 'PROCEDURE DIVISION', 'WORKING-STORAGE'])):
                    cobol_code_list.append(content)
                    logger.info(f"Added COBOL file: {file_name}")
        
        if not cobol_code_list:
            logger.error("No valid COBOL code found in source files")
            return jsonify({"error": "No valid COBOL code found for conversion.", "files": {}}), 400
        
        logger.info(f"Found {len(cobol_code_list)} COBOL files for conversion")
        
        # Prepare conversion data
        cobol_code_str = "\n".join(cobol_code_list)
        target_structure_str = json.dumps(target_structure, indent=2)
        business_requirements_str = json.dumps(business_requirements, indent=2)
        technical_requirements_str = json.dumps(technical_requirements, indent=2)

        # Load RAG context
        vector_store = load_vector_store(project_id)
        rag_context = ""
        standards_context = ""
        if vector_store:
            rag_results = query_vector_store(vector_store, "Relevant COBOL program and C# conversion patterns", k=5)
            if rag_results:
                rag_context = "\n\nRAG CONTEXT:\n" + "\n".join([f"Source: {r.metadata.get('source', 'unknown')}\n{r.page_content}\n" for r in rag_results])
                standards_results = query_vector_store(vector_store, "Relevant coding standards and guidelines", k=3)
                if standards_results:
                    standards_context = "\n\nSTANDARDS CONTEXT:\n" + "\n".join([f"Source: {r.metadata.get('source', 'unknown')}\n{r.page_content}\n" for r in standards_results])
                logger.info("Added RAG and standards context")
            else:
                logger.warning("No RAG results returned from vector store")

        # Detect database usage and get DB template
        db_usage = detect_database_usage(cobol_code_str, source_language="COBOL")
        db_type = db_usage.get("db_type", "none")
        db_setup_template = get_db_template("C#") if db_usage.get("has_db", False) else ""

        # Create conversion prompt using the imported function
        base_conversion_prompt = create_cobol_to_dotnet_conversion_prompt(cobol_code_str, db_setup_template)
        
        # Enhanced conversion prompt with additional context including business requirements
        conversion_prompt = f"""

        {base_conversion_prompt}
        
        **TARGET STRUCTURE (FOLLOW THIS CLOSELY):**
        {target_structure_str}


        **BUSINESS REQUIREMENTS (CRITICAL - ENSURE ALL BUSINESS LOGIC IS PRESERVED):**
        {business_requirements_str}
        
        **Do's and Don'ts Prompt**
        {get_conversion_instructions()}
        
        **RAG CONTEXT:**
        {rag_context}
        
        **STANDARDS CONTEXT:**
        {standards_context}

        **Important Instructions**
        - Ensure all business logic from the BUSINESS REQUIREMENTS is preserved and converted accurately.
        - Map each business rule to appropriate C# implementation patterns.
        - Use modern .NET 8 patterns and practices while maintaining business functionality.
        - Implement proper error handling and validation as specified in requirements.
        - Follow SOLID principles and clean architecture.
        - Use dependency injection for services and repositories.
        - Implement logging using Serilog.
        - Use Entity Framework Core for database interactions.
        - Ensure all converted code is well-structured and maintainable.
        - Pay special attention to business rules and constraints mentioned in the requirements.
        
        **REQUIRED OUTPUT:** Provide a complete C# .NET 8 solution with proper folder structure that implements all business requirements.
        """

        # Call Azure OpenAI for conversion
        conversion_msgs = [
            {
                "role": "system",
                "content": (
                    "You are an expert COBOL to C# migration specialist with deep knowledge of both mainframe systems and modern .NET development. "
                    "Your task is to convert COBOL applications to modern, scalable C# .NET 8 applications while preserving ALL business logic and requirements. "
                    "You have been provided with comprehensive business requirements analysis - you MUST ensure every business rule and requirement is properly implemented in the C# code. "
                    "You understand enterprise architecture patterns, clean code principles, and modern development practices. "
                    "You MUST follow the provided target structure precisely and create ALL specified components. "
                    "Output your conversion as a JSON object with the following structure:\n"
                    "{\n"
                    "  \"converted_code\": [\n"
                    "    {\n"
                    "      \"file_name\": \"string\",\n"
                    "      \"path\": \"string\",\n"
                    "      \"content\": \"string\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"conversion_notes\": [\n"
                    "    {\"note\": \"string\", \"severity\": \"Info/Warning/Error\"}\n"
                    "  ],\n"
                    "  \"business_rules_implemented\": [\n"
                    "    {\"rule\": \"string\", \"implementation\": \"string\", \"location\": \"string\"}\n"
                    "  ]\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": conversion_prompt
            }
        ]

        logger.info("Calling Azure OpenAI for conversion with business requirements")
        
        conversion_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=conversion_msgs,
            temperature = 0.1
        )

        logger.info(f"Conversion response received. Usage: {conversion_response.usage}")

        # Extract and parse the JSON response
        converted_json = extract_json_from_response(conversion_response.choices[0].message.content)
        
        if not converted_json:
            logger.error("Failed to extract JSON from conversion response")
            return jsonify({"error": "Failed to process conversion response.", "files": {}}), 500

        # --- BEGIN: Unit and Functional Test Generation Integration ---
        # Extract Controllers and Services for test generation
        converted_code = converted_json.get("converted_code", [])
        # Try to extract Controllers and Services from the converted_code list
        controllers = []
        print(controllers)
        services = []
        print(services)
        for file_info in converted_code:
            if isinstance(file_info, dict):
                file_name = file_info.get("file_name", "")
                path = file_info.get("path", "")
                content = file_info.get("content", "")
                # Heuristics: look for 'Controller' or 'Service' in file name or path
                if "controller" in file_name.lower() or "controller" in path.lower():
                    controllers.append({"file_name": file_name, "path": path, "content": content})
                if "service" in file_name.lower() or "service" in path.lower():
                    services.append({"file_name": file_name, "path": path, "content": content})

        # Compose a minimal dict to pass to the unit/functional test prompt
        unit_test_input = {
            "Controllers": controllers,
            "Services": services
        }
        print("[DEBUG] Extracted controllers:", controllers)
        print("[DEBUG] Extracted services:", services)

        # Generate unit test prompt
        print("[DEBUG] Creating unit test prompt with input:", unit_test_input)
        unit_test_prompt = create_unit_test_prompt(
            "C#",
            unit_test_input,
        )
        unit_test_system = (
            "You are an expert test engineer specializing in writing comprehensive unit tests for .NET 8 applications. "
            "For EACH Controller class found, generate a separate unit test file named '[ControllerName]Tests.cs'. "
            "Return your response in JSON as follows:\n"
            "{\n"
            '  "unitTestFiles": [{'
            '       "fileName": "[ControllerName]Tests.cs",'
            '       "content": "...unit test code..."'
            '   }, ...],'
            '  "testDescription": "...",'
            '  "coverage": [...],'
            '  "businessRuleTests": [...]'
            "}\n"
        )

        unit_test_messages = [
            {"role": "system", "content": unit_test_system},
            {"role": "user", "content": unit_test_prompt}
        ]
        print("[DEBUG] Sending unit test messages to LLM:", unit_test_messages)
        try:
            unit_test_response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=unit_test_messages,
                temperature=0.1,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            unit_test_content = unit_test_response.choices[0].message.content.strip()
            print("[DEBUG] Raw unit test LLM response:", unit_test_content)
            try:
                unit_test_json = json.loads(unit_test_content)
                print("[DEBUG] Parsed unit test JSON:", unit_test_json)
                logger.info("✅ Unit test JSON parsed successfully")
            except json.JSONDecodeError:
                logger.warning("⚠️ Failed to parse unit test JSON directly")
                unit_test_json = extract_json_from_response(unit_test_content)
                print("[DEBUG] Extracted unit test JSON via fallback:", unit_test_json)
            # Fix: Extract unit test files correctly from the JSON
            unit_test_code = unit_test_json.get("unitTestFiles")
            if not unit_test_code:
                unit_test_code = unit_test_json.get("unitTestCode", "")
            print("[DEBUG] Final unit test code:", unit_test_code)
        except Exception as e:
            logger.error(f"Unit test generation failed: {e}")
            print("[ERROR] Exception during unit test generation:", e)
            try:
                unit_test_json = json.loads(unit_test_content)
                print("[DEBUG] Exception fallback, parsed unit test JSON:", unit_test_json)
                unit_test_code = unit_test_json.get("unitTestFiles", [])
            except Exception as ex:
                print("[ERROR] Exception fallback also failed:", ex)
                unit_test_json = {}
                unit_test_code = []

        # Generate functional test prompt
        functional_test_prompt = create_functional_test_prompt(
            "C#",
            unit_test_input
        )
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
        functional_test_messages = [
            {"role": "system", "content": functional_test_system},
            {"role": "user", "content": functional_test_prompt}
        ]
        try:
            functional_test_response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=functional_test_messages,
                temperature=0.1,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            functional_test_content = functional_test_response.choices[0].message.content.strip()
            try:
                functional_test_json = json.loads(functional_test_content)
                logger.info("✅ Functional test JSON parsed successfully")
            except json.JSONDecodeError:
                logger.warning("⚠️ Failed to parse functional test JSON directly")
                functional_test_json = extract_json_from_response(functional_test_content)
        except Exception as e:
            logger.error(f"Functional test generation failed: {e}")
            functional_test_json = {}
        # --- END: Unit and Functional Test Generation Integration ---

        # Save converted code JSON
        output_dir_path = os.path.join("output", "converted", project_id)
        os.makedirs(output_dir_path, exist_ok=True)
        output_path = os.path.join(output_dir_path, "converted_csharp.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(converted_json, f, indent=2)
        logger.info(f"Converted C# code saved to: {output_path}")

        # Create and save .NET folder structure
        files = flatten_converted_code(
            converted_json.get("converted_code", []), 
            unit_test_code,
            project_id,
            target_structure
        )
        
        logger.info(f"Generated {len(files)} files for .NET project")

        return jsonify({
            "status": "success",
            "project_id": project_id,
            "converted_code": converted_json.get("converted_code", []),
            "conversion_notes": converted_json.get("conversion_notes", []),
            "unit_tests": unit_test_code,
            "unit_test_details": unit_test_json,
            "functional_tests": functional_test_json,
            "files": files
        })

    except Exception as e:
        logger.error(f"❌ Conversion failed: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "files": {}}), 500

@bp.route("/converted-files/<base_name>", methods=["GET"])
def get_converted_files(base_name):
    """Return the file tree and contents for a given conversion (by base_name) from ConvertedCode."""
    try:
        converted_code_dir = os.path.join("output", "converted", base_name)
        if not os.path.exists(converted_code_dir):
            return jsonify({"error": "Converted files not found"}), 404
        
        file_tree = {"files": {}}
        for root, dirs, files in os.walk(converted_code_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, converted_code_dir)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_tree["files"][rel_path] = f.read()
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
                    file_tree["files"][rel_path] = f"Error reading file: {str(e)}"
        
        return jsonify(file_tree)
    except Exception as e:
        logger.error(f"Error getting converted files: {str(e)}")
        return jsonify({"error": str(e)}), 500