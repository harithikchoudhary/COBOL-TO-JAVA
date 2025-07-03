import { useState, useEffect } from "react";
import {
  ClipboardList,
  Copy,
  Download,
  FileCode,
  Plus,
  Edit,
  Trash2,
  CheckCircle,
  Activity,
  Database,
  Layers,
  AlertCircle,
  Info,
  Zap
} from "lucide-react";

export default function Requirements({
  businessRequirements,
  technicalRequirements,
  technicalRequirementsList,
  setTechnicalRequirementsList,
  activeRequirementsTab,
  setActiveRequirementsTab,
  editingRequirementIndex,
  setEditingRequirementIndex,
  editingRequirementText,
  setEditingRequirementText,
  handleCopyRequirements,
  handleDownloadRequirements,
  copyStatus,
  setActiveTab,
  handleConvert,
  isLoading,
  targetLanguage,
}) {
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      setLoading(true);
      try {
        const res = await fetch("/cobo/analysis-status");
        if (res.ok) setAnalysisStatus(await res.json());
      } catch {}
      setLoading(false);
    };
    fetchStatus();
    let id;
    if (isLoading) id = setInterval(fetchStatus, 10000);
    return () => clearInterval(id);
  }, [isLoading]);

  const addReq = () => {
    setTechnicalRequirementsList([
      ...technicalRequirementsList,
      { text: "New requirement" },
    ]);
    setEditingRequirementIndex(technicalRequirementsList.length);
    setEditingRequirementText("New requirement");
  };
  const editReq = (i) => {
    setEditingRequirementIndex(i);
    setEditingRequirementText(technicalRequirementsList[i].text);
  };
  const saveReq = () => {
    const arr = [...technicalRequirementsList];
    arr[editingRequirementIndex] = { text: editingRequirementText };
    setTechnicalRequirementsList(arr);
    setEditingRequirementIndex(null);
    setEditingRequirementText("");
  };
  const delReq = (i) => {
    setTechnicalRequirementsList(
      technicalRequirementsList.filter((_, idx) => idx !== i)
    );
  };

  const AnalysisCard = () =>
    analysisStatus ? (
      <div className="bg-light rounded border p-3 mb-3">
        <div className="d-flex justify-content-between align-items-center">
          <h6 className="text-primary mb-0">
            <Activity size={16} className="me-2" />
            Analysis Status
          </h6>
          <button
            className="btn btn-sm btn-outline-primary"
            onClick={() => setShowDetails(!showDetails)}
            disabled={loading}
          >
            {loading
              ? <div className="spinner-border spinner-border-sm"></div>
              : showDetails ? "Hide" : "Show"} Details
          </button>
        </div>
        {showDetails && (
          <div className="mt-2">
            <div>
              <small className="text-muted">Files Analyzed:</small>{" "}
              <strong>{analysisStatus.project_files_loaded}</strong>
            </div>
            <div>
              <small className="text-muted">Analysis Done:</small>{" "}
              <strong>
                {analysisStatus.analysis_completed ? "Yes" : "No"}
              </strong>
            </div>
            <div>
              <small className="text-muted">Standards RAG:</small>{" "}
              <strong>
                {analysisStatus.rag_status?.standards_rag_active
                  ? "Active"
                  : "Inactive"}
              </strong>
            </div>
            <div>
              <small className="text-muted">Project RAG:</small>{" "}
              <strong>
                {analysisStatus.rag_status?.project_rag_active
                  ? "Active"
                  : "Inactive"}
              </strong>
            </div>
            {analysisStatus.conversion_context_ready && (
              <div className="mt-2">
                <small className="text-success">
                  <Zap size={14} className="me-1" />
                  Conversion context ready
                </small>
              </div>
            )}
          </div>
        )}
      </div>
    ) : null;

  const renderEditModal = () =>
    editingRequirementIndex === null
      ? null
      : (
        <div
          className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
          style={{ backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1050 }}
        >
          <div className="bg-white p-4 rounded shadow w-75" style={{ maxWidth: "600px" }}>
            <h5>Edit Requirement</h5>
            <textarea
              className="form-control my-3"
              style={{ height: "120px" }}
              value={editingRequirementText}
              onChange={e => setEditingRequirementText(e.target.value)}
            />
            <div className="d-flex justify-content-end">
              <button
                className="btn btn-secondary me-2"
                onClick={() => setEditingRequirementIndex(null)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary text-white"
                onClick={saveReq}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      );

  return (
    <div className="d-flex flex-column gap-4">
      <AnalysisCard />

      <div className="d-flex justify-content-between align-items-center">
        <div className="d-flex gap-2">
          <button
            className="btn px-4 py-2"
            style={{
              border: "1px solid #000",
              backgroundColor: activeRequirementsTab === "business" ? "#0d9488" : "#fff",
              color: activeRequirementsTab === "business" ? "#fff" : "#000"
            }}
            onClick={() => setActiveRequirementsTab("business")}
          >
            <ClipboardList size={16} className="me-2" />
            Business Requirements
          </button>
          <button
            className="btn px-4 py-2"
            style={{
              border: "1px solid #000",
              backgroundColor: activeRequirementsTab === "technical" ? "#0d9488" : "#fff",
              color: activeRequirementsTab === "technical" ? "#fff" : "#000"
            }}
            onClick={() => setActiveRequirementsTab("technical")}
          >
            <ClipboardList size={16} className="me-2" />
            Technical Requirements
          </button>
        </div>
        <div className="d-flex gap-2">
          <button
            className="btn px-4 py-2 d-flex align-items-center"
            style={{
              backgroundColor: copyStatus ? "#0d9488" : "#6c757d",
              color: "#fff"
            }}
            disabled={!businessRequirements && !technicalRequirements}
            onClick={handleCopyRequirements}
          >
            {copyStatus
              ? (
                <>
                  <CheckCircle size={16} className="me-2" />
                  Copied
                </>
              )
              : (
                <>
                  <Copy size={16} className="me-2" />
                  Copy
                </>
              )}
          </button>
          <button
            className="btn btn-secondary px-4 py-2 d-flex align-items-center"
            disabled={!businessRequirements && !technicalRequirements}
            onClick={handleDownloadRequirements}
          >
            <Download size={16} className="me-2" />
            Download
          </button>
        </div>
      </div>

      <div className="bg-white rounded border p-3" style={{ height: "28rem", overflowY: "auto" }}>
        {activeRequirementsTab === "business" ? (
          businessRequirements
            ? businessRequirements.split("\n").map((line, i) => (
              <p key={i} style={{ margin: "0.5rem 0" }}>{line}</p>
            ))
            : (
              <div className="text-center text-secondary mt-5">
                <ClipboardList size={48} className="mb-3" />
                <p>No business requirements yet.</p>
              </div>
            )
        ) : technicalRequirementsList.length ? (
          technicalRequirementsList.map((req, i) => (
            <div key={i} className="d-flex align-items-center mb-2">
              <span style={{ color: "#0d9488" }}>•</span>
              <p className="flex-grow-1 mb-0 ms-2">{req.text}</p>
              <button className="btn btn-sm btn-link" onClick={() => editReq(i)}>
                <Edit size={16} />
              </button>
              <button className="btn btn-sm btn-link text-danger" onClick={() => delReq(i)}>
                <Trash2 size={16} />
              </button>
            </div>
          ))
        ) : (
          <div className="text-center text-secondary mt-5">
            <AlertCircle size={48} className="mb-3" />
            <p>No technical requirements yet.</p>
          </div>
        )}
        {activeRequirementsTab === "technical" && (
          <button
            className="btn px-3 py-1 text-white"
            style={{ backgroundColor: "#0d9488" }}
            onClick={addReq}
          >
            <Plus size={16} className="me-1" />
            Add Requirement
          </button>
        )}
      </div>

      <div className="d-flex justify-content-center gap-4">
        <button
          className="btn btn-outline-dark px-4 py-2"
          onClick={() => setActiveTab("input")}
        >
          <FileCode size={18} className="me-2" />
          Back to Code
        </button>
        <button
          className="btn px-5 py-2 text-white"
          style={{ backgroundColor: "#0d9488" }}
          onClick={() => handleConvert(setActiveTab)}
          disabled={isLoading}
        >
          {isLoading
            ? (
              <div className="spinner-border spinner-border-sm me-2" role="status"></div>
            )
            : (
              <>
                <Layers size={16} className="me-2" />
                Convert to {targetLanguage}
              </>
            )}
        </button>
      </div>

      {renderEditModal()}
    </div>
  );
}