import os        
import time       
import json       
import re         


def extract_json_from_response(text):
    """
    Extract JSON content from the response text.
    Handle cases where the model might wrap JSON in markdown code blocks,
    add additional text, or return truncated/incomplete JSON.
    """
    logger.info("=== JSON EXTRACTION PROCESS ===")
    logger.info(f"Input text length: {len(text)} characters")
    logger.info(f"Input text preview: {text[:300]}...")
    
    try:
        # First, try to parse the whole text as JSON
        result = json.loads(text)
        logger.info(" Direct JSON parsing successful")
        return result
    except json.JSONDecodeError as e:
        logger.info(f" Direct JSON parsing failed: {str(e)}")
        logger.info("Trying alternative methods...")
        
        # Try to extract JSON from markdown code blocks
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, text)
        
        if matches:
            logger.info(f"Found {len(matches)} potential JSON blocks in markdown")
            # Try each potential JSON block
            for i, match in enumerate(matches):
                try:
                    result = json.loads(match)
                    logger.info(f" Successfully parsed JSON from markdown block {i+1}")
                    return result
                except json.JSONDecodeError:
                    logger.info(f" Failed to parse markdown block {i+1}")
                    continue
        
        # Look for JSON-like structures with repair attempt for truncated JSON
        try:
            # Find text between curly braces including nested braces
            if text.count('{') > text.count('}'):
                logger.info("Detected potentially truncated JSON, attempting repair")
                
                # Basic repair for common truncation issues
                if '"convertedCode"' in text and '"conversionNotes"' in text:
                    # Extract what we have between the main braces
                    main_content = re.search(r'{(.*)', text)
                    if main_content:
                        content = main_content.group(0)
                        
                        # Check if we have the convertedCode field but it's incomplete
                        code_match = re.search(r'"convertedCode"\s*:\s*"(.*?)(?<!\\)"', content)
                        if code_match:
                            code = code_match.group(1)
                        else:
                            code_start = re.search(r'"convertedCode"\s*:\s*"(.*)', content)
                            if code_start:
                                code = code_start.group(1)
                            else:
                                code = ""
                        
                        # Check for conversionNotes
                        notes_match = re.search(r'"conversionNotes"\s*:\s*"(.*?)(?<!\\)"', content)
                        if notes_match:
                            notes = notes_match.group(1)
                        else:
                            notes = "Truncated during processing"
                        
                        # Create a valid JSON object with what we could extract
                        result = {
                            "convertedCode": code.replace('\\n', '\n').replace('\\"', '"'),
                            "conversionNotes": notes,
                            "potentialIssues": ["Response was truncated - some content may be missing"]
                        }
                        logger.info(" Successfully repaired truncated JSON")
                        return result
            
            # If repair didn't work, try to find complete JSON objects
            brace_pattern = r'({[\s\S]*?})'
            potential_jsons = re.findall(brace_pattern, text)
            
            logger.info(f"Found {len(potential_jsons)} potential JSON objects")
            for i, potential_json in enumerate(potential_jsons):
                try:
                    if len(potential_json) > 20:  # Avoid tiny fragments
                        result = json.loads(potential_json)
                        logger.info(f" Successfully parsed JSON object {i+1}")
                        return result
                except json.JSONDecodeError:
                    logger.info(f" Failed to parse JSON object {i+1}")
                    continue
            
            logger.warning("Could not extract valid JSON from response")
            
            # Last resort: create a minimal valid response
            result = {
                "convertedCode": "Extraction failed - see raw response",
                "conversionNotes": "JSON parsing failed. The model response may have been truncated.",
                "potentialIssues": ["JSON extraction failed"],
                "raw_text": text[:1000] + "..." if len(text) > 1000 else text
            }
            logger.info("Created fallback JSON response")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting JSON: {str(e)}")
            return {
                "error": "JSON extraction failed",
                "raw_text": text[:1000] + "..." if len(text) > 1000 else text
            }
