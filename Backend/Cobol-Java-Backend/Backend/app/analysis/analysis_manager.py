import os
import json
import logging
from typing import Dict, List, Any, Optional
from .dual_rag_analyzer import DualRAGCOBOLAnalyzer
from .cics_analyzer import CICSAnalyzer
from .cics_converter import CICSConverter
from ..config import AZURE_CONFIG, UPLOAD_DIR, OUTPUT_DIR, API_OUTPUT_DIR, DOCUMENTS_DIR

logger = logging.getLogger(__name__)

class AnalysisManager:
    """
    Central manager for all COBOL analysis including RAG and CICS
    """
    
    def __init__(self):
        self.dual_rag_analyzer = None
        self.cics_analyzer = None
        self.cics_converter = None
        self.project_files = {}
        self.analysis_results = None
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
            
            logger.info("✅ All analysis components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize analysis components: {e}")
            raise
    
    def process_uploaded_files(self, files_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Process uploaded files with RAG and CICS analysis
        
        Args:
            files_data: Dictionary of filename -> content
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"🔍 Processing {len(files_data)} uploaded files")
        
        # Store files
        self.project_files = files_data
        self._save_files_to_disk()
        
        # Run comprehensive analysis
        results = {
            "files_processed": len(files_data),
            "rag_analysis": None,
            "cics_analysis": None,
            "status": "success"
        }
        
        try:
            # Run RAG analysis
            logger.info("🔗 Running RAG analysis...")
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
            
            # Run CICS analysis
            logger.info("⚙️ Running CICS analysis...")
            cics_results = self.cics_analyzer.analyze_project()
            results["cics_analysis"] = {
                "total_programs": len(cics_results.get("programs", {})),
                "total_copybooks": len(cics_results.get("copybooks", {})),
                "business_domain": cics_results.get("project_metadata", {}).get("business_domain", "Unknown"),
                "cics_commands": sum(len(p.get("cics_commands", [])) for p in cics_results.get("programs", {}).values())
            }
            
            # Store analysis results
            self.analysis_results = {
                "rag_results": rag_results,
                "cics_results": cics_results
            }
            
            logger.info("✅ Analysis completed successfully")
            
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
    
    def _save_files_to_disk(self):
        """Save project files to upload directory"""
        for filename, content in self.project_files.items():
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
    
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
            }
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