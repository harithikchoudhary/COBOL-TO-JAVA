import re
from typing import List

def extract_business_logic_lines(cobol_code: str) -> List[str]:
    """
    Extracts lines from COBOL code that likely represent business logic (e.g., IF, PERFORM, EVALUATE, COMPUTE).
    Returns a list of relevant lines for summarization or prompt inclusion.
    """
    logic_keywords = [
        r"^\s*IF ",
        r"^\s*PERFORM ",
        r"^\s*EVALUATE ",
        r"^\s*COMPUTE ",
        r"^\s*ADD ",
        r"^\s*SUBTRACT ",
        r"^\s*MULTIPLY ",
        r"^\s*DIVIDE ",
        r"^\s*CALL ",
        r"^\s*GO TO ",
        r"^\s*MOVE ",
        r"^\s*READ ",
        r"^\s*WRITE ",
        r"^\s*ACCEPT ",
        r"^\s*DISPLAY "
    ]
    pattern = re.compile(r"|".join(logic_keywords), re.IGNORECASE)
    lines = cobol_code.splitlines()
    business_logic_lines = [line.strip() for line in lines if pattern.match(line)]
    return business_logic_lines

def extract_business_operations(cobol_code: str) -> list:
    """
    Extracts business operation names (paragraphs and PERFORM targets) from COBOL code.
    Returns a list of operation names (e.g., ACCOUNT-TRANSFER, TRANSACTION-HISTORY).
    """
    import re
    # Find paragraph names (e.g., ACCOUNT-TRANSFER.)
    paragraph_pattern = re.compile(r"^\s*([A-Z0-9-]+)\.", re.MULTILINE)
    paragraphs = set(paragraph_pattern.findall(cobol_code))
    # Find PERFORM targets (e.g., PERFORM ACCOUNT-TRANSFER)
    perform_pattern = re.compile(r"PERFORM\s+([A-Z0-9-]+)", re.IGNORECASE)
    performs = set(perform_pattern.findall(cobol_code))
    # Only keep those that are not utility/boilerplate
    ignore = {"INITIALIZE-TRANSACTION", "FINALIZE-TRANSACTION", "HANDLE-FILE-ERROR", "START-AUDIT-LOG", "END-AUDIT-LOG", "INITIALIZE-TEMP-STORAGE", "SEND-ACCOUNT-MAP", "SEND-HISTORY-MAP", "SEND-MQ-NOTIFICATION", "STORE-ACCOUNT-IN-TSQ", "STORE-TRANSACTION-IN-TSQ", "LOG-TRANSACTION", "LOG-ERROR", "DEBIT-FROM-ACCOUNT", "CREDIT-TO-ACCOUNT", "READ-TRANSACTION-HISTORY", "PROCESS-REPORT-RECORDS", "FORMAT-REPORT-LINE", "WRITE-REPORT-LINE"}
    business_ops = sorted((paragraphs | performs) - ignore)
    return business_ops 