import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .dual_rag_analyzer import DualRAGCOBOLAnalyzer
from .cics_analyzer import CICSAnalyzer
from .cics_converter import CICSConverter
from ..config import AZURE_CONFIG, UPLOAD_DIR, OUTPUT_DIR, API_OUTPUT_DIR, DOCUMENTS_DIR

logger = logging.getLogger(__name__)

class AnalysisManager:
    """
    Enhanced Central manager for all COBOL analysis including RAG and CICS with comprehensive context generation
    """
    
    def __init__(self):
        self.dual_rag_analyzer = None
        self.cics_analyzer = None
        self.cics_converter = None
        self.project_files = {}
        self.analysis_results = None
        self.conversion_context = None  # NEW: Store conversion-ready context
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all analysis components"""
        try:
            # Initialize Dual RAG Analyzer
            self.dual_rag_analyzer = DualRAGCOBOLAnalyzer(AZURE_CONFIG, API_OUTPUT_DIR)
            
            # Initialize CICS Analyzer
            self.cics_analyzer = CICSAnalyzer(AZURE_CONFIG, uploads_dir=UPLOAD_DIR, output_dir=OUTPUT_DIR)
            
            # Initialize CICS Converter
            self.cics_converter = CICSConverter(AZURE_CONFIG, output_dir=OUTPUT_DIR)
            
            logger.info("✅ All enhanced analysis components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize analysis components: {e}")
            raise
    
    def process_uploaded_files(self, files_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Enhanced process uploaded files with comprehensive RAG and CICS analysis
        
        Args:
            files_data: Dictionary of filename -> content
            
        Returns:
            Dictionary with comprehensive analysis results
        """
        logger.info(f"🔍 Processing {len(files_data)} uploaded files for comprehensive analysis")
        
        # Store files
        self.project_files = files_data
        self._save_files_to_disk()
        
        # Run comprehensive analysis
        results = {
            "files_processed": len(files_data),
            "rag_analysis": None,
            "cics_analysis": None,
            "conversion_context": None,  # NEW: Pre-built conversion context
            "status": "success"
        }
        
        try:
            # 1. Run RAG analysis
            logger.info("🔗 Running comprehensive RAG analysis...")
            rag_results = self.dual_rag_analyzer.analyze_project(files_data)
            results["rag_analysis"] = {
                "total_files": len(rag_results["files"]),
                "business_entities": len(rag_results["business_entities"]),
                "file_connections": sum(len(conn["depends_on"]) for conn in rag_results["connections"].values()),
                "conversion_patterns": len(rag_results["conversion_patterns"]),
                "rag_status": {
                    "standards_rag_active": self.dual_rag_analyzer.standards_vector_store is not None,
                    "project_rag_active": self.dual_rag_analyzer.project_vector_store is not None
                }
            }
            
            # 2. Run CICS analysis
            logger.info("⚙️ Running comprehensive CICS analysis...")
            cics_results = self.cics_analyzer.analyze_project()
            results["cics_analysis"] = {
                "total_programs": len(cics_results.get("programs", {})),
                "total_copybooks": len(cics_results.get("copybooks", {})),
                "business_domain": cics_results.get("project_metadata", {}).get("business_domain", "Unknown"),
                "cics_commands": sum(len(p.get("cics_commands", [])) for p in cics_results.get("programs", {}).values())
            }
            
            # 3. NEW: Generate conversion-ready context
            logger.info("📝 Generating conversion-ready context...")
            self.conversion_context = self._generate_conversion_context(rag_results, cics_results)
            results["conversion_context"] = {
                "entities_count": len(self.conversion_context.get("business_entities", [])),
                "patterns_count": len(self.conversion_context.get("conversion_patterns", [])),
                "dependencies_count": len(self.conversion_context.get("dependencies", {})),
                "context_ready": True
            }
            
            # Store analysis results
            self.analysis_results = {
                "rag_results": rag_results,
                "cics_results": cics_results,
                "conversion_context": self.conversion_context
            }
            
            # Save enhanced analysis to disk
            self._save_enhanced_analysis()
            
            logger.info("✅ Comprehensive analysis completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            results["status"] = "error"
            results["error"] = str(e)
        
        return results
    
    def process_standards_documents(self, standards_files: Dict[str, bytes]) -> Dict[str, Any]:
        """
        Process standards documents for RAG
        
        Args:
            standards_files: Dictionary of filename -> file content (bytes)
            
        Returns:
            Processing results
        """
        logger.info(f"📄 Processing {len(standards_files)} standards documents")
        
        try:
            # Save standards files to documents directory
            for filename, content in standards_files.items():
                file_path = os.path.join(DOCUMENTS_DIR, filename)
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            # Process standards documents
            self.dual_rag_analyzer.process_standards_documents()
            
            return {
                "status": "success",
                "files_processed": len(standards_files),
                "standards_rag_active": self.dual_rag_analyzer.standards_vector_store is not None
            }
            
        except Exception as e:
            logger.error(f"❌ Standards processing failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _generate_conversion_context(self, rag_results: Dict, cics_results: Dict) -> Dict[str, Any]:
        """Generate conversion-ready context from analysis results"""
        
        logger.info("🎯 Building comprehensive conversion context...")
        
        conversion_context = {
            "business_entities": [],
            "conversion_patterns": [],
            "dependencies": {},
            "cics_patterns": [],
            "architecture_recommendations": [],
            "technology_stack": {
                "database_usage": False,
                "messaging_patterns": [],
                "caching_patterns": [],
                "security_patterns": []
            }
        }
        
        # Extract business entities with .NET mapping
        for entity in rag_results.get("business_entities", []):
            dotnet_entity = {
                "cobol_name": entity.get("name", ""),
                "dotnet_class": entity.get("java_class_name", "").replace("Java", "").replace("Class", ""),
                "namespace": f"CicsModernization.Domain.Entities",
                "source_file": entity.get("source_file", ""),
                "complexity": entity.get("estimated_complexity", "medium")
            }
            conversion_context["business_entities"].append(dotnet_entity)
        
        # Extract conversion patterns with .NET equivalents
        for pattern in rag_results.get("conversion_patterns", []):
            dotnet_pattern = {
                "pattern_type": pattern.get("pattern_type", ""),
                "cobol_pattern": pattern.get("cobol_pattern", ""),
                "dotnet_equivalent": self._convert_java_to_dotnet_pattern(pattern.get("java_equivalent", "")),
                "context": pattern.get("context", ""),
                "source_file": pattern.get("source_file", "")
            }
            conversion_context["conversion_patterns"].append(dotnet_pattern)
        
        # Extract CICS patterns for microservices architecture
        programs = cics_results.get("programs", {})
        for prog_name, prog_data in programs.items():
            for cics_cmd in prog_data.get("cics_commands", []):
                cics_pattern = {
                    "command_type": cics_cmd.get("command_type", ""),
                    "dotnet_service": cics_cmd.get("dotnet_service", ""),
                    "microservice_pattern": self._determine_microservice_pattern(cics_cmd),
                    "program": prog_name
                }
                conversion_context["cics_patterns"].append(cics_pattern)
        
        # Determine technology stack
        conversion_context["technology_stack"] = self._determine_technology_stack(cics_results)
        
        # Generate architecture recommendations
        conversion_context["architecture_recommendations"] = self._generate_architecture_recommendations(
            rag_results, cics_results
        )
        
        logger.info(f"✅ Conversion context generated with {len(conversion_context['business_entities'])} entities")
        return conversion_context
    
    def _convert_java_to_dotnet_pattern(self, java_pattern: str) -> str:
        """Convert Java patterns to .NET equivalents"""
        java_to_dotnet = {
            "public class": "public class",
            "Repository pattern": "Repository pattern with Entity Framework",
            "// Repository pattern": "// Repository pattern with Entity Framework Core",
            "// TODO: Convert": "// TODO: Convert to .NET Core pattern"
        }
        
        for java_term, dotnet_term in java_to_dotnet.items():
            java_pattern = java_pattern.replace(java_term, dotnet_term)
        
        return java_pattern
    
    def _determine_microservice_pattern(self, cics_cmd: Dict) -> str:
        """Determine appropriate microservice pattern for CICS command"""
        command_type = cics_cmd.get("command_type", "")
        
        patterns = {
            "WRITEQ_TS": "Caching Service",
            "READQ_TS": "Cache Query Service", 
            "WRITEQ_TD": "Message Publisher Service",
            "READQ_TD": "Message Consumer Service",
            "LINK": "Service Orchestrator",
            "READ": "Data Access Service",
            "WRITE": "Data Persistence Service",
            "SEND": "Response Service",
            "RECEIVE": "Request Handler Service"
        }
        
        return patterns.get(command_type, "Generic Business Service")
    
    def _determine_technology_stack(self, cics_results: Dict) -> Dict[str, Any]:
        """Determine appropriate .NET technology stack"""
        
        programs = cics_results.get("programs", {})
        
        # Analyze CICS commands to determine tech stack
        uses_caching = any(
            cmd.get("command_type", "").startswith("WRITEQ_TS") or cmd.get("command_type", "").startswith("READQ_TS")
            for prog in programs.values()
            for cmd in prog.get("cics_commands", [])
        )
        
        uses_messaging = any(
            cmd.get("command_type", "").startswith("WRITEQ_TD") or cmd.get("command_type", "").startswith("READQ_TD")
            for prog in programs.values()
            for cmd in prog.get("cics_commands", [])
        )
        
        uses_database = any(
            len(prog.get("sql_blocks", [])) > 0
            for prog in programs.values()
        )
        
        return {
            "database_usage": uses_database,
            "messaging_patterns": ["Azure Service Bus", "RabbitMQ"] if uses_messaging else [],
            "caching_patterns": ["Redis", "In-Memory Caching"] if uses_caching else [],
            "security_patterns": ["JWT Authentication", "Role-based Authorization"],
            "recommended_packages": [
                "Microsoft.EntityFrameworkCore",
                "Microsoft.AspNetCore.Authentication.JwtBearer",
                "Swashbuckle.AspNetCore",
                "Serilog.AspNetCore"
            ] + (["StackExchange.Redis"] if uses_caching else []) +
                (["Azure.ServiceBus"] if uses_messaging else [])
        }
    
    def _generate_architecture_recommendations(self, rag_results: Dict, cics_results: Dict) -> List[str]:
        """Generate architecture recommendations"""
        
        recommendations = [
            "Implement Clean Architecture with Domain-Driven Design",
            "Use Entity Framework Core for data persistence",
            "Implement CQRS pattern for read/write separation",
            "Use MediatR for decoupled command/query handling"
        ]
        
        # Add specific recommendations based on analysis
        business_domain = cics_results.get("project_metadata", {}).get("business_domain", "")
        if business_domain == "BANKING":
            recommendations.extend([
                "Implement event sourcing for audit trails",
                "Use decimal type for all financial calculations",
                "Implement strict validation for financial transactions"
            ])
        
        total_programs = len(cics_results.get("programs", {}))
        if total_programs > 5:
            recommendations.append("Consider microservices architecture for better scalability")
        
        return recommendations
    
    def get_conversion_context_for_code(self, code_snippet: str = "") -> str:
        """Get enhanced conversion context for code conversion"""
        
        if not self.conversion_context:
            logger.warning("⚠️ No conversion context available")
            return ""
        
        context_parts = [
            "\n=== ENHANCED CONVERSION CONTEXT FROM COMPREHENSIVE ANALYSIS ===\n"
        ]
        
        # Business Domain Context
        business_domain = self.analysis_results.get("cics_results", {}).get("project_metadata", {}).get("business_domain", "Unknown")
        context_parts.append(f"🏢 Business Domain: {business_domain}")
        
        # Architecture Recommendations
        if self.conversion_context.get("architecture_recommendations"):
            context_parts.append("\n🏗️ Architecture Recommendations:")
            for rec in self.conversion_context["architecture_recommendations"]:
                context_parts.append(f"  • {rec}")
        
        # Business Entities Mapping
        if self.conversion_context.get("business_entities"):
            context_parts.append(f"\n📊 Business Entities ({len(self.conversion_context['business_entities'])}):")
            for entity in self.conversion_context["business_entities"][:5]:  # Show top 5
                context_parts.append(f"  • {entity['cobol_name']} → {entity['dotnet_class']} (Namespace: {entity['namespace']})")
        
        # CICS Patterns to Microservices
        if self.conversion_context.get("cics_patterns"):
            context_parts.append(f"\n⚙️ CICS to Microservices Patterns:")
            unique_patterns = {}
            for pattern in self.conversion_context["cics_patterns"]:
                service_type = pattern.get("microservice_pattern", "Unknown")
                if service_type not in unique_patterns:
                    unique_patterns[service_type] = pattern.get("dotnet_service", "")
            
            for service_type, dotnet_service in unique_patterns.items():
                context_parts.append(f"  • {service_type} → {dotnet_service}")
        
        # Technology Stack
        tech_stack = self.conversion_context.get("technology_stack", {})
        if tech_stack:
            context_parts.append(f"\n🛠️ Recommended Technology Stack:")
            if tech_stack.get("database_usage"):
                context_parts.append("  • Database: Entity Framework Core with SQL Server")
            if tech_stack.get("caching_patterns"):
                context_parts.append(f"  • Caching: {', '.join(tech_stack['caching_patterns'])}")
            if tech_stack.get("messaging_patterns"):
                context_parts.append(f"  • Messaging: {', '.join(tech_stack['messaging_patterns'])}")
        
        # RAG Context if available
        if hasattr(self, 'dual_rag_analyzer') and self.dual_rag_analyzer:
            if code_snippet:
                standards_context = self.dual_rag_analyzer.get_standards_context(code_snippet, k=2)
                project_context = self.dual_rag_analyzer.get_project_context(code_snippet, k=3)
                
                if standards_context and "No standards documents" not in standards_context:
                    context_parts.append(f"\n📚 Standards Context:\n{standards_context[:500]}...")
                
                if project_context and "No project patterns" not in project_context:
                    context_parts.append(f"\n🔗 Project Context:\n{project_context[:500]}...")
        
        context_parts.append("\n=== END ENHANCED CONTEXT ===\n")
        
        full_context = "\n".join(context_parts)
        logger.info(f"✅ Generated enhanced conversion context ({len(full_context)} characters)")
        
        return full_context
    
    def _save_files_to_disk(self):
        """Save project files to upload directory"""
        for filename, content in self.project_files.items():
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
    
    def _save_enhanced_analysis(self):
        """Save enhanced analysis results"""
        try:
            analysis_file = os.path.join(OUTPUT_DIR, "enhanced_analysis.json")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "analysis_results": self.analysis_results,
                    "conversion_context": self.conversion_context,
                    "project_files_count": len(self.project_files),
                    "timestamp": self._get_timestamp()
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Enhanced analysis saved to {analysis_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save enhanced analysis: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of current analysis state"""
        return {
            "project_files_loaded": len(self.project_files),
            "analysis_completed": self.analysis_results is not None,
            "rag_status": {
                "standards_rag_active": self.dual_rag_analyzer.standards_vector_store is not None if self.dual_rag_analyzer else False,
                "project_rag_active": self.dual_rag_analyzer.project_vector_store is not None if self.dual_rag_analyzer else False
            },
            "directories": {
                "uploads": UPLOAD_DIR,
                "cics_analysis": OUTPUT_DIR,
                "rag_storage": API_OUTPUT_DIR,
                "documents": DOCUMENTS_DIR
            },
            "enhanced_features": True,
            "conversion_context_ready": self.conversion_context is not None
        }
    
    def query_rag_system(self, query: str, rag_type: str = "both", k: int = 5) -> Dict[str, Any]:
        """
        Query the RAG system
        
        Args:
            query: Query string
            rag_type: "standards", "project", or "both"
            k: Number of results to return
            
        Returns:
            Query results
        """
        if not self.dual_rag_analyzer:
            return {"error": "RAG system not initialized"}
        
        try:
            results = {}
            
            if rag_type in ["standards", "both"]:
                if self.dual_rag_analyzer.standards_vector_store:
                    results["standards_context"] = self.dual_rag_analyzer.get_standards_context(query, k)
                else:
                    results["standards_context"] = "Standards RAG not available"
            
            if rag_type in ["project", "both"]:
                if self.dual_rag_analyzer.project_vector_store:
                    results["project_context"] = self.dual_rag_analyzer.get_project_context(query, k)
                else:
                    results["project_context"] = "Project RAG not available"
            
            if rag_type == "both":
                results["combined_context"] = self.dual_rag_analyzer.get_combined_conversion_context(query)
            
            return {"status": "success", "results": results}
            
        except Exception as e:
            logger.error(f"❌ RAG query failed: {e}")
            return {"status": "error", "error": str(e)}