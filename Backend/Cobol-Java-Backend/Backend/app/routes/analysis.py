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

# Use the real AnalysisManager
from ..analysis.analysis_manager import AnalysisManager

# Single global instance
analysis_manager = AnalysisManager()

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
    1) Classify uploaded files
    2) Auto-run simple analysis (placeholder)
    3) Run GPT for business & technical requirements
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

        # 2) AUTOMATIC ANALYSIS (Simple version)
        cobol_files = get_cobol_files_for_analysis(classified)
        manager = analysis_manager
        
        auto_analysis = {"status": "skipped", "reason": "No analysis manager"}
        if cobol_files and manager:
            try:
                # Save files to uploads directory
                os.makedirs("uploads", exist_ok=True)
                for filename, content in cobol_files.items():
                    with open(os.path.join("uploads", filename), 'w', encoding='utf-8') as f:
                        f.write(content)
                
                auto_analysis = manager.process_uploaded_files(cobol_files)
                logger.info(f"✅ Simple analysis completed: {auto_analysis['status']}")
                
                # Store in current app for conversion route
                current_app.simple_analysis_data = {
                    "cobol_files": cobol_files,
                    "classified_files": classified
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Simple analysis failed: {e}")
                auto_analysis = {"status": "failed", "error": str(e)}

        log_processing_step("Simple analysis completed", {
            "status": auto_analysis.get("status", "unknown"),
            "files_processed": len(cobol_files)
        }, 3)

        # 3) GPT REQUIREMENTS ANALYSIS
        src = data.get("sourceLanguage")
        tgt = data.get("targetLanguage")
        cobol_list = [f["content"] for f in classified.get("COBOL Code", [])]
        
        if not src or not cobol_list:
            return jsonify({"error": "Missing sourceLanguage or no COBOL code"}), 400

        log_processing_step("Creating business and technical prompts", {
            "source_language": src,
            "target_language": tgt,
            "cobol_files_count": len(cobol_list)
        }, 4)

        bus_prompt = create_business_requirements_prompt(src, cobol_list)
        tech_prompt = create_technical_requirements_prompt(src, tgt, cobol_list)

        # Business Requirements Analysis
        business_msgs = [
            {
                "role": "system",
                "content": (
                    f"You are an expert in analyzing COBOL code to extract business requirements. "
                    f"You understand COBOL deeply and can identify business rules and processes in the code. "
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
            {"role": "user", "content": bus_prompt}
        ]
        
        log_processing_step("Calling GPT for business requirements", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1
        }, 5)
        
        business_resp = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=business_msgs,
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        try:
            business_json = json.loads(business_resp.choices[0].message.content)
        except json.JSONDecodeError:
            business_json = extract_json_from_response(business_resp.choices[0].message.content)

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
            {"role": "user", "content": tech_prompt}
        ]
        
        log_processing_step("Calling GPT for technical requirements", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1
        }, 6)
        
        technical_resp = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=technical_msgs,
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        try:
            technical_json = json.loads(technical_resp.choices[0].message.content)
        except json.JSONDecodeError:
            technical_json = extract_json_from_response(technical_resp.choices[0].message.content)

        # 4) BUILD RESPONSE
        result = {
            "businessRequirements": business_json,
            "technicalRequirements": technical_json,
            "sourceLanguage": src,
            "targetLanguage": tgt,
            "fileClassification": classified,
            "automaticAnalysis": auto_analysis
        }
        
        log_processing_step("Analysis completed successfully", {
            "business_requirements_available": bool(business_json),
            "technical_requirements_available": bool(technical_json),
            "automatic_analysis_status": auto_analysis.get("status", "unknown")
        }, 7)
        
        logger.info("=== ANALYZE REQUIREMENTS REQUEST COMPLETED SUCCESSFULLY ===")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in /analyze-requirements: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@bp.route("/upload-standards", methods=["POST"])
def upload_standards():
    """Upload standards documents → build Standards RAG (placeholder)"""
    try:
        files = request.files.getlist("files")
        std_map = {f.filename: f.read() for f in files if f.filename}
        
        # Save to documents directory
        os.makedirs("documents", exist_ok=True)
        for filename, content in std_map.items():
            with open(os.path.join("documents", filename), 'wb') as f:
                f.write(content)
        
        manager = analysis_manager
        if not manager:
            return jsonify({"error": "Analysis Manager unavailable"}), 503
            
        out = manager.process_standards_documents(std_map)
        return jsonify(out)
        
    except Exception as e:
        logger.error(f"Error in /upload-standards: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/query-rag", methods=["POST"])
def query_rag():
    """Query RAG: standards/project/both (placeholder)"""
    try:
        p = request.json or {}
        q = p.get("query", "")
        t = p.get("type", "both")
        k = p.get("k", 5)
        
        manager = analysis_manager
        if not manager:
            return jsonify({"error": "Analysis Manager unavailable"}), 503
            
        return jsonify(manager.query_rag_system(q, t, k))
        
    except Exception as e:
        logger.error(f"Error in /query-rag: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/analysis-status", methods=["GET"])
def analysis_status():
    """Return RAG/CICS analysis status"""
    try:
        manager = analysis_manager
        if not manager:
            return jsonify({
                "status": "unavailable",
                "message": "Analysis Manager not available",
                "enhanced_features": False
            })
            
        status = manager.get_analysis_summary()
        status["enhanced_features"] = True
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error in /analysis-status: {e}")
        return jsonify({"error": str(e)}), 500
    
@bp.route("/upload-project-files", methods=["POST"])
def upload_project_files():
    """Accept JSON { file_data: { filename: content, … } } and write to uploads/"""
    data = request.json or {}
    files_map = data.get("file_data", {})
    if not isinstance(files_map, dict):
        return jsonify({"error":"file_data must be dict"}), 400

    # Write each to uploads/
    os.makedirs("uploads", exist_ok=True)
    for fn, content in files_map.items():
        with open(os.path.join("uploads", fn), "w", encoding="utf-8") as f:
            f.write(content)

    return jsonify({
        "status":"success",
        "message":f"Wrote {len(files_map)} files to uploads/"
    })


@bp.route("/analyze-project", methods=["POST"])
def analyze_project():
    """
    Run Dual RAG + CICS analysis over whatever lives in uploads/.
    Writes out rag_storage/project_analysis.json, cics_analysis/analysis.json, etc.
    """
    try:
        result = analysis_manager.process_uploaded_files(analysis_manager.project_files)
        return jsonify(result)
    except Exception as e:
        logger.error(f"analyze-project failed: {e}", exc_info=True)
        return jsonify({"status":"error","error":str(e)}), 500


@bp.route("/clear-analysis", methods=["DELETE"])
def clear_analysis():
    """Wipe uploads/, cics_analysis/, rag_storage/ → reinit Analysis Manager"""
    import shutil
    try:
        directories_to_clear = ["uploads", "cics_analysis", "rag_storage", "documents"]
        cleared_dirs = []
        
        for d in directories_to_clear:
            if os.path.exists(d):
                shutil.rmtree(d)
                cleared_dirs.append(d)
            os.makedirs(d, exist_ok=True)
        
        # Reset analysis manager
        global analysis_manager
        analysis_manager = None
        
        return jsonify({
            "status": "cleared",
            "cleared_directories": cleared_dirs,
            "message": "Analysis data cleared successfully"
        })
        
    except Exception as e:
        logger.error(f"Error in /clear-analysis: {e}")
        return jsonify({"error": str(e)}), 500