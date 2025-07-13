from flask import Blueprint, request, jsonify, current_app
from ..config import logger
from ..utils.cobol_analyzer import create_cobol_json
from ..utils.rag_indexer import index_files_for_rag, index_standards_document, load_vector_store, query_vector_store
from pathlib import Path
import uuid
import json

bp = Blueprint('cobol_analyzer', __name__, url_prefix='/cobo')

@bp.route("/upload-cobol-files", methods=["POST"])
def upload_cobol_files():
    """Upload COBOL files for a project."""
    try:
        if 'files' not in request.files:
            return jsonify({"error": "No files provided"}), 400

        files = request.files.getlist('files')
        if not files:
            return jsonify({"error": "No files selected"}), 400

        project_id = str(uuid.uuid4())
        project_dir = Path(current_app.config["UPLOAD_DIR"]) / project_id
        project_dir.mkdir(exist_ok=True, parents=True)
        uploaded_files = []

        for file in files:
            if file.filename and file.filename.lower().endswith((".cbl", ".cpy", ".jcl")):
                file_path = project_dir / file.filename
                try:
                    file.save(file_path)
                    logger.info(f"Uploaded COBOL file: {file.filename}")
                    uploaded_files.append(file.filename)
                except Exception as e:
                    logger.error(f"Error saving file {file.filename}: {e}")
            else:
                logger.warning(f"Skipping invalid file: {file.filename}")

        return jsonify({
            "project_id": project_id,
            "status": "Files uploaded successfully",
            "uploaded_files": uploaded_files
        })
    except Exception as e:
        logger.error(f"Error uploading COBOL files: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/upload-standards-documents", methods=["POST"])
def upload_standards_documents():
    """Upload standards documents for RAG indexing."""
    try:
        if 'files' not in request.files:
            return jsonify({"error": "No files provided"}), 400

        project_id = request.form.get("project_id")
        if not project_id:
            return jsonify({"error": "Project ID is required"}), 400

        files = request.files.getlist('files')
        if not files:
            return jsonify({"error": "No files selected"}), 400

        project_dir = Path(current_app.config["output_dir"]) / "standards-rag" / project_id
        project_dir.mkdir(exist_ok=True, parents=True)
        uploaded_files = []

        for file in files:
            if file.filename and file.filename.lower().endswith((".pdf", ".doc", ".docx", ".txt")):
                file_path = project_dir / file.filename
                try:
                    file.save(file_path)
                    logger.info(f"Uploaded standards document: {file.filename}")
                    uploaded_files.append(file.filename)
                    index_standards_document(project_id, file_path)
                    logger.info(f"Indexed standards document: {file.filename}")
                except Exception as e:
                    logger.error(f"Error processing standards document {file.filename}: {e}")
            else:
                logger.warning(f"Skipping invalid standards document: {file.filename}")

        return jsonify({
            "project_id": project_id,
            "status": "Standards documents uploaded and indexed successfully",
            "uploaded_files": uploaded_files,
            "output_path": str(project_dir / "faiss_index")
        })
    except Exception as e:
        logger.error(f"Error uploading standards documents: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/analyze-cobol", methods=["POST"])
def analyze_cobol():
    """Analyze uploaded COBOL files and generate JSON summary."""
    try:
        data = request.json
        if not data or "project_id" not in data:
            return jsonify({"error": "Project ID is required"}), 400

        project_id = data["project_id"]
        cobol_json = create_cobol_json(project_id)
        current_app.comprehensive_analysis_data["cobol_analysis"] = cobol_json  # Share with analysis.py
        return jsonify({
            "project_id": project_id,
            "status": "Analysis completed",
            "output_path": str(Path(current_app.config["output_dir"]) / "analysis" / project_id / "cobol_analysis.json")
        })
    except Exception as e:
        logger.error(f"Error during COBOL analysis: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/index-rag", methods=["POST"])
def index_rag():
    """Index COBOL analysis JSON for RAG."""
    try:
        data = request.json
        if not data or "project_id" not in data:
            return jsonify({"error": "Project ID is required"}), 400

        project_id = data["project_id"]
        cobol_json_path = Path(current_app.config["output_dir"]) / "analysis" / project_id / "cobol_analysis.json"
        if not cobol_json_path.exists():
            return jsonify({"error": "COBOL analysis JSON not found. Run analysis first."}), 404

        with open(cobol_json_path, "r") as f:
            cobol_json = json.load(f)

        index_files_for_rag(project_id, cobol_json)
        return jsonify({
            "project_id": project_id,
            "status": "Indexing completed",
            "output_path": str(Path(current_app.config["output_dir"]) / "rag" / project_id / "faiss_index")
        })
    except Exception as e:
        logger.error(f"Error during RAG indexing: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/query-rag", methods=["POST"])
def query_rag():
    """Query the RAG vector store."""
    try:
        data = request.json
        if not data or "project_id" not in data or "query" not in data:
            return jsonify({"error": "Project ID and query are required"}), 400

        project_id = data["project_id"]
        query = data["query"]
        k = data.get("k", 3)

        vector_store = load_vector_store(project_id)
        if not vector_store:
            return jsonify({"error": "Vector store not found. Run indexing first."}), 404

        results = query_vector_store(vector_store, query, k)
        formatted_results = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": getattr(doc, 'score', 0.0) if hasattr(doc, 'score') else 0.0
            } for doc in results
        ]

        return jsonify({
            "project_id": project_id,
            "results": formatted_results
        })
    except Exception as e:
        logger.error(f"Error during RAG query: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "message": "COBOL Analyzer is running"})