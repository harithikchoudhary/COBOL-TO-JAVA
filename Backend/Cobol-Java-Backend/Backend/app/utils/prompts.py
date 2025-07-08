"""
Module for generating prompts for code analysis and conversion.
"""

def create_business_requirements_prompt(source_language, source_code):
    # Unchanged, as business requirements don't need Onion Architecture-specific changes
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
    # Updated to include Onion Architecture principles in technical requirements
    return f"""
            Analyze the following {source_language} code and extract the technical requirements for migrating it to {target_language} using Onion Architecture.
            Do not use any Markdown formatting (e.g., no **bold**, italics, or backticks).
            Return plain text only.

            Focus on implementation details such as:
            1. Examine the entire codebase first to understand architectural patterns and dependencies.
            2. Analyze code in logical sections, mapping technical components to system functions.
            3. For each COBOL-specific construct, identify the exact technical requirement it represents.
            4. Document all technical constraints, dependencies, and integration points.
            5. Pay special attention to error handling, transaction management, and data access patterns.
            6. Ensure alignment with Onion Architecture principles:
               - Domain Layer: Core entities, interfaces, and business logic, independent of frameworks.
               - Application Layer: Use cases and application services, dependent only on Domain.
               - Infrastructure Layer: Data access, external services, dependent on Application interfaces.
               - Presentation Layer: API controllers, dependent on Application services.

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

def create_dotnet_specific_prompt(source_language, source_code, business_requirements, technical_requirements, db_setup_template):
    """
    Creates a .NET 8-specific prompt for code conversion using Onion Architecture.
    """
    return f"""
    .NET 8-Specific Requirements (Onion Architecture):
    - Target Framework: .NET 8 with Onion Architecture principles
    - Organize code into four main layers: Domain, Application, Infrastructure, Presentation
    - Enforce dependency inversion: Outer layers depend on inner layers via interfaces
    - Domain Layer:
        - Contains entities, enums, exceptions, and service interfaces
        - Must be independent of frameworks and external systems
        - Use plain C# classes with no external dependencies
        - Namespace: Company.Project.Domain.[Entities|Interfaces|Exceptions]
        - Project file: Domain.csproj (Class Library)
    - Application Layer:
        - Contains application services, DTOs, and interfaces
        - Implements business use cases from business_requirements
        - Depends only on Domain layer
        - Defines interfaces for infrastructure implementations
        - Namespace: Company.Project.Application.[Services|Interfaces|DTOs]
        - Project file: Application.csproj (Class Library)
    - Infrastructure Layer:
        - Contains repositories, DbContext, and external service implementations
        - Implements interfaces defined in Application layer
        - Uses Entity Framework Core for database operations
        - Namespace: Company.Project.Infrastructure.[Data|Repositories]
        - Project file: Infrastructure.csproj (Class Library)
    - Presentation Layer:
        - Contains API controllers
        - Depends on Application layer services
        - Uses ASP.NET Core for RESTful APIs
        - Namespace: Company.Project.Presentation.Controllers
        - Project file: Presentation.csproj (Web Application)
    - Solution Structure:
        - Solution file: TaskManagementSystem.sln
        - Each layer has its own .csproj file with appropriate dependencies
        - Proper project references between layers
    - Naming Conventions:
        - PascalCase for public members, classes, and interfaces
        - camelCase with _prefix for private fields
    - Implement exception handling with try-catch blocks and custom exceptions in Domain/Exceptions
    - Use C# 12 features (e.g., primary constructors, collection expressions) where appropriate
    - Implement logging with Microsoft.Extensions.Logging
    - Use dependency injection with IServiceCollection in Program.cs
    - Follow SOLID principles
    - Use Entity Framework Core for database operations with proper connection management
    - Implement validation with System.ComponentModel.DataAnnotations
    - Required NuGet Packages by Layer:
        - Domain: No external dependencies (pure C#)
        - Application: Microsoft.Extensions.DependencyInjection, AutoMapper
        - Infrastructure: Microsoft.EntityFrameworkCore, Microsoft.EntityFrameworkCore.SqlServer, Microsoft.Extensions.Logging
        - Presentation: Microsoft.AspNetCore.App, Microsoft.EntityFrameworkCore.Design, Swashbuckle.AspNetCore, AutoMapper.Extensions.Microsoft.DependencyInjection

    Project Structure:
    TaskManagementSystem/
    ├── Domain/
    │   ├── Domain.csproj
    │   ├── Entities/
    │   ├── Interfaces/
    │   ├── Exceptions/
    ├── Application/
    │   ├── Application.csproj
    │   ├── Interfaces/
    │   ├── Services/
    │   ├── DTOs/
    ├── Infrastructure/
    │   ├── Infrastructure.csproj
    │   ├── Data/
    │   ├── Repositories/
    ├── Presentation/
    │   ├── Presentation.csproj
    │   ├── Controllers/
    │   ├── Program.cs
    │   ├── appsettings.json
    ├── TaskManagementSystem.sln

    .NET 8-Specific Attributes:
    - Use [ApiController] and [Route] for controllers
    - Use [FromBody] for request body binding
    - Use [Required] and [StringLength] for validation
    - Use [JsonPropertyName] for JSON serialization
    """

def create_code_conversion_prompt(
    source_language,
    target_language,
    source_code,
    business_requirements,
    technical_requirements,
    db_setup_template
):
    """
    Creates a prompt for converting code from one language to .NET 8 using Onion Architecture.

    Args:
        source_language (str): The programming language of the source code
        target_language (str): The target programming language (.NET 8)
        source_code (str): The source code to convert
        business_requirements (str): The business requirements extracted from analysis
        technical_requirements (str): The technical requirements extracted from analysis
        db_setup_template (str): The database setup template for .NET 8

    Returns:
        str: The prompt for code conversion
    """
    if not isinstance(source_code, str):
        raise ValueError("source_code must be a string")

    language_specific_prompt = ""
    normalized_target = target_language.lower().strip()

    if normalized_target in [".net 8", "c#", "csharp", ".net"]:
        language_specific_prompt = create_dotnet_specific_prompt(
            source_language,
            source_code,
            business_requirements,
            technical_requirements,
            db_setup_template
        )
    else:
        raise ValueError("Only .NET 8 / C# is supported as the target language.")

    base_prompt = f"""
    Convert the following {source_language} code to {target_language} using Onion Architecture, ensuring the output is a complete, executable .NET 8 application that maintains all business logic and functionality.

    Source Language: {source_language}
    Target Language: {target_language}

    {language_specific_prompt}

    Required Output Structure:
    Return the response in JSON format with the following structure:
    {{
      "convertedCode": {{
        "DomainEntity": {{"FileName": "EntityName.cs", "Path": "Domain/Entities/", "content": ""}},
        "DomainInterface": {{"FileName": "IEntityNameService.cs", "Path": "Domain/Interfaces/", "content": ""}},
        "DomainExceptions": {{"FileName": "EntityNameException.cs", "Path": "Domain/Exceptions/", "content": ""}},
        "ApplicationServiceInterface": {{"FileName": "IEntityNameAppService.cs", "Path": "Application/Interfaces/", "content": ""}},
        "ApplicationService": {{"FileName": "EntityNameAppService.cs", "Path": "Application/Services/", "content": ""}},
        "ApplicationDTO": {{"FileName": "EntityNameDTO.cs", "Path": "Application/DTOs/", "content": ""}},
        "InfrastructureRepository": {{"FileName": "EntityNameRepository.cs", "Path": "Infrastructure/Repositories/", "content": ""}},
        "InfrastructureDbContext": {{"FileName": "ApplicationDbContext.cs", "Path": "Infrastructure/Data/", "content": ""}},
        "PresentationController": {{"FileName": "EntityNameController.cs", "Path": "Presentation/Controllers/", "content": ""}},
        "Program": {{"FileName": "Program.cs", "Path": "Presentation/", "content": ""}},
        "AppSettings": {{"FileName": "appsettings.json", "Path": "Presentation/", "content": ""}},
        "DomainProject": {{"FileName": "Domain.csproj", "Path": "Domain/", "content": ""}},
        "ApplicationProject": {{"FileName": "Application.csproj", "Path": "Application/", "content": ""}},
        "InfrastructureProject": {{"FileName": "Infrastructure.csproj", "Path": "Infrastructure/", "content": ""}},
        "PresentationProject": {{"FileName": "Presentation.csproj", "Path": "Presentation/", "content": ""}},
        "SolutionFile": {{"FileName": "TaskManagementSystem.sln", "Path": "./", "content": ""}},
        "Dependencies": {{"content": "NuGet packages and .NET dependencies needed"}}
      }},
      "databaseUsed": true/false,
      "conversionNotes": "Detailed notes about the conversion process",
      "potentialIssues": ["List of potential issues or considerations"]
    }}

    Each section must be clearly separated with correct file names and paths. Ensure:
    - Proper dependency injection between layers
    - Domain layer has no dependencies (pure C# class library)
    - Application layer depends only on Domain (references Domain project)
    - Infrastructure layer implements Application interfaces (references Application project)
    - Presentation layer depends on Application (references Application project)
    - Each layer has its own .csproj file with appropriate dependencies
    - Solution file (.sln) includes all projects with proper references
    - Code follows C# naming conventions and SOLID principles
    - Project references follow dependency direction (outer layers reference inner layers)

    Database Instructions:
    - Include Entity Framework Core setup in Infrastructure layer only if {source_language} code contains database operations (e.g., EXEC SQL, FILE SECTION, VSAM)
    - Use this database setup template if applicable:
    {db_setup_template if db_setup_template else 'No database setup required.'}

    Business Requirements:
    {business_requirements if business_requirements else 'None provided.'}

    Technical Requirements:
    {technical_requirements if technical_requirements else 'None provided.'}

    Source Code ({source_language}):
    {source_code}

    Additional Instructions:
    - Only include database code if explicitly required by source code
    - Ensure all variables are initialized and methods are implemented
    - Use proper namespace organization (Company.Project.[Layer])
    - Include all necessary using statements
    - Handle COBOL-specific constructs (e.g., PIC clauses, PERFORM) appropriately
    - Return raw code without markdown code fences
    """

    return base_prompt

def create_unit_test_prompt(target_language, converted_code, business_requirements, technical_requirements):
    """
    Creates a prompt for generating unit tests for the converted .NET 8 code.
    """
    return f"""
    Generate unit tests for the following .NET 8 code using xUnit and Moq, focusing on the Application and Domain layers. Ensure tests cover all business logic and edge cases.

    Target Language: {target_language}
    Converted Code: {converted_code}
    Business Requirements: {business_requirements}
    Technical Requirements: {technical_requirements}

    Return the response in JSON format:
    {{
      "unitTestCode": "Complete unit test code",
      "testDescription": "Description of the test strategy",
      "coverage": ["List of functionalities covered"]
    }}
    """

def create_functional_test_prompt(target_language, converted_code, business_requirements):
    """
    Creates a prompt for generating functional tests for the converted .NET 8 code.
    """
    return f"""
    Generate functional test scenarios for the following .NET 8 application, focusing on user journeys and business requirements. Use SpecFlow for acceptance testing.

    Target Language: {target_language}
    Converted Code: {converted_code}
    Business Requirements: {business_requirements}

    Return the response in JSON format:
    {{
      "functionalTests": [
        {{"id": "FT1", "title": "Test scenario title", "steps": ["Step 1", "Step 2"], "expectedResult": "Expected outcome"}}
      ],
      "testStrategy": "Description of the overall testing approach"
    }}
    """

def create_unit_test_prompt(target_language, converted_code, business_requirements, technical_requirements):
    """Create a prompt for generating unit tests for the converted .NET 8 code"""
    
    prompt = f"""
    You are tasked with creating comprehensive unit tests for newly converted {target_language} code organized in Onion Architecture.
    
    Please generate unit tests for the following {target_language} code. The tests should verify that 
    the code meets all business requirements and handles edge cases appropriately.
    
    Business Requirements:
    {business_requirements}
    
    Technical Requirements:
    {technical_requirements}
    
    Converted Code ({target_language}):
    
    {converted_code}
    
    Guidelines for the unit tests:
    1. Use NUnit as the unit testing framework for .NET 8
    2. Create tests for all public methods in Application and Domain services
    3. Include positive test cases, negative test cases, and edge cases
    4. Use Moq for mocking dependencies (e.g., repository interfaces)
    5. Follow test naming conventions that clearly describe what is being tested
    6. Include setup and teardown as needed using [SetUp] and [TearDown]
    7. Add comments explaining complex test scenarios
    8. Ensure high code coverage, especially for complex business logic
    9. Place tests in a Tests/UnitTests/ folder with appropriate namespace (e.g., SolutionName.Tests.UnitTests)
    
    Provide ONLY the unit test code without additional explanations.
    """
    
    return prompt

def create_functional_test_prompt(target_language, converted_code, business_requirements):
    # Unchanged, as functional tests don't need specific changes for Onion Architecture
    prompt = f"""
    You are tasked with creating functional test cases for a newly converted {target_language} application.
    Give response of functional tests in numeric plain text numbering.
    
    Please generate comprehensive functional test cases that verify the application meets all business requirements.
    These test cases will be used by QA engineers to validate the application functionality.
    
    Business Requirements:
    {business_requirements}
    
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