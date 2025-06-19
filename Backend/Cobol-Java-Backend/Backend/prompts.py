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

def create_java_specific_prompt(source_language, source_code, business_requirements, technical_requirements, db_setup_template, vsam_definition=""):
    """
    Creates a Java-specific prompt for code conversion.
    
    Args:
        source_language (str): The programming language of the source code
        source_code (str): The source code to convert
        business_requirements (str): The business requirements extracted from analysis
        technical_requirements (str): The technical requirements extracted from analysis
        db_setup_template (str): The database setup template for Java
        vsam_definition (str): Optional VSAM file definition
        
    Returns:
        str: The Java-specific prompt for code conversion
    """
    return f"""
    **Java-Specific Requirements:**
    - Use Spring Boot framework for the application
    - Follow Java naming conventions (camelCase for variables/methods, PascalCase for classes)
    - Implement proper exception handling using try-catch blocks
    - Use Java 8+ features where appropriate
    - Implement proper logging using SLF4J/Logback
    - Use Lombok annotations to reduce boilerplate code
    - Follow Spring Boot best practices for dependency injection
    - Use JPA/Hibernate for database operations
    - Implement proper validation using Jakarta Validation
    - Use proper Java package structure (com.company.project.*)
    
    **Required Dependencies:**
    - spring-boot-starter-web
    - spring-boot-starter-data-jpa
    - spring-boot-starter-validation
    - lombok
    - spring-boot-starter-test (for testing)
    
    **Java Project Structure:**
    ```
    src/main/java/com/company/project/
    ├── config/
    ├── controller/
    ├── service/
    ├── repository/
    ├── model/
    ├── dto/
    └── exception/
    ```
    
    **Java-Specific Annotations:**
    - Use @RestController for REST controllers
    - Use @Service for service layer
    - Use @Repository for repository layer
    - Use @Entity for JPA entities
    - Use @Data for Lombok data classes
    - Use @Valid for validation
    """

def create_csharp_specific_prompt(source_language, source_code, business_requirements, technical_requirements, db_setup_template, vsam_definition=""):
    """
    Creates a C#-specific prompt for code conversion.
    
    Args:
        source_language (str): The programming language of the source code
        source_code (str): The source code to convert
        business_requirements (str): The business requirements extracted from analysis
        technical_requirements (str): The technical requirements extracted from analysis
        db_setup_template (str): The database setup template for C#
        vsam_definition (str): Optional VSAM file definition
        
    Returns:
        str: The C#-specific prompt for code conversion
    """
    return f"""
    **C#-Specific Requirements:**
    - Use .NET Core/.NET 6+ framework
    - Follow C# naming conventions (PascalCase for public members, camelCase for private)
    - Implement proper exception handling using try-catch blocks
    - Use C# 9+ features where appropriate
    - Implement proper logging using ILogger
    - Use dependency injection with IServiceCollection
    - Follow SOLID principles
    - Use Entity Framework Core for database operations
    - Implement proper validation using FluentValidation
    - Use proper C# namespace structure (Company.Project.*)
    
    **Required NuGet Packages:**
    - Microsoft.AspNetCore.App
    - Microsoft.EntityFrameworkCore
    - FluentValidation
    - AutoMapper
    - Serilog
    
    **C# Project Structure:**
    ```
    src/
    ├── Controllers/
    ├── Services/
    ├── Repositories/
    ├── Models/
    ├── DTOs/
    ├── Extensions/
    └── Infrastructure/
    ```
    
    **C#-Specific Attributes:**
    - Use [ApiController] for API controllers
    - Use [Route] for routing
    - Use [FromBody] for request body binding
    - Use [Required] for validation
    - Use [JsonProperty] for JSON serialization
    """

def create_code_conversion_prompt(
    source_language,
    target_language,
    source_code,
    business_requirements,
    technical_requirements,
    db_setup_template,
    vsam_definition=""
):
    """
    Creates a prompt for converting code from one language to another.
    Now uses language-specific prompts based on the target language.

    Args:
        source_language (str): The programming language of the source code
        target_language (str): The target programming language for conversion
        source_code (str): The source code to convert
        business_requirements (str): The business requirements extracted from analysis
        technical_requirements (str): The technical requirements extracted from analysis
        db_setup_template (str): The database setup template for the target language
        vsam_definition (str): Optional VSAM file definition

    Returns:
        str: The prompt for code conversion
    """
    # Get language-specific prompt
    language_specific_prompt = ""
    if target_language.lower() == "java":
        language_specific_prompt = create_java_specific_prompt(
            source_language, source_code, business_requirements,
            technical_requirements, db_setup_template, vsam_definition
        )
    elif target_language.lower() in ["c#", "csharp"]:
        language_specific_prompt = create_csharp_specific_prompt(
            source_language, source_code, business_requirements,
            technical_requirements, db_setup_template, vsam_definition
        )

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

    {language_specific_prompt}

    **Required Output Structure:**
    
    Give output in below structure mentioned clearly. Each section must be properly formatted with clear section markers.
    
    Your response must be organized in the following sections, each clearly marked with a section header:

    ##Entity
    FileName: [filename]
    ```java
    // Entity code here
    ```

    ##Repository
    FileName: [filename]
    ```java
    // Repository code here
    ```

    ##Service
    FileName: [filename]
    ```java
    // Service code here
    ```

    ##Controller
    FileName: [filename]
    ```java
    // Controller code here
    ```

    ##application.properties
    ```properties
    // Properties configuration here
    ```

    ##Dependencies
    ```xml
    // Dependencies configuration here
    ```

    Each section must be clearly separated using the above headers. Include only relevant code for each layer.
    Ensure proper dependency injection and relationships between layers are maintained.
    Each code block must be properly formatted with the correct language identifier (java, properties, xml).
    File names must be clearly specified for each section.

    {vsam_section}

    **Requirements:**
    - The output should be a complete, executable implementation in the target language
    - Maintain all business logic, functionality, and behavior of the original code
    - Produce idiomatic code following best practices in the target language
    - Include all necessary class definitions, method implementations, and boilerplate code
    - Ensure consistent data handling, formatting, and computations
    - DO NOT include markdown code blocks (like ```java or ```) in your response, just provide the raw code
    - Do not return any unwanted code in {target_language} or functions which are not in {source_language}.

    **Database-Specific Instructions**
    - If the {source_language} code includes any database-related operations, automatically generate the necessary setup code
    - Follow this example format for database initialization and setup:

    {db_setup_template if db_setup_template else 'No database setup required.'}

    **Business Requirements:**
    {business_requirements if business_requirements else 'None provided.'}

    **Technical Requirements:**
    {technical_requirements if technical_requirements else 'None provided.'}

    **Source Code ({source_language}):**
    {source_code}

    IMPORTANT: Only return the complete converted code WITHOUT any markdown formatting. DO NOT wrap your code in triple backticks (```). Return just the raw code itself.

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