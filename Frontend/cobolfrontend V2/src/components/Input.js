import { useState, useEffect } from "react";
import {
  Upload,
  FileArchive,
  ClipboardList,
  FileText,
  RefreshCw,
  X,
  CheckCircle,
  AlertCircle,
  Activity,
  Database,
  Layers,
  Info
} from "lucide-react";

export default function Input({
  targetLanguage,
  setTargetLanguage,
  targetLanguages,
  handleReset,
  handleGenerateRequirements,
  isGeneratingRequirements,
  setActiveTab,
  setSourceCodeJson,
}) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState({});
  const [activeFileTab, setActiveFileTab] = useState(null);
  const [standardsStatus, setStandardsStatus] = useState(null);
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const [message, setMessage] = useState("");
  const [fileStats, setFileStats] = useState({
    cobol: 0,
    jcl: 0,
    copybooks: 0,
    total: 0,
  });

  const getSourceJson = () => JSON.stringify(uploadedFiles, null, 2);
  const sourceCodeJson = getSourceJson();

  useEffect(() => {
    setSourceCodeJson(sourceCodeJson);
  }, [sourceCodeJson, setSourceCodeJson]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("/cobo/analysis-status");
        if (res.ok) setAnalysisStatus(await res.json());
      } catch {}
    };
    fetchStatus();
    let id;
    if (isGeneratingRequirements) {
      id = setInterval(fetchStatus, 3000);
    }
    return () => clearInterval(id);
  }, [isGeneratingRequirements]);

  useEffect(() => {
    const files = Object.values(uploadedFiles);
    setFileStats({
      cobol: files.filter((f) => f.type === "COBOL").length,
      jcl: files.filter((f) => f.type === "JCL").length,
      copybooks: files.filter((f) => f.type === "Copybook").length,
      total: files.length,
    });
  }, [uploadedFiles]);

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    setMessage(`Processing ${files.length} files…`);
    const getType = (name) => {
      const ext = name.split(".").pop().toLowerCase();
      const map = {
        cob: "COBOL",
        cobol: "COBOL",
        cbl: "COBOL",
        jcl: "JCL",
        cpy: "Copybook",
        copybook: "Copybook",
        bms: "BMS",
        txt: "Text",
      };
      return map[ext] || "Unknown";
    };
    const read = await Promise.all(
      files.map(
        (file) =>
          new Promise((res) => {
            const r = new FileReader();
            r.onload = (ev) =>
              res({
                fileName: file.name,
                content: ev.target.result,
                type: getType(file.name),
              });
            r.readAsText(file);
          })
      )
    );
    setUploadedFiles((prev) => {
      const nxt = { ...prev };
      read.forEach((f) => (nxt[f.fileName] = f));
      return nxt;
    });
    if (!activeFileTab && read.length) setActiveFileTab(read[0].fileName);
    setMessage(`Processed ${read.length} files`);
    setTimeout(() => setMessage(""), 2000);
    e.target.value = "";
  };

  const handleStandardsUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setStandardsStatus("uploading");
    setMessage(`Uploading ${files.length} docs…`);
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    try {
      const res = await fetch("http://localhost:8010/cobo/upload-standards", {
      method: "POST",
      body: fd,
    });
      if (!res.ok) throw new Error(res.status);
      setStandardsStatus("success");
      setMessage(`Uploaded ${files.length} docs`);
      setTimeout(() => setMessage(""), 2000);
    } catch {
      setStandardsStatus("error");
      setMessage("Standards upload failed");
      setTimeout(() => setMessage(""), 2000);
    } finally {
      e.target.value = null;
    }
  };

  const removeFile = (name) => {
    setUploadedFiles((prev) => {
      const nxt = { ...prev };
      delete nxt[name];
      return nxt;
    });
    const keys = Object.keys(uploadedFiles).filter((k) => k !== name);
    setActiveFileTab(keys[0] || null);
  };

  const fileIcon = (type) =>
    type === "COBOL"
      ? "📄"
      : type === "JCL"
      ? "⚙️"
      : type === "Copybook"
      ? "📋"
      : "📄";

  const hasFiles = Object.keys(uploadedFiles).length > 0;

  const AnalysisCard = () =>
    analysisStatus ? (
      <div className="bg-light rounded border p-3 mb-3">
        <h6 className="text-primary mb-2">
          <Activity size={16} className="me-2" />
          Analysis Status
        </h6>
        <div>
          <small className="text-muted">Files Loaded:</small>{" "}
          <strong>{analysisStatus.project_files_loaded}</strong>
        </div>
        <div>
          <small className="text-muted">Context Ready:</small>{" "}
          <strong>
            {analysisStatus.conversion_context_ready ? "Yes" : "No"}
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
      </div>
    ) : null;

  return (
    <div className="d-flex flex-column gap-4">
      <AnalysisCard />

      <div className="d-flex gap-2 flex-wrap">
        <label
          className="btn px-3 py-2 text-white"
          style={{ backgroundColor: "#0d9488" }}
        >
          <Upload size={16} className="me-2" />
          Upload Files
          <input
            type="file"
            multiple
            accept=".cob,.cbl,.cobol,.jcl,.cpy,.copybook,.bms,.txt"
            className="d-none"
            onChange={handleFileUpload}
          />
        </label>

        <label
          className="btn px-3 py-2 text-white"
          style={{ backgroundColor: "#634d03" }}
        >
          <FileArchive size={16} className="me-2" />
          Upload Standards
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.pptx,.txt"
            className="d-none"
            onChange={handleStandardsUpload}
          />
        </label>

        <div className="dropdown">
          <button
            className="btn btn-outline-dark px-3 py-2"
            onClick={() => setShowDropdown(!showDropdown)}
          >
            {targetLanguages.find((l) => l.name === targetLanguage)?.icon}{" "}
            {targetLanguage} ▼
          </button>
          {showDropdown && (
            <div className="dropdown-menu show">
              {targetLanguages.map((lang) => (
                <button
                  key={lang.name}
                  className="dropdown-item"
                  onClick={() => {
                    setTargetLanguage(lang.name);
                    setShowDropdown(false);
                  }}
                >
                  {lang.icon} {lang.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {message && (
        <div className="alert alert-info d-flex align-items-center">
          <Activity size={16} className="me-2" />
          {message}
        </div>
      )}
      {standardsStatus === "success" && (
        <div className="alert alert-success d-flex align-items-center">
          <CheckCircle size={16} className="me-2" />
          Standards uploaded
        </div>
      )}
      {standardsStatus === "error" && (
        <div className="alert alert-danger d-flex align-items-center">
          <AlertCircle size={16} className="me-2" />
          Standards upload failed
        </div>
      )}

      {hasFiles ? (
        <div className="bg-white rounded border">
          <div className="d-flex bg-light border-bottom overflow-auto">
            {Object.entries(uploadedFiles).map(([name, f]) => (
              <div
                key={name}
                className={`px-3 py-2 border-end ${
                  activeFileTab === name ? "bg-white" : "bg-light"
                }`}
                onClick={() => setActiveFileTab(name)}
                style={{ cursor: "pointer" }}
              >
                <span className="me-2">{fileIcon(f.type)}</span>
                <span className="text-truncate" style={{ maxWidth: "80px" }}>
                  {name}
                </span>
                <X
                  size={12}
                  className="ms-2 text-danger"
                  onClick={(ev) => {
                    ev.stopPropagation();
                    removeFile(name);
                  }}
                />
              </div>
            ))}
          </div>
          {activeFileTab && (
            <pre
              className="p-3 mb-0"
              style={{
                maxHeight: "400px",
                overflow: "auto",
                backgroundColor: "#f8f9fa",
                fontFamily: 'Consolas, "Courier New", monospace',
              }}
            >
              {uploadedFiles[activeFileTab].content}
            </pre>
          )}
        </div>
      ) : (
        <div className="bg-white rounded border text-center py-5">
          <FileText size={48} className="text-secondary mb-3" />
          <div>No files uploaded yet.</div>
        </div>
      )}

      <div className="d-flex justify-content-center gap-3">
        <button
          className="btn btn-outline-dark px-3 py-2"
          onClick={() => {
            handleReset();
            setUploadedFiles({});
            setActiveFileTab(null);
            setAnalysisStatus(null);
          }}
        >
          <RefreshCw className="me-2" /> Reset
        </button>
        <button
          className="btn px-4 py-2 text-white"
          style={{ backgroundColor: "#0d9488" }}
          onClick={() => handleGenerateRequirements(setActiveTab, sourceCodeJson)}
          disabled={isGeneratingRequirements || !hasFiles}
        >
          {isGeneratingRequirements ? (
            <>
              <div
                className="spinner-border spinner-border-sm me-2"
                role="status"
              ></div>
              Analyzing…
            </>
          ) : (
            <>
              <Database size={16} className="me-2" />
              Generate Requirements & Analyze
            </>
          )}
        </button>
      </div>
    </div>
  );
}