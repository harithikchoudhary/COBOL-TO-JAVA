from ..config import logger

def classify_uploaded_files(file_json):
    """Classify uploaded files by type. Accepts a mapping of filename to content (string)."""
    logger.info("=== FILE CLASSIFICATION STARTED ===")
    logger.info(f"Number of files to classify: {len(file_json)}")
    
    # Define type-to-extension mappings
    type_extensions = {
        "COBOL Code": [".cob", ".cbl", ".cobol", ".pco", ".ccp"],
        "JCL": [".jcl", ".job", ".cntl", ".ctl"],
        "Copybooks": [".cpy", ".copybook", ".cblcpy", ".inc"],
        "VSAM Definitions": [".ctl", ".cntl", ".def", ".vsam"],
    }

    # Normalize extensions for quick lookup
    ext_to_type = {}
    for type_name, exts in type_extensions.items():
        for ext in exts:
            ext_to_type[ext] = type_name

    # Prepare result dictionary
    classified = {
        "COBOL Code": [],
        "JCL": [],
        "Copybooks": [],
        "VSAM Definitions": [],
        "Unknown": []
    }

    # Iterate over uploaded files (filename: content)
    for file_name, content in file_json.items():
        lower_name = file_name.lower()
        matched_type = None

        for ext, type_name in ext_to_type.items():
            if lower_name.endswith(ext):
                matched_type = type_name
                break

        file_info = {"fileName": file_name, "content": content}

        if matched_type:
            classified[matched_type].append(file_info)
            logger.info(f"Classified '{file_name}' as '{matched_type}'")
        else:
            classified["Unknown"].append(file_info)
            logger.info(f"Could not classify '{file_name}' - marked as Unknown")

    # Log classification summary
    for file_type, files in classified.items():
        if files:
            logger.info(f"{file_type}: {len(files)} files")
    
    logger.info("=== FILE CLASSIFICATION COMPLETED ===")
    return classified