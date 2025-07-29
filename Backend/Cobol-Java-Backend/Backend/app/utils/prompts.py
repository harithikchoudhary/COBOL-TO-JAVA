"""
Module for generating prompts for code analysis and conversion.
"""
def create_target_structure_prompt(source_language, source_code):
    """
    Creates a prompt for analyzing COBOL code and all related artifacts (JCL, VSAM, Copybooks, BMS Maps, Control Files, CICS screens/sections) to generate a comprehensive target .NET 8 WebAPI project structure.

    Args:
        source_language (str): The programming language of the source code (e.g., COBOL)
        source_code (str): The source code and related artifacts to analyze (should include all relevant content)

    Returns:
        str: The prompt for target structure analysis
    """
    return f"""
    You are an expert software architect specializing in COBOL to .NET 8 migration.
    Analyze the provided {source_language} code and ALL related mainframe artifacts to create a comprehensive target structure for a modern .NET 8 WebAPI application.

    The input may include:
    - COBOL source code (programs, modules)
    - JCL (Job Control Language) scripts
    - VSAM file definitions
    - Copybooks (data structure definitions)
    - BMS Maps (CICS screen definitions)
    - Control Files (configuration, batch control)
    - CICS commands and screen sections
    - Any other legacy mainframe artifacts

    For each artifact type, perform the following:
    1. Identify and describe its purpose in the legacy system.
    2. Map its functionality and structure to the appropriate .NET 8 WebAPI components (Controllers, Models, Services, Repositories, Configuration, etc.).
    3. For JCL: Describe how batch jobs, scheduling, and file operations should be represented or replaced in .NET 8 (e.g., background services, scheduled jobs, or API endpoints).
    4. For VSAM: Map file-based data storage to relational database tables using Entity Framework Core, and describe the migration of data access patterns.
    5. For Copybooks: Extract all data structures and show how they become C# models/entities.
    6. For BMS Maps: Identify all CICS screen definitions and describe their equivalent in a modern web API (e.g., API endpoints, DTOs, or UI integration points).
    7. For Control Files: Explain how configuration and control logic should be handled in .NET (e.g., appsettings.json, environment variables).
    8. For CICS commands and screens: Map transaction and screen logic to .NET 8 patterns (API endpoints, controllers, service methods, etc.).
    9. For each artifact, note any special migration considerations, dependencies, or integration points.

    Based on the code structure, business logic, data models, and all mainframe artifacts, design a standard .NET 8 WebAPI project structure that follows:
    - Standard .NET 8 WebAPI conventions
    - .NET 8 best practices

    The structure should include:
    - Controllers (for API endpoints)
    - Models (for data structures)
    - Services (for business logic)
    - Repositories (for data access)
    - Interfaces (for services and repositories)
    - Database design (if applicable)
    - Configuration files (appsettings.json)
    - Logging and error handling
    - Security considerations (authentication, authorization)
    - Integration points (if any)
    - Program.cs
    - Entity Framework Core setup (always include if data is present)
    - Application DbContext for database interactions
    - Batch/background job handling (if JCL or batch logic is present)
    - UI integration points (if BMS/CICS screens are present)

    Analyze the following {source_language} code and artifacts and provide a detailed target structure:

    {source_code}

    Provide your analysis in a DYNAMIC JSON format. The JSON structure should be flexible and reflect only the relevant sections and keys for the provided artifacts. Do NOT include empty or irrelevant sections. Add or omit keys as appropriate for the content. Example structure (adapt as needed):
    {{
      "project_name": "string",
      "architecture_pattern": "Standard .NET 8 WebAPI",
      "folders": [
        {{
          "name": "string",
          "purpose": "string",
          "folder_structure": [
            {{
              "name": "string",
              "type": "string",
              "purpose": "string"
            }}
          ]
        }}
      ],
      "external_dependencies": ["string"],
      "configuration_requirements": ["string"]
    }}
    
    Note: This JSON format is only a guideline. Adapt the structure to fit the actual content and artifacts found in the analysis. Do not include all keys if not relevant. Add new keys if needed for special artifacts or migration considerations.

    Focus on:
    1. Identifying all data structures from COBOL records and copybooks
    2. Mapping CICS operations and BMS screens to appropriate .NET WebAPI patterns (controllers, endpoints, DTOs)
    3. Converting file operations and VSAM definitions to database operations (Entity Framework Core)
    4. Creating appropriate API endpoints in Controllers for all business and screen logic
    5. Defining Services and Repositories with interfaces for business logic and data access
    6. Implementing proper error handling and validation
    7. Security considerations
    8. Logging and auditing requirements
    9. Integration points (including batch jobs, control files, and external systems)
    10. UI or API integration for legacy screens (if BMS/CICS present)
    11. Batch/background job handling for JCL logic
    """

def create_business_requirements_prompt(source_language, source_code):
    """
    Creates a prompt for analyzing business requirements from source code.
    
    Args:
        source_language (str): The programming language of the source code
        source_code (str): The source code to analyze
        
    Returns:
        str: The prompt for business requirements analysis
    """
    return f"""
            You are a business analyst responsible for analyzing and documenting the business requirements from the following {source_language} code. Your task is to interpret the code's intent and extract meaningful business logic suitable for non-technical stakeholders.

            The code may be written in a legacy language like COBOL, possibly lacking comments or modern structure. You must infer business rules by examining variable names, control flow, data manipulation, and any input/output operations. Focus only on business intent—do not describe technical implementation.

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
            """

def create_technical_requirements_prompt(source_language, target_language, source_code):
    """
    Creates a prompt for analyzing technical requirements from source code.
    
    Args:
        source_language (str): The programming language of the source code
        target_language (str): The target programming language for conversion (.NET 8)
        source_code (str): The source code to analyze
        
    Returns:
        str: The prompt for technical requirements analysis
    """
    return f"""
            Analyze the following {source_language} code and extract the technical requirements for migrating it to {target_language}.
            Do not use any Markdown formatting (e.g., no **bold**, italics, or backticks).
            Return plain text only.

            Focus on implementation details such as:
            1. Examine the entire codebase first to understand architectural patterns and dependencies.
            2. Analyze code in logical sections, mapping technical components to system functions.
            3. For each COBOL-specific construct, identify the exact technical requirement it represents.
            4. Document all technical constraints, dependencies, and integration points.
            5. Pay special attention to error handling, transaction management, and data access patterns.

            Format each requirement as 'The system must [specific technical capability]' or 'The system should [specific technical capability]' with direct traceability to code sections.

            Ensure your output captures ALL technical requirements including:
            - Data structure definitions and relationships
            - Processing algorithms and computation logic
            - I/O operations and file handling
            - Error handling and recovery mechanisms
            - Performance considerations and optimizations
            - Security controls and access management
            - Integration protocols and external system interfaces
            - Database interactions and equivalent in .NET 8 using Entity Framework Core

            Format your response as a numbered list with '# Technical Requirements' as the title.
            Each requirement should start with a number followed by a period (e.g., "1.", "2.", etc.)

            {source_language} Code:
            {source_code}
            """

def create_cobol_to_dotnet_conversion_prompt(source_code, db_setup_template):
    """
    Creates a comprehensive prompt for converting COBOL code to .NET 8 WebAPI.
    
    Args:
        source_code (str): The COBOL source code to convert
        db_setup_template (str): The database setup template for .NET 8
        
    Returns:
        str: The complete COBOL to .NET 8 conversion prompt
    """
    return f"""
    COBOL TO .NET 8 WEBAPI CONVERSION

    Important: Please ensure that the COBOL code is translated into its exact equivalent in .NET 8, using a standard WebAPI project structure.
    Convert the following COBOL code to .NET 8 while strictly adhering to the provided business and technical requirements.

    .NET 8 WebAPI Requirements:
    - Use .NET 8 framework
    - Follow C# naming conventions (PascalCase for public members, camelCase for private)
    - Implement proper exception handling using try-catch blocks
    - Use C# 12 features where appropriate
    - Implement logging using Microsoft.Extensions.Logging
    - Use dependency injection with IServiceCollection
    - Use Entity Framework Core for database operations if needed
    - Implement validation using System.ComponentModel.DataAnnotations
    - Use proper C# namespace structure (Company.Project.*)

    Required NuGet Packages:
    - Microsoft.AspNetCore.App
    - Microsoft.EntityFrameworkCore (if database is used)
    - Microsoft.Extensions.Logging

    .NET 8 WebAPI Project Structure:
    MyProject/
      Controllers/
      Models/
      Services/
        Interfaces/
      Repositories/
        Interfaces/
      Program.cs
      appsettings.json

    .NET 8-Specific Attributes:
    - Use [ApiController] for API controllers
    - Use [Route] for routing
    - Use [FromBody] for request body binding
    - Use [Required] for validation
    - Use [JsonPropertyName] for JSON serialization
    - For each business domain or major function, create appropriately named Controllers, Services, Repositories, and Models (e.g., CustomerController, ICustomerService, CustomerService, ICustomerRepository, CustomerRepository, CustomerModel) by analyzing the input files.
    - Always create interfaces for Services and Repositories and implement them in concrete classes.

    OUTPUT STRUCTURE REQUIREMENTS:
    - Use a standard .NET 8 WebAPI structure with Controllers, Models, Services, and Repositories
    - Place business logic in Controllers and Services, and data access logic in Repositories
    - Always create interfaces for Services and Repositories and implement them in concrete classes
    - Use Entity Framework Core only if the original COBOL code interacts with a database
    - Use standard .NET 8 conventions for controllers, models, services, repositories, and configuration
    - Implement all required endpoints in Controllers
    - Use dependency injection for required services (e.g., DbContext, Logger, Services, Repositories)
    - Implement proper exception handling and validation
    - The output should be a complete, executable .NET 8 WebAPI project
    - Do NOT include markdown code blocks (like ```csharp or ```), just provide the raw code
    - Do NOT include placeholder comments or stub implementations; fully implement all business logic and method bodies based on the COBOL source and requirements

    Database Setup Template:
    {db_setup_template}

    COBOL Source Code:
    {source_code}
    """
    
def create_unit_test_prompt(target_language, converted_code):
    """Create a prompt for generating unit tests for the converted .NET 8 code"""
    
    prompt = f"""
    You are tasked with creating comprehensive unit tests for newly converted {target_language} code.
    
    Please generate unit tests for the following {target_language} code. The tests should verify that 
    the code meets all business requirements and handles edge cases appropriately.
    
    
    Converted Code ({target_language}):
    
    {converted_code}
    
    Guidelines for the unit tests:
    1. Use NUnit or xUnit as the unit testing framework for .NET 8
    2. Create tests for all public methods and key functionality
    3. Include positive test cases, negative test cases, and edge cases
    4. Use Moq for mocking external dependencies where appropriate
    5. Follow test naming conventions that clearly describe what is being tested
    6. Include setup and teardown as needed using [SetUp] and [TearDown]
    7. Add comments explaining complex test scenarios
    8. Ensure high code coverage, especially for complex business logic
    
    Provide ONLY the unit test code without additional explanations.
    """
    
    return prompt

def create_functional_test_prompt(target_language, converted_code):
    """Create a prompt for generating functional test cases based on business requirements"""
    
    prompt = f"""
    You are tasked with creating functional test cases for a newly converted {target_language} application.
    Give response of functional tests in numeric plain text numbering.
    
    Please generate comprehensive functional test cases that verify the application meets all business requirements.
    These test cases will be used by QA engineers to validate the application functionality.
    
    
    Converted Code ({target_language}):
    
    {converted_code}
    
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
    Return the response in JSON format
    """
    
    return prompt