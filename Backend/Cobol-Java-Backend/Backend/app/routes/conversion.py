from flask import Blueprint, request, jsonify, current_app
from ..config import logger, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, output_dir
from openai import AzureOpenAI
import logging
import os
from ..utils.code_converter import create_code_converter
from ..utils.prompts import create_code_conversion_prompt, create_unit_test_prompt, create_functional_test_prompt
from ..utils.logs import log_request_details, log_processing_step, log_gpt_interaction
from ..utils.response import extract_json_from_response
from ..utils.db_usage import detect_database_usage
from ..utils.db_templates import get_db_template
from ..utils.rag_indexer import load_vector_store, query_vector_store
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

def build_conversion_instructions():
    """Build basic conversion instructions"""
    return """
BASIC CONVERSION INSTRUCTIONS:
1. Convert COBOL code to modern .NET 8 patterns
2. Use standard .NET conventions and best practices
3. Ensure proper error handling and validation
4. Follow SOLID principles and clean architecture
"""

def extract_project_name(converted_code):
    """Extract project name from converted code"""
    if isinstance(converted_code, list) and len(converted_code) > 0:
        for file_info in converted_code:
            if isinstance(file_info, dict):
                file_name = file_info.get("file_name", "")
                if file_name.endswith(".csproj"):
                    return file_name[:-7]  # Remove .csproj extension
                elif file_name.endswith(".cs"):
                    content = file_info.get("content", "")
                    match = re.search(r'namespace ([^\s{]+)', content)
                    if match:
                        return match.group(1)
    return "ConvertedApp"

def flatten_converted_code(converted_code, unit_test_code=None, project_id=None):
    """Create a standard .NET 8 folder structure and save it to the filesystem."""
    files = {}
    project_name = extract_project_name(converted_code)
    test_project_name = f"{project_name}.Tests"

    # Process each file in converted_code
    if isinstance(converted_code, list):
        for file_info in converted_code:
            if isinstance(file_info, dict):
                file_name = file_info.get("file_name", "")
                content = file_info.get("content", "")
                path = file_info.get("path", "")

                # Ensure path is relative to project root
                if path.startswith("src/"):
                    path = path.replace("src/", f"{project_name}/")
                elif not path.startswith(project_name):
                    path = f"{project_name}/{path}"

                # Categorize files based on type
                if file_name.endswith(".csproj"):
                    files[f"{project_name}/{file_name}"] = content
                elif file_name in ["Program.cs", "appsettings.json", "Startup.cs"]:
                    files[f"{project_name}/{file_name}"] = content
                elif "Controller" in file_name:
                    files[f"{project_name}/Controllers/{file_name}"] = content
                elif "Service" in file_name:
                    files[f"{project_name}/Services/{file_name}"] = content
                elif "Model" in file_name or "Entity" in file_name:
                    files[f"{project_name}/Models/{file_name}"] = content
                elif "Repository" in file_name or "Context" in file_name:
                    files[f"{project_name}/Data/{file_name}"] = content
                else:
                    files[path] = content

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
  </ItemGroup>
</Project>'''
        files[f"{project_name}/{project_name}.csproj"] = csproj_content

    # Add test project if unit_test_code is provided
    if unit_test_code:
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
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="../{project_name}/{project_name}.csproj" />
  </ItemGroup>
</Project>'''
        files[f"{test_project_name}/{test_project_name}.csproj"] = test_csproj_content
        files[f"{test_project_name}/UnitTests.cs"] = unit_test_code

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

@bp.route("/convert", methods=["POST"])
def convert_cobol_to_csharp():
    try:
        data = request.json
        project_id = data.get("projectId")
        
        if not project_id:
            logger.error("Project ID is missing in request")
            return jsonify({"error": "Project ID is missing. Please upload files first.", "files": {}}), 400

        logger.info(f"Starting conversion for project: {project_id}")

        # Load analysis data
        analysis_path = os.path.join("output", "analysis", project_id, "cobol_analysis.json")
        if not os.path.exists(analysis_path):
            logger.error(f"No analysis data found for project: {project_id}")
            return jsonify({"error": "No analysis data found. Please run analysis first.", "files": {}}), 400
        
        with open(analysis_path, "r", encoding="utf-8") as f:
            cobol_json = json.load(f)
        
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
        cobol_analysis_str = json.dumps(cobol_json, indent=2)
        business_requirements = json.dumps(data.get("businessRequirements", {}), indent=2)
        technical_requirements = json.dumps(data.get("technicalRequirements", {}), indent=2)

        # Load RAG context
        vector_store = load_vector_store(project_id)
        rag_context = ""
        standards_context = ""
        if vector_store:
            rag_results = query_vector_store(vector_store, "Relevant COBOL program and C# conversion patterns", k=5)
            rag_context = "\n\nRAG CONTEXT:\n" + "\n".join([f"Source: {r.metadata['source']}\n{r.page_content}\n" for r in rag_results])
            standards_results = query_vector_store(vector_store, "Relevant coding standards and guidelines", k=3)
            standards_context = "\n\nSTANDARDS CONTEXT:\n" + "\n".join([f"Source: {r.metadata['source']}\n{r.page_content}\n" for r in standards_results])
            logger.info("Added RAG and standards context")

        # Detect database usage and get DB template
        db_usage = detect_database_usage(cobol_code_str, source_language="COBOL")
        db_type = db_usage.get("db_type", "none")
        db_setup_template = get_db_template("C#") if db_usage.get("has_db", False) else ""

        # Create conversion prompt
        conversion_prompt = f"""
        Convert the following COBOL code to C# (.NET 8), adhering to the business and technical requirements.
        
        Source Language: COBOL
        Target Language: C#
        
        COBOL Code:
        {cobol_code_str}
        
        COBOL Analysis:
        {cobol_analysis_str}
        
        Business Requirements:
        {business_requirements}
        
        Technical Requirements:
        {technical_requirements}
        
        Database Setup Template:
        {db_setup_template}
        
        {rag_context}
        {standards_context}
        
        Please provide a complete C# .NET 8 solution with proper folder structure.
        """

        # Call Azure OpenAI for conversion
        conversion_msgs = [
            {
                "role": "system",
                "content": (
                    "You are an expert in COBOL to C# migration. "
                    "Convert the provided COBOL code to C# (.NET 8), adhering to the business, technical requirements, and coding standards. "
                    "Use the COBOL analysis JSON to understand program structure, variables, and dependencies. "
                    "Incorporate the provided database setup template for database operations. "
                    "Organize the output in a standard .NET 8 folder structure (e.g., Controllers, Services, Models, Data). "
                    "Output the C# code as a JSON object with the following structure:\n"
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
                    "  \"unit_tests\": \"string\",\n"
                    "  \"functional_tests\": \"string\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": conversion_prompt
            }
        ]

        logger.info("Calling Azure OpenAI for conversion")
        
        conversion_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=conversion_msgs,
            temperature=0.3,
            max_tokens=8000
        )

        logger.info(f"Conversion response received. Usage: {conversion_response.usage}")

        # Extract and parse the JSON response
        converted_json = extract_json_from_response(conversion_response.choices[0].message.content)
        
        if not converted_json:
            logger.error("Failed to extract JSON from conversion response")
            return jsonify({"error": "Failed to process conversion response.", "files": {}}), 500

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
            converted_json.get("unit_tests", ""),
            project_id
        )
        
        logger.info(f"Generated {len(files)} files for .NET project")

        return jsonify({
            "status": "success",
            "project_id": project_id,
            "converted_code": converted_json.get("converted_code", []),
            "conversion_notes": converted_json.get("conversion_notes", []),
            "unit_tests": converted_json.get("unit_tests", ""),
            "functional_tests": converted_json.get("functional_tests", ""),
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
        converted_code_dir = os.path.join(output_dir, "converted", base_name)
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