"""
Module for generating prompts for code analysis and conversion.
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

            The code may be written in a legacy language like COBOL, possibly lacking comments or modern structure. You must infer business rules by examining variable names, control flow, data manipulation, and any input/output operations. Focus only on **business intent**—do not describe technical implementation.

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

def create_dotnet_specific_prompt(source_language, source_code, db_setup_template):
    """
    Creates a .NET 8-specific prompt for code conversion.
    
    Args:
        source_language (str): The programming language of the source code
        source_code (str): The source code to convert
        db_setup_template (str): The database setup template for .NET 8
        
    Returns:
        str: The .NET 8-specific prompt for code conversion
    """
    return f"""
    .NET 8-Specific Requirements:
    - Use .NET 8 framework
    - Follow C# naming conventions (PascalCase for public members, camelCase for private)
    - Implement proper exception handling using try-catch blocks
    - Use C# 12 features where appropriate
    - Implement proper logging using Microsoft.Extensions.Logging
    - Use dependency injection with IServiceCollection
    - Follow SOLID principles
    - Use Entity Framework Core for database operations
    - Implement proper validation using System.ComponentModel.DataAnnotations
    - Use proper C# namespace structure (Company.Project.*)

    Required NuGet Packages:
    - Microsoft.AspNetCore.App
    - Microsoft.EntityFrameworkCore
    - Microsoft.Extensions.Logging
    - AutoMapper

    .NET 8 Project Structure:
    src/
    ├── Controllers/
    ├── Services/
    │   └── Interfaces/       # Service layer interfaces
    ├── Repositories/
    │   └── Interfaces/       # Repository layer interfaces
    ├── Models/
    ├── DTOs/

    .NET 8-Specific Attributes:
    - Use [ApiController] for API controllers
    - Use [Route] for routing
    - Use [FromBody] for request body binding
    - Use [Required] for validation
    - Use [JsonPropertyName] for JSON serialization
    """

def create_code_conversion_prompt(
    source_language,
    target_language,
    source_code,
    db_setup_template
):
    """
    Creates a prompt for converting code from one language to .NET 8.

    Args:
        source_language (str): The programming language of the source code
        target_language (str): The target programming language for conversion (.NET 8)
        source_code (str): The source code to convert
        db_setup_template (str): The database setup template for .NET 8

    Returns:
        str: The prompt for code conversion
    """
    language_specific_prompt = ""

# Normalize the input for safe comparison
    normalized_target = target_language.lower().strip()

    # Accept multiple synonyms
    if normalized_target in [".net 8", "c#", "csharp", ".net"]:
        language_specific_prompt = create_dotnet_specific_prompt(
            source_language,
            source_code,
            db_setup_template
        )
    else:
        raise ValueError("Only .NET 8 / C# is supported as the target language.")


    base_prompt = f"""
    Important: Please ensure that the {source_language} code is translated into its exact equivalent in {target_language}, maintaining a clean layered architecture.
    Convert the following {source_language} code to {target_language} while strictly adhering to the provided business and technical requirements.

    Source Language: {source_language}
    Target Language: {target_language}

    {language_specific_prompt}

    ENHANCED OUTPUT STRUCTURE REQUIREMENTS:
    
    Analyze the COBOL code complexity and generate the appropriate number of components:
    
    1. **Multiple Controllers**: Create separate controllers for different business domains or major functions
    2. **Multiple Services**: Implement service layer with separate services for different business logic areas
    3. **Multiple Models**: Create entity models for each major data structure found in the COBOL code
    4. **Multiple Repositories**: Implement repository pattern with separate repositories for different data access needs
    5. **DTOs**: Create data transfer objects for complex data structures when needed
    
    COMPONENT GENERATION GUIDELINES:
    
    - **Controllers**: Create one controller per major business function or COBOL program
      - Use descriptive names like "CustomerController", "OrderController", "ReportController"
      - Each controller should handle related business operations
      - Implement proper HTTP methods (GET, POST, PUT, DELETE)
    
    - **Services**: Create services for business logic separation
      - Use descriptive names like "CustomerService", "OrderService", "ValidationService"
      - Each service should handle specific business domain logic
      - Implement interfaces for dependency injection
    
    - **Models**: Create entity models for data structures
      - Use descriptive names like "Customer", "Order", "Product"
      - Include proper validation attributes
      - Follow Entity Framework Core conventions
    
    - **Repositories**: Create repositories for data access
      - Use descriptive names like "CustomerRepository", "OrderRepository"
      - Implement repository pattern with interfaces
      - Handle different data sources (database, files, etc.)
    
    - **DTOs**: Create data transfer objects when needed
      - Use for complex data structures or API responses
      - Separate internal models from external contracts
    
    NAMING CONVENTIONS:
    - Use PascalCase for all public members and class names
    - Use descriptive, business-focused names
    - Follow .NET naming conventions
    - Include proper namespaces (Company.Project.*)
    
    ARCHITECTURE PATTERNS:
    - Implement Clean Architecture principles
    - Use Dependency Injection throughout
    - Follow SOLID principles
    - Implement proper separation of concerns
    - Use async/await patterns for all I/O operations

    Requirements:
    - The output should be a complete, executable implementation in .NET 8
    - Maintain all business logic, functionality, and behavior of the original code
    - Produce idiomatic code following .NET 8 best practices
    - Include all necessary class definitions, method implementations, and boilerplate code
    - Ensure consistent data handling, formatting, and computations
    - DO NOT include markdown code blocks (like ```csharp or ```) in your response, just provide the raw code
    - Do not return any unwanted code in {target_language} or functions which are not in {source_language}.
    - **NEVER use placeholder comments or stub implementations (such as 'return await Task.FromResult(new Account());' or '// Placeholder for actual implementation'). You MUST fully implement all business logic and method bodies based on the COBOL source and requirements.**
    
    MULTIPLE COMPONENT GENERATION REQUIREMENTS:
    - **Analyze the COBOL code structure** to identify distinct business domains and functions
    - **Create separate controllers** for each major business function (e.g., CustomerController, OrderController, ReportController)
    - **Implement multiple services** for different business logic areas (e.g., CustomerService, OrderService, ValidationService)
    - **Generate multiple models** for different data structures found in the COBOL code
    - **Create multiple repositories** for different data access patterns (e.g., CustomerRepository, OrderRepository, FileRepository)
    - **Use descriptive, business-focused names** for all components
    - **Ensure proper relationships** between controllers, services, and repositories
    - **Implement dependency injection** for all service and repository dependencies
    - **Follow single responsibility principle** - each component should have one clear purpose

    Database-Specific Instructions:
    - If the {source_language} code includes any database-related operations, automatically generate the necessary setup code using Entity Framework Core
    - Follow this example format for database initialization and setup:

    {db_setup_template if db_setup_template else 'No database setup required.'}


    Source Code ({source_language}):
    {source_code}

    IMPORTANT: Only return the complete converted code WITHOUT any markdown formatting. DO NOT wrap your code in triple backticks (```). Return just the raw code itself.

    Additional Database Setup Instructions:
    If database operations are detected in the source code, include these files in your output:

    ##appsettings.json
    - Database connection configuration
    - Logging settings

    ##Dependencies
    - Required database dependencies (e.g., Microsoft.EntityFrameworkCore)
    - EF Core provider dependencies (e.g., Pomelo.EntityFrameworkCore.MySql)
    """

    return base_prompt

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