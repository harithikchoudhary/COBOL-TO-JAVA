import logging
import os
import json
import re
import time
import traceback
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from ..config import logger, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME, output_dir
from openai import AzureOpenAI
from ..utils.code_converter import create_code_converter, should_chunk_code
from ..utils.prompts import create_code_conversion_prompt, create_unit_test_prompt, create_functional_test_prompt
from ..utils.logs import log_request_details, log_processing_step, log_gpt_interaction
from ..utils.response import extract_json_from_response
from ..utils.db_usage import detect_database_usage
from ..utils.db_templates import get_db_template
from ..utils.rag_indexer import load_vector_store, query_vector_store
import shutil

bp = Blueprint('conversion', __name__, url_prefix='/cobo')

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def setup_logging(project_id: str = None):
    log_dir = f"output/converted/{project_id}" if project_id else "output/converted"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        filename=f"{log_dir}/conversion.log",
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='a'
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger(__name__)
    logger.addHandler(console)
    return logger

logger = setup_logging()

def save_json_response(cobol_filename, json_obj, project_id=None):
    base_dir = os.path.dirname(output_dir)
    json_output_dir = os.path.join(base_dir, "json_output", project_id if project_id else "")
    os.makedirs(json_output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(cobol_filename))[0] if cobol_filename else f"converted_{int(time.time())}"
    output_filename = f"{base_name}_output.json"
    output_path = os.path.join(json_output_dir, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_obj, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved JSON response to: {output_path}")
    return output_path

def build_conversion_instructions():
    return """
BASIC CONVERSION INSTRUCTIONS:
1. Convert COBOL code to modern .NET 8 patterns
2. Use standard .NET conventions and best practices
3. Ensure proper error handling and validation
4. Follow SOLID principles and clean architecture
5. Preserve COBOL business logic and comments
6. Handle CICS operations with REST API equivalents
7. Use async/await for I/O operations
"""

def extract_project_name(target_structure):
    if isinstance(target_structure, dict):
        return target_structure.get("project_name", "BankingSystem")
    return "BankingSystem"

def flatten_converted_code(converted_code, unit_test_code=None, project_id=None, target_structure=None):
    files = {}
    project_name = extract_project_name(target_structure) if target_structure else "BankingSystem"
    test_project_name = f"{project_name}.Tests"

    if isinstance(converted_code, str):
        converted_code = [{"file_name": "ConvertedCode.cs", "path": "", "content": converted_code}]
    elif isinstance(converted_code, dict) and "convertedCode" in converted_code:
        converted_code = [{"file_name": "ConvertedCode.cs", "path": "", "content": converted_code["convertedCode"]}]

    if isinstance(converted_code, list):
        for file_info in converted_code:
            if isinstance(file_info, dict):
                file_name = file_info.get("file_name", "")
                content = file_info.get("content", "")
                path = file_info.get("path", "")
                if path:
                    if not path.startswith(project_name):
                        file_path = f"{project_name}/{path}/{file_name}"
                    else:
                        file_path = f"{path}/{file_name}"
                else:
                    file_path = f"{project_name}/{file_name}"
                files[file_path] = content

    if target_structure and isinstance(target_structure, dict):
        for cls in target_structure.get("classes", []):
            class_name = cls.get("name", "")
            class_content = f"""
namespace {project_name};
public {cls.get('type', 'class')} {class_name} {{
    // Fields
    {chr(10).join([f"{field.get('access_modifier', 'private')} {field.get('type')} _{field.get('name')};" for field in cls.get('fields', [])])}

    // Methods
    {chr(10).join([f"{method.get('access_modifier', 'public')} {method.get('return_type')} {method.get('name')}({chr(44).join([f"{param.get('type')} {param.get('name')}" for param in method.get('parameters', [])])}) {{}}" for method in cls.get('methods', [])])}
}}
"""
            file_path = f"{project_name}/{class_name}.cs"
            if file_path not in files:
                files[file_path] = class_content
            self.logger.info(f"Generated class file {file_path} from target structure")

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
        logger.info(f"Generated {project_name}.csproj")

    if not any("appsettings.json" in f for f in files.keys()):
        appsettings_content = f'''{{
  "ConnectionStrings": {{
    "DefaultConnection": "Server=localhost;Database={project_name};Trusted_Connection=true;TrustServerCertificate=true;"
  }},
  "Logging": {{
    "LogLevel": {{
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }}
  }},
  "AllowedHosts": "*"
}}'''
        files[f"{project_name}/appsettings.json"] = appsettings_content
        logger.info(f"Generated appsettings.json")

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
    logger.info(f"Generated {test_project_name}.csproj")

    if unit_test_code:
        logger.info(f"Processing unit test code: {type(unit_test_code)}")
        if isinstance(unit_test_code, list):
            for test_file in unit_test_code:
                if isinstance(test_file, dict):
                    file_name = test_file.get("fileName")
                    content = test_file.get("content", "")
                    if file_name and content:
                        files[f"{test_project_name}/Tests/{file_name}"] = content
                        logger.info(f"Added unit test file: {file_name}")
        elif isinstance(unit_test_code, dict):
            if "unitTestFiles" in unit_test_code:
                for test_file in unit_test_code["unitTestFiles"]:
                    if isinstance(test_file, dict):
                        file_name = test_file.get("fileName")
                        content = test_file.get("content", "")
                        if file_name and content:
                            files[f"{test_project_name}/Tests/{file_name}"] = content
                            logger.info(f"Added unit test file: {file_name}")
            else:
                for file_name, content in unit_test_code.items():
                    if content:
                        files[f"{test_project_name}/Tests/{file_name}"] = content
                        logger.info(f"Added unit test file: {file_name}")
        elif isinstance(unit_test_code, str):
            if unit_test_code.strip():
                files[f"{test_project_name}/Tests/UnitTests.cs"] = unit_test_code
                logger.info("Added single unit test file: UnitTests.cs")

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
    logger.info(f"Generated {project_name}.sln")

    if project_id:
        output_dir_path = os.path.join("output", "converted", project_id)
        os.makedirs(output_dir_path, exist_ok=True)
        for file_path, content in files.items():
            full_path = os.path.join(output_dir_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Saved file: {full_path} (size: {len(content)})")
        logger.info(f"Saved {len(files)} files to {output_dir_path}")

    appsettings_keys = [k for k in files if k.lower().endswith("appsettings.json") and k != f"{project_name}/appsettings.json"]
    for key in appsettings_keys:
        files[f"{project_name}/appsettings.json"] = files[key]
        del files[key]

    program_cs_path = f"{project_name}/Program.cs"
    if not any(k.lower() == program_cs_path.lower() for k in files):
        files[program_cs_path] = f'''
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
var app = builder.Build();

if (app.Environment.IsDevelopment())
{{
    app.UseDeveloperExceptionPage();
}}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
'''
        logger.info(f"Generated {program_cs_path}")

    return files

def get_source_code_from_project(project_id):
    try:
        if hasattr(current_app, 'comprehensive_analysis_data') and current_app.comprehensive_analysis_data:
            project_data = current_app.comprehensive_analysis_data
            if project_data.get('project_id') == project_id:
                cobol_files = project_data.get('cobol_files', {})
                if cobol_files:
                    logger.info(f"Found {len(cobol_files)} COBOL files in analysis data")
                    return cobol_files

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
    analysis_data = {}
    cobol_analysis_path = os.path.join("output", "analysis", project_id, "cobol_analysis.json")
    if os.path.exists(cobol_analysis_path):
        with open(cobol_analysis_path, "r", encoding="utf-8") as f:
            analysis_data["cobol_analysis"] = json.load(f)
        logger.info(f"Loaded COBOL analysis for project: {project_id}")
    else:
        logger.warning(f"COBOL analysis not found for project: {project_id}")

    target_structure_path = os.path.join("output", "analysis", project_id, "target_structure.json")
    if os.path.exists(target_structure_path):
        with open(target_structure_path, "r", encoding="utf-8") as f:
            analysis_data["target_structure"] = json.load(f)
        logger.info(f"Loaded target structure for project: {project_id}")
    else:
        logger.warning(f"Target structure not found for project: {project_id}")

    return analysis_data

@bp.route("/convert", methods=["POST"])
def convert_cobol_to_csharp():
    try:
        data = request.json
        project_id = data.get("projectId")
        
        if not project_id:
            logger.error("Project ID is missing in request")
            return jsonify({"error": "Project ID is missing. Please upload files first.", "files": {}}), 400

        logger = setup_logging(project_id)
        logger.info(f"Starting conversion for project: {project_id}")

        analysis_data = load_analysis_data(project_id)
        if not analysis_data.get("cobol_analysis"):
            logger.error(f"No COBOL analysis data found for project: {project_id}")
            return jsonify({"error": "No analysis data found. Please run analysis first.", "files": {}}), 400

        cobol_json = analysis_data["cobol_analysis"]
        target_structure = analysis_data.get("target_structure", {})
        logger.info(f"Loaded analysis data for project: {project_id}")

        source_code = {}
        request_source_code = data.get("sourceCode", {})
        if request_source_code:
            logger.info("Using source code from request")
            if isinstance(request_source_code, str):
                try:
                    request_source_code = json.loads(request_source_code)
                except json.JSONDecodeError:
                    logger.error("Failed to parse sourceCode from request")
                    request_source_code = {}
            for file_name, file_data in request_source_code.items():
                if isinstance(file_data, dict) and 'content' in file_data:
                    source_code[file_name] = file_data['content']
                elif isinstance(file_data, str):
                    source_code[file_name] = file_data

        if not source_code:
            logger.info("Getting source code from project files")
            source_code = get_source_code_from_project(project_id)

        if not source_code:
            logger.error(f"No source code found for project: {project_id}")
            return jsonify({"error": "No source code found. Please upload COBOL files first.", "files": {}}), 400

        cobol_code_list = []
        for file_name, content in source_code.items():
            if isinstance(content, str) and content.strip():
                if (file_name.lower().endswith(('.cbl', '.cpy', '.jcl')) or 
                    any(keyword in content.upper() for keyword in ['IDENTIFICATION DIVISION', 'PROGRAM-ID', 'PROCEDURE DIVISION', 'WORKING-STORAGE'])):
                    cobol_code_list.append(content)
                    logger.info(f"Added COBOL file: {file_name}")

        if not cobol_code_list:
            logger.error("No valid COBOL code found in source files")
            return jsonify({"error": "No valid COBOL code found for conversion.", "files": {}}), 400

        logger.info(f"Found {len(cobol_code_list)} COBOL files for conversion")

        cobol_code_str = "\n".join(cobol_code_list)
        target_structure_str = json.dumps(target_structure, indent=2)

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

        db_usage = detect_database_usage(cobol_code_str, source_language="COBOL")
        db_type = db_usage.get("db_type", "none")
        db_setup_template = get_db_template("C#") if db_usage.get("has_db", False) else ""

        conversion_prompt = f"""
        You are an expert COBOL to C# (.NET 8) migration specialist. Convert the provided COBOL code to a modern, 
        well-structured C# application following the target structure and requirements provided.
        
        IMPORTANT: Use the target structure as your blueprint for organizing the code. Create ALL the files and 
        components specified in the target structure.
        
        **SOURCE CODE:**
        {cobol_code_str}
        
        **TARGET STRUCTURE (FOLLOW THIS CLOSELY):**
        {target_structure_str}
        
        **DATABASE TEMPLATE:**
        {db_setup_template}
        
        **RAG CONTEXT:**
        {rag_context}
        
        **STANDARDS CONTEXT:**
        {standards_context}
        
        **CONVERSION GUIDELINES:**
        1. Follow the target structure exactly - create all specified projects, folders, and files
        2. Map all COBOL data structures to appropriate C# models/entities
        3. Convert all CICS operations to REST API endpoints
        4. Implement proper service layer architecture
        5. Create comprehensive API controllers with proper endpoints
        6. Use Entity Framework Core for data access
        7. Implement proper dependency injection
        8. Add comprehensive error handling and logging
        9. Follow .NET 8 best practices and conventions
        10. Ensure thread safety and async/await patterns
        11. Add proper validation and security measures
        12. Include proper configuration management
        13. Preserve COBOL comments and business logic
        14. Handle large COBOL files by ensuring logical chunking and context-aware merging
        """

        code_converter = create_code_converter(client, AZURE_OPENAI_DEPLOYMENT_NAME)
        if should_chunk_code(cobol_code_str):
            logger.info(f"Code size ({len(cobol_code_str.splitlines())} lines) exceeds threshold, initiating chunking")
            chunks = code_converter.chunk_code(
                cobol_code_str, source_language="COBOL", chunk_size=23500, chunk_overlap=1000, project_id=project_id
            )
            converted_json = code_converter.convert_code_chunks(
                chunks=chunks,
                source_language="COBOL",
                target_language="C#",
                business_requirements=build_conversion_instructions(),
                technical_requirements=target_structure_str,
                db_setup_template=db_setup_template,
                project_id=project_id
            )
        else:
            logger.info("Code size within threshold, converting directly")
            converted_json = code_converter._convert_single_chunk(
                code_chunk=cobol_code_str,
                source_language="COBOL",
                target_language="C#",
                business_requirements=build_conversion_instructions(),
                technical_requirements=target_structure_str,
                db_setup_template=db_setup_template
            )

        if not converted_json.get("convertedCode"):
            logger.error("Failed to obtain converted code")
            return jsonify({"error": "Failed to process conversion response.", "files": {}}), 500

        converted_code = [
            {"file_name": "ConvertedCode.cs", "path": "", "content": converted_json["convertedCode"]}
        ]
        logger.info("Generating unit tests")
        unit_test_input = {
            "Controllers": [],
            "Services": []
        }
        for file_info in converted_code:
            if isinstance(file_info, dict):
                file_name = file_info.get("file_name", "")
                path = file_info.get("path", "")
                content = file_info.get("content", "")
                if "controller" in file_name.lower() or "controller" in path.lower():
                    unit_test_input["Controllers"].append({"file_name": file_name, "path": path, "content": content})
                if "service" in file_name.lower() or "service" in path.lower():
                    unit_test_input["Services"].append({"file_name": file_name, "path": path, "content": content})

        unit_test_prompt = create_unit_test_prompt("C#", unit_test_input)
        unit_test_system = (
            "You are an expert test engineer specializing in writing comprehensive unit tests for .NET 8 applications. "
            "For EACH Controller and Service class found, generate a separate unit test file named '[ClassName]Tests.cs'. "
            "Return your response in JSON as follows:\n"
            "{\n"
            '  "unitTestFiles": [\n'
            '    {"fileName": "[ClassName]Tests.cs", "content": "...unit test code..."}\n'
            '  ],\n'
            '  "testDescription": "...",\n'
            '  "coverage": [...],\n'
            '  "businessRuleTests": [...]\n'
            "}"
        )

        unit_test_messages = [
            {"role": "system", "content": unit_test_system},
            {"role": "user", "content": unit_test_prompt}
        ]
        try:
            logger.info("Calling Azure OpenAI for unit test generation")
            unit_test_response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=unit_test_messages,
                temperature=0.1,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            unit_test_content = unit_test_response.choices[0].message.content.strip()
            try:
                unit_test_json = json.loads(unit_test_content)
                logger.info("Unit test JSON parsed successfully")
                unit_test_code = unit_test_json.get("unitTestFiles", [])
            except json.JSONDecodeError:
                logger.warning("Failed to parse unit test JSON directly")
                unit_test_json = extract_json_from_response(unit_test_content)
                unit_test_code = unit_test_json.get("unitTestFiles", [])
        except Exception as e:
            logger.error(f"Unit test generation failed: {str(e)}")
            unit_test_json = {}
            unit_test_code = []

        logger.info("Generating functional tests")
        functional_test_prompt = create_functional_test_prompt("C#", unit_test_input)
        functional_test_system = (
            "You are an expert QA engineer specializing in creating functional tests for .NET 8 applications. "
            "Create comprehensive test scenarios that verify the application meets all business requirements. "
            "Return your response in JSON format with the following structure:\n"
            "{\n"
            '  "functionalTests": [\n'
            '    {"id": "FT1", "title": "Test scenario title", "steps": ["Step 1", "Step 2"], "expectedResult": "Expected outcome", "businessRule": "Related business rule"},\n'
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
            logger.info("Calling Azure OpenAI for functional test generation")
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
                logger.info("Functional test JSON parsed successfully")
            except json.JSONDecodeError:
                logger.warning("Failed to parse functional test JSON directly")
                functional_test_json = extract_json_from_response(functional_test_content)
        except Exception as e:
            logger.error(f"Functional test generation failed: {str(e)}")
            functional_test_json = {}

        output_dir_path = os.path.join("output", "converted", project_id)
        os.makedirs(output_dir_path, exist_ok=True)
        output_path = os.path.join(output_dir_path, "converted_csharp.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(converted_json, f, indent=2)
        logger.info(f"Converted C# code saved to: {output_path}")

        files = flatten_converted_code(
            converted_code,
            unit_test_code,
            project_id,
            target_structure=converted_json.get("targetStructure")
        )

        temp_dir = os.path.join("output", "converted", project_id, "temp_chunks")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary chunk files in {temp_dir}")

        logger.info(f"Generated {len(files)} files for .NET project in {output_dir_path}")

        return jsonify({
            "status": "success",
            "project_id": project_id,
            "converted_code": converted_code,
            "conversion_notes": converted_json.get("conversionNotes", []),
            "unit_tests": unit_test_code,
            "unit_test_details": unit_test_json,
            "functional_tests": functional_test_json,
            "files": files,
            "target_structure": converted_json.get("targetStructure", {})
        })

    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "files": {}}), 500

@bp.route("/converted-files/<base_name>", methods=["GET"])
def get_converted_files(base_name):
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