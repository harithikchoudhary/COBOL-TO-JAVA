"""
Module for generating prompts for code analysis and conversion.
"""

def create_business_requirements_prompt(source_language, source_code, vsam_definition=""):
    """
    Creates a prompt for analyzing business requirements from source code.
    
    Args:
        source_language (str): The programming language of the source code
        source_code (str): The source code to analyze
        vsam_definition (str): Optional VSAM file definition
        
    Returns:
        str: The prompt for business requirements analysis
    """
    vsam_section = ""
    if vsam_definition:
        vsam_section = f"""
        VSAM Definition:
        {vsam_definition}
        """

    return f"""
            You are a business analyst responsible for analyzing and documenting the business requirements from the following {source_language} code and VSAM definition. Your task is to interpret the code's intent and extract meaningful business logic suitable for non-technical stakeholders.

            The code may be written in a legacy language like COBOL, possibly lacking comments or modern structure. You must infer business rules by examining variable names, control flow, data manipulation, and any input/output operations, including VSAM file structures. Focus only on **business intent**—do not describe technical implementation.

            ### Output Format Instructions:
            - Use plain text headings and paragraphs with the following structure:
            - Use '#' for main sections (equivalent to h2)
            - Use '##' for subsection headings (equivalent to h4)
            - Use '###' for regular paragraph text
            - Use '-' for bullet points and emphasize them by using bold tone in phrasing
            - Do not give response with ** anywhere.
            - Do NOT use Markdown formatting like **bold**, _italic_, or backticks

            ### Structure your output into these 5 sections:

            # Overview
            ## Purpose of the System  
            ### Describe the system's primary function and how it fits into the business.
            ## Context and Business Impact  
            ### Explain the operational context and value the system provides.

            # Objectives
            ## Primary Objective  
            ### Clearly state the system's main goal.
            ## Key Outcomes  
            ### Outline expected results (e.g., improved processing speed, customer satisfaction).

            # Business Rules & Requirements
            ## Business Purpose  
            ### Explain the business objective behind this specific module or logic.
            ## Business Rules  
            ### List the inferred rules/conditions the system enforces.
            ## Impact on System  
            ### Describe how this part affects the system's overall operation.
            ## Constraints  
            ### Note any business limitations or operational restrictions.

            # Assumptions & Recommendations
            - Assumptions  
            ### Describe what is presumed about data, processes, or environment.
            - Recommendations  
            ### Suggest enhancements or modernization directions.

            # Expected Output
            ## Output  
            ### Describe the main outputs (e.g., reports, logs, updates).
            ## Business Significance  
            ### Explain why these outputs matter for business processes.
            

            {source_language} Code:
            {source_code}

            {vsam_section}
            """

def create_technical_requirements_prompt(source_language, target_language, source_code, vsam_definition=""):
    """
    Creates a prompt for analyzing technical requirements from source code.
    
    Args:
        source_language (str): The programming language of the source code
        target_language (str): The target programming language for conversion
        source_code (str): The source code to analyze
        vsam_definition (str): Optional VSAM file definition
        
    Returns:
        str: The prompt for technical requirements analysis
    """
    vsam_section = ""
    if vsam_definition:
        vsam_section = f"""
        VSAM Definition:
        {vsam_definition}

        Additional Requirements for VSAM:
        - Analyze VSAM file structures and access methods
        - Map VSAM record layouts to appropriate database tables or data structures
        - Consider VSAM-specific operations (KSDS, RRDS, ESDS) and their equivalents
        - Plan for data migration from VSAM to modern storage
        """

    return f"""
            Analyze the following {source_language} code and extract the technical requirements for migrating it to {target_language}.
            Do not use any Markdown formatting (e.g., no **bold**, italics, or backticks).
            Return plain text only.

            **Focus on implementation details such as:**
            "1. Examine the entire codebase first to understand architectural patterns and dependencies.\n"
            "2. Analyze code in logical sections, mapping technical components to system functions.\n"
            "3. For each M204 or COBOL-specific construct, identify the exact technical requirement it represents.\n"
            "4. Document all technical constraints, dependencies, and integration points.\n"
            "5. Pay special attention to error handling, transaction management, and data access patterns.\n\n"
            "kindat each requirement as 'The system must [specific technical capability]' or 'The system should [specific technical capability]' with direct traceability to code sections.\n\n"
            "Ensure your output captures ALL technical requirements including:\n"
            "- Data structure definitions and relationships\n"
            "- Processing algorithms and computation logic\n"
            "- I/O operations and file handling\n"
            "- Error handling and recovery mechanisms\n"
            "- Performance considerations and optimizations\n"
            "- Security controls and access management\n"
            "- Integration protocols and external system interfaces\n"
            "- Database Interactions and equivalent in target language\n"
            "- VSAM file structures and their modern equivalents\n"


            Format your response as a numbered list with '# Technical Requirements' as the title.
            Each requirement should start with a number followed by a period (e.g., "1.", "2.", etc.)

            {source_language} Code:
            {source_code}

            {vsam_section}
             """

def create_code_conversion_prompt(
    source_language,
    target_language,
    source_code,
    business_requirements,
    technical_requirements,
    db_setup_template,
    vsam_definition="",
    is_chunk=False,
    chunk_type="mixed",
    chunk_index=0,
    total_chunks=1
):
    """
    Creates a prompt for converting code from one language to another.
    Now enforces a layered architecture output format.

    Args:
        source_language (str): The programming language of the source code
        target_language (str): The target programming language for conversion
        source_code (str): The source code to convert
        business_requirements (str): The business requirements extracted from analysis
        technical_requirements (str): The technical requirements extracted from analysis
        db_setup_template (str): The database setup template for the target language
        vsam_definition (str): Optional VSAM file definition
        is_chunk (bool): Whether the code is a chunk of a larger COBOL program
        chunk_type (str): Type of chunk ('declarations', 'procedures', or 'mixed')
        chunk_index (int): Index of current chunk (0-based)
        total_chunks (int): Total number of chunks

    Returns:
        str: The prompt for code conversion
    """
    vsam_section = ""
    if vsam_definition:
        vsam_section = f"""
        **VSAM Definition:**
        {vsam_definition}

        **VSAM-Specific Instructions:**
        - Convert VSAM file structures to appropriate database tables or data structures
        - Map VSAM operations to equivalent database operations
        - Maintain VSAM-like functionality (KSDS, RRDS, ESDS) using modern storage
        - Ensure data integrity and transaction management
        """

    base_prompt = f"""
        **Important- Please ensure that the {source_language} code is translated into its exact equivalent in {target_language}, maintaining a clean layered architecture.**
    Convert the following {source_language} code to {target_language} while strictly adhering to the provided business and technical requirements.

    **Source Language:** {source_language}
    **Target Language:** {target_language}

    **Required Output Structure:**
    
    Your response must be organized in the following sections, each clearly marked with a section header:

    
    ##Entity
    FileName: 
    - Define all entities and their properties
    - Define all domain entities/models
    - Include all necessary properties and relationships
    - Add appropriate annotations/decorators

    ##Repository
    FileName: 
    - Define repository interfaces
    - Include necessary data access methods
    - Add appropriate annotations/decorators


    ##Service
    FileName: 
    - Define service interfaces and implementations
    - Include business logic and transaction management
    - Add appropriate dependency injections and annotations

    ##Controller
    FileName: 
    - Define REST endpoints or API controllers
    - Include request/response handling
    - Add appropriate route mappings and annotations

    Each section must be clearly separated using the above headers. Include only relevant code for each layer.
    Ensure proper dependency injection and relationships between layers are maintained.
   

    {vsam_section}
    """
    
    if is_chunk:
        base_prompt += f"""
    **IMPORTANT CHUNKING INFORMATION:**
    This code is chunk {chunk_index + 1} of {total_chunks} from a larger {source_language} program.
    Chunk type identified as: {chunk_type}
    """
        
        if chunk_type == "declarations":
            base_prompt += f"""
    **Instructions for Declarations Chunk:**
    - Focus ONLY on converting data structures, file definitions, and variable declarations in this chunk
    - Generate appropriate class structures, fields, and data types in {target_language}
    - If needed, create class skeletons but DO NOT implement full methods
    - Ensure your output can be combined with other chunks (proper scoping)
    - Only include database connection setup code if this is the first chunk (chunk {chunk_index + 1})
    - If this is chunk 1, generate appropriate overall program structure
    - DO NOT add any "placeholder" or "to be implemented" comments for other chunks
    """
        
        elif chunk_type == "procedures":
            base_prompt += f"""
    **Instructions for Procedures Chunk:**
    - Focus ONLY on converting the business logic and procedures in this chunk
    - Ensure method implementations and logic maintain the exact behavior as the original
    - Only include necessary method/function definitions needed for this specific chunk
    - Assume data declarations are handled in other chunks
    - DO NOT include database connection code unless it's specifically part of this procedure chunk
    - DO NOT duplicate database initialization that might have been in previous chunks
    """
        
        else:  # mixed type
            base_prompt += f"""
    **Instructions for Mixed Content Chunk:**
    - Convert BOTH declarations and procedures in this chunk as appropriate
    - Maintain the structure and relationship between declarations and procedures
    - Only include database initialization if it's actually in this chunk's source code
    - If this is chunk 1, include appropriate program structure and entry points
    - If this chunk contains multiple procedures, ensure they're properly organized
    """
            
        base_prompt += f"""
    **Chunking Guidelines:**
    - Generate ONLY code for this specific chunk - don't try to complete the entire program
    - Ensure your code fragment is syntactically correct on its own
    - Maintain consistent naming across chunks (follow naming patterns in the source)
    - If this chunk references variables/methods defined in other chunks, continue using those names
    """
    
    base_prompt += f"""
    **Requirements:**
    - The output should be a complete, executable implementation in the target language
    - Maintain all business logic, functionality, and behavior of the original code
    - Produce idiomatic code following best practices in the target language
    - Include all necessary class definitions, method implementations, and boilerplate code
    - Ensure consistent data handling, formatting, and computations
    - DO NOT include markdown code blocks (like ```java or ```) in your response, just provide the raw code
    - Do not return any unwanted code in {target_language} or functions which are not in {source_language}.

    **Language-Specific Instructions:**
    - If converting to Java: Produce a fully functional and idiomatic Java implementation with appropriate class structures
    - If converting to C#: Produce a fully functional and idiomatic C# implementation that matches the original behavior exactly

    **Database-Specific Instructions**
    - If the {source_language} code includes any database-related operations, automatically generate the necessary setup code
    """
    
    # Only include DB setup template for first chunk or if it's a single chunk
    if not is_chunk or chunk_index == 0:
        base_prompt += f"""
    - Follow this example format for database initialization and setup:

    {db_setup_template if db_setup_template else 'No database setup required.'}
    """
    else:
        base_prompt += f"""
    - DO NOT include database initialization code as it should be in chunk 1
    """

    # Include business and technical requirements for context
    base_prompt += f"""
    **Business Requirements:**
    {business_requirements if business_requirements else 'None provided.'}

    **Technical Requirements:**
    {technical_requirements if technical_requirements else 'None provided.'}

    **Source Code ({source_language}{' - CHUNK ' + str(chunk_index + 1) + ' of ' + str(total_chunks) if is_chunk else ''}):**
    {source_code}

    IMPORTANT: Only return the complete converted code WITHOUT any markdown formatting. DO NOT wrap your code in triple backticks (```). Return just the raw code itself.
    """

    if is_chunk:
        # Add additional reminder for chunked processing
        base_prompt += f"""
    REMINDER: You are converting ONLY CHUNK {chunk_index + 1} of {total_chunks}. Do not try to implement logic from other chunks.
    For database-related operations, only include connection initialization if this is chunk 1 or if the database operations 
    are specifically in this chunk.
    """

    base_prompt += f"""
    **Additional Database Setup Instructions:**
    If database operations are detected in the source code, include these files in your output:

    ##application.properties
    - Database connection configuration
    - JPA/Hibernate settings
    - Connection pool settings

    ##Dependencies
    - Required database dependencies
    - Connection pool dependencies
    - ORM dependencies
    """

    return base_prompt


def create_unit_test_prompt(target_language, converted_code, business_requirements, technical_requirements):
    """Create a prompt for generating unit tests for the converted code"""
    
    prompt = f"""
    You are tasked with creating comprehensive unit tests for newly converted {target_language} code.
    
    Please generate unit tests for the following {target_language} code. The tests should verify that 
    the code meets all business requirements and handles edge cases appropriately.
    
    Business Requirements:
    {business_requirements}
    
    Technical Requirements:
    {technical_requirements}
    
    Converted Code ({target_language}):
    
    ```
    {converted_code}
    ```
    
    Guidelines for the unit tests:
    1. Use appropriate unit testing framework for {target_language} (e.g., JUnit for Java, NUnit/xUnit for C#)
    2. Create tests for all public methods and key functionality
    3. Include positive test cases, negative test cases, and edge cases
    4. Use mocks/stubs for external dependencies where appropriate
    5. Follow test naming conventions that clearly describe what is being tested
    6. Include setup and teardown as needed
    7. Add comments explaining complex test scenarios
    8. Ensure high code coverage, especially for complex business logic
    
    Provide ONLY the unit test code without additional explanations.
    """
    
    return prompt


def create_functional_test_prompt(target_language, converted_code, business_requirements):
    """Create a prompt for generating functional test cases based on business requirements"""
    
    prompt = f"""
    You are tasked with creating functional test cases for a newly converted {target_language} application.
    Give response of functional tests in numeric plain text numbering.
    
    Please generate comprehensive functional test cases that verify the application meets all business requirements.
    These test cases will be used by QA engineers to validate the application functionality.
    
    Business Requirements:
    {business_requirements}
    
    Converted Code ({target_language}):
    
    ```
    {converted_code}
    ```
    
    Guidelines for functional test cases:
    1. Create test cases that cover all business requirements
    2. Organize test cases by feature or business functionality
    3. For each test case, include:
       a. Test ID and title
       b. Description/objective
       c. Preconditions
       d. Test steps with clear instructions
       e. Expected results
       f. Priority (High/Medium/Low)
    4. Include both positive and negative test scenarios
    5. Include test cases for boundary conditions and edge cases
    6. Create end-to-end test scenarios that cover complete business processes
    
    Format your response as a structured test plan document with clear sections and test case tables.
    Return the respons ein JSON FORMA
    """
    
    return prompt