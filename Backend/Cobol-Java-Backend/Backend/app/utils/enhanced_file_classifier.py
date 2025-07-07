import os
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def classify_and_process_files(files_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Enhanced file classification that handles both file uploads and content
    
    Args:
        files_data: Can be either:
            - Dict of filename -> content (string)
            - Dict of file objects with fileName and content
    
    Returns:
        Classified files dictionary
    """
    logger.info("=== ENHANCED FILE CLASSIFICATION STARTED ===")
    
    # Normalize input data
    normalized_files = {}
    
    if isinstance(files_data, dict):
        for key, value in files_data.items():
            if isinstance(value, dict) and "fileName" in value:
                # Format from current project
                filename = value["fileName"]
                content = value.get("content", "")
                normalized_files[filename] = content
            else:
                # Direct filename -> content format
                normalized_files[key] = value
    
    logger.info(f"Number of files to classify: {len(normalized_files)}")
    
    # Enhanced type-to-extension mappings
    type_extensions = {
        "COBOL Code": [".cob", ".cbl", ".cobol", ".pco", ".ccp"],
        "JCL": [".jcl", ".job", ".cntl", ".ctl"],
        "Copybooks": [".cpy", ".copybook", ".cblcpy", ".inc"],
        "VSAM Definitions": [".ctl", ".cntl", ".def", ".vsam"],
        "BMS Maps": [".bms", ".map"],
        "Control Files": [".ctl", ".cfg", ".conf"],
        "Standards Documents": [".pdf", ".docx", ".pptx", ".txt", ".md"]
    }

    # Normalize extensions for quick lookup
    ext_to_type = {}
    for type_name, exts in type_extensions.items():
        for ext in exts:
            ext_to_type[ext.lower()] = type_name

    # Prepare result dictionary
    classified = {
        "COBOL Code": [],
        "JCL": [],
        "Copybooks": [],
        "VSAM Definitions": [],
        "BMS Maps": [],
        "Control Files": [],
        "Standards Documents": [],
        "Unknown": []
    }

    # Classify files
    for filename, content in normalized_files.items():
        file_ext = Path(filename).suffix.lower()
        matched_type = ext_to_type.get(file_ext, None)
        
        # Content-based classification if extension doesn't match
        if not matched_type:
            matched_type = _classify_by_content(filename, content)
        
        file_info = {
            "fileName": filename,
            "content": content,
            "size": len(content) if isinstance(content, str) else len(str(content)),
            "extension": file_ext,
            "lines": len(str(content).split('\n'))
        }
        
        if matched_type and matched_type in classified:
            classified[matched_type].append(file_info)
            logger.info(f"Classified '{filename}' as '{matched_type}'")
        else:
            classified["Unknown"].append(file_info)
            logger.info(f"Could not classify '{filename}' - marked as Unknown")

    # Log classification summary
    for file_type, files in classified.items():
        if files:
            logger.info(f"{file_type}: {len(files)} files")
    
    logger.info("=== ENHANCED FILE CLASSIFICATION COMPLETED ===")
    return classified

def _classify_by_content(filename: str, content: str) -> str:
    """
    Classify file by analyzing its content
    
    Args:
        filename: Name of the file
        content: File content as string
        
    Returns:
        Detected file type or None
    """
    if not content or not isinstance(content, str):
        return None
    
    content_upper = content.upper()
    
    # COBOL indicators
    if any(keyword in content_upper for keyword in [
        "IDENTIFICATION DIVISION", "PROGRAM-ID", "DATA DIVISION", 
        "PROCEDURE DIVISION", "WORKING-STORAGE"
    ]):
        return "COBOL Code"
    
    # JCL indicators
    if any(keyword in content_upper for keyword in [
        "//", "JOB ", "EXEC PGM=", "DD DSN="
    ]):
        return "JCL"
    
    # Copybook indicators (data structures without divisions)
    if any(keyword in content_upper for keyword in [
        "01 ", "05 ", "PIC ", "PICTURE"
    ]) and "PROCEDURE DIVISION" not in content_upper:
        return "Copybooks"
    
    # BMS indicators
    if any(keyword in content_upper for keyword in [
        "DFHMSD", "DFHMDI", "DFHMDF"
    ]):
        return "BMS Maps"
    
    return None

def get_cobol_files_for_analysis(classified_files: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
    """
    Extract COBOL-related files for analysis
    
    Args:
        classified_files: Classified files dictionary
        
    Returns:
        Dictionary of filename -> content for COBOL analysis
    """
    analysis_files = {}
    
    # Include COBOL programs
    for file_info in classified_files.get("COBOL Code", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    # Include copybooks
    for file_info in classified_files.get("Copybooks", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    # Include control files
    for file_info in classified_files.get("Control Files", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    # Include JCL files
    for file_info in classified_files.get("JCL", []):
        analysis_files[file_info["fileName"]] = file_info["content"]
    
    return analysis_files