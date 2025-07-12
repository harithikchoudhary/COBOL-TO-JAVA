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

bp = Blueprint('analysis', __name__, url_prefix='/cobo')

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def enhanced_classify_files(file_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Enhanced file classification using existing classifier"""
    logger.info("=== ENHANCED FILE CLASSIFICATION STARTED ===")
    
    # Use existing classifier first
    basic_classified = classify_uploaded_files(file_data)
    
    # Convert to enhanced format
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
    
    # Map basic classification to enhanced
    for category, files in basic_classified.items():
        if category in enhanced:
            for file_info in files:
                # Ensure file_info has the right structure
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
    
    # Include COBOL programs
    for file_info in classified_files.get("COBOL Code", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    # Include copybooks
    for file_info in classified_files.get("Copybooks", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    # Include JCL files
    for file_info in classified_files.get("JCL", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    return analysis_files

@bp.route("/analyze-requirements", methods=["POST"])
def analyze_requirements():
    """
    Simplified flow: 
    1) Classify uploaded files
    2) Run GPT for business & technical requirements
    """
    try:
        data = request.json
        log_request_details("ANALYZE REQUIREMENTS", data)
        if not data:
            return jsonify({"error": "No data provided"}), 400

        log_processing_step("Parsing request data", {
            "has_file_data": "file_data" in data,
            "source_language": data.get("sourceLanguage"),
            "target_language": data.get("targetLanguage")
        }, 1)

        # 1) CLASSIFY FILES
        file_data = data.get("file_data", {})
        if isinstance(file_data, str):
            file_data = json.loads(file_data)
        
        classified = enhanced_classify_files(file_data)
        
        log_processing_step("File classification completed", {
            "total_files": sum(len(files) for files in classified.values()),
            "cobol_files": len(classified.get("COBOL Code", [])),
            "copybooks": len(classified.get("Copybooks", []))
        }, 2)

        # 2) GPT REQUIREMENTS ANALYSIS
        src = data.get("sourceLanguage")
        tgt = data.get("targetLanguage")
        cobol_list = [f["content"] for f in classified.get("COBOL Code", [])]
        
        if not src or not cobol_list:
            return jsonify({"error": "Missing sourceLanguage or no COBOL code"}), 400

        log_processing_step("Creating business and technical prompts", {
            "source_language": src,
            "target_language": tgt,
            "cobol_files_count": len(cobol_list)
        }, 3)

        # Ensure cobol_list is a string for prompt functions
        cobol_code_str = cobol_list if isinstance(cobol_list, str) else "\n".join(cobol_list)
        
        # Add standards context if available
        standards_context = ""
        if hasattr(current_app, 'standards_documents') and current_app.standards_documents:
            standards_context = f"\n\nSTANDARDS DOCUMENTS CONTEXT:\n{chr(10).join(current_app.standards_documents)}\n"
            logger.info(f"Adding standards context with {len(current_app.standards_documents)} documents")
        
        bus_prompt = create_business_requirements_prompt(src, cobol_code_str) + standards_context
        tech_prompt = create_technical_requirements_prompt(src, tgt, cobol_code_str) + standards_context

        # Business Requirements Analysis
        business_msgs = [
            {
                "role": "system",
                "content": (
                    f"You are an expert in analyzing COBOL/CICS code to extract business requirements. "
                    f"You understand COBOL, CICS commands, and mainframe business processes deeply. "
                    f"You have access to comprehensive analysis results including CICS patterns and RAG context. "
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
        }, 4)

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
                "content": f"You are an expert in COBOL to .NET 8 migration. "
                          f"You deeply understand both COBOL and .NET 8 and can identify technical challenges and requirements for migration. "
                          f"Output your analysis in JSON format with the following structure:\n"
                          f"{{\n"
                          f'  "technicalRequirements": [\n'
                          f'    {{"id": "TR1", "description": "First technical requirement", "complexity": "High/Medium/Low"}},\n'
                          f'    {{"id": "TR2", "description": "Second technical requirement", "complexity": "High/Medium/Low"}}\n'
                          f'  ],\n'
                          f"}}"
            },
            {
                "role": "user",
                "content": tech_prompt
            }
        ]

        log_processing_step("Running technical requirements analysis", {
            "prompt_length": len(tech_prompt)
        }, 5)

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
            "cobol_files": get_cobol_files_for_analysis(classified),
            "classified_files": classified,
            "analysis_results": {
                "business_requirements": business_json,
                "technical_requirements": technical_json,
                "status": "success"
            }
        }

        log_processing_step("Analysis completed successfully", {
            "business_rules_count": len(business_json.get("Business_Rules", [])),
            "technical_challenges_count": len(technical_json.get("Technical_Challenges", [])),
            "conversionContextReady": True
        }, 6)

        return jsonify({
            "status": "success",
            "business_requirements": business_json,
            "technical_requirements": technical_json,
            "file_classification": classified,
            "conversionContextReady": True
        })

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@bp.route("/upload-standards", methods=["POST"])
def upload_standards():
    """Upload standards documents for requirements analysis context"""
    try:
        if 'files' not in request.files:
            return jsonify({"error": "No files provided"}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({"error": "No files selected"}), 400

        processed_files = []
        standards_content = []
        
        for file in files:
            if file.filename:
                try:
                    # Read file content
                    content = file.read()
                    if hasattr(content, 'decode'):
                        content = content.decode('utf-8', errors='ignore')
                    
                    # Store file info and content
                    processed_files.append({
                        "filename": file.filename,
                        "size": len(content),
                        "status": "processed"
                    })
                    
                    # Extract text content for analysis context
                    standards_content.append(f"Document: {file.filename}\n{content[:2000]}...")
                    
                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {e}")
                    processed_files.append({
                        "filename": file.filename,
                        "size": 0,
                        "status": "error",
                        "error": str(e)
                    })

        # Store standards content in current_app for use in requirements analysis
        if standards_content:
            current_app.standards_documents = standards_content
            logger.info(f"Stored {len(standards_content)} standards documents for analysis context")

        return jsonify({
            "status": "success",
            "files_processed": len(processed_files),
            "standards_rag_active": len(standards_content) > 0,
            "message": f"Successfully processed {len(processed_files)} standards documents"
        })

    except Exception as e:
        logger.error(f"❌ Standards upload failed: {e}")
        return jsonify({"error": str(e)}), 500

