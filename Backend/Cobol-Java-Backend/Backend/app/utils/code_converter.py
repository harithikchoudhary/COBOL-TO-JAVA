import logging
import re
import json
from typing import List, Dict, Any, Optional
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from .prompts import create_code_conversion_prompt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class CodeConverter:
    """
    A class to handle code conversion process, including code chunking and 
    managing the conversion of large code files.
    """
    
    def __init__(self, client, model_name: str):
        """
        Initialize the CodeConverter.
        
        Args:
            client: The OpenAI client instance
            model_name: The deployment name of the model to use
        """
        self.client = client
        self.model_name = model_name
    
    def get_language_enum(self, language_name: str) -> Optional[Language]:
        """
        Convert a language name string to a LangChain Language enum value.
        Handles unsupported languages gracefully by returning None if the language isn't available.
        
        Args:
            language_name: Name of the programming language
            
        Returns:
            The corresponding Language enum or None if not supported
        """
        try:
            return Language[language_name.upper()]
        except KeyError:
            logger.warning(f"Language '{language_name}' is not supported by langchain_text_splitters. Using generic splitter.")
            return None
    
    def chunk_code(self, source_code: str, source_language: str, 
                chunk_size: int = 23500, chunk_overlap: int = 1000) -> List[str]:
        """
        Split source code into manageable chunks using LangChain text splitters.
        
        Args:
            source_code: The code to be chunked
            source_language: The programming language of the source code
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between consecutive chunks
            
        Returns:
            List of code chunks
        """
        language_enum = self.get_language_enum(source_language)
        
        if language_enum:
            logger.info(f"Using language-specific splitter for {source_language}")
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=language_enum,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        else:
            logger.info(f"Using generic splitter for {source_language}")
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ".", " ", ""]
            )
        
        chunks = splitter.split_text(source_code)
        logger.info(f"Split code into {len(chunks)} chunks")
        return chunks
    
    def _extract_entity_name(self, source_code: str, fallback: str = "Task") -> str:
        import re
        match = re.search(r'PROGRAM-ID\.\s*([A-Z0-9_\-]+)\.', source_code, re.IGNORECASE)
        if match:
            return match.group(1).title().replace('_', '')
        # Try to extract first 01-level record
        match = re.search(r'01\s+([A-Z0-9_\-]+)\s+PIC', source_code, re.IGNORECASE)
        if match:
            return match.group(1).title().replace('_', '')
        return fallback
    
    def convert_code_chunks(self, chunks: List[str], source_language: str, 
                           target_language: str, business_requirements: str,
                           technical_requirements: str, db_setup_template: str,
                           project_name: str = "TaskManagementSystem") -> Dict[str, Any]:
        if not chunks:
            logger.warning("No code chunks to convert")
            return {
                "convertedCode": [],
                "conversionNotes": "Error: No code provided for conversion",
                "potentialIssues": ["No source code was provided"],
                "databaseUsed": False
            }
        full_code = "\n".join(chunks)
        entity_name = self._extract_entity_name(full_code)
        # Onion Architecture file structure
        file_map = [
            ("Domain/Entities", f"{entity_name}.cs", f"Convert the following COBOL data structures to a C# Domain Entity class named {entity_name}."),
            ("Domain/Interfaces", f"I{entity_name}Repository.cs", f"Convert the following COBOL data structures and business logic to a C# Domain Repository Interface named I{entity_name}Repository."),
            ("Domain/Exceptions", f"{entity_name}Exception.cs", f"Convert the following COBOL error handling and status codes to a C# custom exception class named {entity_name}Exception."),
            ("Application/DTOs", f"{entity_name}Dto.cs", f"Convert the following COBOL data structures to a C# DTO class named {entity_name}Dto for the Application layer."),
            ("Application/Services", f"I{entity_name}Service.cs", f"Convert the following COBOL business logic to a C# Application Service Interface named I{entity_name}Service."),
            ("Application/Services", f"{entity_name}Service.cs", f"Convert the following COBOL business logic to a C# Application Service implementation named {entity_name}Service."),
            ("Infrastructure/Data", f"InMemory{entity_name}Repository.cs", f"Convert the following COBOL file/database operations to a C# Infrastructure Repository class named InMemory{entity_name}Repository using Entity Framework Core."),
            ("Infrastructure/Data", f"ApplicationDbContext.cs", "If the COBOL code uses files or databases, generate a C# DbContext class named ApplicationDbContext."),
            ("Presentation/Controllers", f"{entity_name}sController.cs", f"Convert the following COBOL main program and control flow to a C# Web API Controller class named {entity_name}sController."),
            ("Presentation", "Program.cs", "Generate the Program.cs file for a .NET 8 Web API project using Onion Architecture, with dependency injection for all layers."),
            ("Presentation", "appsettings.json", "Generate the appsettings.json file for a .NET 8 Web API project using Onion Architecture."),
        ]
        converted_code_list = []
        notes = []
        issues = []
        database_used = False
        for path, filename, instruction in file_map:
            prompt = f"""
            {instruction}
            
            COBOL code:
            ```cobol
            {full_code}
            ```
            
            Business requirements:
            {business_requirements}
            
            Technical requirements:
            {technical_requirements}
            
            Database setup template (if any):
            {db_setup_template}
            
            If there is not enough information in the COBOL code, generate a minimal valid C# file for this layer (e.g., an empty class, interface, or controller with correct namespace and structure).
            Please return ONLY the code for this file, with all necessary using statements, namespace, and class definition. Do not include explanations.
            """
            try:
                logger.info(f"Prompt for {filename}:\n{prompt}")
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": f"You are an expert COBOL to {target_language} converter specializing in Onion Architecture. Generate high-quality, idiomatic {target_language} code for each layer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=4000
                )
                code_content = response.choices[0].message.content.strip()
                code_content = re.sub(r'^```[a-zA-Z]*\n|\n```$', '', code_content, flags=re.MULTILINE)
                logger.info(f"Model response for {filename}:\n{code_content}")
                # Python fallback for empty files
                if not code_content.strip():
                    if filename.startswith('I') and filename.endswith('Repository.cs'):
                        code_content = f"public interface {filename[:-3]} {{ }}"
                    elif filename.endswith('Service.cs'):
                        code_content = f"public class {filename[:-3]} {{ }}"
                    elif filename.endswith('Controller.cs'):
                        code_content = f"public class {filename[:-3]} {{ }}"
                    elif filename.endswith('Exception.cs'):
                        code_content = f"public class {filename[:-3]} : Exception {{ }}"
                    elif filename.endswith('Dto.cs'):
                        code_content = f"public class {filename[:-3]} {{ }}"
                    elif filename.endswith('.cs'):
                        code_content = f"public class {filename[:-3]} {{ }}"
                    elif filename.endswith('.json'):
                        code_content = "{}"
                converted_code_list.append({
                    "FileName": filename,
                    "Path": path + "/",
                    "content": code_content
                })
            except Exception as e:
                logger.error(f"Error generating {filename}: {str(e)}")
                converted_code_list.append({"FileName": filename, "Path": path + "/", "content": ""})
                issues.append(f"Failed to generate {filename}: {str(e)}")
        # Ensure all files in file_map are present in the output
        existing_files = set((f["Path"], f["FileName"]) for f in converted_code_list)
        for path, filename, instruction in file_map:
            if (path + "/", filename) not in existing_files:
                # Add a minimal stub if missing
                if filename.startswith('I') and filename.endswith('Repository.cs'):
                    code_content = f"public interface {filename[:-3]} {{ }}"
                elif filename.endswith('Service.cs'):
                    code_content = f"public class {filename[:-3]} {{ }}"
                elif filename.endswith('Controller.cs'):
                    code_content = f"public class {filename[:-3]} {{ }}"
                elif filename.endswith('Exception.cs'):
                    code_content = f"public class {filename[:-3]} : Exception {{ }}"
                elif filename.endswith('Dto.cs'):
                    code_content = f"public class {filename[:-3]} {{ }}"
                elif filename.endswith('.cs'):
                    code_content = f"public class {filename[:-3]} {{ }}"
                elif filename.endswith('.json'):
                    code_content = "{}"
                else:
                    code_content = ""
                converted_code_list.append({
                    "FileName": filename,
                    "Path": path + "/",
                    "content": code_content
                })
        # Log the final output for debugging
        logger.info(f"Final converted_code_list: {[{'FileName': f['FileName'], 'Path': f['Path']} for f in converted_code_list]}")
        # Project/solution files
        project_files = self._generate_project_files(project_name)
        for key, value in project_files.items():
            converted_code_list.append(value)
        return {
            "convertedCode": converted_code_list,
            "conversionNotes": "\n".join(notes),
            "potentialIssues": issues,
            "databaseUsed": database_used
        }
    
    def _create_structure_prompt(self, chunks: List[str], source_language: str, target_language: str) -> str:
        """
        Create a prompt to get the overall structure of the code before detailed conversion.
        Enhanced for COBOL to C# migration with Onion Architecture.
        
        Args:
            chunks: List of code chunks
            source_language: Source programming language
            target_language: Target programming language
            
        Returns:
            A prompt for the model
        """
        complete_code = "\n\n".join(chunks)
        
        if len(complete_code) > 30000:
            begin = complete_code[:10000]
            middle_start = len(complete_code) // 2 - 5000
            middle_end = len(complete_code) // 2 + 5000
            middle = complete_code[middle_start:middle_end]
            end = complete_code[-10000:]
            
            complete_code = f"{begin}\n\n... [code truncated for brevity] ...\n\n{middle}\n\n... [code truncated for brevity] ...\n\n{end}"
        
        language_specific = """
        For C# output using Onion Architecture, please include:
        
        1. NAMESPACE STRUCTURE - Organize code with appropriate namespaces
        - Use Company.Project.[Layer] (e.g., Company.Project.Domain, Company.Project.Application)
        - Group related classes by layer (Domain, Application, Infrastructure, Presentation)
        
        2. LAYER ORGANIZATION - Design according to Onion Architecture
        - Domain Layer: Entities, interfaces, exceptions (no dependencies)
        - Application Layer: Application services, DTOs (depends on Domain)
        - Infrastructure Layer: Repositories, DbContext (implements Application interfaces)
        - Presentation Layer: Controllers (depends on Application)
        
        3. ACCESS MODIFIERS - Apply correct encapsulation
        - Use private for fields with properties
        - Protect internal implementation details
        - Expose only necessary public methods
        
        4. FIELD DEFINITIONS - Proper variable declarations
        - Include appropriate data types for all fields
        - Use properties with getters/setters
        - Initialize all fields with appropriate defaults
        
        5. EXCEPTION HANDLING - Use .NET exception hierarchy
        - Define application-specific exceptions in Domain/Exceptions
        - Use try-catch-finally blocks consistently
        - Include appropriate exception handling strategies
        
        6. C# CONVENTIONS - Follow standard C# practices
        - Use camelCase for private fields (with _ prefix)
        - Use PascalCase for properties, methods, and class names
        - Use PascalCase for public fields (rarely used)
        """
        
        cobol_specific = """
        For COBOL to C# migration, please also provide:
        
        1. DATA DIVISION mapping - Map all COBOL records/structures to Domain entities
        - Identify all WORKING-STORAGE SECTION items and how they should be represented
        - Map FILE SECTION records to Domain entities
        - Determine which COBOL fields should become class fields vs. local variables
        - Handle COBOL PICTURE clauses with appropriate data types and precision
        - Handle REDEFINES with appropriate object patterns (e.g., inheritance, interfaces)
        
        2. PROCEDURE DIVISION mapping - Map all COBOL paragraphs/sections to Application services
        - Identify main program flow and control structures
        - Map PERFORM statements to appropriate method calls 
        - Create structured methods with single responsibility
        - Determine how to handle GOTO statements and eliminate spaghetti code
        - Convert COBOL-style control flow to modern OO structured programming
        
        3. Database integration - Identify any database or file access
        - Map COBOL file operations to Entity Framework Core in Infrastructure layer
        - Convert COBOL file I/O to appropriate database operations
        - Handle indexed files with proper key management 
        - Convert any embedded SQL to prepared statements and proper connection handling
        
        4. Error handling - Map COBOL error handling to exception-based approach
        - Convert status code checks to try-catch blocks
        - Identify ON ERROR and similar constructs
        - Create appropriate custom exception classes in Domain/Exceptions
        - Implement proper resource cleanup in finally blocks
        
        5. Numeric/decimal handling - Identify precision requirements
        - Use decimal for financial calculations
        - Handle implicit decimal points properly (PIC 9(7)V99)
        - Apply proper rounding modes where needed
        - Ensure numeric formatting follows business requirements
        
        6. MODULE ORGANIZATION - Properly organize the application
        - Separate business logic into Domain and Application layers
        - Implement repositories in Infrastructure layer
        - Create controllers in Presentation layer
        - Follow Onion Architecture dependency rules
        """
        
        return f"""
        I need to convert {source_language} code to {target_language} using Onion Architecture, but first I need a detailed high-level structure to ensure consistency, quality, and maintainability.
        
        Please analyze this code and provide a DETAILED architectural blueprint including:
        
        1. COMPLETE LAYER STRUCTURE with:
        - Domain Layer: Entities, interfaces, exceptions
        - Application Layer: Application services, DTOs, interfaces
        - Infrastructure Layer: Repositories, DbContext
        - Presentation Layer: Controllers
        - Clear inheritance hierarchies and relationships
        - Fields with their types and access modifiers
        - Complete method signatures (return types, parameters, exceptions)
        
        2. NAMESPACE ORGANIZATION:
        - Logical grouping of related classes by layer
        - Proper naming following C# conventions (Company.Project.[Layer])
        
        3. DATABASE ACCESS (if present):
        - Connection management approach in Infrastructure layer
        - Transaction handling
        - Resource cleanup strategy
        
        4. DESIGN PATTERNS to implement:
        - Repository pattern for data access
        - Service pattern for business logic
        - Dependency injection for loose coupling
        
        5. ERROR HANDLING STRATEGY:
        - Exception hierarchy in Domain/Exceptions
        - Resource cleanup approach
        - Logging strategy
        
        {language_specific}
        
        {cobol_specific}
        
        DO NOT convert the code in detail yet. Provide ONLY a comprehensive structural blueprint focusing on architecture, relationships, and ensuring clean, maintainable code that follows all {target_language} best practices and Onion Architecture principles.
        
        Here's the {source_language} code to analyze:
        
        ```
        {complete_code}
        ```
        """
    
    def _get_code_structure(self, structure_prompt: str, target_language: str) -> Dict[str, Any]:
        """
        Get the overall structure of the code to guide the conversion process.
        
        Args:
            structure_prompt: The prompt asking for the code structure
            target_language: The target programming language
            
        Returns:
            Dictionary with structure information
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert software architect specializing in {target_language} and Onion Architecture. "
                                f"Your task is to analyze legacy code and provide a detailed architectural blueprint for modern, clean, "
                                f"maintainable {target_language} code. You excel at creating well-structured object-oriented designs that "
                                f"follow Onion Architecture principles and dependency inversion."
                    },
                    {"role": "user", "content": structure_prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            structure_content = response.choices[0].message.content.strip()
            
            structure_info = {
                "structure": structure_content,
                "classes": [],
                "namespace": None,
                "interfaces": [],
                "database_access": False,
                "exception_strategy": "standard",
                "patterns": []
            }
            
            class_matches = re.findall(r'class\s+([A-Za-z0-9_]+)', structure_content)
            structure_info["classes"] = list(set(class_matches))
            
            namespace_match = re.search(r'namespace\s+([A-Za-z0-9_.]+)', structure_content, re.IGNORECASE)
            if namespace_match:
                structure_info["namespace"] = namespace_match.group(1)
            
            interface_matches = re.findall(r'interface\s+([A-Za-z0-9_]+)', structure_content)
            structure_info["interfaces"] = list(set(interface_matches))
            
            db_keywords = ['Connection', 'SqlCommand', 'DataReader', 'EntityFramework',
                        'Repository', 'DataSource', 'DbContext']
            for keyword in db_keywords:
                if keyword in structure_content:
                    structure_info["database_access"] = True
                    break
            
            pattern_keywords = {
                "Repository": ["Repository", "IRepository"],
                "Service": ["Service", "AppService"],
                "DTO": ["DTO", "Data Transfer Object"]
            }
            
            for pattern, keywords in pattern_keywords.items():
                for keyword in keywords:
                    if keyword in structure_content:
                        structure_info["patterns"].append(pattern)
                        break
            
            structure_info["patterns"] = list(set(structure_info["patterns"]))
            
            if "custom exception" in structure_content.lower() or "applicationexception" in structure_content.lower():
                structure_info["exception_strategy"] = "custom"
            
            return structure_info
                
        except Exception as e:
            logger.error(f"Error getting code structure: {str(e)}")
            return {
                "structure": "Could not determine code structure",
                "classes": [],
                "namespace": None,
                "interfaces": [],
                "database_access": False,
                "exception_strategy": "standard",
                "patterns": []
            }
    
    def _convert_single_chunk(self, code_chunk: str, source_language: str,
                            target_language: str, business_requirements: str,
                            technical_requirements: str, db_setup_template: str,
                            additional_context: str = "") -> Dict[str, Any]:
        """
        Convert a single code chunk with enhanced COBOL-specific instructions.
        
        Args:
            code_chunk: The code chunk to convert
            source_language: Source programming language
            target_language: Target programming language
            business_requirements: Business requirements
            technical_requirements: Technical requirements
            db_setup_template: Database setup template
            additional_context: Additional context for the model
            
        Returns:
            Dictionary with conversion results
        """
        prompt = create_code_conversion_prompt(
            source_language,
            target_language,
            code_chunk,
            business_requirements,
            technical_requirements,
            db_setup_template
        )
        
        if source_language == "COBOL" and target_language in ["C#"]:
            prompt += """
            
            CRITICAL INSTRUCTIONS FOR COBOL TO C# CONVERSION:
            
            1. DATA STRUCTURE MAPPING:
            - Convert COBOL records (01 level items) to Domain entities
            - Map COBOL group items (05-49 level) to nested classes or complex properties
            - Map elementary items (PIC clauses) to appropriate data types:
                * PIC 9(n) -> int, long, or BigInteger depending on size
                * PIC 9(n)V9(m) -> decimal (use decimal for financial calculations)
                * PIC X(n) -> String (with proper length)
                * PIC A(n) -> String (with proper length)
                * COMP-3 fields -> decimal with scaling
            - Handle REDEFINES with appropriate conversion strategy (e.g., inheritance or multiple properties)
            - Convert COBOL tables (OCCURS clause) to arrays or Lists
            
            2. PROCEDURE CONVERSION:
            - Convert COBOL paragraphs to Application service methods
            - Convert PERFORM statements to method calls
            - Replace GOTO statements with structured alternatives (loops, conditionals)
            - Convert in-line PERFORM with appropriate loop structure
            - Handle COBOL specific control flow (EVALUATE, etc.)
            
            3. FILE HANDLING CONVERSION:
            - Convert COBOL file operations (OPEN, READ, WRITE) to Infrastructure repository methods
            - For indexed files, use Entity Framework Core with appropriate key management
            - For sequential files, use appropriate stream-based I/O
            - Handle record locking mechanisms appropriately
            
            4. ERROR HANDLING:
            - Convert COBOL ON SIZE ERROR to Domain exceptions
            - Convert FILE STATUS checks to try-catch blocks
            - Implement appropriate logging and error reporting
            
            5. NUMERIC PROCESSING:
            - Preserve exact decimal calculations using decimal type
            - Handle implicit decimal points from COBOL PIC clauses
            - Preserve COBOL numeric editing behavior when formatting output
            
            6. COMPLETENESS AND STRUCTURE:
            - Ensure all variables are properly initialized
            - Add appropriate constructors to classes
            - Implement appropriate access modifiers (public, private, etc.)
            - Add appropriate getters and setters for class properties
            - Add appropriate namespace organization following Onion Architecture
            """
        
        if target_language == "C#":
            prompt += """
            
            CRITICAL INSTRUCTIONS FOR ONION ARCHITECTURE:
            
            1. LAYER SEPARATION:
            - Domain: Entities, interfaces, exceptions (no external dependencies)
            - Application: Services, DTOs (depends on Domain)
            - Infrastructure: Repositories, DbContext (implements Application interfaces)
            - Presentation: Controllers (depends on Application)
            
            2. DEPENDENCY INVERSION:
            - Define service interfaces in Domain and Application layers
            - Implement interfaces in Application and Infrastructure layers
            - Use dependency injection in Program.cs
            
            3. EXCEPTION HANDLING:
            - Define custom exceptions in Domain/Exceptions
            - All catch blocks must have actual code handling the exception
            - Use try-with-resources where appropriate
            - Add specific exception types when possible
            
            4. DATABASE CODE:
            - Implement in Infrastructure layer using Entity Framework Core
            - Always close connections in finally blocks
            - Implement proper transaction management
            
            5. CLASS STRUCTURE:
            - Include all necessary imports at the top
            - Declare all fields with proper access modifiers
            - Include necessary constructors
            - Implement interfaces and extend classes as needed
            
            6. COMPLETENESS:
            - No undefined variables or methods
            - No placeholder comments where code should be
            """
        
        if additional_context:
            prompt += f"\n\n{additional_context}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert code converter specializing in {source_language} to {target_language} migration using Onion Architecture. "
                                f"You convert legacy code to modern, idiomatic code while maintaining all business logic. "
                                f"Ensure that all syntax is correct, with matching brackets and proper statement terminations. "
                                f"Only include database setup/initialization in the Infrastructure layer if the original code uses databases or SQL. "
                                f"For simple algorithms or calculations without database operations, don't add any database code. "
                                f"Return your response in JSON format always with the following structure:\n"
                                f"{{\n"
                                f'  \"convertedCode\": {{\n'
                                f'    \"DomainEntity\": {{\"FileName\": \"EntityName.cs\", \"Path\": \"Domain/Entities/\", \"content\": \"\"}},\n'
                                f'    \"DomainInterface\": {{\"FileName\": \"IEntityNameService.cs\", \"Path\": \"Domain/Interfaces/\", \"content\": \"\"}},\n'
                                f'    \"ApplicationServiceInterface\": {{\"FileName\": \"IEntityNameAppService.cs\", \"Path\": \"Application/Interfaces/\", \"content\": \"\"}},\n'
                                f'    \"ApplicationService\": {{\"FileName\": \"EntityNameAppService.cs\", \"Path\": \"Application/Services/\", \"content\": \"\"}},\n'
                                f'    \"ApplicationDTO\": {{\"FileName\": \"EntityNameDTO.cs\", \"Path\": \"Application/DTOs/\", \"content\": \"\"}},\n'
                                f'    \"InfrastructureRepository\": {{\"FileName\": \"EntityNameRepository.cs\", \"Path\": \"Infrastructure/Repositories/\", \"content\": \"\"}},\n'
                                f'    \"InfrastructureDbContext\": {{\"FileName\": \"ApplicationDbContext.cs\", \"Path\": \"Infrastructure/Data/\", \"content\": \"\"}},\n'
                                f'    \"PresentationController\": {{\"FileName\": \"EntityNameController.cs\", \"Path\": \"Presentation/Controllers/\", \"content\": \"\"}},\n'
                                f'    \"Program\": {{\"FileName\": \"Program.cs\", \"Path\": \"./\", \"content\": \"\"}},\n'
                                f'    \"AppSettings\": {{\"FileName\": \"appsettings.json\", \"Path\": \"./\", \"content\": \"\"}},\n'
                                f'    \"ProjectFile\": {{\"FileName\": \"SolutionName.csproj\", \"Path\": \"./\", \"content\": \"\"}},\n'
                                f'    \"Dependencies\": {{\"content\": \"NuGet packages and .NET dependencies needed\"}}\n'
                                f'  }},\n'
                                f'  \"conversionNotes\": \"Notes about the conversion process\",\n'
                                f'  \"potentialIssues\": [\"List of any potential issues or limitations\"],\n'
                                f'  \"databaseUsed\": true/false\n'
                                f"}}"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            conversion_content = response.choices[0].message.content.strip()
            
            try:
                conversion_json = json.loads(conversion_content)
                
                if target_language == "C#":
                    self._validate_code(conversion_json, target_language)
                    
                return conversion_json
                
            except json.JSONDecodeError as json_err:
                logger.error(f"Error parsing JSON response: {str(json_err)}")
                logger.debug(f"Problematic response content: {conversion_content}")
                
                try:
                    json_pattern = r'(\{[\s\S]*\})'
                    match = re.search(json_pattern, conversion_content)
                    if match:
                        potential_json = match.group(1)
                        conversion_json = json.loads(potential_json)
                        logger.info("Successfully extracted JSON from response using regex")
                        
                        if target_language == "C#":
                            self._validate_code(conversion_json, target_language)
                            
                        return conversion_json
                except Exception as extract_err:
                    logger.error(f"Failed to extract JSON using regex: {str(extract_err)}")
                
                return {
                    "convertedCode": [],
                    "conversionNotes": f"Error processing response: {str(json_err)}",
                    "potentialIssues": ["Failed to process model response", "Response was not valid JSON"],
                    "databaseUsed": False
                }
                
        except Exception as e:
            logger.error(f"Error calling model API: {str(e)}")
            return {
                "convertedCode": [],
                "conversionNotes": f"Error calling model API: {str(e)}",
                "potentialIssues": ["Failed to get response from model"],
                "databaseUsed": False
            }
    
    def _validate_code(self, conversion_result: Dict[str, Any], target_language: str) -> None:
        """
        Validate the converted code for common issues and Onion Architecture compliance.
        
        Args:
            conversion_result: The conversion result dictionary
            target_language: The target programming language
        """
        converted_code = conversion_result.get("convertedCode", [])
        if not converted_code:
            logger.warning("Converted code is empty, skipping validation")
            return
        
        issues = []
        
        # Validate each file's content
        for file in converted_code:
            code = file.get("content", "")
            if not code:
                issues.append(f"Missing or empty content for {file['FileName']}")
                continue
            
            # Check for mismatched braces
            opening_braces = code.count("{")
            closing_braces = code.count("}")
            if opening_braces != closing_braces:
                issues.append(f"Mismatched braces in {file['FileName']}: {opening_braces} opening vs {closing_braces} closing")
            
            # Check for incomplete try-catch blocks
            try_count = len(re.findall(r'\btry\s*{', code))
            catch_count = len(re.findall(r'\bcatch\s*\(', code))
            if try_count > catch_count:
                issues.append(f"Incomplete exception handling in {file['FileName']}: {try_count} try blocks but only {catch_count} catch blocks")
            
            # Check for empty catch blocks
            empty_catches = len(re.findall(r'catch\s*\([^)]*\)\s*{\s*}', code))
            if empty_catches > 0:
                issues.append(f"Found {empty_catches} empty catch blocks in {file['FileName']}")
        
        # Onion Architecture-specific validations
        if target_language == "C#":
            # Check Domain layer for external dependencies
            domain_code = [file.get("content", "") for file in converted_code if file.get("Path", "") == "Domain/Entities/" or file.get("Path", "") == "Domain/Interfaces/"]
            if any("Microsoft.EntityFrameworkCore" in code or "System.Data" in code for code in domain_code):
                issues.append("Domain layer contains infrastructure dependencies")
            
            # Check Application layer dependencies
            app_service_code = [file.get("content", "") for file in converted_code if file.get("Path", "") == "Application/Services/"]
            if any("DbContext" in code or "Repository" in code for code in app_service_code):
                issues.append("Application layer contains direct references to Infrastructure layer")
            
            # Check dependency injection in Program.cs
            program_code = [file.get("content", "") for file in converted_code if file.get("Path", "") == "./" and file.get("FileName", "") == "Program.cs"]
            if "AddScoped" not in program_code and "AddSingleton" not in program_code:
                issues.append("Program.cs missing dependency injection setup")
        
        if issues:
            existing_issues = conversion_result.get("potentialIssues", [])
            conversion_result["potentialIssues"] = existing_issues + issues
    
    def _merge_conversion_results(self, results: List[Dict[str, Any]], 
                                target_language: str,
                                structure_info: Dict[str, Any] = None,
                                project_name: str = "TaskManagementSystem") -> Dict[str, Any]:
        """
        Merge multiple conversion results into a single result.
        
        Args:
            results: List of conversion results to merge
            target_language: The target programming language
            structure_info: Information about the code structure
            project_name: The name of the solution/project
            
        Returns:
            Merged conversion result
        """
        if not results:
            return {
                "convertedCode": [],
                "conversionNotes": "No conversion results to merge",
                "potentialIssues": ["No conversion was performed"],
                "databaseUsed": False
            }
        
        all_notes = []
        all_issues = []
        database_used = any(result.get("databaseUsed", False) for result in results)
        merged_code = []
        
        # Merge each section
        for result in results:
            converted_code = result.get("convertedCode", [])
            for file in converted_code:
                if file.get("content"):
                    merged_code.append(file)
            
            notes = result.get("conversionNotes", "")
            if notes:
                all_notes.append(notes)
                
            issues = result.get("potentialIssues", [])
            if issues:
                all_issues.extend(issues)
        
        # Polish the merged code
        if target_language == "C#":
            for file in merged_code:
                if file.get("content"):
                    file["content"] = self._polish_code(file["content"], target_language)
        
        # Generate project files for C# Onion Architecture
        if target_language == "C#":
            project_files = self._generate_project_files(project_name)
            # Merge project files with existing code
            merged_code.extend(project_files.values())
        
        all_notes.insert(0, f"The original code was processed in {len(results)} chunks due to its size and merged into a single codebase.")
        
        if target_language == "C#":
            validation_result = self._validate_merged_code(merged_code, target_language)
            if validation_result:
                all_issues.extend(validation_result)
        
        return {
            "convertedCode": merged_code,
            "conversionNotes": "\n\n".join(all_notes),
            "potentialIssues": all_issues,
            "databaseUsed": database_used
        }
    
    def _polish_code(self, code: str, target_language: str) -> str:
        """
        Polish the merged code to fix any syntax errors or incomplete blocks, ensuring Onion Architecture compliance.
        
        Args:
            code: The merged code to polish
            target_language: The target programming language
            
        Returns:
            The polished code
        """
        if not code or len(code.strip()) == 0:
            logger.warning("Empty code provided for polishing")
            return code
            
        polished = code
        
        # Fix mismatched braces
        open_count = polished.count('{')
        close_count = polished.count('}')
        if open_count > close_count:
            polished += '\n' + '}' * (open_count - close_count)
        
        # Fix empty catch blocks
        empty_catch_pattern = r'catch\s*\(([^)]*)\)\s*{\s*}'
        polished = re.sub(
            empty_catch_pattern, 
            r'catch (\1) {\n    // Error handling\n    Console.WriteLine("Error caught: " + \1.Message);\n}',
            polished
        )
        
        # Ensure consistent indentation
        lines = polished.split('\n')
        indented_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.endswith('{'):
                indented_lines.append('    ' * indent_level + stripped)
                indent_level += 1
            elif stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)
                indented_lines.append('    ' * indent_level + stripped)
            else:
                indented_lines.append('    ' * indent_level + stripped)
        
        polished = '\n'.join(indented_lines)
        
        # Ensure Onion Architecture compliance and proper namespace organization
        prompt = f"""
        Below is a {target_language} code that was generated by converting from another language. It may have syntax errors, style issues, or violations of Onion Architecture principles.
        Please fix the following types of issues to make it valid and well-structured {target_language} code following Onion Architecture:
        
        1. Fix any syntax errors (missing semicolons, mismatched braces, etc.)
        2. Ensure proper class structure with correct access modifiers
        3. Fix method signatures (return types, parameter types)
        4. Ensure proper variable initialization
        5. Add appropriate exception handling in try-catch blocks
        6. Fix import statements to align with Onion Architecture:
           - Domain layer: No external dependencies (e.g., no Microsoft.EntityFrameworkCore)
           - Application layer: Only depends on Domain
           - Infrastructure layer: Implements Application interfaces, includes EF Core
           - Presentation layer: Depends on Application
        7. Ensure proper namespace organization:
           - Domain: Company.Project.Domain
           - Application: Company.Project.Application
           - Infrastructure: Company.Project.Infrastructure
           - Presentation: Company.Project.Presentation
        8. Follow standard {target_language} naming conventions
        9. Ensure consistent indentation and formatting
        10. Remove any redundant or duplicate code
        11. Add necessary comments for complex logic
        12. Remove any database-related code from Domain and Application layers
        13. Ensure dependency injection is properly set up in Program.cs
        
        Here is the code to fix:
        
        ```{target_language.lower()}
        {polished}
        ```
        
        Please provide ONLY the corrected code without any explanations. Keep ALL functionality intact.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert {target_language} developer specializing in code quality, syntax correction, and Onion Architecture. Your task is to fix code issues while preserving all functionality and ensuring compliance with Onion Architecture principles."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            polished_code = response.choices[0].message.content.strip()
            polished_code = re.sub(r'```(?:' + target_language.lower() + r')?\n([\s\S]*?)\n```', r'\1', polished_code)
            return polished_code
        except Exception as e:
            logger.error(f"Error polishing code: {str(e)}")
            return polished  # Return original if polishing fails
    
    def _validate_merged_code(self, merged_code: List[Dict[str, Any]], target_language: str) -> List[str]:
        """
        Validate the merged code for Onion Architecture compliance and common issues.
        
        Args:
            merged_code: The merged code list
            target_language: The target programming language
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if target_language != "C#":
            return issues
        
        # Validate folder structure
        expected_paths = {
            "DomainEntity": "Domain/Entities/",
            "DomainInterface": "Domain/Interfaces/",
            "ApplicationServiceInterface": "Application/Interfaces/",
            "ApplicationService": "Application/Services/",
            "ApplicationDTO": "Application/DTOs/",
            "InfrastructureRepository": "Infrastructure/Repositories/",
            "InfrastructureDbContext": "Infrastructure/Data/",
            "PresentationController": "Presentation/Controllers/",
            "Program": "./",
            "AppSettings": "./",
            "ProjectFile": "./"
        }
        
        for file in merged_code:
            if file.get("Path", "") not in expected_paths.values():
                issues.append(f"Incorrect path for {file['FileName']}: expected one of {list(expected_paths.values())}")
            
            if not file.get("FileName"):
                issues.append(f"Missing FileName for {file['FileName']}")
            
            if not file.get("content"):
                issues.append(f"Empty content for {file['FileName']}")
        
        # Check for Onion Architecture compliance
        domain_code = [file.get("content", "") for file in merged_code if file.get("Path", "") in ["Domain/Entities/", "Domain/Interfaces/"]]
        
        # Check for forbidden dependencies in Domain layer
        forbidden_imports = [
            "Microsoft.EntityFrameworkCore",
            "System.Data",
            "Microsoft.AspNetCore",
            "Infrastructure",
            "Application"
        ]
        for forbidden in forbidden_imports:
            if forbidden in domain_code:
                issues.append(f"Domain layer contains forbidden dependency: {forbidden}")
        
        # Check Application layer dependencies
        app_service_code = [file.get("content", "") for file in merged_code if file.get("Path", "") == "Application/Services/"]
        if any("DbContext" in code or "Repository" in code for code in app_service_code):
            issues.append("Application layer contains direct references to Infrastructure layer")
        
        # Check dependency injection setup
        program_code = [file.get("content", "") for file in merged_code if file.get("Path", "") == "./" and file.get("FileName", "") == "Program.cs"]
        if "AddScoped" not in program_code and "AddSingleton" not in program_code:
            issues.append("Program.cs missing dependency injection setup")
        
        # Check for proper namespace organization
        for file in merged_code:
            code = file.get("content", "")
            namespace_match = re.search(r'namespace\s+([A-Za-z0-9_.]+)', code)
            if code and not namespace_match:
                issues.append(f"Missing namespace declaration in {file['FileName']}")
            elif namespace_match:
                namespace = namespace_match.group(1)
                expected_namespace = f"Company.Project.{file['FileName'].split('.')[0]}"
                if not namespace.startswith("Company.Project"):
                    issues.append(f"Invalid namespace in {file['FileName']}: expected {expected_namespace}, got {namespace}")
        
        # Check for proper DbContext in Infrastructure layer
        db_context = [file.get("content", "") for file in merged_code if file.get("Path", "") == "Infrastructure/Data/" and "DbContext" in file.get("content", "")]
        if db_context and "DbContext" not in db_context:
            issues.append("InfrastructureDbContext does not inherit from DbContext")
        
        # Check for API controller attributes
        controller_code = [file.get("content", "") for file in merged_code if file.get("Path", "") == "Presentation/Controllers/" and "[ApiController]" not in file.get("content", "")]
        if controller_code:
            issues.append("PresentationController missing [ApiController] attribute")
        
        return issues
    
    def _merge_oop_code(self, results: List[Dict[str, Any]], 
                        target_language: str,
                        structure_info: Dict[str, Any] = None) -> str:
        """
        Intelligently merge OOP code (Java/C#) by extracting package/namespace,
        imports, class definitions, methods, etc.
        
        Args:
            results: List of conversion results
            target_language: Target language (Java or C#)
            structure_info: Information about the code structure
            
        Returns:
            Merged code as a string
        """
        # Extract components from each chunk
        package_namespace = None
        imports = set()
        classes = {}  # Dictionary to store class definitions and their content
        utility_methods = []  # For non-class methods/functions
        other_code = []  # For any unclassified code
        field_declarations = set()  # For class-level fields
        constants = set()  # For constant declarations
        
        # Define regexes based on target language
        if target_language == "Java":
            package_regex = r'^package\s+([^;]+);'
            import_regex = r'^import\s+([^;]+);'
            class_regex = r'(public|private|protected|)\s*(final|abstract|)\s*class\s+([^\s{<]+)(?:<[^>]*>)?(?:\s+extends\s+[^\s{]+)?(?:\s+implements\s+[^{]+)?\s*{([^}]*)}'
            method_in_class_regex = r'(public|private|protected|static|final|abstract|)\s*(static|final|abstract|)\s*(?:<[^>]*>\s*)?([^(\s]+)\s+([^\s(]+)\s*\(([^)]*)\)\s*(?:throws\s+[^{]+)?\s*{'
            standalone_method_regex = r'^(?:public|private|protected|static|final|abstract|)\s*(?:static|final|abstract|)\s*(?:<[^>]*>\s*)?([^(\s]+)\s+([^\s(]+)\s*\(([^)]*)\)\s*(?:throws\s+[^{]+)?\s*{'
            field_regex = r'(public|private|protected|static|final|)\s*(static|final|)\s*([^\s(]+)\s+([^\s(=]+)(?:\s*=\s*[^;]+)?;'
            constant_regex = r'(public|private|protected|static|final|)\s*(static\s+final|final\s+static)\s*([^\s(]+)\s+([A-Z_][A-Z0-9_]*)(?:\s*=\s*[^;]+)?;'
        elif target_language == "C#":
            package_regex = r'^namespace\s+([^{;]+)'
            import_regex = r'^using\s+([^;]+);'
            class_regex = r'(public|private|protected|internal|)\s*(static|abstract|sealed|partial|)\s*class\s+([^\s:{<]+)(?:<[^>]*>)?(?:\s*:\s*[^{]+)?\s*{([^}]*)}'
            method_in_class_regex = r'(public|private|protected|internal|static|virtual|abstract|override|sealed|)\s*(static|virtual|abstract|override|sealed|)\s*(?:<[^>]*>\s*)?([^(\s]+)\s+([^\s(]+)\s*\(([^)]*)\)\s*({'
            standalone_method_regex = r'^(?:public|private|protected|internal|static|virtual|abstract|override|sealed|)\s*(?:static|virtual|abstract|override|sealed|)\s*(?:<[^>]*>\s*)?([^(\s]+)\s+([^\s(]+)\s*\(([^)]*)\)\s*{'
            field_regex = r'(public|private|protected|internal|static|readonly|)\s*(static|readonly|)\s*([^\s(]+)\s+([^\s(=]+)(?:\s*=\s*[^;]+)?;'
            constant_regex = r'(public|private|protected|internal|static|const|)\s*(static\s+const|const\s+static|const)\s*([^\s(]+)\s+([A-Z_][A-Z0-9_]*)(?:\s*=\s*[^;]+)?;'
        else:
            logger.warning(f"No specialized merging for {target_language}, using simple merge")
            return self._fallback_merge(results)
        
        # Process each result to extract components
        for i, result in enumerate(results):
            code = result.get("convertedCode", "")
            if not code:
                continue
            
            # Extract package/namespace
            package_match = re.search(package_regex, code, re.MULTILINE)
            if package_match and not package_namespace:
                if target_language == "Java":
                    package_namespace = f"package {package_match.group(1)};"
                else:  # C#
                    package_namespace = f"namespace {package_match.group(1)}"
            
            # Extract imports/usings
            import_matches = re.finditer(import_regex, code, re.MULTILINE)
            for match in import_matches:
                if target_language == "Java":
                    imports.add(f"import {match.group(1)};")
                else:  # C#
                    imports.add(f"using {match.group(1)};")
            
            # Extract constant declarations
            constant_matches = re.finditer(constant_regex, code, re.MULTILINE)
            for match in constant_matches:
                constants.add(match.group(0))
            
            # Extract field declarations
            field_matches = re.finditer(field_regex, code, re.MULTILINE)
            for match in field_matches:
                if not re.search(constant_regex, match.group(0)):  # Avoid duplicating constants
                    field_declarations.add(match.group(0))
            
            # Extract class definitions with their content
            class_matches = re.finditer(class_regex, code, re.DOTALL)
            for match in class_matches:
                access_modifier = match.group(1).strip()
                class_modifier = match.group(2).strip()
                class_name = match.group(3).strip()
                class_content = match.group(4).strip() if match.group(4) else ""
                
                # Create full class signature
                class_signature = ""
                if access_modifier:
                    class_signature += access_modifier + " "
                if class_modifier:
                    class_signature += class_modifier + " "
                class_signature += "class " + class_name
                
                # Extract the full class definition including potential extends/implements/inheritance
                full_match = match.group(0)
                header_end_idx = full_match.find("{")
                if header_end_idx > 0:
                    header = full_match[:header_end_idx].strip()
                    class_signature = header
                
                # Store or update the class definition
                if class_name in classes:
                    # Merge content of the same class from different chunks
                    classes[class_name]["content"] += "\n\n" + class_content
                else:
                    classes[class_name] = {
                        "signature": class_signature,
                        "content": class_content
                    }
            
            # Collect any standalone methods/functions (outside of classes)
            method_matches = re.finditer(standalone_method_regex, code, re.MULTILINE)
            for match in method_matches:
                method_text = match.group(0)
                # Ensure this is not a method inside a class
                if not re.search(r'class\s+[^{]*{[^}]*' + re.escape(method_text), code, re.DOTALL):
                    utility_methods.append(method_text)
            
            # Store any remaining code that wasn't matched
            code_without_matches = code
            for pattern in [package_regex, import_regex, class_regex, standalone_method_regex, field_regex, constant_regex]:
                code_without_matches = re.sub(pattern, '', code_without_matches, flags=re.MULTILINE | re.DOTALL)
            
            code_without_matches = code_without_matches.strip()
            if code_without_matches and len(code_without_matches) > 10:  # Filtering out noise
                other_code.append(code_without_matches)
        
        # Build the merged code
        merged_code = []
        
        # Add package/namespace declaration
        if package_namespace:
            merged_code.append(package_namespace)
            merged_code.append("")  # Empty line for readability
        
        # Add sorted imports
        if imports:
            for imp in sorted(imports):
                merged_code.append(imp)
            merged_code.append("")  # Empty line for readability
        
        # Add constant declarations
        if constants:
            merged_code.append("// Constants")
            for constant in sorted(constants):
                merged_code.append(constant)
            merged_code.append("")  # Empty line
        
        # Add field declarations
        if field_declarations:
            merged_code.append("// Fields")
            for field in sorted(field_declarations):
                merged_code.append(field)
            merged_code.append("")  # Empty line
        
        # Add class definitions
        for class_name, class_info in classes.items():
            merged_code.append(class_info["signature"] + " {")
            if class_info["content"]:
                merged_code.append(class_info["content"])
            merged_code.append("}")
            merged_code.append("")  # Empty line for readability
        
        # Add utility methods
        if utility_methods:
            merged_code.append("// Utility Methods")
            for method in utility_methods:
                merged_code.append(method)
            merged_code.append("")  # Empty line for readability
        
        # Add other code
        if other_code:
            merged_code.append("// Additional Code")
            for code in other_code:
                merged_code.append(code)
            merged_code.append("")  # Empty line for readability
        
        # Return the merged code as a string
        if not merged_code:
            return "// No code was generated during the conversion process"
        else:
            return "\n".join(merged_code)

    def _fallback_merge(self, results: List[Dict[str, Any]]) -> str:
        """
        Simple fallback method to merge code chunks when the intelligent merge fails.
        
        Args:
            results: List of conversion results
            
        Returns:
            Merged code as a string
        """
        merged_code = ""
        for i, result in enumerate(results):
            code = result.get("convertedCode", "").strip()
            if code:
                if merged_code:
                    merged_code += f"\n\n// ----- Chunk {i+1} -----\n\n"
                merged_code += code
        
        return merged_code
    
    def _deduplicate_methods(self, class_content: str, method_regex: str) -> str:
            """
            Removes duplicate method definitions in class content based on method signatures.
            
            Args:
                class_content: The content of a class with potential duplicate methods
                method_regex: Regular expression to identify methods
                
            Returns:
                Deduplicated class content
            """
            method_signatures = {}
            method_matches = list(re.finditer(method_regex, class_content, re.DOTALL))

            # Identify the most complete version of each method
            for match in method_matches:
                method_name = match.group(4)  # Method name
                return_type = match.group(3)  # Return type
                params = match.group(5)      # Parameters
                param_types = [param.strip().split(' ')[0] for param in params.split(',') if param.strip()]
                signature = f"{method_name}({','.join(param_types)})"
                full_method_text = match.group(0)

                # Keep the longest (most complete) version of the method
                if signature not in method_signatures or len(full_method_text) > len(method_signatures[signature]):
                    method_signatures[signature] = full_method_text

            # Remove duplicates by reconstructing the content
            deduplicated_content = class_content
            for match in reversed(method_matches):
                method_name = match.group(4)
                params = match.group(5)
                param_types = [param.strip().split(' ')[0] for param in params.split(',') if param.strip()]
                signature = f"{method_name}({','.join(param_types)})"
                full_method_text = match.group(0)

                if method_signatures[signature] != full_method_text:
                    deduplicated_content = deduplicated_content[:match.start()] + deduplicated_content[match.end():]

            return deduplicated_content

    def _generate_project_files(self, project_name: str = "TaskManagementSystem") -> Dict[str, Dict[str, str]]:
        """
        Generate .csproj files for each layer and solution file.
        
        Args:
            project_name: The name of the solution/project
            
        Returns:
            Dictionary containing project files
        """
        project_files = {}
        
        # Domain Project (.csproj)
        domain_csproj = f"""<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

</Project>"""
        
        # Application Project (.csproj)
        application_csproj = f"""<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <ProjectReference Include="../Domain/Domain.csproj" />
  </ItemGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.Extensions.DependencyInjection.Abstractions" Version="8.0.0" />
    <PackageReference Include="AutoMapper" Version="12.0.0" />
  </ItemGroup>

</Project>"""
        
        # Infrastructure Project (.csproj)
        infrastructure_csproj = f"""<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <ProjectReference Include="../Application/Application.csproj" />
  </ItemGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.0" />
    <PackageReference Include="Microsoft.Extensions.Logging.Abstractions" Version="8.0.0" />
  </ItemGroup>

</Project>"""
        
        # Presentation Project (.csproj)
        presentation_csproj = f"""<Project Sdk="Microsoft.NET.Sdk.Web">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <ProjectReference Include="../Application/Application.csproj" />
    <ProjectReference Include="../Infrastructure/Infrastructure.csproj" />
  </ItemGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.App" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Design" Version="8.0.0">
      <PrivateAssets>all</PrivateAssets>
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
    </PackageReference>
    <PackageReference Include="Swashbuckle.AspNetCore" Version="6.5.0" />
    <PackageReference Include="AutoMapper.Extensions.Microsoft.DependencyInjection" Version="12.0.0" />
  </ItemGroup>

</Project>"""
        
        # Solution File (.sln)
        solution_file = f"""Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31903.59
MinimumVisualStudioVersion = 10.0.40219.1
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "Domain", "Domain\\Domain.csproj", "{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}"
EndProject
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "Application", "Application\\Application.csproj", "{{B2C3D4E5-F6G7-8901-BCDE-F23456789012}}"
EndProject
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "Infrastructure", "Infrastructure\\Infrastructure.csproj", "{{C3D4E5F6-G7H8-9012-CDEF-345678901234}}"
EndProject
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "Presentation", "Presentation\\Presentation.csproj", "{{D4E5F6G7-H8I9-0123-DEF0-456789012345}}"
EndProject
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Debug|Any CPU = Debug|Any CPU
		Release|Any CPU = Release|Any CPU
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}.Release|Any CPU.Build.0 = Release|Any CPU
		{{B2C3D4E5-F6G7-8901-BCDE-F23456789012}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{B2C3D4E5-F6G7-8901-BCDE-F23456789012}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{B2C3D4E5-F6G7-8901-BCDE-F23456789012}}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{{B2C3D4E5-F6G7-8901-BCDE-F23456789012}}.Release|Any CPU.Build.0 = Release|Any CPU
		{{C3D4E5F6-G7H8-9012-CDEF-345678901234}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{C3D4E5F6-G7H8-9012-CDEF-345678901234}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{C3D4E5F6-G7H8-9012-CDEF-345678901234}}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{{C3D4E5F6-G7H8-9012-CDEF-345678901234}}.Release|Any CPU.Build.0 = Release|Any CPU
		{{D4E5F6G7-H8I9-0123-DEF0-456789012345}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{D4E5F6G7-H8I9-0123-DEF0-456789012345}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{D4E5F6G7-H8I9-0123-DEF0-456789012345}}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{{D4E5F6G7-H8I9-0123-DEF0-456789012345}}.Release|Any CPU.Build.0 = Release|Any CPU
	EndGlobalSection
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
	GlobalSection(ExtensibilityGlobals) = postSolution
		SolutionGuid = {{E5F6G7H8-I9J0-1234-EF01-567890123456}}
	EndGlobalSection
EndGlobal"""
        
        project_files["DomainProject"] = {
            "FileName": "Domain.csproj",
            "Path": "Domain/",
            "content": domain_csproj
        }
        
        project_files["ApplicationProject"] = {
            "FileName": "Application.csproj", 
            "Path": "Application/",
            "content": application_csproj
        }
        
        project_files["InfrastructureProject"] = {
            "FileName": "Infrastructure.csproj",
            "Path": "Infrastructure/", 
            "content": infrastructure_csproj
        }
        
        project_files["PresentationProject"] = {
            "FileName": "Presentation.csproj",
            "Path": "Presentation/",
            "content": presentation_csproj
        }
        
        project_files["SolutionFile"] = {
            "FileName": f"{project_name}.sln",
            "Path": "./",
            "content": solution_file
        }
        
        return project_files


def should_chunk_code(code: str, line_threshold: int = 24000) -> bool:
    """
    Determine if the COBOL code is large enough (based on line count) to require chunking.
    
    Args:
        code: The source code as a string
        line_threshold: Maximum allowed lines before chunking
        
    Returns:
        True if the code should be chunked, False otherwise
    """
    return len(code.splitlines()) > line_threshold


# Factory function to create a CodeConverter instance
def create_code_converter(client, model_name: str) -> CodeConverter:
    """
    Create a CodeConverter instance.
    
    Args:
        client: The OpenAI client
        model_name: The model deployment name
        
    Returns:
        A CodeConverter instance
    """
    return CodeConverter(client, model_name)

def extract_cobol_program_name(source_code: str, fallback: str = "TaskManagementSystem") -> str:
    """
    Extracts the PROGRAM-ID from COBOL code, or returns the fallback if not found.
    """
    import re
    match = re.search(r'PROGRAM-ID\.\s*([A-Z0-9_-]+)\.', source_code, re.IGNORECASE)
    if match:
        return match.group(1)
    return fallback