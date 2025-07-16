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
    for key, info in converted_code.items():
        if isinstance(info, dict):
            file_name = info.get("FileName", "")
            if file_name.endswith(".cs"):
                content = info.get("content", "")
                match = re.search(r'namespace ([^\s{]+)', content)
                if match:
                    return match.group(1)
    proj = converted_code.get("ProjectFile") or converted_code.get("Project")
    if proj and isinstance(proj, dict):
        content = proj.get("content", "")
        match = re.search(r'<RootNamespace>(.*?)</RootNamespace>', content)
        if match:
            return match.group(1)
        file_name = proj.get("FileName")
        if file_name and file_name.endswith(".csproj"):
            return file_name[:-7]
    return "Project"

def flatten_converted_code(converted_code, unit_test_code=None):
    """Create a standard .NET 8 folder structure and save it to the filesystem."""
    files = {}
    project_name = "ConvertedApp"  # Default project name
    test_project_name = f"{project_name}.Tests"

    # Standard .NET 8 folder structure
    folders = {
        "Controllers": [],
        "Services": [],
        "Models": [],
        "Data": [],
        "Configuration": [],
        "Program.cs": None,
        "appsettings.json": None,
    }

    # Process each file in converted_code
    for file_info in converted_code:  # Iterate over the list
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
        elif file_name in ["Program.cs", "appsettings.json"]:
            files[f"{project_name}/{file_name}"] = content
        elif "Controller" in file_name:
            folders["Controllers"].append(file_info)
            files[f"{project_name}/Controllers/{file_name}"] = content
        elif "Service" in file_name:
            folders["Services"].append(file_info)
            files[f"{project_name}/Services/{file_name}"] = content
        elif "Model" in file_name or "Entity" in file_name:
            folders["Models"].append(file_info)
            files[f"{project_name}/Models/{file_name}"] = content
        elif "Repository" in file_name or "Context" in file_name:
            folders["Data"].append(file_info)
            files[f"{project_name}/Data/{file_name}"] = content
        else:
            files[path] = content

    # Add test project if unit_test_code is provided
    if unit_test_code:
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
        files[f"{test_project_name}/{test_project_name}.csproj"] = test_csproj_content
        files[f"{test_project_name}/Tests/UnitTests.cs"] = unit_test_code

        # Add solution file
        sln_content = f"""
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
    GlobalSection
    GlobalSection(ProjectConfigurationPlatforms) = postSolution
        {{11111111-1111-1111-1111-111111111111}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
        {{11111111-1111-1111-1111-111111111111}}.Debug|Any CPU.Build.0 = Debug|Any CPU
        {{11111111-1111-1111-1111-111111111111}}.Release|Any CPU.ActiveCfg = Release|Any CPU
        {{11111111-1111-1111-1111-111111111111}}.Release|Any CPU.Build.0 = Release|Any CPU
        {{22222222-2222-2222-2222-222222222222}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
        {{22222222-2222-2222-2222-222222222222}}.Debug|Any CPU.Build.0 = Debug|Any CPU
        {{22222222-2222-2222-2222-222222222222}}.Release|Any CPU.ActiveCfg = Release|Any CPU
        {{22222222-2222-2222-2222-222222222222}}.Release|Any CPU.Build.0 = Release|Any CPU
    GlobalSection
EndGlobal
"""
        files[f"{project_name}.sln"] = sln_content.strip()

    # Save files to the filesystem
    output_dir = os.path.join("output", "converted", project_id)
    os.makedirs(output_dir, exist_ok=True)
    for file_path, content in files.items():
        full_path = os.path.join(output_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved file: {full_path}")

    return files

    
@bp.route("/convert", methods=["POST"])
def convert_cobol_to_csharp():
    try:
        data = request.json
        global project_id  # Note: Using global is not ideal; consider passing project_id explicitly
        project_id = data.get("projectId")
        if not project_id:
            logger.error("Project ID is missing in request")
            return jsonify({"error": "Project ID is missing. Please upload files first.", "files": {}}), 400

        # Load analysis data
        analysis_path = os.path.join("output", "analysis", project_id, "cobol_analysis.json")
        if not os.path.exists(analysis_path):
            logger.error(f"No analysis data found for project: {project_id}")
            return jsonify({"error": "No analysis data found. Please run analysis first.", "files": {}}), 400
        
        with open(analysis_path, "r", encoding="utf-8") as f:
            cobol_json = json.load(f)

        # Handle sourceCode field
        source_code = data.get("sourceCode", {})
        if isinstance(source_code, str):
            try:
                source_code = json.loads(source_code)  # Attempt to parse if it's a JSON string
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse sourceCode JSON: {str(e)}")
                return jsonify({"error": "Invalid sourceCode format. Expected a JSON object.", "files": {}}), 400

        # Extract COBOL code
        if not isinstance(source_code, dict):
            logger.error("sourceCode must be a dictionary")
            return jsonify({"error": "sourceCode must be a dictionary with file contents.", "files": {}}), 400

        cobol_code_list = [content for content in source_code.values() if isinstance(content, str)]
        if not cobol_code_list:
            logger.error("No valid COBOL code found in sourceCode")
            return jsonify({"error": "No valid COBOL code found for conversion.", "files": {}}), 400

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
        """

        # Call Azure OpenAI
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview"
        )
        
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

        conversion_response = client.chat.completions.create(
            model="gpt-4o",
            messages=conversion_msgs,
            temperature=0.3,
            max_tokens=8000
        )

        logger.info(f"=== C# CONVERSION - GPT INTERACTION ===")
        logger.info(f"Model: gpt-4o")
        logger.info(f"Response ID: {conversion_response.id}")
        logger.info(f"Usage: {conversion_response.usage}")
        logger.info(f"Finish Reason: {conversion_response.choices[0].finish_reason}")

        converted_json = extract_json_from_response(conversion_response.choices[0].message.content)

        # Save converted code JSON
        output_dir = os.path.join("output", "converted", project_id)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "converted_csharp.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(converted_json, f, indent=2)
        logger.info(f"Converted C# code saved to: {output_path}")

        # Create and save .NET folder structure
        files = flatten_converted_code(converted_json.get("converted_code", []), converted_json.get("unit_tests", ""))

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
        return jsonify({"error": str(e), "files": {}}), 500

@bp.route("/converted-files/<base_name>", methods=["GET"])
def get_converted_files(base_name):
    """Return the file tree and contents for a given conversion (by base_name) from ConvertedCode."""
    import os
    from flask import jsonify
    
    converted_code_dir = os.path.join(output_dir, "ConvertedCode")
    base_dir = os.path.join(converted_code_dir, base_name)
    if not os.path.exists(base_dir):
        files = [f for f in os.listdir(converted_code_dir) if f.startswith(base_name)]
        file_tree = {"files": {}}
        for file in files:
            file_path = os.path.join(converted_code_dir, file)
            if os.path.isfile(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    file_tree["files"][file] = f.read()
        return jsonify(file_tree)
    file_tree = {"files": {}}
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, base_dir)
            with open(file_path, "r", encoding="utf-8") as f:
                file_tree["files"][rel_path] = f.read()
    return jsonify(file_tree)