import re
import logging


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def detect_database_usage(source_code, source_language="COBOL"):

    """
    Detect if the source code contains database operations or embedded SQL.
    
    Args:
        source_code (str): The source code to analyze
        source_language (str): The programming language of the source code
        
    Returns:
        bool: True if database operations are detected, False otherwise
    """
    # For COBOL, check for common database-related keywords and statements
    if source_language.upper() == "COBOL":
        # Check for embedded SQL
        sql_patterns = [
            r'EXEC\s+SQL',
            r'SELECT\s+.*\s+FROM',
            r'INSERT\s+INTO',
            r'UPDATE\s+.*\s+SET',
            r'DELETE\s+FROM',
            r'CURSOR',
            r'DECLARE\s+.*\s+TABLE',
            r'FETCH',
            
            # Check for common COBOL database access methods
            r'CALL\s+.*DB2',
            r'CALL\s+.*SQL',
            r'CALL\s+.*ORACLE',
            r'CALL\s+.*DATABASE',
            r'OPEN\s+.*INPUT',
            r'OPEN\s+.*OUTPUT',
            r'OPEN\s+.*I-O',
            r'READ\s+.*FILE',
            r'WRITE\s+.*RECORD',
            r'START\s+.*KEY',
            
            # Data division entries that might indicate file/DB operations
            r'FD\s+',
            r'SELECT\s+.*ASSIGN\s+TO',
            r'ORGANIZATION\s+IS\s+INDEXED',
            r'ORGANIZATION\s+IS\s+RELATIVE',
            r'ACCESS\s+MODE\s+IS\s+DYNAMIC',
            r'ACCESS\s+MODE\s+IS\s+RANDOM',
            r'RECORD\s+KEY'
        ]
        
        # Look for any of the patterns in the source code
        for pattern in sql_patterns:
            if re.search(pattern, source_code, re.IGNORECASE):
                logger.info(f"Database usage detected with pattern: {pattern}")
                return True
                
    return False