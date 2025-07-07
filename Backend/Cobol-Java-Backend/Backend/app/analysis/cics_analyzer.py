import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ConversionContext:
    program_name: str
    business_entities: List[str]
    dependencies: List[str]
    cics_commands: List[Dict]
    sql_blocks: List[str]
    complexity_score: int

class CICSAnalyzer:
    """
    Professional CICS Analyzer focused on analysis functionality
    """

    # Enhanced CICS command patterns with detailed mappings
    CICS_PATTERNS = {
        "WRITEQ_TS": {
            "pattern": r"WRITEQ\s+TS",
            "dotnet_service": "ICacheService",
            "conversion_hint": "Redis/MemoryCache implementation",
            "parameters": ["QUEUE", "FROM", "LENGTH", "ITEM"],
            "dotnet_method": "WriteToTempStorageAsync"
        },
        "READQ_TS": {
            "pattern": r"READQ\s+TS", 
            "dotnet_service": "ICacheService",
            "conversion_hint": "Cache retrieval with key-based lookup",
            "parameters": ["QUEUE", "INTO", "LENGTH", "ITEM"],
            "dotnet_method": "ReadFromTempStorageAsync"
        },
        "DELETEQ_TS": {
            "pattern": r"DELETEQ\s+TS",
            "dotnet_service": "ICacheService", 
            "conversion_hint": "Cache invalidation",
            "parameters": ["QUEUE"],
            "dotnet_method": "DeleteTempStorageAsync"
        },
        "WRITEQ_TD": {
            "pattern": r"WRITEQ\s+TD",
            "dotnet_service": "IMessageQueueService", 
            "conversion_hint": "Azure Service Bus/RabbitMQ",
            "parameters": ["QUEUE", "FROM", "LENGTH"],
            "dotnet_method": "PublishMessageAsync"
        },
        "READQ_TD": {
            "pattern": r"READQ\s+TD",
            "dotnet_service": "IMessageQueueService",
            "conversion_hint": "Message consumption",
            "parameters": ["QUEUE", "INTO", "LENGTH"],
            "dotnet_method": "ConsumeMessageAsync"
        },
        "LINK": {
            "pattern": r"LINK\s+PROGRAM",
            "dotnet_service": "IMediator",
            "conversion_hint": "MediatR command/query pattern",
            "parameters": ["PROGRAM", "COMMAREA", "LENGTH", "CHANNEL", "CONTAINER"],
            "dotnet_method": "SendAsync"
        },
        "SEND": {
            "pattern": r"SEND\s+(MAP|MAPSET)", 
            "dotnet_service": "IResponseService",
            "conversion_hint": "API response with view models",
            "parameters": ["MAPSET", "MAP", "ERASE", "CURSOR"],
            "dotnet_method": "SendResponseAsync"
        },
        "RECEIVE": {
            "pattern": r"RECEIVE\s+(MAP|MAPSET)",
            "dotnet_service": "IRequestService", 
            "conversion_hint": "Request binding and validation",
            "parameters": ["MAPSET", "MAP", "INTO", "LENGTH"],
            "dotnet_method": "ReceiveRequestAsync"
        },
        "START": {
            "pattern": r"START\s+TRANSID",
            "dotnet_service": "IBackgroundTaskService",
            "conversion_hint": "Background job scheduling",
            "parameters": ["TRANSID", "INTERVAL", "TIME"],
            "dotnet_method": "ScheduleTaskAsync"
        },
        "RETURN": {
            "pattern": r"RETURN",
            "dotnet_service": "ITransactionService",
            "conversion_hint": "Transaction completion",
            "parameters": ["TRANSID", "COMMAREA", "LENGTH"],
            "dotnet_method": "CompleteTransactionAsync"
        },
        "READ": {
            "pattern": r"READ\s+(FILE|UPDATE)",
            "dotnet_service": "IRepositoryService",
            "conversion_hint": "Entity Framework repository pattern",
            "parameters": ["FILE", "INTO", "RIDFLD"],
            "dotnet_method": "ReadAsync"
        },
        "WRITE": {
            "pattern": r"WRITE\s+FILE",
            "dotnet_service": "IRepositoryService",
            "conversion_hint": "Entity Framework Add operation",
            "parameters": ["FILE", "FROM", "RIDFLD"],
            "dotnet_method": "CreateAsync"
        },
        "REWRITE": {
            "pattern": r"REWRITE\s+FILE",
            "dotnet_service": "IRepositoryService",
            "conversion_hint": "Entity Framework Update operation",
            "parameters": ["FILE", "FROM"],
            "dotnet_method": "UpdateAsync"
        }
    }

    # Business domain patterns
    BUSINESS_PATTERNS = {
        "BANKING": ["ACCOUNT", "BALANCE", "DEPOSIT", "WITHDRAW", "TRANSFER", "CUSTOMER", "BANK"],
        "INSURANCE": ["POLICY", "CLAIM", "PREMIUM", "COVERAGE", "BENEFICIARY"],
        "RETAIL": ["PRODUCT", "INVENTORY", "ORDER", "CUSTOMER", "PAYMENT"],
        "HEALTHCARE": ["PATIENT", "DOCTOR", "APPOINTMENT", "TREATMENT", "INSURANCE"],
        "LOGISTICS": ["SHIPMENT", "DELIVERY", "TRACKING", "WAREHOUSE", "ROUTE"]
    }

    # Regex patterns
    PROG_ID_RE = re.compile(r"PROGRAM-ID\.\s*([A-Z0-9-]+)", re.I)
    COPY_RE = re.compile(r"COPY\s+([A-Z0-9-]+)", re.I)
    FD_RE = re.compile(r"FD\s+([A-Z0-9-]+)", re.I)
    LEVEL_RE = re.compile(r"^\s*(\d{2})\s+([A-Z0-9-]+)\s+PIC\s+([\w\(\)\.V]+)", re.I)
    CICS_START = re.compile(r"EXEC\s+CICS\s+([A-Z0-9-]+)", re.I)
    PARAM_RE = re.compile(r"(\w+)\(([^)]+)\)", re.I)
    SQL_START = re.compile(r"EXEC\s+SQL", re.I)
    SQL_END = re.compile(r"END-EXEC", re.I)
    PERFORM_RE = re.compile(r"PERFORM\s+([A-Z0-9-]+)", re.I)
    IF_RE = re.compile(r"IF\s+(.+)", re.I)

    def __init__(self, azure_config: Dict[str, str], uploads_dir: str = "uploads", 
                 output_dir: str = "cics_analysis"):
        self.uploads_dir = uploads_dir
        self.output_dir = output_dir
        self.analysis_file = os.path.join(output_dir, "analysis.json")
        
        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize Azure OpenAI client
        self.azure_config = azure_config
        from openai import AzureOpenAI
        self.client = AzureOpenAI(
            api_key=azure_config["AZURE_OPENAI_API_KEY"],
            api_version=azure_config["AZURE_OPENAI_API_VERSION"], 
            azure_endpoint=azure_config["AZURE_OPENAI_ENDPOINT"]
        )
        
        self.model_name = azure_config.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        self.analysis_result = {}
        
        logger.info("🚀 CICS Analyzer initialized")

    def analyze_project(self) -> Dict[str, Any]:
        """Main analysis method"""
        
        logger.info("🔍 Starting comprehensive CICS analysis...")
        
        # Load files
        files = self._load_project_files()
        
        # Enhanced analysis
        analysis = self._perform_enhanced_analysis(files)
        
        # AI insights
        enhanced_analysis = self._ai_enhance_analysis(analysis)
        
        # Save analysis
        self._save_analysis(enhanced_analysis)
        
        logger.info("✅ CICS analysis completed")
        
        return enhanced_analysis

    def _load_project_files(self) -> Dict[str, Any]:
        """Load and categorize project files"""
        
        if not os.path.exists(self.uploads_dir):
            raise FileNotFoundError(f"Uploads directory not found: {self.uploads_dir}")
        
        files = os.listdir(self.uploads_dir)
        categorized = {
            "programs": [f for f in files if f.lower().endswith((".cbl", ".cob"))],
            "copybooks": [f for f in files if f.lower().endswith(".cpy")], 
            "control_includes": [f for f in files if f.lower().endswith(".ctl")],
            "jcl_files": [f for f in files if f.lower().endswith((".jcl", ".job"))],
            "bms_maps": [f for f in files if f.lower().endswith(".bms")],
            "other": []
        }
        
        # Load content
        content_dict = {}
        categories_to_process = ["programs", "copybooks", "control_includes", "jcl_files", "bms_maps"]
        
        for category in categories_to_process:
            file_list = categorized.get(category, [])
            content_dict[f"{category}_content"] = {}
            
            for filename in file_list:
                path = os.path.join(self.uploads_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        content_dict[f"{category}_content"][filename] = content
                except Exception as e:
                    logger.warning(f"⚠️ Could not read {filename}: {e}")
        
        categorized.update(content_dict)
        
        logger.info(f"📁 Loaded {sum(len(categorized[k]) for k in categories_to_process)} files")
        return categorized

    def _perform_enhanced_analysis(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced analysis with deeper CICS insights"""
        
        result = {
            "programs": {},
            "copybooks": {},
            "control_includes": {},
            "jcl_files": {},
            "bms_maps": {},
            "summary": {
                "total_programs": len(files.get("programs", [])),
                "total_copybooks": len(files.get("copybooks", [])),
                "total_control_includes": len(files.get("control_includes", [])),
                "total_jcl_files": len(files.get("jcl_files", [])),
                "total_bms_maps": len(files.get("bms_maps", []))
            },
            "project_metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "total_files": sum(len(files.get(k, [])) for k in 
                                 ["programs", "copybooks", "control_includes", "jcl_files", "bms_maps"]),
                "business_domain": self._detect_business_domain(files),
                "cics_transaction_flow": [],
                "data_flow_analysis": {},
                "integration_points": []
            }
        }

        # Analyze each file type with enhanced logic
        for filename in files.get("copybooks", []):
            content = files.get("copybooks_content", {}).get(filename, "")
            if content:
                result["copybooks"][filename] = self._analyze_enhanced_copybook(filename, content)

        for filename in files.get("control_includes", []):
            content = files.get("control_includes_content", {}).get(filename, "")
            if content:
                result["control_includes"][filename] = self._analyze_enhanced_control(filename, content)

        for filename in files.get("programs", []):
            content = files.get("programs_content", {}).get(filename, "")
            if content:
                result["programs"][filename] = self._analyze_enhanced_program(filename, content, result)

        for filename in files.get("jcl_files", []):
            content = files.get("jcl_files_content", {}).get(filename, "")
            if content:
                result["jcl_files"][filename] = self._analyze_enhanced_jcl(filename, content)

        for filename in files.get("bms_maps", []):
            content = files.get("bms_maps_content", {}).get(filename, "")
            if content:
                result["bms_maps"][filename] = self._analyze_bms_map(filename, content)

        # Cross-reference analysis
        result["cross_references"] = self._analyze_cross_references(result)
        result["transaction_flows"] = self._analyze_transaction_flows(result)

        self.analysis_result = result
        return result

    def _analyze_enhanced_copybook(self, filename: str, content: str) -> Dict[str, Any]:
        """Enhanced copybook analysis"""
        
        fields = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            m = self.LEVEL_RE.match(line)
            if m:
                level, name, pic = m.groups()
                
                field_info = {
                    "level": level,
                    "name": name,
                    "pic": pic,
                    "line_number": i,
                    "cobol_type": self._determine_cobol_type(pic),
                    "dotnet_property": self._generate_dotnet_property(name, pic),
                    "java_property": self._generate_java_property(name, pic),
                    "validation_hints": self._generate_validation_hints(pic),
                    "is_key_field": self._is_key_field(name),
                    "is_required": self._is_required_field(name, pic)
                }
                fields.append(field_info)
        
        return {
            "description": "COBOL copybook defining a data structure",
            "fields": fields,
            "total_fields": len(fields),
            "complexity_score": self._calculate_complexity_score(fields),
            "suggested_dotnet_class": self._suggest_dotnet_class_name(filename),
            "entity_type": "Entity" if len(fields) > 5 else "ValueObject",
            "has_key_fields": any(f.get("is_key_field", False) for f in fields)
        }

    def _analyze_enhanced_control(self, filename: str, content: str) -> Dict[str, Any]:
        """Enhanced control include analysis"""
        
        # Same as copybook but mark as control structure
        result = self._analyze_enhanced_copybook(filename, content)
        result["description"] = "COBOL control-include defining control record layout"
        result["entity_type"] = "Configuration"
        return result

    def _analyze_enhanced_program(self, filename: str, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced program analysis with comprehensive CICS extraction"""
        
        lines = content.split('\n')
        
        # Initialize analysis structure
        program_analysis = {
            "description": "COBOL CICS program",
            "program_id": None,
            "copybooks": set(),
            "control_includes": set(),
            "file_descriptors": [],
            "cics_commands": [],
            "sql_blocks": [],
            "business_logic": [],
            "procedures": [],
            "data_movements": [],
            "conditional_logic": [],
            "state_mechanisms": {
                "TSQ_queues": set(),
                "TDQ_queues": set(), 
                "COMMAREAs": set(),
                "CHANNELS": set(),
                "CONTAINERS": set(),
                "MAPSETS": set(),
                "TRANSIDS": set()
            },
            "performance_indicators": {
                "file_operations": 0,
                "database_operations": 0,
                "network_operations": 0,
                "loops": 0,
                "conditions": 0
            },
            "error_handling": [],
            "security_aspects": []
        }

        i = 0
        while i < len(lines):
            line = lines[i]
            line_upper = line.upper().strip()
            
            if not line_upper or line_upper.startswith('*'):
                i += 1
                continue

            # Extract program ID
            if not program_analysis["program_id"]:
                m = self.PROG_ID_RE.search(line)
                if m:
                    program_analysis["program_id"] = m.group(1)

            # COPY references
            for m in self.COPY_RE.finditer(line_upper):
                cpy = m.group(1) + ".cpy"
                program_analysis["copybooks"].add(cpy)
                ctl = m.group(1) + ".ctl"
                if ctl in context.get("control_includes", {}):
                    program_analysis["control_includes"].add(ctl)

            # FD references
            m = self.FD_RE.search(line_upper)
            if m:
                program_analysis["file_descriptors"].append({
                    "name": m.group(1),
                    "line": i + 1,
                    "type": "VSAM" if "VSAM" in line_upper else "Sequential"
                })
                program_analysis["performance_indicators"]["file_operations"] += 1

            # Enhanced CICS command processing
            m = self.CICS_START.search(line_upper)
            if m:
                verb = m.group(1).upper()
                block, i = self._extract_cics_block(lines, i)
                
                command_info = self._analyze_enhanced_cics_command(verb, block, i + 1)
                program_analysis["cics_commands"].append(command_info)
                
                # Update state mechanisms
                self._update_enhanced_program_state(command_info, program_analysis["state_mechanisms"])
                
                # Performance tracking
                if command_info.get("command_type") in ["WRITEQ_TS", "READQ_TS", "WRITEQ_TD", "READQ_TD"]:
                    program_analysis["performance_indicators"]["network_operations"] += 1
                
                continue

            # Enhanced SQL processing
            if self.SQL_START.search(line_upper):
                sql_block, i = self._extract_sql_block(lines, i)
                sql_analysis = self._analyze_enhanced_sql(sql_block, i + 1)
                program_analysis["sql_blocks"].append(sql_analysis)
                program_analysis["performance_indicators"]["database_operations"] += 1
                continue

            # PERFORM statements (procedures)
            m = self.PERFORM_RE.search(line_upper)
            if m:
                program_analysis["procedures"].append({
                    "name": m.group(1),
                    "line": i + 1,
                    "type": "PERFORM",
                    "dotnet_equivalent": "private async Task " + self._to_pascal_case(m.group(1)) + "Async()"
                })
                program_analysis["performance_indicators"]["loops"] += 1

            # IF statements (conditional logic)
            m = self.IF_RE.search(line_upper)
            if m:
                program_analysis["conditional_logic"].append({
                    "condition": m.group(1),
                    "line": i + 1,
                    "complexity": self._assess_condition_complexity(m.group(1))
                })
                program_analysis["performance_indicators"]["conditions"] += 1

            # Data movement operations
            if line_upper.startswith("MOVE"):
                program_analysis["data_movements"].append({
                    "line": i + 1,
                    "statement": line.strip(),
                    "type": "MOVE",
                    "dotnet_hint": "Property assignment or mapping"
                })

            # Error handling
            if any(keyword in line_upper for keyword in ['RESP', 'ERROR', 'EXCEPTION', 'ABEND']):
                program_analysis["error_handling"].append({
                    "line": i + 1,
                    "type": "error_handling",
                    "statement": line.strip()
                })

            i += 1

        # Convert sets to sorted lists for JSON serialization
        for key in ["copybooks", "control_includes"]:
            program_analysis[key] = sorted(program_analysis[key])
        
        for key in program_analysis["state_mechanisms"]:
            program_analysis["state_mechanisms"][key] = sorted(program_analysis["state_mechanisms"][key])

        # Calculate complexity and generate .NET suggestions
        program_analysis["metadata"] = self._calculate_enhanced_metadata(program_analysis)
        program_analysis["dotnet_suggestions"] = self._generate_enhanced_dotnet_suggestions(program_analysis)

        return program_analysis

    def _analyze_enhanced_jcl(self, filename: str, content: str) -> Dict[str, Any]:
        """Enhanced JCL analysis"""
        
        lines = content.split('\n')
        
        jobs = []
        datasets = []
        programs = []
        steps = []
        
        for i, line in enumerate(lines, 1):
            line_clean = line.strip()
            if not line_clean or line_clean.startswith('*'):
                continue
                
            # Job names
            if line_clean.startswith('//') and 'JOB' in line_clean:
                job_match = re.search(r'//(\w+)\s+JOB', line_clean)
                if job_match:
                    jobs.append(job_match.group(1))
            
            # Steps
            if line_clean.startswith('//') and 'EXEC' in line_clean:
                step_match = re.search(r'//(\w+)\s+EXEC', line_clean)
                if step_match:
                    steps.append({
                        "name": step_match.group(1),
                        "line": i,
                        "dotnet_equivalent": "Background Service or Azure Function"
                    })
            
            # Dataset references
            if 'DSN=' in line_clean:
                dsn_match = re.search(r'DSN=([A-Z0-9.]+)', line_clean)
                if dsn_match:
                    datasets.append(dsn_match.group(1))
            
            # Program executions
            if 'PGM=' in line_clean:
                pgm_match = re.search(r'PGM=([A-Z0-9]+)', line_clean)
                if pgm_match:
                    programs.append(pgm_match.group(1))
        
        return {
            "description": "JCL job control file",
            "jobs": jobs,
            "steps": steps,
            "datasets": datasets,
            "programs": programs,
            "dotnet_equivalent": "Azure Functions, Background Services, or Docker containers",
            "complexity_score": len(steps) + len(programs)
        }

    def _analyze_bms_map(self, filename: str, content: str) -> Dict[str, Any]:
        """Analyze BMS map files"""
        
        return {
            "description": "BMS map definition for CICS screen handling",
            "filename": filename,
            "dotnet_equivalent": "Razor views, Web API models, or Blazor components",
            "conversion_hint": "Convert to REST API endpoints with JSON payloads"
        }

    def _analyze_enhanced_cics_command(self, verb: str, block: str, line_number: int) -> Dict[str, Any]:
        """Enhanced CICS command analysis"""
        
        # Extract parameters more comprehensively
        params = {}
        
        # Standard parameter extraction
        for k, v in self.PARAM_RE.findall(block):
            params[k.upper()] = v.strip("'\"")
        
        # Additional parameter patterns
        queue_match = re.search(r"QUEUE\s*\(\s*['\"]([^'\"]+)['\"]", block, re.I)
        if queue_match:
            params["QUEUE"] = queue_match.group(1)
        
        program_match = re.search(r"PROGRAM\s*\(\s*['\"]([^'\"]+)['\"]", block, re.I)
        if program_match:
            params["PROGRAM"] = program_match.group(1)

        file_match = re.search(r"FILE\s*\(\s*['\"]([^'\"]+)['\"]", block, re.I)
        if file_match:
            params["FILE"] = file_match.group(1)

        # Determine command type with enhanced matching
        command_type = ""
        dotnet_service = ""
        conversion_hint = ""
        dotnet_method = ""
        
        for pattern_name, pattern_info in self.CICS_PATTERNS.items():
            if re.search(pattern_info["pattern"], block, re.I):
                command_type = pattern_name
                dotnet_service = pattern_info["dotnet_service"]
                conversion_hint = pattern_info["conversion_hint"]
                dotnet_method = pattern_info["dotnet_method"]
                break
        
        # Generate AI-powered conversion
        ai_conversion = self._get_enhanced_ai_cics_conversion(verb, command_type, params, block)
        
        return {
            "line": line_number,
            "verb": verb,
            "command_type": command_type,
            "parameters": params,
            "raw_block": block,
            "dotnet_service": dotnet_service,
            "dotnet_method": dotnet_method,
            "conversion_hint": conversion_hint,
            "ai_conversion": ai_conversion,
            "complexity_score": self._calculate_command_complexity(params, block),
            "performance_impact": self._assess_performance_impact(command_type),
            "security_considerations": self._assess_security_considerations(command_type, params)
        }

    def _extract_cics_block(self, lines: List[str], start_idx: int) -> tuple:
        """Extract complete CICS command block"""
        block = [lines[start_idx].strip()]
        i = start_idx + 1
        
        while i < len(lines) and not lines[i].upper().strip().endswith('END-EXEC'):
            block.append(lines[i].strip())
            i += 1
        
        if i < len(lines):
            block.append(lines[i].strip())
        
        return " ".join(block), i

    def _extract_sql_block(self, lines: List[str], start_idx: int) -> tuple:
        """Extract complete SQL block"""
        block = [lines[start_idx].strip()]
        i = start_idx + 1
        
        while i < len(lines) and not self.SQL_END.search(lines[i].upper()):
            block.append(lines[i].strip())
            i += 1
        
        if i < len(lines):
            block.append(lines[i].strip())
        
        return "\n".join(block), i

    def _analyze_enhanced_sql(self, sql_block: str, line_number: int) -> Dict[str, Any]:
        """Enhanced SQL analysis"""
        
        sql_upper = sql_block.upper()
        
        # Determine SQL type
        sql_type = "SELECT"
        if "INSERT" in sql_upper:
            sql_type = "INSERT"
        elif "UPDATE" in sql_upper:
            sql_type = "UPDATE"
        elif "DELETE" in sql_upper:
            sql_type = "DELETE"
        elif "DECLARE" in sql_upper and "CURSOR" in sql_upper:
            sql_type = "CURSOR"
        
        return {
            "original_sql": sql_block,
            "line_number": line_number,
            "sql_type": sql_type,
            "dotnet_equivalent": self._convert_sql_to_dotnet(sql_block),
            "entity_framework_hint": self._suggest_ef_pattern(sql_block),
            "complexity": "HIGH" if "CURSOR" in sql_upper or "JOIN" in sql_upper else "MEDIUM"
        }

    def _ai_enhance_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """AI-enhanced business analysis"""
        
        try:
            # Create context for AI
            context = {
                "business_domain": analysis.get("project_metadata", {}).get("business_domain"),
                "programs": list(analysis.get("programs", {}).keys()),
                "cics_commands": sum(len(p.get("cics_commands", [])) for p in analysis.get("programs", {}).values()),
                "sql_operations": sum(len(p.get("sql_blocks", [])) for p in analysis.get("programs", {}).values())
            }
            
            prompt = (
                "Analyze this CICS system and return ONLY a JSON object with keys: "
                "business_domain, integration_patterns, data_flows, modernization_recommendations, risk_assessment. "
                f"Context: {json.dumps(context)}"
            )
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a business analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            ai_insights = json.loads(response.choices[0].message.content)
            analysis["ai_insights"] = ai_insights
            analysis["enhancement_timestamp"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.warning(f"AI enhancement failed: {e}")
            analysis["ai_insights"] = {"error": "AI analysis unavailable"}
        
        return analysis

    def _save_analysis(self, analysis: Dict[str, Any]):
        """Save analysis to file"""
        
        with open(self.analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Analysis saved to {self.analysis_file}")

    # === ALL HELPER METHODS ===
    
    def _detect_business_domain(self, files: Dict[str, Any]) -> str:
        """Detect business domain from file content"""
        
        all_content = ""
        for category in ["programs_content", "copybooks_content"]:
            for content in files.get(category, {}).values():
                all_content += content.upper()
        
        domain_scores = {}
        for domain, keywords in self.BUSINESS_PATTERNS.items():
            score = sum(all_content.count(keyword) for keyword in keywords)
            domain_scores[domain] = score
        
        return max(domain_scores.items(), key=lambda x: x[1])[0] if domain_scores else "GENERAL"

    def _analyze_cross_references(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cross-references between components"""
        
        cross_refs = {
            "program_to_copybook": {},
            "program_to_program": {},
            "data_dependencies": []
        }
        
        for prog_name, prog_data in result.get("programs", {}).items():
            cross_refs["program_to_copybook"][prog_name] = list(prog_data.get("copybooks", []))
        
        return cross_refs

    def _analyze_transaction_flows(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze transaction flows"""
        
        flows = []
        
        for prog_name, prog_data in result.get("programs", {}).items():
            flow = {
                "program": prog_name,
                "entry_point": prog_data.get("program_id"),
                "cics_operations": len(prog_data.get("cics_commands", [])),
                "data_operations": len(prog_data.get("sql_blocks", [])),
                "complexity": prog_data.get("metadata", {}).get("complexity_score", 0)
            }
            flows.append(flow)
        
        return flows

    def _update_enhanced_program_state(self, command_info: Dict, state_mechanisms: Dict):
        """Update program state from CICS command"""
        params = command_info.get("parameters", {})
        command_type = command_info.get("command_type", "")
        
        if "TS" in command_type and "QUEUE" in params:
            state_mechanisms["TSQ_queues"].add(params["QUEUE"])
        elif "TD" in command_type and "QUEUE" in params:
            state_mechanisms["TDQ_queues"].add(params["QUEUE"])
        
        if "COMMAREA" in params:
            state_mechanisms["COMMAREAs"].add(params["COMMAREA"])
        
        if "CHANNEL" in params:
            state_mechanisms["CHANNELS"].add(params["CHANNEL"])
        
        if "CONTAINER" in params:
            state_mechanisms["CONTAINERS"].add(params["CONTAINER"])
        
        if "MAPSET" in params:
            state_mechanisms["MAPSETS"].add(params["MAPSET"])
        
        if "TRANSID" in params:
            state_mechanisms["TRANSIDS"].add(params["TRANSID"])

    def _calculate_enhanced_metadata(self, program_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced metadata"""
        
        return {
            "total_lines": 0,
            "cics_commands_count": len(program_analysis.get("cics_commands", [])),
            "sql_blocks_count": len(program_analysis.get("sql_blocks", [])),
            "business_logic_statements": len(program_analysis.get("business_logic", [])),
            "procedures_count": len(program_analysis.get("procedures", [])),
            "complexity_score": self._calculate_program_complexity(program_analysis),
            "modernization_score": self._calculate_modernization_score(program_analysis)
        }

    def _generate_enhanced_dotnet_suggestions(self, program_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced .NET suggestions"""
        
        prog_id = program_analysis.get("program_id", "Unknown")
        
        return {
            "service_name": self._to_pascal_case(prog_id) + "Service",
            "controller_name": self._to_pascal_case(prog_id) + "Controller",
            "required_services": self._determine_required_services(program_analysis.get("cics_commands", [])),
            "suggested_patterns": self._suggest_design_patterns(program_analysis),
            "performance_considerations": self._suggest_performance_optimizations(program_analysis),
            "security_recommendations": self._suggest_security_measures(program_analysis)
        }

    def _get_enhanced_ai_cics_conversion(self, verb: str, command_type: str, params: Dict[str, str], block: str) -> str:
        """Get AI-powered CICS conversion"""
        
        try:
            prompt = (
                "Convert this CICS command to C# code. Return ONLY clean C# code, no explanations or markdown.\n"
                f"VERB: {verb}\nTYPE: {command_type}\nPARAMS: {json.dumps(params)}\nBLOCK: {block}"
            )
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a CICS-to-C# converter. Return only clean C# code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            return self._clean_ai_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.warning(f"AI CICS conversion failed: {e}")
            return f"// TODO: Convert {verb} {command_type} - {params}"

    def _clean_ai_response(self, text: str) -> str:
        """Clean AI response"""
        text = re.sub(r'```[\w]*\n?', '', text)
        text = re.sub(r'```', '', text)
        return text.strip()

    # === UTILITY HELPER METHODS ===

    def _determine_cobol_type(self, pic: str) -> str:
        """Determine COBOL data type from PIC clause"""
        if not pic:
            return "alphanumeric"
        pic_upper = pic.upper()
        if "X" in pic_upper:
            return "alphanumeric"
        elif "9" in pic_upper:
            if "V" in pic_upper or "." in pic_upper:
                return "numeric_decimal"
            else:
                return "numeric_integer"
        elif "A" in pic_upper:
            return "alphabetic"
        return "unknown"
    
    def _is_key_field(self, name: str) -> bool:
        """Detect if a field name implies a key/ID."""
        uname = name.upper()
        return any(token in uname for token in ("ID", "KEY", "NO"))

    def _is_required_field(self, name: str, pic: str) -> bool:
        """Heuristic: mark numeric fields as required"""
        pu = pic.upper()
        if "9" in pu:
            return True
        return bool(re.match(r"[XA]\(\d+\)", pu))

    def _pic_to_dotnet_type(self, pic: str) -> str:
        """Convert PIC clause to .NET type"""
        if not pic:
            return "string"
        pu = pic.upper()
        if "X" in pu or "A" in pu:
            return "string"
        if "9" in pu:
            if "V" in pu or "." in pu:
                return "decimal"
            count = pu.count("9")
            if count <= 4:
                return "short"
            if count <= 9:
                return "int"
            return "long"
        return "string"

    def _pic_to_java_type(self, pic: str) -> str:
        """Convert PIC clause to Java type"""
        if not pic:
            return "String"
        pu = pic.upper()
        if "X" in pu or "A" in pu:
            return "String"
        if "9" in pu:
            if "V" in pu or "." in pu:
                return "BigDecimal"
            return "Integer" if pu.count("9") <= 9 else "Long"
        return "String"

    def _to_pascal_case(self, text: str) -> str:
        """Convert to PascalCase"""
        parts = re.split(r"[\s_-]+", text)
        return "".join(p.capitalize() for p in parts if p)

    def _to_camel_case(self, text: str) -> str:
        """Convert to camelCase"""
        pascal = self._to_pascal_case(text)
        return pascal[0].lower() + pascal[1:] if pascal else ""

    def _generate_dotnet_property(self, name: str, pic: str) -> Dict[str, str]:
        """Generate .NET property info"""
        return {
            "name": self._to_pascal_case(name.replace("-", "_")),
            "type": self._pic_to_dotnet_type(pic),
            "original_name": name,
            "pic_clause": pic
        }

    def _generate_java_property(self, name: str, pic: str) -> Dict[str, str]:
        """Generate Java property info"""
        return {
            "name": self._to_camel_case(name.replace("-", "_")),
            "type": self._pic_to_java_type(pic),
            "original_name": name,
            "pic_clause": pic
        }

    def _generate_validation_hints(self, pic: str) -> List[str]:
        """Generate validation hints from PIC clause"""
        hints: List[str] = []
        pu = pic.upper()
        if "9" in pu:
            hints.append("Numeric")
        if "X" in pu:
            match = re.search(r"X\((\d+)\)", pu)
            length = match.group(1) if match else "variable"
            hints.append(f"MaxLength={length}")
        return hints
    
    def _calculate_complexity_score(self, fields: List[Dict]) -> int:
        """Simple complexity: capped at 10"""
        return min(len(fields), 10)

    def _suggest_dotnet_class_name(self, filename: str) -> str:
        """Suggest .NET class name from filename"""
        base = Path(filename).stem
        return self._to_pascal_case(base)

    def _calculate_program_complexity(self, program_analysis: Dict[str, Any]) -> int:
        """Complexity = commands + 2*sql + business_logic"""
        cmds = len(program_analysis.get("cics_commands", []))
        sqls = len(program_analysis.get("sql_blocks", []))
        biz = len(program_analysis.get("business_logic", []))
        return cmds + sqls * 2 + biz

    def _calculate_modernization_score(self, program_analysis: Dict[str, Any]) -> int:
        """Rough modernization score 1–10"""
        complexity = self._calculate_program_complexity(program_analysis)
        return max(1, 10 - min(complexity, 9))

    def _determine_required_services(self, commands: List[Dict]) -> List[str]:
        """List distinct dotnet_service names"""
        return sorted({cmd.get("dotnet_service") for cmd in commands if cmd.get("dotnet_service")})

    def _suggest_design_patterns(self, program_analysis: Dict[str, Any]) -> List[str]:
        """Recommend design patterns"""
        patterns = []
        if any(c["command_type"] == "LINK" for c in program_analysis.get("cics_commands", [])):
            patterns.append("Mediator (MediatR)")
        if any(c["command_type"] in ("READQ_TS", "READQ_TD") for c in program_analysis.get("cics_commands", [])):
            patterns.append("Query/Read Model")
        if any(c["command_type"] in ("WRITEQ_TS", "WRITEQ_TD") for c in program_analysis.get("cics_commands", [])):
            patterns.append("Command/Write Model")
        if program_analysis.get("procedures"):
            patterns.append("Strategy or Template Method")
        return patterns

    def _suggest_performance_optimizations(self, program_analysis: Dict[str, Any]) -> List[str]:
        """Suggest performance tips"""
        tips = []
        pi = program_analysis.get("performance_indicators", {})
        if pi.get("loops", 0) > 5:
            tips.append("Batch operations instead of loops")
        if pi.get("database_operations", 0) > 3:
            tips.append("Use EF Change Tracking wisely")
        if pi.get("network_operations", 0) > 2:
            tips.append("Cache frequently used data")
        return tips
    
    def _calculate_command_complexity(self, params: Dict[str, str], block: str) -> int:
        """Rough complexity: number of parameters plus block length factor."""
        param_count = len(params)
        token_count = len(block.split())
        return param_count + token_count // 20

    def _assess_performance_impact(self, command_type: str) -> str:
        """Estimate performance impact of a CICS command."""
        high = {"LINK", "START"}
        medium = {"READ", "READQ_TS", "READQ_TD", "WRITE", "WRITEQ_TS", "WRITEQ_TD", "REWRITE"}
        low = {"DELETEQ_TS", "RETURN", "SEND", "RECEIVE"}
        if command_type in high:
            return "high"
        if command_type in medium:
            return "medium"
        return "low"

    def _assess_security_considerations(self, command_type: str, params: Dict[str, str]) -> List[str]:
        """List security checks needed for this CICS command."""
        cons: List[str] = []
        if "COMMAREA" in params:
            cons.append("Validate and sanitize COMMAREA payload")
        if "CHANNEL" in params or "CONTAINER" in params:
            cons.append("Ensure container data is authenticated")
        if command_type == "LINK":
            cons.append("Ensure linked program is authorized")
        return cons

    def _assess_condition_complexity(self, condition: str) -> str:
        """Assess complexity of a COBOL IF condition."""
        length = len(condition)
        if length > 80:
            return "high"
        if length > 40:
            return "medium"
        return "low"

    def _suggest_security_measures(self, program_analysis: Dict[str, Any]) -> List[str]:
        """Suggest security measures"""
        sec = program_analysis.get("security_aspects", [])
        recs = []
        if sec:
            recs.append("Validate and sanitize COMMAREA")
        recs.extend([
            "Use HTTPS for all endpoints",
            "Implement authentication & authorization",
            "Log sensitive operations"
        ])
        return recs

    def _convert_sql_to_dotnet(self, sql: str) -> str:
        """Convert a COBOL EXEC SQL block to an EF Core snippet."""
        sql_up = sql.upper()
        if "SELECT COUNT(*)" in sql_up:
            return "var count = await _context.EntitySet.CountAsync();"
        elif "SELECT" in sql_up and "FROM" in sql_up:
            return "var results = await _context.EntitySet.ToListAsync();"
        elif "INSERT" in sql_up:
            return "await _context.EntitySet.AddAsync(entity); await _context.SaveChangesAsync();"
        elif "UPDATE" in sql_up:
            return "_context.EntitySet.Update(entity); await _context.SaveChangesAsync();"
        elif "DELETE" in sql_up:
            return "_context.EntitySet.Remove(entity); await _context.SaveChangesAsync();"
        else:
            return f"// TODO: Convert SQL: {sql.strip()}"

    def _suggest_ef_pattern(self, sql: str) -> str:
        """Suggest an EF Core pattern for this SQL."""
        sql_up = sql.upper()
        if "SELECT" in sql_up:
            return "LINQ Query with projection"
        if "INSERT" in sql_up:
            return "Add + SaveChanges pattern"
        if "UPDATE" in sql_up:
            return "Update + SaveChanges pattern"
        if "DELETE" in sql_up:
            return "Remove + SaveChanges pattern"
        return "Repository pattern"