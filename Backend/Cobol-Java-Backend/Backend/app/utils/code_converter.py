import logging
import re
import json
import os
from typing import List, Dict, Any, Optional
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

def setup_logging(project_id: str = None):
    log_dir = f"output/converted/{project_id}" if project_id else "output/converted"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        filename=f"{log_dir}/conversion.log",
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='a'
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger(__name__)
    logger.addHandler(console)
    return logger

logger = setup_logging()

class CodeConverter:
    def __init__(self, client, model_name: str):
        self.client = client
        self.model_name = model_name
        self.logger = logger

    def get_language_enum(self, language_name: str) -> Optional[Language]:
        try:
            return Language[language_name.upper()]
        except KeyError:
            self.logger.warning(f"Language '{language_name}' is not supported by langchain_text_splitters. Using generic splitter.")
            return None

    def chunk_code(self, source_code: str, source_language: str, chunk_size: int = 23500, chunk_overlap: int = 1000, project_id: str = None) -> List[str]:
        self.logger = setup_logging(project_id) if project_id else logger
        self.logger.info(f"Chunking code of length {len(source_code)} ({len(source_code.splitlines())} lines) for language: {source_language}")

        if source_language.lower() == "cobol":
            self.logger.info("Using COBOL-specific chunking")
            chunks = self._split_cobol_code(source_code, chunk_size, chunk_overlap)
        else:
            language_enum = self.get_language_enum(source_language)
            if language_enum:
                self.logger.info(f"Using language-specific splitter for {source_language}")
                splitter = RecursiveCharacterTextSplitter.from_language(
                    language=language_enum,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
            else:
                self.logger.info(f"Using generic splitter for {source_language}")
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separators=["\n\n", "\n", ".", " ", ""]
                )
            chunks = splitter.split_text(source_code)

        self.logger.info(f"Split code into {len(chunks)} chunks. Chunk sizes: {[len(chunk) for chunk in chunks]}")
        return chunks

    def _split_cobol_code(self, code: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        lines = code.splitlines()
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_count = 0

        for i, line in enumerate(lines):
            line_size = len(line) + 1
            current_chunk.append(line)
            current_size += line_size

            if (re.match(r'^\s*([A-Z0-9-]+)\s+SECTION\.', line, re.IGNORECASE) or
                re.match(r'^\s*([A-Z0-9-]+)\s*\.', line, re.IGNORECASE) or
                " PROCEDURE DIVISION" in line.upper() or
                " WORKING-STORAGE SECTION" in line.upper() or
                current_size > chunk_size):
                if current_chunk and current_size > chunk_overlap:
                    chunks.append("\n".join(current_chunk))
                    self.logger.info(f"Chunk {chunk_count} created at boundary: {line.strip()[:50]}... (size: {current_size}, lines: {len(current_chunk)})")
                    chunk_count += 1
                    overlap_lines = current_chunk[-min(len(current_chunk), int(chunk_overlap/10)):] if chunk_overlap else []
                    current_chunk = overlap_lines
                    current_size = sum(len(l) + 1 for l in overlap_lines)

        if current_chunk:
            chunks.append("\n".join(current_chunk))
            self.logger.info(f"Final chunk {chunk_count} created (size: {current_size}, lines: {len(current_chunk)})")

        return chunks

    def convert_code_chunks(self, chunks: List[str], source_language: str, target_language: str, business_requirements: str,
                           technical_requirements: str, db_setup_template: str, project_id: str = None) -> Dict[str, Any]:
        self.logger = setup_logging(project_id) if project_id else logger
        if not chunks:
            self.logger.warning("No code chunks to convert")
            return {
                "convertedCode": "",
                "conversionNotes": "Error: No code provided for conversion",
                "potentialIssues": ["No source code was provided"],
                "databaseUsed": False,
                "targetStructure": {}
            }

        temp_dir = f"output/converted/{project_id}/temp_chunks" if project_id else "output/converted/temp_chunks"
        os.makedirs(temp_dir, exist_ok=True)
        converted_context_file = f"{temp_dir}/../converted_context.json"
        converted_context = self.load_json_file(converted_context_file) if os.path.exists(converted_context_file) else []

        target_structure_path = f"output/analysis/{project_id}/target_structure.json" if project_id else None
        target_structure = self.load_json_file(target_structure_path) if target_structure_path and os.path.exists(target_structure_path) else {
            "project_name": "ConvertedProject",
            "namespaces": [],
            "classes": [],
            "interfaces": [],
            "database_access": False,
            "patterns": []
        }
        self.logger.info(f"Initial target structure loaded: {json.dumps(target_structure, indent=2)}")

        if len(chunks) == 1:
            self.logger.info("Converting single chunk")
            result = self._convert_single_chunk(
                code_chunk=chunks[0],
                source_language=source_language,
                target_language=target_language,
                business_requirements=business_requirements,
                technical_requirements=technical_requirements,
                db_setup_template=db_setup_template,
                additional_context="",
                target_structure=target_structure,
                converted_context=converted_context
            )
            target_structure = self._update_target_structure(result["convertedCode"], target_structure, project_id)
            result["targetStructure"] = target_structure
            self.save_json_file(target_structure, target_structure_path)
            self.logger.info(f"Final target structure saved after single chunk conversion")
            return result

        self.logger.info(f"Converting {len(chunks)} code chunks with iterative target structure updates and temporary chunk storage")
        structure_prompt = self._create_structure_prompt(chunks, source_language, target_language)
        target_structure = self._get_code_structure(structure_prompt, target_language)
        self.save_json_file(target_structure, target_structure_path)
        self.logger.info(f"Initial target structure created: {json.dumps(target_structure, indent=2)}")

        conversion_results = []
        for i, chunk in enumerate(chunks):
            self.logger.info(f"Converting chunk {i+1}/{len(chunks)} (size: {len(chunk)}, lines: {len(chunk.splitlines())})")
            # Load previous converted chunks for context
            previous_chunks = [ctx for ctx in converted_context if ctx["index"] < i]
            previous_code = "\n".join([ctx["code"] for ctx in previous_chunks[-2:]])  # Use last 2 chunks for context
            self.logger.info(f"Using context from {len(previous_chunks[-2:])} previous chunks for chunk {i+1}")
            
            chunk_context = f"""
            This is chunk {i+1} of {len(chunks)} from the complete source code.

            IMPORTANT: Align your conversion with the current target structure:
            {json.dumps(target_structure, indent=2)}

            Previous converted code for context:
            {previous_code}

            Conversion Guidelines:
            1. Follow the target structure for consistent class/method names
            2. Include complete exception handling blocks
            3. Properly close all resources in finally blocks
            4. Ensure all methods have proper signatures and return types
            5. Define all methods and classes completely
            6. Avoid duplicating code defined in other chunks
            7. Ensure all imports are included for this chunk
            8. Map COBOL constructs (PERFORM, EXEC CICS) to .NET 8 equivalents
            9. Preserve COBOL comments and business logic
            """

            result = self._convert_single_chunk(
                code_chunk=chunk,
                source_language=source_language,
                target_language=target_language,
                business_requirements=business_requirements,
                technical_requirements=technical_requirements,
                db_setup_template=db_setup_template,
                additional_context=chunk_context,
                target_structure=target_structure,
                converted_context=converted_context
            )

            chunk_file = f"{temp_dir}/chunk_{i}.json"
            chunk_data = {"index": i, "code": result["convertedCode"], "source_chunk": chunk}
            self.save_json_file(chunk_data, chunk_file)
            self.logger.info(f"Stored converted chunk {i+1} at {chunk_file}")

            converted_context.append(chunk_data)
            self.save_json_file(converted_context, converted_context_file)

            target_structure = self._update_target_structure(result["convertedCode"], target_structure, project_id)
            self.save_json_file(target_structure, target_structure_path)
            self.logger.info(f"Updated target structure after chunk {i+1}: {json.dumps(target_structure, indent=2)}")

            conversion_results.append(result)

        merged_result = self._merge_conversion_results(conversion_results, target_language, target_structure)
        validated_code = self._validate_merged_code_against_analysis(merged_result["convertedCode"], target_language, project_id)
        merged_result["convertedCode"] = validated_code
        merged_result["targetStructure"] = target_structure

        final_structure = self._finalize_target_structure(merged_result["convertedCode"], target_structure, project_id)
        self.save_json_file(final_structure, target_structure_path)
        merged_result["targetStructure"] = final_structure
        self.logger.info(f"Final target structure generated: {json.dumps(final_structure, indent=2)}")

        return merged_result

    def _create_structure_prompt(self, chunks: List[str], source_language: str, target_language: str) -> str:
        complete_code = "\n\n".join(chunks)
        if len(complete_code) > 30000:
            begin = complete_code[:10000]
            middle_start = len(complete_code) // 2 - 5000
            middle_end = len(complete_code) // 2 + 5000
            middle = complete_code[middle_start:middle_end]
            end = complete_code[-10000:]
            complete_code = f"{begin}\n\n... [code truncated for brevity] ...\n\n{middle}\n\n... [code truncated for brevity] ...\n\n{end}"

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

        cobol_specific = """
        For COBOL to C# migration, please also provide:

        1. DATA DIVISION mapping - Map all COBOL records/structures to appropriate classes
        - Identify all WORKING-STORAGE SECTION items and how they should be represented
        - Map FILE SECTION records to appropriate data models
        - Determine which COBOL fields should become class fields vs. local variables
        - Handle COBOL PICTURE clauses with appropriate data types and precision
        - Handle REDEFINES with appropriate object patterns

        2. PROCEDURE DIVISION mapping - Map all COBOL paragraphs/sections to methods
        - Identify main program flow and control structures
        - Map PERFORM statements to appropriate method calls
        - Convert COBOL-style control flow to modern OO structured programming

        3. CICS HANDLING - Map CICS operations to REST API endpoints
        - Convert EXEC CICS commands to HTTP client calls
        - Implement proper transaction management
        - Handle CICS-specific error conditions

        4. Database integration - Identify any database or file access
        - Map COBOL file operations to Entity Framework Core
        - Convert embedded SQL to LINQ or parameterized queries
        - Handle indexed files with proper key management

        5. Error handling - Map COBOL error handling to exception-based approach
        - Convert status code checks to try-catch blocks
        - Implement proper logging and error reporting
        """

        # Create the JSON structure template as a string to avoid nested f-string issues
        json_structure = """{
  "project_name": "string",
  "namespaces": ["string"],
  "classes": [
    {
      "name": "string",
      "access_modifier": "string",
      "type": "class|interface|enum",
      "inherits": ["string"],
      "implements": ["string"],
      "methods": [
        {
          "name": "string",
          "return_type": "string",
          "parameters": [{"name": "string", "type": "string"}],
          "access_modifier": "string"
        }
      ],
      "fields": [
        {
          "name": "string",
          "type": "string",
          "access_modifier": "string"
        }
      ]
    }
  ],
  "database_access": boolean,
  "patterns": ["string"],
  "exception_strategy": "string"
}"""

        return f"""
        I need to convert {source_language} code to {target_language}, but first I need a detailed high-level structure to ensure consistency, quality, and maintainability.

        Please analyze this code and provide a DETAILED architectural blueprint in JSON format with the following structure:
        {json_structure}

        {language_specific}

        {cobol_specific}

        DO NOT convert the code in detail yet. Provide ONLY a comprehensive structural blueprint focusing on architecture, relationships, and ensuring clean, maintainable code that follows all {target_language} best practices.

        Here's the {source_language} code to analyze:

        ```cobol
        {complete_code}
        ```
        """

    def _get_code_structure(self, structure_prompt: str, target_language: str) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert software architect specializing in {target_language} and modern object-oriented design."
                    },
                    {"role": "user", "content": structure_prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            structure_content = response.choices[0].message.content.strip()
            try:
                structure_info = json.loads(structure_content)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse structure JSON directly, attempting to extract")
                json_pattern = r'(\{[\s\S]*\})'
                match = re.search(json_pattern, structure_content)
                if match:
                    structure_info = json.loads(match.group(1))
                else:
                    self.logger.error("Could not extract valid JSON from structure response")
                    structure_info = {
                        "project_name": "ConvertedProject",
                        "namespaces": [],
                        "classes": [],
                        "database_access": False,
                        "patterns": [],
                        "exception_strategy": "standard"
                    }
            self.logger.info(f"Generated initial structure: {json.dumps(structure_info, indent=2)}")
            return structure_info
        except Exception as e:
            self.logger.error(f"Error getting code structure: {str(e)}")
            return {
                "project_name": "ConvertedProject",
                "namespaces": [],
                "classes": [],
                "database_access": False,
                "patterns": [],
                "exception_strategy": "standard"
            }

    def _convert_single_chunk(self, code_chunk: str, source_language: str, target_language: str, business_requirements: str,
                             technical_requirements: str, db_setup_template: str, additional_context: str = "",
                             target_structure: Dict = None, converted_context: List[Dict] = None) -> Dict[str, Any]:
        from .prompts import create_code_conversion_prompt
        prompt = create_code_conversion_prompt(
            source_language, target_language, code_chunk, business_requirements, technical_requirements, db_setup_template
        )
        if target_structure:
            prompt += f"\n\nTARGET STRUCTURE:\n{json.dumps(target_structure, indent=2)}\n"
        if source_language == "COBOL" and target_language == "C#":
            prompt += """
            CRITICAL INSTRUCTIONS FOR COBOL TO C# CONVERSION:

            1. DATA STRUCTURE MAPPING:
            - Convert COBOL records to C# classes
            - Map group items to properties or nested classes
            - Map PIC clauses:
                * PIC 9(n) -> int or long
                * PIC 9(n)V9(m) -> decimal
                * PIC X(n) -> string
                * COMP-3 -> decimal
            - Handle REDEFINES with inheritance or union types
            - Convert OCCURS to List<T> or arrays

            2. PROCEDURE CONVERSION:
            - Convert paragraphs to methods
            - Map PERFORM to method calls
            - Replace GOTO with structured control flow
            - Convert EVALUATE to switch or if-else

            3. CICS HANDLING:
            - Map EXEC CICS to REST API calls
            - Implement transaction management
            - Handle CICS errors with exceptions

            4. FILE HANDLING:
            - Convert file operations to Entity Framework Core
            - Map indexed files to database tables
            - Handle sequential files with streams

            5. ERROR HANDLING:
            - Convert FILE STATUS to exceptions
            - Implement logging with Serilog
            """
        if target_language == "C#":
            prompt += """
            CRITICAL INSTRUCTIONS FOR C# CODE:
            1. Use proper namespaces
            2. Implement async/await for I/O
            3. Use dependency injection
            4. Follow SOLID principles
            5. Ensure all blocks are complete
            """
        if additional_context:
            prompt += f"\n\n{additional_context}"

        try:
            self.logger.info(f"Converting chunk of size {len(code_chunk)}")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert code converter specializing in {source_language} to {target_language} migration."
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
                self.logger.error(f"Error parsing JSON response: {str(json_err)}")
                json_pattern = r'(\{[\s\S]*\})'
                match = re.search(json_pattern, conversion_content)
                if match:
                    conversion_json = json.loads(match.group(1))
                    if target_language == "C#":
                        self._validate_code(conversion_json, target_language)
                    return conversion_json
                return {
                    "convertedCode": "// Error: Invalid response format",
                    "conversionNotes": f"Error processing response: {str(json_err)}",
                    "potentialIssues": ["Failed to process model response"],
                    "databaseUsed": False
                }
        except Exception as e:
            self.logger.error(f"Error calling model API: {str(e)}")
            return {
                "convertedCode": "",
                "conversionNotes": f"Error calling model API: {str(e)}",
                "potentialIssues": ["Failed to get response from model"],
                "databaseUsed": False
            }

    def _validate_code(self, conversion_result: Dict[str, Any], target_language: str) -> None:
        code = conversion_result.get("convertedCode")
        if not isinstance(code, str):
            self.logger.warning(f"Converted code is not a string, but {type(code)}")
            return
        issues = []
        opening_braces = code.count("{")
        closing_braces = code.count("}")
        if opening_braces != closing_braces:
            issues.append(f"Mismatched braces: {opening_braces} vs {closing_braces}")
        try_count = len(re.findall(r'\btry\s*{', code))
        catch_count = len(re.findall(r'\bcatch\s*\(', code))
        if try_count > catch_count:
            issues.append(f"Incomplete exception handling: {try_count} try vs {catch_count} catch")
        if issues:
            conversion_result["potentialIssues"] = conversion_result.get("potentialIssues", []) + issues

    def _merge_conversion_results(self, results: List[Dict[str, Any]], target_language: str, structure_info: Dict[str, Any] = None) -> Dict[str, Any]:
        if not results:
            return {
                "convertedCode": "",
                "conversionNotes": "No conversion results to merge",
                "potentialIssues": ["No conversion was performed"],
                "databaseUsed": False,
                "targetStructure": structure_info or {}
            }
        merged_code = ""
        all_notes = []
        all_issues = []
        database_used = any(result.get("databaseUsed", False) for result in results)

        if target_language == "C#":
            merged_code = self._merge_oop_code(results, target_language, structure_info)
        else:
            merged_code = self._fallback_merge(results)

        if target_language == "C#":
            merged_code = self._polish_code(merged_code, target_language)

        for i, result in enumerate(results):
            notes = result.get("conversionNotes", "")
            if notes:
                all_notes.append(f"Chunk {i+1}: {notes}")
            issues = result.get("potentialIssues", [])
            if issues:
                all_issues.extend([f"Chunk {i+1}: {issue}" for issue in issues])

        all_notes.insert(0, f"Processed {len(results)} chunks and merged into a single codebase")
        return {
            "convertedCode": merged_code,
            "conversionNotes": "\n\n".join(all_notes),
            "potentialIssues": all_issues,
            "databaseUsed": database_used,
            "targetStructure": structure_info
        }

    def _polish_code(self, code: str, target_language: str) -> str:
        if not code:
            self.logger.warning("Empty code provided for polishing")
            return code
        polished = code
        open_count = polished.count('{')
        close_count = polished.count('}')
        if open_count > close_count:
            polished += '\n' + '}' * (open_count - close_count)

        empty_catch_pattern = r'catch\s*\(([^)]*)\)\s*{\s*}'
        polished = re.sub(
            empty_catch_pattern,
            r'catch (\1) {\n    Console.WriteLine("Error: " + \1.Message);\n}',
            polished
        )

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

        prompt = f"""
        Fix the following C# code for syntax errors, proper formatting, and best practices:

        ```csharp
        {polished}
        ```

        Ensure:
        1. Proper namespace declarations
        2. Consistent use of async/await for I/O operations
        3. Dependency injection patterns
        4. SOLID principles
        5. Proper exception handling
        6. Removal of redundant code
        7. Consistent naming conventions

        Return only the corrected code.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert C# developer specializing in code quality."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            polished_code = response.choices[0].message.content.strip()
            code_match = re.search(r'```csharp\n([\s\S]*?)\n```', polished_code)
            if code_match:
                polished_code = code_match.group(1).strip()
            return polished_code
        except Exception as e:
            self.logger.error(f"Error polishing code: {str(e)}")
            return polished

    def _merge_oop_code(self, results: List[Dict[str, Any]], target_language: str, structure_info: Dict[str, Any] = None) -> str:
        self.logger.info(f"Merging {len(results)} chunks for {target_language} using target structure")
        package_namespace = f"namespace {structure_info.get('project_name', 'ConvertedProject')};" if structure_info else "namespace ConvertedProject;"
        imports = set()
        classes = {}
        utility_methods = []
        other_code = []
        field_declarations = set()
        constants = set()

        package_regex = r'^namespace\s+([^{;]+)'
        import_regex = r'^using\s+([^;]+);'
        class_regex = r'(public|private|protected|internal|)\s*(static|abstract|sealed|partial|)\s*class\s+([^\s:{<]+)(?:<[^>]*>)?(?:\s*:\s*[^{]+)?\s*{([^}]*)}'
        method_in_class_regex = r'(public|private|protected|internal|static|virtual|abstract|override|sealed|)\s*(static|virtual|abstract|override|sealed|)\s*(?:<[^>]*>\s*)?([^(\s]+)\s+([^\s(]+)\s*\(([^)]*)\)\s*({'
        standalone_method_regex = r'^(?:public|private|protected|internal|static|virtual|abstract|override|sealed|)\s*(?:static|virtual|abstract|override|sealed|)\s*(?:<[^>]*>\s*)?([^(\s]+)\s+([^\s(]+)\s*\(([^)]*)\)\s*{'
        field_regex = r'(public|private|protected|internal|static|readonly|)\s*(static|readonly|)\s*([^\s(]+)\s+([^\s(=]+)(?:\s*=\s*[^;]+)?;'
        constant_regex = r'(public|private|protected|internal|static|const|)\s*(static\s+const|const\s+static|const)\s*([^\s(]+)\s+([A-Z_][A-Z0-9_]*)(?:\s*=\s*[^;]+)?;'

        for i, result in enumerate(results):
            code = result.get("convertedCode", "")
            if not code:
                continue

            package_match = re.search(package_regex, code, re.MULTILINE)
            if package_match and not package_namespace:
                package_namespace = f"namespace {package_match.group(1).strip()};"

            import_matches = re.finditer(import_regex, code, re.MULTILINE)
            for match in import_matches:
                imports.add(match.group(0))

            constant_matches = re.finditer(constant_regex, code, re.MULTILINE)
            for match in constant_matches:
                constants.add(match.group(0))

            field_matches = re.finditer(field_regex, code, re.MULTILINE)
            for match in field_matches:
                if not re.search(constant_regex, match.group(0)):
                    field_declarations.add(match.group(0))

            class_matches = re.finditer(class_regex, code, re.DOTALL)
            for match in class_matches:
                access_modifier = match.group(1).strip()
                class_modifier = match.group(2).strip()
                class_name = match.group(3).strip()
                class_content = match.group(4).strip() if match.group(4) else ""
                class_content = self._deduplicate_methods(class_content, method_in_class_regex)
                class_signature = f"{access_modifier} {class_modifier} class {class_name}".strip()
                full_match = match.group(0)
                header_end_idx = full_match.find("{")
                if header_end_idx > 0:
                    class_signature = full_match[:header_end_idx].strip()
                if class_name in classes:
                    classes[class_name]["content"] += "\n\n" + class_content
                else:
                    classes[class_name] = {
                        "signature": class_signature,
                        "content": class_content
                    }

            method_matches = re.finditer(standalone_method_regex, code, re.MULTILINE)
            for match in method_matches:
                method_text = match.group(0)
                if not re.search(r'class\s+[^{]*{[^}]*' + re.escape(method_text), code, re.DOTALL):
                    utility_methods.append(method_text)

            code_without_matches = code
            for pattern in [package_regex, import_regex, class_regex, standalone_method_regex, field_regex, constant_regex]:
                code_without_matches = re.sub(pattern, '', code_without_matches, flags=re.MULTILINE | re.DOTALL)
            code_without_matches = code_without_matches.strip()
            if code_without_matches and len(code_without_matches) > 10:
                other_code.append(code_without_matches)

        merged_code = []
        if package_namespace:
            merged_code.append(package_namespace)
            merged_code.append("")
        if imports:
            merged_code.append("// Imports")
            for imp in sorted(imports):
                merged_code.append(imp)
            merged_code.append("")
        if constants:
            merged_code.append("// Constants")
            for constant in sorted(constants):
                merged_code.append(constant)
            merged_code.append("")
        if field_declarations:
            merged_code.append("// Fields")
            for field in sorted(field_declarations):
                merged_code.append(field)
            merged_code.append("")
        for class_name, class_info in classes.items():
            merged_code.append(class_info["signature"] + " {")
            if class_info["content"]:
                merged_code.append(self._deduplicate_methods(class_info["content"], method_in_class_regex))
            merged_code.append("}")
            merged_code.append("")
        if utility_methods:
            merged_code.append("// Utility Methods")
            for method in utility_methods:
                merged_code.append(method)
            merged_code.append("")
        if other_code:
            merged_code.append("// Additional Code")
            for code in other_code:
                merged_code.append(code)
            merged_code.append("")

        self.logger.info(f"Merged code size: {len('\n'.join(merged_code))} characters")
        return "\n".join(merged_code)

    def _fallback_merge(self, results: List[Dict[str, Any]]) -> str:
        merged_code = []
        for i, result in enumerate(results):
            code = result.get("convertedCode", "").strip()
            if code:
                merged_code.append(f"// ----- Chunk {i+1} -----\n{code}")
        self.logger.info(f"Fallback merged code size: {len('\n'.join(merged_code))} characters")
        return "\n".join(merged_code)

    def _deduplicate_methods(self, class_content: str, method_regex: str) -> str:
        method_signatures = {}
        method_matches = list(re.finditer(method_regex, class_content, re.DOTALL))
        for match in method_matches:
            method_name = match.group(4)
            params = match.group(5)
            param_types = [param.strip().split(' ')[0] for param in params.split(',') if param.strip()]
            signature = f"{method_name}({','.join(param_types)})"
            full_method_text = match.group(0)
            if signature not in method_signatures or len(full_method_text) > len(method_signatures[signature]):
                method_signatures[signature] = full_method_text
        deduplicated_content = class_content
        for match in reversed(method_matches):
            method_name = match.group(4)
            params = match.group(5)
            param_types = [param.strip().split(' ')[0] for param in params.split(',') if param.strip()]
            signature = f"{method_name}({','.join(param_types)})"
            if method_signatures[signature] != match.group(0):
                deduplicated_content = deduplicated_content[:match.start()] + deduplicated_content[match.end():]
        return deduplicated_content

    def _update_target_structure(self, converted_code: str, current_structure: Dict, project_id: str) -> Dict:
        self.logger.info(f"Updating target structure for project {project_id}")
        
        # Create the JSON structure template as a string to avoid nested f-string issues
        json_structure_template = """{
  "project_name": "string",
  "namespaces": ["string"],
  "classes": [
    {
      "name": "string",
      "access_modifier": "string",
      "type": "class|interface|enum",
      "inherits": ["string"],
      "implements": ["string"],
      "methods": [
        {
          "name": "string",
          "return_type": "string",
          "parameters": [{"name": "string", "type": "string"}],
          "access_modifier": "string"
        }
      ],
      "fields": [
        {
          "name": "string",
          "type": "string",
          "access_modifier": "string"
        }
      ]
    }
  ],
  "database_access": boolean,
  "patterns": ["string"],
  "exception_strategy": "string"
}"""

        try:
            prompt = f"""
            Analyze the following C# code and update the provided target structure to include new classes, methods, and relationships.
            Ensure consistency with existing structure and avoid duplication.

            C# Code:
            ```csharp
            {converted_code}
            ```

            Current Target Structure:
            {json.dumps(current_structure, indent=2)}

            Return the updated structure in JSON format with the following structure:
            {json_structure_template}
            """
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            updated_structure = json.loads(response.choices[0].message.content)
            self.logger.info(f"Target structure updated with new elements")
            return updated_structure
        except Exception as e:
            self.logger.error(f"Error updating target structure: {str(e)}")
            return current_structure

    def _finalize_target_structure(self, merged_code: str, current_structure: Dict, project_id: str) -> Dict:
        self.logger.info(f"Finalizing target structure for project {project_id}")
        
        # Create the JSON structure template as a string to avoid nested f-string issues
        json_structure_template = """{
  "project_name": "string",
  "namespaces": ["string"],
  "classes": [
    {
      "name": "string",
      "access_modifier": "string",
      "type": "class|interface|enum",
      "inherits": ["string"],
      "implements": ["string"],
      "methods": [
        {
          "name": "string",
          "return_type": "string",
          "parameters": [{"name": "string", "type": "string"}],
          "access_modifier": "string"
        }
      ],
      "fields": [
        {
          "name": "string",
          "type": "string",
          "access_modifier": "string"
        }
      ]
    }
  ],
  "database_access": boolean,
  "patterns": ["string"],
  "exception_strategy": "string"
}"""

        try:
            prompt = f"""
            Analyze the complete merged C# code and finalize the target structure to ensure it comprehensively represents the entire codebase.
            Ensure all classes, methods, fields, and relationships are included without duplication, and validate consistency.

            Merged C# Code:
            ```csharp
            {merged_code}
            ```

            Current Target Structure:
            {json.dumps(current_structure, indent=2)}

            Return the finalized structure in JSON format with the following structure:
            {json_structure_template}
            """
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            final_structure = json.loads(response.choices[0].message.content)
            self.logger.info(f"Final target structure generated")
            return final_structure
        except Exception as e:
            self.logger.error(f"Error finalizing target structure: {str(e)}")
            return current_structure

    def _validate_merged_code_against_analysis(self, code: str, target_language: str, project_id: str) -> str:
        self.logger.info(f"Validating merged code for project {project_id}")
        cobol_analysis_path = f"output/analysis/{project_id}/cobol_analysis.json"
        cobol_analysis = self.load_json_file(cobol_analysis_path) if os.path.exists(cobol_analysis_path) else {}
        
        prompt = f"""
        Validate the following C# code against the COBOL analysis to ensure all business logic is preserved and COBOL constructs are correctly mapped:

        COBOL Analysis:
        {json.dumps(cobol_analysis, indent=2)}

        Converted C# Code:
        ```csharp
        {code}
        ```

        Instructions:
        - Ensure all COBOL business logic is preserved
        - Verify that PERFORM statements are mapped to method calls
        - Check that EXEC CICS commands are converted to REST API calls
        - Ensure FILE STATUS checks are converted to exception handling
        - Validate that all classes and methods align with the target structure
        - Ensure async/await patterns are used for I/O operations
        - Check for proper dependency injection and SOLID principles
        - Return the validated code in JSON: {{"code": "..."}}

        If any issues are found, fix them in the returned code.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            validated_code = json.loads(response.choices[0].message.content).get("code", code)
            self.logger.info(f"Validated code size: {len(validated_code)}")
            return validated_code
        except Exception as e:
            self.logger.error(f"Error validating merged code: {str(e)}")
            return code

    def save_json_file(self, data: Dict, file_path: str) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Saved JSON to {file_path}")

    def load_json_file(self, file_path: str) -> Dict:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading JSON from {file_path}: {str(e)}")
            return {}

def should_chunk_code(code: str, line_threshold: int = 1000) -> bool:
    return len(code.splitlines()) > line_threshold

def create_code_converter(client, model_name: str) -> CodeConverter:
    return CodeConverter(client, model_name)