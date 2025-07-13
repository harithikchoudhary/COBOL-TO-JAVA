import json
import logging
from pathlib import Path
from typing import Dict
from ..config import logger, UPLOAD_DIR, output_dir

ANALYSIS_DIR = Path(output_dir) / "analysis"

def analyze_cobol_file(file_path: Path) -> Dict:
    """Analyze a single COBOL file and return its structure."""
    logger.info(f"Analyzing file: {file_path}")
    if file_path.suffix.lower() not in [".cbl", ".cpy", ".jcl"]:
        logger.warning(f"Invalid file extension for {file_path}. Expected .cbl, .cpy, or .jcl.")
        return {"error": f"Invalid file extension: {file_path.suffix}"}

    try:
        with open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return {"error": f"Could not read file: {e}"}
    
    analysis = {
        "file_name": file_path.name,
        "file_type": file_path.suffix.lower(),
        "divisions": {
            "identification": {},
            "environment": {},
            "data": {
                "working_storage": [],
                "linkage_section": [],
                "file_section": []
            },
            "procedure": []
        },
        "copybooks": [],
        "cics_commands": [],
        "variables": [],
        "paragraphs": [],
        "jcl_definitions": [] if file_path.suffix.lower() == ".jcl" else None
    }
    
    lines = content.splitlines()
    current_division = None
    current_section = None
    current_paragraph = None
    is_copybook = file_path.suffix.lower() == ".cpy"
    
    for line in lines:
        line = line.strip().upper()
        if not line or line.startswith("*") or line.startswith("//*"):
            continue
        
        if file_path.suffix.lower() == ".jcl":
            if line.startswith("//") and not line.startswith("//*"):
                parts = line.split()
                if len(parts) > 1:
                    if "EXEC" in line:
                        analysis["jcl_definitions"].append({
                            "type": "EXEC",
                            "name": parts[1],
                            "details": line
                        })
                    elif "DD" in line:
                        analysis["jcl_definitions"].append({
                            "type": "DD",
                            "name": parts[1],
                            "details": line
                        })
                    elif "DEFINE" in line:
                        analysis["jcl_definitions"].append({
                            "type": "DEFINE",
                            "resource": line.split("DEFINE")[1].split()[0] if "DEFINE" in line else "",
                            "details": line
                        })
            continue
        
        if line.startswith("IDENTIFICATION DIVISION"):
            current_division = "identification"
        elif line.startswith("ENVIRONMENT DIVISION"):
            current_division = "environment"
        elif line.startswith("DATA DIVISION"):
            current_division = "data"
        elif line.startswith("PROCEDURE DIVISION"):
            current_division = "procedure"
        
        if current_division == "identification":
            if line.startswith("PROGRAM-ID"):
                analysis["divisions"]["identification"]["program_id"] = line.split()[1].strip(".")
        
        if current_division == "data":
            if line.startswith("WORKING-STORAGE SECTION"):
                current_section = "working_storage"
            elif line.startswith("LINKAGE SECTION"):
                current_section = "linkage_section"
            elif line.startswith("FILE SECTION"):
                current_section = "file_section"
            elif line.startswith("COPY"):
                copybook = line.split()[1].strip(".")
                analysis["copybooks"].append({
                    "name": copybook,
                    "content": line
                })
        
        if "EXEC CICS" in line and not is_copybook:
            cics_type = line.split()[2] if len(line.split()) > 2 else "UNKNOWN"
            analysis["cics_commands"].append({
                "command": line,
                "type": cics_type,
                "parameters": line[line.find("EXEC CICS"):],
                "context": current_paragraph
            })
        
        if current_division == "data" and current_section in ["working_storage", "linkage_section"]:
            if line.startswith(("01", "05", "77")) or (is_copybook and line.startswith(("01", "05", "77", "88"))):
                parts = line.split()
                if len(parts) >= 2:
                    var_level = parts[0]
                    var_name = parts[1].strip(".")
                    var_type = " ".join(parts[2:]) if len(parts) > 2 else ""
                    analysis["divisions"]["data"][current_section].append({
                        "level": var_level,
                        "name": var_name,
                        "type": var_type,
                        "picture": var_type if "PIC" in var_type else ""
                    })
                    analysis["variables"].append(var_name)
        
        if current_division == "procedure" and not is_copybook and line.endswith(".") and not line.startswith("EXEC"):
            if not any(kw in line for kw in ["MOVE", "PERFORM", "IF", "ELSE", "END"]):
                current_paragraph = line.split()[0]
                analysis["paragraphs"].append(current_paragraph)
                analysis["divisions"]["procedure"].append({
                    "paragraph": current_paragraph,
                    "code": [line]
                })
            elif current_paragraph and analysis["divisions"]["procedure"]:
                analysis["divisions"]["procedure"][-1]["code"].append(line)
    
    if is_copybook and not analysis["variables"]:
        logger.warning(f"No variables found in copybook {file_path.name}. Content may be empty or malformed.")
    
    logger.info(f"File {file_path.name} analyzed: {len(analysis['variables'])} variables, {len(analysis['cics_commands'])} CICS commands, {len(analysis['paragraphs'])} paragraphs")
    return analysis

def create_cobol_json(project_id: str) -> Dict:
    """Create a JSON file summarizing COBOL file analysis."""
    logger.info(f"Creating COBOL JSON for project: {project_id}")
    project_dir = Path(UPLOAD_DIR) / project_id
    if not project_dir.exists():
        logger.error(f"Project directory not found: {project_dir}")
        raise ValueError("Project directory not found")
    
    cobol_json = {
        "project_id": project_id,
        "files": [],
        "dependencies": []
    }
    
    for file_path in project_dir.glob("**/*"):
        if file_path.suffix.lower() in [".cbl", ".cpy", ".jcl"]:
            file_analysis = analyze_cobol_file(file_path)
            if "error" not in file_analysis:
                cobol_json["files"].append(file_analysis)
                if file_analysis.get("copybooks"):
                    dependencies = [cb["name"] for cb in file_analysis["copybooks"]]
                    cobol_json["dependencies"].extend(dependencies)
                    logger.info(f"Extracted dependencies from {file_path.name}: {dependencies}")
    
    if not cobol_json["files"]:
        logger.warning(f"No valid COBOL files found for project: {project_id}")
    
    json_path = ANALYSIS_DIR / project_id / "cobol_analysis.json"
    json_path.parent.mkdir(exist_ok=True, parents=True)
    with open(json_path, mode='w', encoding='utf-8') as f:
        json.dump(cobol_json, f, indent=2)
    
    logger.info(f"COBOL JSON created at: {json_path}")
    return cobol_json