from flask import Blueprint, request, jsonify, current_app
from ..config import logger, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME
from openai import AzureOpenAI
import json, traceback, os
from pathlib import Path
from typing import Dict, List, Any
from ..utils.prompts import (
    create_business_requirements_prompt,
    create_technical_requirements_prompt
)
from ..utils.logs import (
    log_request_details,
    log_processing_step,
    log_gpt_interaction
)
from ..utils.response import extract_json_from_response
from ..utils.file_classifier import classify_uploaded_files
from ..utils.rag_indexer import load_vector_store, query_vector_store, index_files_for_rag
from ..utils.cobol_analyzer import create_cobol_json

bp = Blueprint('analysis', __name__, url_prefix='/cobo')

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def enhanced_classify_files(file_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Enhanced file classification using existing classifier"""
    logger.info("=== ENHANCED FILE CLASSIFICATION STARTED ===")
    
    basic_classified = classify_uploaded_files(file_data)
    
    enhanced = {
        "COBOL Code": [],
        "JCL": [],
        "Copybooks": [],
        "VSAM Definitions": [],
        "BMS Maps": [],
        "Control Files": [],
        "Standards Documents": [],
        "Unknown": []
    }
    
    for category, files in basic_classified.items():
        if category in enhanced:
            for file_info in files:
                if isinstance(file_info, dict) and "fileName" in file_info:
                    enhanced_file_info = {
                        "fileName": file_info["fileName"],
                        "content": file_info.get("content", ""),
                        "size": len(file_info.get("content", "")),
                        "extension": Path(file_info["fileName"]).suffix.lower(),
                        "lines": len(str(file_info.get("content", "")).split('\n'))
                    }
                    enhanced[category].append(enhanced_file_info)
    
    logger.info("=== ENHANCED FILE CLASSIFICATION COMPLETED ===")
    return enhanced

def get_cobol_files_for_analysis(classified_files: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
    """Extract COBOL-related files for analysis"""
    analysis_files = {}
    
    for file_info in classified_files.get("COBOL Code", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    for file_info in classified_files.get("Copybooks", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    for file_info in classified_files.get("JCL", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    return analysis_files

def create_target_structure_analysis(project_id: str, file_data: Dict[str, Any], classified_files: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Create target structure analysis using GPT"""
    logger.info(f"=== TARGET STRUCTURE ANALYSIS STARTED for project: {project_id} ===")
    
    # Combine all COBOL-related content
    cobol_content = ""
    for category in ["COBOL Code", "Copybooks", "JCL"]:
        for file_info in classified_files.get(category, []):
            cobol_content += f"\n\n=== {file_info['fileName']} ===\n{file_info['content']}"
    
    if not cobol_content.strip():
        logger.warning("No COBOL content found for target structure analysis")
        return {"error": "No COBOL content available for analysis"}
    
    structure_prompt = f"""
    You are an expert software architect specializing in COBOL to .NET 8 migration. 
    Analyze the provided COBOL/CICS code and create a comprehensive target structure for a modern .NET 8 application.
    
    Based on the code structure, business logic, data models, and CICS operations, design a complete .NET 8 project structure that follows:
    - Clean Architecture principles
    - SOLID design principles
    - .NET 8 best practices
    - Modern software patterns
    
    Analyze the following COBOL code and provide a detailed target structure:
    
    {cobol_content}
    
    Provide your analysis in the following JSON format:
    {{
      "project_name": "string",
      "architecture_pattern": "string",
      "projects": [
        {{
          "name": "string",
          "type": "string",
          "purpose": "string",
          "folders": [
            {{
              "name": "string",
              "purpose": "string",
              "files": [
                {{
                  "name": "string",
                  "type": "string",
                  "purpose": "string",
                  "key_classes": ["string"],
                  "dependencies": ["string"]
                }}
              ]
            }}
          ]
        }}
      ],
      "data_models": [
        {{
          "name": "string",
          "source": "string",
          "properties": [
            {{
              "name": "string",
              "type": "string",
              "source_field": "string"
            }}
          ]
        }}
      ],
      "services": [
        {{
          "name": "string",
          "purpose": "string",
          "methods": [
            {{
              "name": "string",
              "purpose": "string",
              "parameters": ["string"],
              "return_type": "string"
            }}
          ]
        }}
      ],
      "controllers": [
        {{
          "name": "string",
          "purpose": "string",
          "endpoints": [
            {{
              "method": "string",
              "route": "string",
              "purpose": "string"
            }}
          ]
        }}
      ],
      "infrastructure": [
        {{
          "component": "string",
          "purpose": "string",
          "implementation": "string"
        }}
      ],
      "database_design": {{
        "tables": [
          {{
            "name": "string",
            "source": "string",
            "columns": [
              {{
                "name": "string",
                "type": "string",
                "source_field": "string"
              }}
            ]
          }}
        ]
      }},
      "key_patterns": ["string"],
      "external_dependencies": ["string"],
      "configuration_requirements": ["string"]
    }}
    
    Focus on:
    1. Identifying all data structures from COBOL records
    2. Mapping CICS operations to appropriate .NET patterns
    3. Converting file operations to database operations
    4. Identifying business logic for service layer
    5. Creating appropriate API endpoints
    6. Handling transaction management
    7. Implementing proper error handling
    8. Security considerations
    9. Logging and auditing requirements
    10. Integration points
    """
    
    try:
        structure_msgs = [
            {
                "role": "system",
                "content": (
                    "You are an expert software architect specializing in COBOL to .NET 8 migration. "
                    "You understand legacy mainframe systems and modern .NET architecture patterns. "
                    "Your task is to analyze COBOL code and design a comprehensive, modern .NET 8 project structure "
                    "that maintains all business logic while following current best practices."
                )
            },
            {
                "role": "user",
                "content": structure_prompt
            }
        ]
        
        log_processing_step("Calling GPT for target structure analysis", {
            "prompt_length": len(structure_prompt),
            "project_id": project_id
        }, "TARGET_STRUCTURE")
        
        structure_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=structure_msgs,
            temperature=0.2,
            max_tokens=4000
        )
        
        log_gpt_interaction("TARGET_STRUCTURE", AZURE_OPENAI_DEPLOYMENT_NAME, structure_msgs, structure_response)
        
        structure_json = extract_json_from_response(structure_response.choices[0].message.content)
        
        # Save target structure JSON
        output_dir = os.path.join("output", "analysis", project_id)
        os.makedirs(output_dir, exist_ok=True)
        structure_path = os.path.join(output_dir, "target_structure.json")
        with open(structure_path, "w") as f:
            json.dump(structure_json, f, indent=2)
        logger.info(f"Target structure saved to: {structure_path}")
        
        logger.info("=== TARGET STRUCTURE ANALYSIS COMPLETED ===")
        return structure_json
        
    except Exception as e:
        logger.error(f"Error creating target structure analysis: {str(e)}")
        return {"error": str(e)}

@bp.route("/analysis-status", methods=["GET"])
def analysis_status():
    """Return the current analysis status for the project"""
    try:
        project_id = current_app.comprehensive_analysis_data.get("project_id", "N/A")
        cobol_files = current_app.comprehensive_analysis_data.get("cobol_files", {})
        rag_status = {
            "standards_rag_active": hasattr(current_app, 'standards_documents') and bool(current_app.standards_documents),
            "project_rag_active": bool(cobol_files)
        }
        return jsonify({
            "project_id": project_id,
            "project_files_loaded": len(cobol_files),
            "conversion_context_ready": bool(cobol_files and current_app.comprehensive_analysis_data.get("analysis_results")),
            "rag_status": rag_status
        })
    except Exception as e:
        logger.error(f"Error fetching analysis status: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/analyze-requirements", methods=["POST"])
def analyze_requirements():
    """
    Enhanced flow:
    1) Classify uploaded files
    2) Generate cobol_analysis.json
    3) Generate target_structure.json
    4) Index files for RAG
    5) Run GPT for business & technical requirements
    """
    try:
        data = request.json
        log_request_details("ANALYZE REQUIREMENTS", data)
        if not data:
            return jsonify({"error": "No data provided"}), 400

        project_id = data.get("projectId")
        if not project_id:
            return jsonify({"error": "Project ID is required"}), 400

        log_processing_step("Parsing request data", {
            "has_file_data": "file_data" in data,
            "source_language": data.get("sourceLanguage"),
            "target_language": data.get("targetLanguage"),
            "project_id": project_id
        }, 1)

        # 1) CLASSIFY FILES
        file_data = data.get("file_data", {})
        if isinstance(file_data, str):
            file_data = json.loads(file_data)
        
        if not file_data:
            return jsonify({"error": "No file data provided"}), 400
        
        classified = enhanced_classify_files(file_data)
        
        log_processing_step("File classification completed", {
            "total_files": sum(len(files) for files in classified.values()),
            "cobol_files": len(classified.get("COBOL Code", [])),
            "copybooks": len(classified.get("Copybooks", [])),
            "jcl_files": len(classified.get("JCL", []))
        }, 2)

        # 2) GENERATE COBOL ANALYSIS JSON
        log_processing_step("Generating COBOL analysis JSON", {"project_id": project_id}, 3)
        cobol_json = create_cobol_json(project_id)
        
        # Save COBOL JSON
        output_dir = os.path.join("output", "analysis", project_id)
        os.makedirs(output_dir, exist_ok=True)
        analysis_path = os.path.join(output_dir, "cobol_analysis.json")
        with open(analysis_path, "w") as f:
            json.dump(cobol_json, f, indent=2)
        logger.info(f"COBOL JSON created at: {analysis_path}")

        # 3) GENERATE TARGET STRUCTURE JSON
        log_processing_step("Generating target structure analysis", {"project_id": project_id}, 4)
        target_structure = create_target_structure_analysis(project_id, file_data, classified)

        # 4) INDEX FOR RAG
        log_processing_step("Indexing files for RAG", {"project_id": project_id}, 5)
        index_files_for_rag(project_id, cobol_json, file_data)
        
        # 5) GPT REQUIREMENTS ANALYSIS
        src = data.get("sourceLanguage")
        tgt = data.get("targetLanguage")
        cobol_list = [f["content"] for f in classified.get("COBOL Code", [])]
        
        if not src or not cobol_list:
            return jsonify({"error": "Missing sourceLanguage or no COBOL code"}), 400

        log_processing_step("Creating business and technical prompts", {
            "source_language": src,
            "target_language": tgt,
            "cobol_files_count": len(cobol_list)
        }, 6)

        # Combine COBOL code and analysis
        cobol_code_str = "\n".join(cobol_list)
        cobol_analysis_str = json.dumps(cobol_json, indent=2)
        target_structure_str = json.dumps(target_structure, indent=2)
        
        # Add standards and RAG context
        standards_context = ""
        if hasattr(current_app, 'standards_documents') and current_app.standards_documents:
            standards_context = f"\n\nSTANDARDS DOCUMENTS CONTEXT:\n{chr(10).join(current_app.standards_documents)}\n"
            logger.info(f"Adding standards context with {len(current_app.standards_documents)} documents")
        
        vector_store = load_vector_store(project_id)
        rag_context = ""
        if vector_store:
            rag_results = query_vector_store(vector_store, "Relevant COBOL program and standards information", k=5)
            if rag_results:
                rag_context = "\n\nRAG CONTEXT:\n" + "\n".join([f"Source: {r.metadata.get('source', 'unknown')}\n{r.page_content}\n" for r in rag_results])
                logger.info(f"Added RAG context with {len(rag_results)} results")
            else:
                logger.warning("No RAG results returned from vector store")
        
        bus_prompt = create_business_requirements_prompt(src, cobol_code_str) + standards_context + rag_context + f"\n\nCOBOL ANALYSIS:\n{cobol_analysis_str}" + f"\n\nTARGET STRUCTURE:\n{target_structure_str}"
        tech_prompt = create_technical_requirements_prompt(src, tgt, cobol_code_str) + standards_context + rag_context + f"\n\nCOBOL ANALYSIS:\n{cobol_analysis_str}" + f"\n\nTARGET STRUCTURE:\n{target_structure_str}"

        # Business Requirements Analysis
        business_msgs = [
            {
                "role": "system",
                "content": (
                    f"You are an expert in analyzing COBOL/CICS code to extract business requirements. "
                    f"You understand COBOL, CICS commands, and mainframe business processes deeply. "
                    f"You have access to comprehensive analysis results including CICS patterns, RAG context, standards documents, and target structure analysis. "
                    f"Use the provided COBOL analysis JSON and target structure to understand program structure, variables, and dependencies. "
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
                "content": bus_prompt
            }
        ]

        log_processing_step("Running business requirements analysis", {
            "prompt_length": len(bus_prompt)
        }, 7)

        business_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=business_msgs,
            temperature=0.3,
            max_tokens=4000
        )

        log_gpt_interaction("BUSINESS_REQUIREMENTS", AZURE_OPENAI_DEPLOYMENT_NAME, business_msgs, business_response)

        business_json = extract_json_from_response(business_response.choices[0].message.content)

        # Technical Requirements Analysis
        technical_msgs = [
            {
                "role": "system",
                "content": (
                    f"You are an expert in COBOL to .NET 8 migration. "
                    f"You deeply understand both COBOL and .NET 8 and can identify technical challenges and requirements for migration. "
                    f"Use the provided COBOL analysis JSON and target structure to understand program structure, variables, and dependencies. "
                    f"Output your analysis in JSON format with the following structure:\n"
                    f"{{\n"
                    f'  "technicalRequirements": [\n'
                    f'    {{"id": "TR1", "description": "First technical requirement", "complexity": "High/Medium/Low"}},\n'
                    f'    {{"id": "TR2", "description": "Second technical requirement", "complexity": "High/Medium/Low"}}\n'
                    f'  ],\n'
                    f"}}"
                )
            },
            {
                "role": "user",
                "content": tech_prompt
            }
        ]

        log_processing_step("Running technical requirements analysis", {
            "prompt_length": len(tech_prompt)
        }, 8)

        technical_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=technical_msgs,
            temperature=0.3,
            max_tokens=4000
        )

        log_gpt_interaction("TECHNICAL_REQUIREMENTS", AZURE_OPENAI_DEPLOYMENT_NAME, technical_msgs, technical_response)

        technical_json = extract_json_from_response(technical_response.choices[0].message.content)

        # Store analysis data for conversion use
        current_app.comprehensive_analysis_data = {
            "project_id": project_id,
            "cobol_files": get_cobol_files_for_analysis(classified),
            "classified_files": classified,
            "cobol_analysis": cobol_json,
            "target_structure": target_structure,
            "analysis_results": {
                "business_requirements": business_json,
                "technical_requirements": technical_json,
                "status": "success"
            }
        }

        log_processing_step("Analysis completed successfully", {
            "business_rules_count": len(business_json.get("Business Rules & Requirements", {}).get("Business Rules", [])),
            "technical_requirements_count": len(technical_json.get("technicalRequirements", [])),
            "target_structure_created": bool(target_structure and "error" not in target_structure),
            "conversionContextReady": True
        }, 9)

        return jsonify({
            "status": "success",
            "project_id": project_id,
            "business_requirements": business_json,
            "technical_requirements": technical_json,
            "target_structure": target_structure,
            "file_classification": classified,
            "cobol_analysis": cobol_json,
            "conversionContextReady": True
        })

    except Exception as e:
        logger.error(f"❌ Analysis failed: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500