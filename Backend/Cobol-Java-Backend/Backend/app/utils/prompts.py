"""
Module for generating prompts for code analysis and conversion.
"""

def get_conversion_instructions():
    """Get the conversion instructions (dos and donts) for COBOL to C# conversion"""
    return """
    You are an expert COBOL to C# converter. Your task is to convert COBOL code to C# while preserving business logic and adhering to best practices.
    Follow these guidelines strictly:
        DO's

        1. **Preserve Business Logic:** 
        - Extract all COBOL `PROCEDURE DIVISION` logic and move it into Services (not Controllers).
        - Retain original functionality, calculations, validations, and control flow.

        2. **Follow Layered Architecture:**
        - Controllers → Services → Repositories.
        - Controllers must only handle HTTP requests and responses.
        - Services handle business logic.
        - Repositories handle data access (EF Core or in-memory).

        3. **Use Standard .NET 8 Patterns:**
        - Dependency Injection for all Services and Repositories.
        - Proper exception handling (ErrorHandlingMiddleware + try/catch).
        - Logging with ILogger<T>.
        - Validation with DataAnnotations.

        4. **Map COBOL Data Structures Carefully:**
        - `WORKING-STORAGE` and `RECORD` sections → C# Models.
        - Ensure correct type mappings (e.g., `PIC 9(n)` → int/long/decimal).

        5. **Ensure Security:**
        - Implement authentication/authorization if sensitive operations are detected.
        - Validate all inputs to prevent data corruption.

        6. **Output Complete Solution:**
        - Include **all required files** (Controllers, Models, Services, Repositories, DbContext, Program.cs, appsettings.json, etc.).
        - Provide fully implemented, compilable code.

        7. **Replace File I/O and CICS:**
        - Convert file reads/writes to EF Core database operations where applicable.
        - Convert EXEC CICS calls into service abstractions or external API integrations.

        8. **Implement Full Endpoints:**
        - Every major COBOL function should map to at least one API endpoint in Controllers.

        9. **Document Important Parts:**
        - Use XML doc comments (///) above Service methods to explain business rules or assumptions.

        10. **Handle Transactions and Concurrency:**
            - Use EF Core transactions for multi-step updates.
            - Implement optimistic concurrency if COBOL implied record locking.

        ========================================
        DON'Ts
        ========================================
        1. **Don't Omit Logic:**
        - Do NOT leave placeholders or TODO comments.
        - Do NOT simplify business rules; preserve all conditions and flows.

        2. **Don't Put Business Logic in Controllers or Repositories:**
        - Keep Controllers thin.
        - Do NOT embed calculations or validations in Repositories.

        3. **Don't Break Naming Conventions:**
        - Avoid COBOL-style names (e.g., CUSTOMER-ID); convert to PascalCase (CustomerId).

        4. **Don't Use Non-Standard Packages:**
        - Only use built-in Microsoft.* packages unless explicitly instructed.

        5. **Don't Skip Error Handling:**
        - Never leave unhandled exceptions; wrap logic in try/catch where needed.

        6. **Don't Produce Partial Code:**
        - Never output incomplete projects.
        - Never output just a single file unless explicitly requested.

        7. **Don't Use Console Output or File-Based Debugging:**
        - Use ILogger for logging instead of `Console.WriteLine`.

        8. **Don't Hardcode Configuration:**
        - Use appsettings.json for connection strings, external endpoints, and secrets.

        9. **Don't Expose Internal Implementation Details in API Responses:**
        - Only return sanitized models (DTOs) from Controllers.

        10. **Don't Include Markdown Syntax or Commentary in Output:**
            - Output should be raw code files only (no ``` markers or extra explanation).
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

    Analyze the following COBOL source code, CICS, VSAM, Copybooks, BMS and artifacts and provide a detailed target structure:

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

def create_cobol_to_dotnet_conversion_prompt(source_code: str, db_setup_template: str) -> str:
    """
    Creates a comprehensive prompt for converting COBOL code to .NET 8 WebAPI (C#),
    with detailed business-logic handling and COBOL-specific migration guidance.

    Args:
        source_code (str): The COBOL source code to convert.
        db_setup_template (str): The database setup template/instructions for .NET 8 (EF Core).

    Returns:
        str: The complete COBOL -> .NET 8 conversion prompt.
    """
    return f"""
COBOL → .NET 8 C# WEBAPI CONVERSION (FULL PROJECT, PRODUCTION-READY)

ROLE:
You are a senior modernization engineer. Convert the COBOL code below into a complete, runnable .NET 8 WebAPI solution in C#, following clean layering, built-in .NET features, and SOLID principles.

HIGH-LEVEL OBJECTIVES:
- Preserve business rules and data flow exactly as implemented in COBOL.
- Replace file-based I/O with EF Core database operations when applicable.
- Expose business capabilities as REST endpoints with proper validation, error handling, and logging.
- Produce a compilable .NET 8 WebAPI solution with all necessary files.

========================================
A) .NET 8 WEBAPI REQUIREMENTS
========================================
- Target: .NET 8 / C# 12.
- Naming: PascalCase (public types/members), camelCase (locals/params/private fields).
- Controllers: Mark with [ApiController], [Route("api/[controller]")].
- Model Binding: Use [FromBody] for request DTOs. Use DataAnnotations (e.g., [Required], [StringLength], [Range]).
- Dependency Injection: Use IServiceCollection; constructor injection only.
- Logging: Use Microsoft.Extensions.Logging (ILogger<T>).
- EF Core: Use only if the COBOL code performs persistent operations; otherwise keep in-memory abstractions with interfaces.
- Configuration: Use appsettings.json (+ environment-specific variants).
- Versioning (basic): Route-based or conventional (e.g., /api/v1/...).
- Do NOT use third-party packages unless strictly necessary. Prefer built-in BCL and Microsoft.* packages.

Required (built-in) packages:
- Microsoft.AspNetCore.App (metapackage)
- Microsoft.EntityFrameworkCore (if persistence is needed)
- Microsoft.Extensions.Logging

Optional (only if necessary, not required): API Explorer/Swagger via Swashbuckle (do not include if not asked).

========================================
B) PROJECT STRUCTURE (REFERENCE — ADD MORE IF NEEDED)
========================================
MyProject/
  Controllers/
  Models/
  Services/
    Interfaces/
  Repositories/
    Interfaces/
  Middleware/
  Configuration/
  Program.cs
  appsettings.json
  appsettings.Development.json

Notes:
- You may add folders for Infrastructure, BackgroundJobs (Hosted Services), Integration (external systems), Security, etc., IF evidence exists in COBOL (e.g., batch jobs, external calls).
- For messaging or external systems, define abstractions (e.g., IExternalSystemClient, IMessageBus) without pinning to a vendor.

========================================
C) BUSINESS LOGIC HANDLING (MANDATORY)
========================================
- Extract COBOL business logic from PROCEDURE DIVISION. Identify paragraphs/sections implementing rules.
- Map COBOL control flow to idiomatic C#:
  - IF / EVALUATE ⇒ if / switch.
  - PERFORM / PERFORM THRU ⇒ method calls (split into cohesive private/public service methods).
  - GO TO ⇒ refactor into structured control flow; eliminate unstructured jumps.
  - MOVE / COMPUTE ⇒ assignments/expressions with proper types.
  - CALL ⇒ service-layer method calls or integration clients.
- Place ALL business rules in Services (not Controllers, not Repositories).
- Public service classes MUST have interfaces (e.g., IPremiumService, IEligibilityService).
- Keep services cohesive; split large procedures into smaller testable methods with clear names (e.g., CalculatePremium, ValidateEligibility, NormalizeCustomerData).
- Document assumptions as XML doc comments (///) above methods. Avoid TODOs and placeholders; fully implement logic inferred from COBOL.

========================================
D) DATA MODELING & TYPE MAPPING
========================================
- Map WORKING-STORAGE, FILE SECTION, and RECORD definitions to C# models/entities.
- Type conversions:
  - PIC 9(n)      ⇒ int / long (choose range-aware), or decimal for arithmetic/precision.
  - PIC 9(n)V9(m) ⇒ decimal (scale m).
  - COMP-3       ⇒ decimal (packed).
  - PIC X(n)     ⇒ string.
  - Date/Time formats ⇒ DateOnly/TimeOnly/DateTime per semantics.
- Normalize field names to PascalCase in C#; preserve original COBOL field name in an XML summary if helpful.
- If data is persisted in COBOL files, model equivalent EF Core entities and DbContext, with keys and relationships.
- Validate structurally with DataAnnotations (e.g., max length for PIC X(n), numeric ranges for PIC 9).

========================================
E) FILE I/O & CICS MIGRATION
========================================
- READ/WRITE/OPEN/CLOSE (sequential/indexed files): Replace with repository methods using EF Core (e.g., Find, Add, Update, Remove, SaveChangesAsync).
- RECORD locking logic: Map to EF Core concurrency patterns (rowversion/timestamp or optimistic concurrency).
- EXEC CICS equivalents:
  - Data access ⇒ repository + DbContext.
  - Transactional units ⇒ EF Core transactions (IDbContextTransaction) where required.
  - External calls ⇒ define service/HTTP client interfaces; implement with HttpClient (typed clients via DI).
  - Message passing ⇒ define IMessageBus interface (leave provider-agnostic).
- JCL/batch indications: Implement IHostedService/BackgroundService for scheduled/batch processes. Move parameterization to configuration.

========================================
F) CONTROLLERS & ENDPOINTS
========================================
- Controllers are thin: input validation, call service methods, return appropriate results.
- Use IActionResult/Results for HTTP behavior:
  - 200/201 for success with data/creation.
  - 204 when no content.
  - 400 for validation errors; 404 for missing resources; 409 for conflicts; 500 for unhandled errors.
- Implement pagination for list endpoints (query params: page, pageSize) if original logic iterates large sets.
- Ensure idempotency where COBOL implied re-runs (e.g., batch writes) — add natural keys/constraints and conflict handling.

========================================
G) ERROR HANDLING, TRANSACTIONS, AUDIT
========================================
- Centralize exception handling via middleware (e.g., ErrorHandlingMiddleware).
- Use ILogger for:
  - Start/End of major service operations.
  - Validation failures and business rule violations.
  - External system timeouts/retries (if applicable).
- For multi-step operations, use EF Core transactions.
- Add created/updated timestamps and (if needed) correlation/activity IDs on operations for auditability.

========================================
H) SECURITY (AS NEEDED)
========================================
- If original code implies protected operations, add JWT Bearer authentication (Microsoft.AspNetCore.Authentication.JwtBearer) and role-based authorization.
- Validate inputs rigorously; never trust client data.
- Avoid exposing internal IDs if not necessary.

========================================
I) CONFIGURATION & ENVIRONMENTS
========================================
- Use appsettings.json + appsettings.Development.json for overrides.
- Connection strings and external endpoints MUST be in configuration.
- Bind strongly typed options via IOptions<T> (Configuration/Options pattern).

========================================
J) PERFORMANCE & QUALITY
========================================
- Avoid N+1 queries; use projection and pagination.
- Prefer async (Task-based) for I/O operations.
- Keep cyclomatic complexity low by splitting methods logically.
- Ensure repository queries are filtered and indexed appropriately.

========================================
K) OUTPUT FORMAT (STRICT)
========================================
- Output a FULL solution with all files. No markdown code fences (no ```), no extra commentary.
- For EACH file, print:
  === <relative-path-from-root> ===
  <file contents>

Required files (extend as needed by detected features):
- Program.cs
- appsettings.json (+ appsettings.Development.json)
- Controllers/*.cs (at least one)
- Models/*.cs (entities/DTOs as needed)
- Services/Interfaces/*.cs and Services/*.cs
- Repositories/Interfaces/*.cs and Repositories/*.cs
- Middleware/ErrorHandlingMiddleware.cs (centralized exception handling)
- Data/AppDbContext.cs (if persistence needed)
- Configuration/Options classes (if using options pattern)

========================================
L) ACCEPTANCE CRITERIA
========================================
- Compilable .NET 8 WebAPI.
- No placeholders, no TODOs; fully implemented logic based on COBOL.
- Clean separation: Controllers (HTTP) → Services (business) → Repositories (data).
- Interfaces for all public services/repositories.
- EF Core only when COBOL indicates persistent storage.
- Sufficient XML summaries for non-obvious business decisions/assumptions.
- Adheres to naming conventions and layering rules above.

========================================
M) ENTITY FRAMEWORK CORE SETUP (IF NEEDED)
========================================
{db_setup_template}

========================================
N) COBOL SOURCE CODE (INPUT)
========================================
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