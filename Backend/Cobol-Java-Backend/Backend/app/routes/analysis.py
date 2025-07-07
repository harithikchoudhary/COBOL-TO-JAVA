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
    Enhanced flow: 
    1) Classify uploaded files
    2) Run comprehensive analysis (CICS + Dual RAG)
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

        # 2) COMPREHENSIVE ANALYSIS (CICS + Dual RAG)
        cobol_files = get_cobol_files_for_analysis(classified)
        
        comprehensive_analysis = {"status": "skipped", "reason": "No files to analyze"}
        if cobol_files:
            try:
                logger.info("🚀 Starting comprehensive CICS + Dual RAG analysis")
                
                # Process files through the comprehensive analysis manager
                comprehensive_analysis = analysis_manager.process_uploaded_files(cobol_files)
                
                logger.info(f"✅ Comprehensive analysis completed: {comprehensive_analysis.get('status', 'unknown')}")
                
                # Store analysis data for conversion use
                current_app.comprehensive_analysis_data = {
                    "cobol_files": cobol_files,
                    "classified_files": classified,
                    "analysis_results": comprehensive_analysis,
                    "analysis_manager": analysis_manager
                }
                
            except Exception as e:
                logger.error(f"❌ Comprehensive analysis failed: {e}")
                comprehensive_analysis = {"status": "failed", "error": str(e)}

        log_processing_step("Comprehensive analysis completed", {
            "status": comprehensive_analysis.get("status", "unknown"),
            "files_processed": len(cobol_files),
            "rag_analysis": comprehensive_analysis.get("rag_analysis", {}),
            "cics_analysis": comprehensive_analysis.get("cics_analysis", {})
        }, 3)

        # 3) GPT REQUIREMENTS ANALYSIS
        src = data.get("sourceLanguage")
        tgt = data.get("targetLanguage")
        cobol_list = [f["content"] for f in classified.get("COBOL Code", [])]
        
        if not src or not cobol_list:
            return jsonify({"error": "Missing sourceLanguage or no COBOL code"}), 400

        log_processing_step("Creating business and technical prompts with analysis context", {
            "source_language": src,
            "target_language": tgt,
            "cobol_files_count": len(cobol_list),
            "analysis_enhanced": comprehensive_analysis.get("status") == "success"
        }, 4)

        # Enhanced prompts with analysis context
        analysis_context = ""
        if comprehensive_analysis.get("status") == "success":
            analysis_context = f"""
            
ENHANCED CONTEXT FROM COMPREHENSIVE ANALYSIS:
- CICS Analysis: {comprehensive_analysis.get('cics_analysis', {}).get('total_programs', 0)} programs analyzed
- Business Domain: {comprehensive_analysis.get('cics_analysis', {}).get('business_domain', 'Unknown')}
- RAG Analysis: {comprehensive_analysis.get('rag_analysis', {}).get('total_files', 0)} files processed
- File Connections: {comprehensive_analysis.get('rag_analysis', {}).get('file_connections', 0)} dependencies found
- Conversion Patterns: {comprehensive_analysis.get('rag_analysis', {}).get('conversion_patterns', 0)} patterns identified

Use this analysis context to provide more accurate and specific requirements.
"""

        bus_prompt = create_business_requirements_prompt(src, cobol_list) + analysis_context
        tech_prompt = create_technical_requirements_prompt(src, tgt, cobol_list) + analysis_context

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
                    f'  "CICS_Insights": {{\n'
                    f'    "Transaction_Patterns": "Describe CICS transaction patterns identified.",\n'
                    f'    "Business_Domain": "Business domain classification from analysis.",\n'
                    f'    "Integration_Points": "Key integration and data flow points."\n'
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
        
        log_processing_step("Calling GPT for enhanced business requirements", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "analysis_context_included": bool(analysis_context)
        }, 5)
        
        business_resp = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=business_msgs,
            temperature=0.1,
            max_tokens=2500,
            response_format={"type": "json_object"}
        )
        
        try:
            business_json = json.loads(business_resp.choices[0].message.content)
        except json.JSONDecodeError:
            business_json = extract_json_from_response(business_resp.choices[0].message.content)

        # Enhanced Technical Requirements Analysis
        technical_msgs = [
            {
                "role": "system",
                "content": f"You are an expert in COBOL/CICS to .NET 8 migration with deep knowledge of mainframe modernization. "
                          f"You understand CICS commands, VSAM files, JCL, and modern .NET architecture patterns. "
                          f"You have access to comprehensive analysis including CICS patterns and architectural recommendations. "
                          f"Output your analysis in JSON format with the following structure:\n"
                          f"{{\n"
                          f'  "technicalRequirements": [\n'
                          f'    {{"id": "TR1", "description": "Technical requirement description", "complexity": "High/Medium/Low", "category": "CICS/Database/Architecture/etc"}},\n'
                          f'    {{"id": "TR2", "description": "Another technical requirement", "complexity": "High/Medium/Low", "category": "category"}}\n'
                          f'  ],\n'
                          f"}}"
            },
            {"role": "user", "content": tech_prompt}
        ]
        
        log_processing_step("Calling GPT for enhanced technical requirements", {
            "model": AZURE_OPENAI_DEPLOYMENT_NAME,
            "temperature": 0.1,
            "analysis_context_included": bool(analysis_context)
        }, 6)
        
        technical_resp = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=technical_msgs,
            temperature=0.1,
            max_tokens=2500,
            response_format={"type": "json_object"}
        )
        
        try:
            technical_json = json.loads(technical_resp.choices[0].message.content)
        except json.JSONDecodeError:
            technical_json = extract_json_from_response(technical_resp.choices[0].message.content)

        # 4) BUILD ENHANCED RESPONSE
        result = {
            "businessRequirements": business_json,
            "technicalRequirements": technical_json,
            "sourceLanguage": src,
            "targetLanguage": tgt,
            "fileClassification": classified,
            "comprehensiveAnalysis": comprehensive_analysis,
            "analysisEnhanced": comprehensive_analysis.get("status") == "success",
            "conversionContextReady": hasattr(analysis_manager, 'conversion_context') and analysis_manager.conversion_context is not None
        }
        
        log_processing_step("Enhanced analysis completed successfully", {
            "business_requirements_available": bool(business_json),
            "technical_requirements_available": bool(technical_json),
            "comprehensive_analysis_status": comprehensive_analysis.get("status", "unknown"),
            "conversion_context_ready": result["conversionContextReady"]
        }, 7)
        
        logger.info("=== ENHANCED ANALYZE REQUIREMENTS REQUEST COMPLETED SUCCESSFULLY ===")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in /analyze-requirements: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@bp.route("/upload-standards", methods=["POST"])
def upload_standards():
    """Upload standards documents and build Standards RAG"""
    try:
        logger.info("📄 Standards documents upload initiated")
        
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No files provided"}), 400
            
        # Create standards file map
        standards_map = {}
        for file in files:
            if file.filename:
                try:
                    content = file.read()
                    standards_map[file.filename] = content
                    logger.info(f"📄 Read file: {file.filename} ({len(content)} bytes)")
                except Exception as e:
                    logger.error(f"❌ Error reading file {file.filename}: {e}")
                    continue
        
        if not standards_map:
            return jsonify({"error": "No valid files to process"}), 400

        # Save to documents directory and process
        os.makedirs("documents", exist_ok=True)
        for filename, content in standards_map.items():
            try:
                file_path = os.path.join("documents", filename)
                with open(file_path, 'wb') as f:
                    f.write(content)
                logger.info(f"💾 Saved {filename} to documents directory")
            except Exception as e:
                logger.error(f"❌ Error saving {filename}: {e}")
        
        # Process through analysis manager
        if not analysis_manager:
            return jsonify({"error": "Analysis Manager unavailable"}), 503
            
        result = analysis_manager.process_standards_documents(standards_map)
        
        logger.info(f"✅ Standards processing completed: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Error in /upload-standards: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@bp.route("/query-rag", methods=["POST"])
def query_rag():
    """Query RAG systems: standards/project/both"""
    try:
        params = request.json or {}
        query = params.get("query", "")
        rag_type = params.get("type", "both")
        k = params.get("k", 5)
        
        if not query:
            return jsonify({"error": "Query parameter required"}), 400
        
        if not analysis_manager:
            return jsonify({"error": "Analysis Manager unavailable"}), 503
            
        result = analysis_manager.query_rag_system(query, rag_type, k)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Error in /query-rag: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/analysis-status", methods=["GET"])
def analysis_status():
    """Return comprehensive analysis status"""
    try:
        if not analysis_manager:
            return jsonify({
                "status": "unavailable",
                "message": "Analysis Manager not available",
                "enhanced_features": False
            })
            
        status = analysis_manager.get_analysis_summary()
        status["enhanced_features"] = True
        status["comprehensive_analysis_available"] = True
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"❌ Error in /analysis-status: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/upload-project-files", methods=["POST"])
def upload_project_files():
    """Accept project files and trigger indexing"""
    try:
        data = request.json or {}
        files_map = data.get("file_data", {})
        
        if not isinstance(files_map, dict):
            return jsonify({"error": "file_data must be dict"}), 400

        if not files_map:
            return jsonify({"error": "No files provided"}), 400

        # Write each file to uploads directory
        os.makedirs("uploads", exist_ok=True)
        for filename, content in files_map.items():
            try:
                file_path = os.path.join("uploads", filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"💾 Saved {filename} to uploads directory")
            except Exception as e:
                logger.error(f"❌ Error saving {filename}: {e}")

        logger.info(f"✅ Uploaded {len(files_map)} project files")
        
        return jsonify({
            "status": "success",
            "message": f"Uploaded {len(files_map)} files to uploads directory",
            "files_count": len(files_map)
        })

    except Exception as e:
        logger.error(f"❌ Error in /upload-project-files: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/analyze-project", methods=["POST"])
def analyze_project():
    """Run comprehensive Dual RAG + CICS analysis"""
    try:
        logger.info("🚀 Starting comprehensive project analysis")
        
        if not analysis_manager:
            return jsonify({"error": "Analysis Manager unavailable"}), 503
        
        # Check if files exist in uploads directory
        if not os.path.exists("uploads"):
            return jsonify({"error": "No uploads directory found"}), 400
            
        files = os.listdir("uploads")
        if not files:
            return jsonify({"error": "No files found in uploads directory"}), 400
        
        # Load files from uploads directory
        project_files = {}
        for filename in files:
            try:
                file_path = os.path.join("uploads", filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    project_files[filename] = f.read()
            except Exception as e:
                logger.error(f"❌ Error reading {filename}: {e}")
                continue
        
        if not project_files:
            return jsonify({"error": "No valid project files to analyze"}), 400
        
        # Run comprehensive analysis
        result = analysis_manager.process_uploaded_files(project_files)
        
        logger.info(f"✅ Comprehensive analysis completed: {result.get('status', 'unknown')}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ analyze-project failed: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/clear-analysis", methods=["DELETE"])
def clear_analysis():
    """Clear all analysis data and reinitialize"""
    import shutil
    try:
        directories_to_clear = ["uploads", "cics_analysis", "rag_storage", "documents"]
        cleared_dirs = []
        
        for directory in directories_to_clear:
            if os.path.exists(directory):
                shutil.rmtree(directory)
                cleared_dirs.append(directory)
            os.makedirs(directory, exist_ok=True)
        
        # Reset analysis manager
        global analysis_manager
        analysis_manager = AnalysisManager()
        
        logger.info(f"🧹 Cleared analysis data: {cleared_dirs}")
        
        return jsonify({
            "status": "cleared",
            "cleared_directories": cleared_dirs,
            "message": "Analysis data cleared and reinitialized successfully"
        })
        
    except Exception as e:
        logger.error(f"❌ Error in /clear-analysis: {e}")
        return jsonify({"error": str(e)}), 500