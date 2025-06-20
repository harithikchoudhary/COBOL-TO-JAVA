import logging
import re
import json
from typing import List, Dict, Any, Optional
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

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

    def convert_code_chunks(self, chunks: List[str], source_language: str, 
                           target_language: str,vsam_definition: str, business_requirements: str,
                           technical_requirements: str, db_setup_template: str) -> Dict[str, Any]:
        """
        Convert each code chunk and merge the results.
        
        Args:
            chunks: List of code chunks to convert
            source_language: Source programming language
            target_language: Target programming language for conversion
            business_requirements: Business requirements to consider during conversion
            technical_requirements: Technical requirements to consider during conversion
            db_setup_template: Database setup template if needed
            
        Returns:
            Dictionary containing the converted code and related information
        """
        if not chunks:
            logger.warning("No code chunks to convert")
            return {
                "convertedCode": "",
                "conversionNotes": "Error: No code provided for conversion",
                "potentialIssues": ["No source code was provided"],
                "databaseUsed": False
            }
        
        # For a single chunk, convert directly
        if len(chunks) == 1:
            return self._convert_single_chunk(
                chunks[0], source_language, target_language, vsam_definition,
                business_requirements, technical_requirements, db_setup_template
            )
        
        # For multiple chunks, provide an overview of the entire code first
        logger.info(f"Converting {len(chunks)} code chunks using a two-phase approach")
        
        # Phase 1: Generate a high-level structure of the target code
        # This helps maintain consistency across chunks
        structure_prompt = self._create_structure_prompt(chunks, source_language, target_language)
        structure_result = self._get_code_structure(structure_prompt, target_language)
        
        # Phase 2: Convert each chunk with awareness of the overall structure
        conversion_results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Converting chunk {i+1}/{len(chunks)}")
            
            # Enhanced context includes the code structure and chunk position
            chunk_context = f"""
            This is chunk {i+1} of {len(chunks)} from the complete source code.
            
            IMPORTANT: Ensure your conversion aligns with this overall code structure:
            {structure_result.get('structure', 'No structure available')}
            
            When converting this chunk:
            1. Follow the above structure for consistent class/method names
            2. Include complete exception handling blocks
            3. Properly close all resources in finally blocks
            4. Ensure all methods have proper signatures and return types
            5. Define all methods and classes completely - don't leave implementation gaps
            6. Avoid duplicating code that would be defined in other chunks
            7. Ensure all imports are included for this chunk
            
            If you see incomplete code:
            - Complete class definitions even if they appear partial
            - Handle exception blocks properly - don't leave them empty
            - Complete any missing control flow statements (if/while/try)
            """
            
            result = self._convert_single_chunk(
                chunk, source_language, target_language, vsam_definition,
                business_requirements, technical_requirements, 
                db_setup_template, additional_context=chunk_context
            )
            
            conversion_results.append(result)
        
        # Use the structure-aware merge to create the final code
        return self._merge_conversion_results(conversion_results, target_language, structure_result)

    def _create_structure_prompt(self, chunks: List[str], source_language: str, target_language: str) -> str:
        """
        Create a prompt to get the overall structure of the code before detailed conversion.
        Enhanced for COBOL to Java/C# migration with data structure mapping.
        
        Args:
            chunks: List of code chunks
            source_language: Source programming language
            target_language: Target programming language
            
        Returns:
            A prompt for the model
        """
        # Join all chunks to provide a complete overview
        complete_code = "\n\n".join(chunks)
        
        # For very long code, use a summarized version to avoid exceeding token limits
        if len(complete_code) > 30000:
            # Extract a representative sample from the beginning, middle, and end
            begin = complete_code[:10000]
            middle_start = len(complete_code) // 2 - 5000
            middle_end = len(complete_code) // 2 + 5000
            middle = complete_code[middle_start:middle_end]
            end = complete_code[-10000:]
            
            complete_code = f"{begin}\n\n... [code truncated for brevity] ...\n\n{middle}\n\n... [code truncated for brevity] ...\n\n{end}"
        
        # Target language specific instructions
        language_specific = ""
        if target_language == "Java":
            language_specific = """
            For Java output, please include:
            
            1. PROPER PACKAGE STRUCTURE - Organize code with appropriate packages
            - Identify logical components and group related classes
            - Use standard Java package naming conventions (e.g., com.company.module)
            
            2. CLASS HIERARCHY - Design an object-oriented structure
            - Define appropriate class hierarchies with inheritance
            - Use interfaces for common behavior
            - Apply design patterns where appropriate
            
            3. ACCESS MODIFIERS - Apply correct encapsulation
            - Use private for fields with getters/setters
            - Protect internal implementation details
            - Expose only necessary public methods
            
            4. FIELD DEFINITIONS - Proper variable declarations
            - Include appropriate data types for all fields
            - Apply final modifier where variables shouldn't change
            - Initialize all fields with appropriate defaults
            
            5. EXCEPTION HANDLING - Use Java exception hierarchy
            - Define application-specific exceptions if needed
            - Use checked exceptions for recoverable conditions
            - Use unchecked exceptions for programming errors
            
            6. JAVA CONVENTIONS - Follow standard Java practices
            - Use camelCase for variables and methods
            - Use PascalCase for class names
            - Use ALL_CAPS for constants
            """
        elif target_language == "C#":
            language_specific = """
            For C# output, please include:
            
            1. NAMESPACE STRUCTURE - Organize code with appropriate namespaces
            - Identify logical components and group related classes
            - Use standard C# namespace conventions (e.g., Company.Module)
            
            2. CLASS HIERARCHY - Design an object-oriented structure
            - Define appropriate class hierarchies with inheritance
            - Use interfaces for common behavior
            - Apply design patterns where appropriate
            
            3. ACCESS MODIFIERS - Apply correct encapsulation
            - Use private for fields with properties
            - Protect internal implementation details
            - Expose only necessary public methods
            
            4. FIELD DEFINITIONS - Proper variable declarations
            - Include appropriate data types for all fields
            - Use properties with getters/setters
            - Initialize all fields with appropriate defaults
            
            5. EXCEPTION HANDLING - Use .NET exception hierarchy
            - Define application-specific exceptions if needed
            - Use try-catch-finally blocks consistently
            - Include appropriate exception handling strategies
            
            6. C# CONVENTIONS - Follow standard C# practices
            - Use camelCase for private fields (with _ prefix)
            - Use PascalCase for properties, methods, and class names
            - Use PascalCase for public fields (rarely used)
            """
        
        # COBOL-specific instructions for structure analysis
        cobol_specific = ""
        if source_language == "COBOL":
            cobol_specific = """
            For COBOL to Java/C# migration, please also provide:
            
            1. DATA DIVISION mapping - Map all COBOL records/structures to appropriate classes
            - Identify all WORKING-STORAGE SECTION items and how they should be represented
            - Map FILE SECTION records to appropriate data models
            - Determine which COBOL fields should become class fields vs. local variables
            - Handle COBOL PICTURE clauses with appropriate data types and precision
            - Handle REDEFINES with appropriate object patterns (e.g., inheritance, interfaces)
            
            2. PROCEDURE DIVISION mapping - Map all COBOL paragraphs/sections to methods
            - Identify main program flow and control structures
            - Map PERFORM statements to appropriate method calls 
            - Create structured methods with single responsibility
            - Determine how to handle GOTO statements and eliminate spaghetti code
            - Convert COBOL-style control flow to modern OO structured programming
            
            3. Database integration - Identify any database or file access
            - Map COBOL file operations to JDBC/ADO.NET
            - Convert COBOL file I/O to appropriate database operations
            - Handle indexed files with proper key management 
            - Convert any embedded SQL to prepared statements and proper connection handling
            
            4. Error handling - Map COBOL error handling to exception-based approach
            - Convert status code checks to try-catch blocks
            - Identify ON ERROR and similar constructs
            - Create appropriate custom exception classes when needed
            - Implement proper resource cleanup in finally blocks
            
            5. Numeric/decimal handling - Identify precision requirements
            - Use BigDecimal/decimal for financial calculations
            - Handle implicit decimal points properly (PIC 9(7)V99)
            - Apply proper rounding modes where needed
            - Ensure numeric formatting follows business requirements
            
            6. MODULE ORGANIZATION - Properly organize the application
            - Separate business logic from data access
            - Create service layers for main functionality
            - Implement proper dependency management
            - Follow modern OO design principles (SOLID)
            """
        
        return f"""
        I need to convert {source_language} code to {target_language}, but first I need a detailed high-level structure to ensure consistency, quality and maintainability.
        
        Please analyze this code and provide a DETAILED architectural blueprint including:
        
        1. COMPLETE CLASS STRUCTURE with:
        - All necessary classes, interfaces, and enums
        - Clear inheritance hierarchies and relationships
        - Fields with their types and access modifiers
        - Complete method signatures (return types, parameters, exceptions)
        
        2. PACKAGE/NAMESPACE ORGANIZATION:
        - Logical grouping of related classes
        - Proper naming following {target_language} conventions
        
        3. DATABASE ACCESS (if present):
        - Connection management approach
        - Transaction handling
        - Resource cleanup strategy
        
        4. DESIGN PATTERNS to implement:
        - Identify appropriate patterns for clean code structure
        - How to eliminate procedural code and make it object-oriented
        
        5. ERROR HANDLING STRATEGY:
        - Exception hierarchy
        - Resource cleanup approach
        - Logging strategy
        
        {language_specific}
        
        {cobol_specific}
        
        DO NOT convert the code in detail yet. Provide ONLY a comprehensive structural blueprint focusing on architecture, relationships, and ensuring clean, maintainable code that follows all {target_language} best practices.
        
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
                        "content": f"You are an expert software architect specializing in {target_language} and modern object-oriented design. "
                                f"Your task is to analyze legacy code and provide a detailed architectural blueprint for modern, clean, "
                                f"maintainable {target_language} code. You excel at creating well-structured object-oriented designs that "
                                f"follow best practices and design patterns."
                    },
                    {"role": "user", "content": structure_prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            structure_content = response.choices[0].message.content.strip()
            
            # Extract important structure information
            structure_info = {
                "structure": structure_content,
                "classes": [],
                "package": None,
                "interfaces": [],
                "database_access": False,
                "exception_strategy": "standard",
                "patterns": []
            }
            
            # Extract class names
            class_matches = re.findall(r'class\s+([A-Za-z0-9_]+)', structure_content)
            structure_info["classes"] = list(set(class_matches))  # Remove duplicates
            
            # Extract package/namespace
            if target_language == "Java":
                package_match = re.search(r'package\s+([a-z0-9_.]+)', structure_content, re.IGNORECASE)
                if package_match:
                    structure_info["package"] = package_match.group(1)
            else:  # C#
                namespace_match = re.search(r'namespace\s+([A-Za-z0-9_.]+)', structure_content, re.IGNORECASE)
                if namespace_match:
                    structure_info["package"] = namespace_match.group(1)
            
            # Extract interfaces
            interface_matches = re.findall(r'interface\s+([A-Za-z0-9_]+)', structure_content)
            structure_info["interfaces"] = list(set(interface_matches))  # Remove duplicates
            
            # Check for database access
            db_keywords = ['JDBC', 'Connection', 'PreparedStatement', 'ResultSet', 
                        'SqlConnection', 'SqlCommand', 'DataReader', 'EntityFramework',
                        'JPA', 'Repository', 'DataSource']
            for keyword in db_keywords:
                if keyword in structure_content:
                    structure_info["database_access"] = True
                    break
            
            # Identify design patterns
            pattern_keywords = {
                "Factory": ["Factory", "getInstance", "createInstance"],
                "Singleton": ["Singleton", "getInstance", "private constructor"],
                "Builder": ["Builder", "build()", ".build()"],
                "Strategy": ["Strategy", "algorithm", "behavior"],
                "Observer": ["Observer", "Observable", "notify", "subscribe"],
                "Repository": ["Repository", "DAO", "Data Access"],
                "Service": ["Service", "Manager", "Processor"],
                "MVC": ["Model", "View", "Controller"],
                "DTO": ["DTO", "Data Transfer Object"]
            }
            
            for pattern, keywords in pattern_keywords.items():
                for keyword in keywords:
                    if keyword in structure_content:
                        structure_info["patterns"].append(pattern)
                        break
            
            structure_info["patterns"] = list(set(structure_info["patterns"]))  # Remove duplicates
            
            # Get exception handling strategy
            if "custom exception" in structure_content.lower() or "applicationexception" in structure_content.lower():
                structure_info["exception_strategy"] = "custom"
            
            return structure_info
                
        except Exception as e:
            logger.error(f"Error getting code structure: {str(e)}")
            return {
                "structure": "Could not determine code structure",
                "classes": [],
                "package": None,
                "interfaces": [],
                "database_access": False,
                "exception_strategy": "standard",
                "patterns": []
            }
    
    def _convert_single_chunk(self, code_chunk: str, source_language: str,
                            target_language: str,vsam_definition: str, business_requirements: str,
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
        from prompts import create_code_conversion_prompt
        
        # Create prompt for this chunk
        prompt = create_code_conversion_prompt(
            source_language,
            target_language,
            code_chunk,
            business_requirements,
            vsam_definition,
            technical_requirements,
            db_setup_template
        )
        
        # Add COBOL-specific instructions for Java/C# conversion
        if source_language == "COBOL" and target_language in ["Java", "C#"]:
            prompt += """
            
            CRITICAL INSTRUCTIONS FOR COBOL TO JAVA/C# CONVERSION:
            
            1. DATA STRUCTURE MAPPING:
            - Convert COBOL records (01 level items) to classes
            - Map COBOL group items (05-49 level) to nested classes or complex properties
            - Map elementary items (PIC clauses) to appropriate data types:
                * PIC 9(n) -> int, long, or BigInteger depending on size
                * PIC 9(n)V9(m) -> double or BigDecimal (use BigDecimal for financial calculations)
                * PIC X(n) -> String (with proper length)
                * PIC A(n) -> String (with proper length)
                * COMP-3 fields -> appropriate numeric type with scaling
            - Handle REDEFINES with appropriate conversion strategy (e.g., inheritance or multiple properties)
            - Convert COBOL tables (OCCURS clause) to arrays or Collections
            
            2. PROCEDURE CONVERSION:
            - Convert COBOL paragraphs to methods
            - Convert PERFORM statements to method calls
            - Replace GOTO statements with structured alternatives (loops, conditionals)
            - Convert in-line PERFORM with appropriate loop structure
            - Handle COBOL specific control flow (EVALUATE, etc.)
            
            3. FILE HANDLING CONVERSION:
            - Convert COBOL file operations (OPEN, READ, WRITE) to appropriate Java/C# I/O
            - For indexed files, use appropriate database or file-based index solution
            - For sequential files, use appropriate stream-based I/O
            - Handle record locking mechanisms appropriately
            
            4. ERROR HANDLING:
            - Convert COBOL ON SIZE ERROR to appropriate exception handling
            - Convert FILE STATUS checks to try-catch blocks
            - Implement appropriate logging and error reporting
            
            5. NUMERIC PROCESSING:
            - Preserve exact decimal calculations where needed (BigDecimal in Java, decimal in C#)
            - Handle implicit decimal points from COBOL PIC clauses
            - Preserve COBOL numeric editing behavior when formatting output
            
            6. COMPLETENESS AND STRUCTURE:
            - Ensure all variables are properly initialized
            - Add appropriate constructors to classes
            - Implement appropriate access modifiers (public, private, etc.)
            - Add appropriate getters and setters for class properties
            - Add appropriate package/namespace organization
            """
        
        # Enhanced instructions for Java/C# conversion
        if target_language in ["Java", "C#"]:
            prompt += """
            
            CRITICAL INSTRUCTIONS FOR CLEAN CODE GENERATION:
            
            1. COMPLETE ALL CODE BLOCKS - Never leave any block incomplete
            - Every opening brace must have a closing brace
            - Every if/for/while must have a complete body
            - Every try must have catch and finally blocks
            - Every method must have a return type and complete implementation
            
            2. EXCEPTION HANDLING - Implement proper exception handling
            - All catch blocks must have actual code handling the exception
            - Don't leave catch blocks empty or with placeholder comments
            - Use try-with-resources where appropriate
            - Add specific exception types when possible
            
            3. DATABASE CODE - Ensure proper connection management
            - Always close connections, statements, and result sets in finally blocks
            - Use try-with-resources for database resources
            - Implement proper transaction management
            
            4. METHOD SIGNATURES - Use complete and proper method signatures
            - Include all method modifiers (public/private/static/etc.)
            - Specify return types for all methods
            - Include parameter types for all parameters
            - Add throws declarations when needed
            
            5. CLASS STRUCTURE - Make sure classes are properly formatted
            - Include all necessary imports at the top
            - Declare all fields with proper access modifiers
            - Include necessary constructors
            - Implement interfaces and extend classes as needed
            
            6. AVOID DUPLICATIONS - Avoid duplicating code unnecessarily
            
            7. COMPLETENESS - Make sure the generated code is complete and runnable
            - No undefined variables or methods
            - No placeholder comments where code should be
            """
        
        # Add chunk-specific context if provided
        if additional_context:
            prompt += f"\n\n{additional_context}"
        

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert code converter specializing in {source_language} to {target_language} migration. "
                                f"You convert legacy code to modern, idiomatic code while maintaining all business logic. "
                                f"Your code must be complete, well-structured, and follow best practices. "
                                f"Ensure that all syntax is correct, with matching brackets and proper statement terminations. "
                                f"Only include database setup/initialization if the original code uses databases or SQL. "
                                f"For simple algorithms or calculations without database operations, don't add any database code. "
                                f"Return your response in JSON format always with the following structure:\n"
                                f"{{\n"
                                f'  \"convertedCode\": \"The complete converted code here\",\n'
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
            
            # Parse the JSON response
            conversion_content = response.choices[0].message.content.strip()
            
            try:
                # Attempt to parse the JSON response
                conversion_json = json.loads(conversion_content)
                
                # Validate the converted code
                if target_language in ["Java", "C#"]:
                    self._validate_code(conversion_json, target_language)
                    
                return conversion_json
                
            except json.JSONDecodeError as json_err:
                logger.error(f"Error parsing JSON response: {str(json_err)}")
                logger.debug(f"Problematic response content: {conversion_content}")
                
                # Attempt to extract JSON from the response
                try:
                    # Use regex to find JSON-like content
                    json_pattern = r'(\{[\s\S]*\})'
                    match = re.search(json_pattern, conversion_content)
                    if match:
                        potential_json = match.group(1)
                        conversion_json = json.loads(potential_json)
                        logger.info("Successfully extracted JSON from response using regex")
                        
                        # Validate the converted code
                        if target_language in ["Java", "C#"]:
                            self._validate_code(conversion_json, target_language)
                            
                        return conversion_json
                except Exception as extract_err:
                    logger.error(f"Failed to extract JSON using regex: {str(extract_err)}")
                
                # Return a fallback response
                return {
                    "convertedCode": "// Error: Invalid response format received from server",
                    "conversionNotes": f"Error processing response: {str(json_err)}",
                    "potentialIssues": ["Failed to process model response", "Response was not valid JSON"],
                    "databaseUsed": False
                }
                
        except Exception as e:
            logger.error(f"Error calling model API: {str(e)}")
            return {
                "convertedCode": "",
                "conversionNotes": f"Error calling model API: {str(e)}",
                "potentialIssues": ["Failed to get response from model"],
                "databaseUsed": False
            }
    
    def _validate_code(self, conversion_result: Dict[str, Any], target_language: str) -> None:
        """
        Validate the converted code for common issues and try to fix them.
        
        Args:
            conversion_result: The conversion result dictionary
            target_language: The target programming language
        """
        code = conversion_result.get("convertedCode")
        if code is None:
            logger.warning("Converted code is None, skipping validation")
            return
        if not isinstance(code, str):
            logger.warning(f"Converted code is not a string, but {type(code)}, skipping validation")
            return
            
        # Proceed with validation only if code is a string
        issues = []
        
        # Check for mismatched braces
        opening_braces = code.count("{")
        closing_braces = code.count("}")
        if opening_braces != closing_braces:
            issues.append(f"Mismatched braces: {opening_braces} opening vs {closing_braces} closing")
        
        # Check for incomplete try-catch blocks
        try_count = len(re.findall(r'\btry\s*{', code))
        catch_count = len(re.findall(r'\bcatch\s*\(', code))
        if try_count > catch_count:
            issues.append(f"Incomplete exception handling: {try_count} try blocks but only {catch_count} catch blocks")
        
        # Check for empty catch blocks
        empty_catches = len(re.findall(r'catch\s*\([^)]*\)\s*{\s*}', code))
        if empty_catches > 0:
            issues.append(f"Found {empty_catches} empty catch blocks")
        
        # Java/C# specific validations
        if target_language in ["Java", "C#"]:
            # Check for semicolons at the end of statements
            lines = code.split('\n')
            missing_semicolons = 0
            for line in lines:
                line = line.strip()
                # Check if line ends with a statement that should have a semicolon but doesn't
                if (line and not line.endswith(";") and not line.endswith("{") and not line.endswith("}") 
                    and not line.endswith("*/") and not line.startswith("//") 
                    and not line.startswith("import ") and not line.startswith("package ")
                    and not line.startswith("using ") and not line.startswith("namespace ")
                    and not re.match(r'^[a-zA-Z0-9_]+:', line)  # Avoid matching labels in C#
                    and not re.match(r'^(public|private|protected)\s+(class|interface|enum)', line)):
                    missing_semicolons += 1
            
            if missing_semicolons > 0:
                issues.append(f"Potentially missing semicolons in {missing_semicolons} statements")
            
            # Check for missing/malformed method signatures
            malformed_methods = len(re.findall(r'[a-zA-Z0-9_]+\s*\([^)]*\)\s*{', code))
            if malformed_methods > 0:
                issues.append(f"Found {malformed_methods} methods with potentially missing return types or access modifiers")
            
            # Check for uninitialized variables (only basic check)
            if target_language == "Java":
                uninit_variables = len(re.findall(r'(int|double|float|long|boolean|char|byte|short)\s+[a-zA-Z0-9_]+\s*;', code))
                if uninit_variables > 0:
                    issues.append(f"Found {uninit_variables} potentially uninitialized primitive variables")
        
        # Add validation issues to the potential issues list
        if issues:
            existing_issues = conversion_result.get("potentialIssues", [])
            conversion_result["potentialIssues"] = existing_issues + issues

    def _merge_conversion_results(self, results: List[Dict[str, Any]], 
                                target_language: str,
                                structure_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Merge multiple conversion results into a single result.
        
        Args:
            results: List of conversion results to merge
            target_language: The target programming language
            structure_info: Information about the code structure
            
        Returns:
            Merged conversion result
        """
        if not results:
            return {
                "convertedCode": "",
                "conversionNotes": "No conversion results to merge",
                "potentialIssues": ["No conversion was performed"],
                "databaseUsed": False
            }
        
        # Initialize with defaults
        merged_code = ""
        all_notes = []
        all_issues = []
        database_used = any(result.get("databaseUsed", False) for result in results)
        
        # Special handling for Java and C# to properly merge class definitions
        if target_language in ["Java", "C#"]:
            try:
                merged_code = self._merge_oop_code(results, target_language, structure_info)
            except Exception as e:
                logger.error(f"Error in OOP code merging: {str(e)}")
                merged_code = self._fallback_merge(results)
                all_issues.append(f"Error during intelligent code merging: {str(e)}. Used fallback merge method.")
        else:
            # For other languages, use a simpler merging approach
            merged_code = self._fallback_merge(results)
        
        # Polish the merged code for Java and C#
        if target_language in ["Java", "C#"]:
            merged_code = self._polish_code(merged_code, target_language)
        
        # Merge notes and issues
        for i, result in enumerate(results):
            notes = result.get("conversionNotes", "")
            if notes:
                all_notes.append(f"Chunk {i+1}: {notes}")
                
            issues = result.get("potentialIssues", [])
            if issues:
                all_issues.extend([f"Chunk {i+1}: {issue}" for issue in issues])
        
        # Add a note about the chunking process
        all_notes.insert(0, f"The original code was processed in {len(results)} chunks due to its size and merged into a single codebase.")
        
        # Perform final validation on the merged code
        if target_language in ["Java", "C#"]:
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
        Polish the merged code to fix any syntax errors or incomplete blocks.
        
        Args:
            code: The merged code to polish
            target_language: The target programming language
            
        Returns:
            The polished code
        """
        if not code or len(code.strip()) == 0:
            logger.warning("Empty code provided for polishing")
            return code
            
        # First attempt automatic fixes for common issues
        polished = code
        
        # Fix mismatched braces
        open_count = polished.count('{')
        close_count = polished.count('}')
        if open_count > close_count:
            # Add missing closing braces
            polished += '\n' + '}' * (open_count - close_count)
        
        # Ensure all catch blocks have content
        empty_catch_pattern = r'catch\s*\(([^)]*)\)\s*{\s*}'
        polished = re.sub(empty_catch_pattern, 
                        r'catch (\1) {\n    // Error handling\n    System.err.println("Error caught: " + \1.getMessage());\n}' 
                        if target_language == "Java" else 
                        r'catch (\1) {\n    // Error handling\n    Console.WriteLine("Error caught: " + \1.Message);\n}',
                        polished)
        
        # Ensure all class and method blocks are properly indented
        lines = polished.split('\n')
        indented_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Adjust indent level based on braces
            if stripped.endswith('{'):
                indented_lines.append('    ' * indent_level + stripped)
                indent_level += 1
            elif stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)  # Prevent negative indent
                indented_lines.append('    ' * indent_level + stripped)
            else:
                indented_lines.append('    ' * indent_level + stripped)
        
        polished = '\n'.join(indented_lines)
        
        # Now use the model to further polish the code
        prompt = f"""
        Below is a {target_language} code that was generated by converting from another language. It may have syntax errors or style issues.
        Please fix the following types of issues to make it valid and well-structured {target_language} code:
        
        1. Fix any syntax errors (missing semicolons, mismatched braces, etc.)
        2. Ensure proper class structure with correct access modifiers
        3. Fix method signatures (return types, parameter types)
        4. Ensure proper variable initialization
        5. Add appropriate exception handling in try-catch blocks
        6. Fix any import statements if needed
        7. Follow standard {target_language} naming conventions
        8. Ensure consistent indentation and formatting
        9. Remove any redundant or duplicate code
        10. Add necessary comments for complex logic
        
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
                        "content": f"You are an expert {target_language} developer specializing in code quality, syntax correction, and formatting. Your task is to fix code issues while preserving all functionality."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            polished_code = response.choices[0].message.content.strip()
            
            # Extract the code from the response, in case it's wrapped in markdown
            code_match = re.search(r'```(?:' + target_language.lower() + r')?\n([\s\S]*?)\n```', polished_code)
            if code_match:
                polished_code = code_match.group(1).strip()
            else:
                # If no markdown, assume the entire content is the code
                # But check if it seems like valid code (contains class or package/namespace)
                if not re.search(r'(class|package|namespace)\s+', polished_code):
                    logger.warning("Polished code doesn't look like valid Java/C# code, using original polish")
                    return polished
            
            # Make a final validation on the polished code
            validation_issues = self._quick_validate(polished_code, target_language)
            if validation_issues:
                logger.warning(f"Polished code still has issues: {validation_issues}")
                # If the model's polishing made things worse, fall back to our basic polishing
                if len(validation_issues) >= 3:  # Arbitrary threshold for "made things worse"
                    logger.warning("Model polishing degraded code quality, falling back to basic polish")
                    return polished
                    
            return polished_code

        except Exception as e:
            logger.error(f"Error polishing code: {str(e)}")
            return polished  # Return our basic polished code if model polish fails
            
    def _quick_validate(self, code: str, target_language: str) -> List[str]:
        """Quick validation to check if polishing introduced new issues"""
        issues = []
        
        # Check for mismatched braces
        opening_braces = code.count("{")
        closing_braces = code.count("}")
        if opening_braces != closing_braces:
            issues.append(f"Mismatched braces: {opening_braces} opening vs {closing_braces} closing")
        
        # Check for empty catch blocks
        empty_catches = len(re.findall(r'catch\s*\([^)]*\)\s*{\s*}', code))
        if empty_catches > 0:
            issues.append(f"Found {empty_catches} empty catch blocks")
            
        return issues

    def _validate_merged_code(self, merged_code: str, target_language: str) -> List[str]:
        """
        Validate the merged code for common issues.
        
        Args:
            merged_code: The merged code to validate
            target_language: The target programming language
            
        Returns:
            List of validation issues
        """
        if merged_code is None:
            logger.warning("Merged code is None, skipping validation")
            return ["Merged code is None"]
        if not isinstance(merged_code, str):
            logger.warning(f"Merged code is not a string, but {type(merged_code)}, skipping validation")
            return [f"Merged code is not a string, but {type(merged_code)}"]
        
        issues = []
        
        # Check for mismatched braces
        opening_braces = merged_code.count("{")
        closing_braces = merged_code.count("}")
        if opening_braces != closing_braces:
            issues.append(f"Mismatched braces in merged code: {opening_braces} opening vs {closing_braces} closing")
        
        # Check for incomplete try-catch blocks
        try_count = len(re.findall(r'\btry\s*{', merged_code))
        catch_count = len(re.findall(r'\bcatch\s*\(', merged_code))
        if try_count > catch_count:
            issues.append(f"Incomplete exception handling in merged code: {try_count} try blocks but only {catch_count} catch blocks")
        
        # Check for empty catch blocks
        empty_catches = len(re.findall(r'catch\s*\([^)]*\)\s*{\s*}', merged_code))
        if empty_catches > 0:
            issues.append(f"Found {empty_catches} empty catch blocks in merged code")
        
        # Check for incomplete class definitions
        if target_language == "Java":
            class_starts = len(re.findall(r'(public|private|protected|)\s*(class|interface|enum)\s+\w+', merged_code))
            class_ends = len(re.findall(r'}\s*(\/\/.*)?$', merged_code, re.MULTILINE))
            if class_starts > class_ends:
                issues.append(f"Potentially incomplete class definitions: {class_starts} class starts but only {class_ends} endings")
        
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