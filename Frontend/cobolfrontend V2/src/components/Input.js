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
  enhancedProps,
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
  const [projectId, setProjectId] = useState(null);

  const getSourceJson = () => JSON.stringify(uploadedFiles, null, 2);
  const sourceCodeJson = getSourceJson();

  useEffect(() => {
    setSourceCodeJson(sourceCodeJson);
    console.log("Updated sourceCodeJson:", sourceCodeJson);
  }, [sourceCodeJson, setSourceCodeJson]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("http://localhost:8010/cobo/analysis-status");
        if (res.ok) setAnalysisStatus(await res.json());
      } catch (error) {
        console.error("Analysis status fetch failed:", error);
      }
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
    console.log("Updated fileStats:", fileStats);
  }, [uploadedFiles]);

 // Update the enhancedProps handling in Input.js around line 45:

const handleFileUpload = async (e) => {
  const files = Array.from(e.target.files);
  if (!files.length) {
    setMessage("No files selected");
    setTimeout(() => setMessage(""), 2000);
    return;
  }
  setMessage(`Uploading ${files.length} project files…`);

  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));

  try {
    const res = await fetch("http://localhost:8010/cobo/upload-cobol-files", {
      method: "POST",
      body: fd,
    });
    if (!res.ok) throw new Error(`Upload failed with status: ${res.status}`);
    const data = await res.json();
    if (!data.project_id) throw new Error("No project ID returned from server");

    setProjectId(data.project_id);
    
    // Pass project ID to parent component
    if (enhancedProps?.setProjectId) {
      enhancedProps.setProjectId(data.project_id);
    }

    const read = await Promise.all(
      files.map(
        (file) =>
          new Promise((res, rej) => {
            const r = new FileReader();
            r.onload = (ev) =>
              res({
                fileName: file.name,
                content: ev.target.result,
                type: getType(file.name),
              });
            r.onerror = () => rej(new Error(`Failed to read file: ${file.name}`));
            r.readAsText(file);
          })
      )
    );

    setUploadedFiles(() => {
      const nxt = {};
      read.forEach((f) => (nxt[f.fileName] = f));
      return nxt;
    });

    setActiveFileTab(read[0]?.fileName || null);
    console.log("Uploaded files:", read, "Active file tab:", read[0]?.fileName);
    setMessage(`Uploaded and processed ${read.length} project files`);
    setTimeout(() => setMessage(""), 2000);
  } catch (error) {
    console.error("File upload error:", error);
    setMessage(`Project files upload failed: ${error.message}`);
    setTimeout(() => setMessage(""), 2000);
  } finally {
    e.target.value = "";
  }
};

  const handleStandardsUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length || !projectId) {
      setMessage("Please upload project files first to create a project ID");
      setTimeout(() => setMessage(""), 2000);
      e.target.value = null;
      return;
    }

    setStandardsStatus("uploading");
    setMessage(`Uploading ${files.length} standards documents…`);

    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    fd.append("project_id", projectId);

    try {
      const res = await fetch("http://localhost:8010/cobo/upload-standards-documents", {
        method: "POST",
        body: fd,
      });
      if (!res.ok) throw new Error(`Standards upload failed with status: ${res.status}`);
      setStandardsStatus("success");
      setMessage(`Uploaded and indexed ${files.length} standards documents`);
      setTimeout(() => setMessage(""), 2000);
    } catch (error) {
      console.error("Standards upload error:", error);
      setStandardsStatus("error");
      setMessage(`Standards documents upload failed: ${error.message}`);
      setTimeout(() => setMessage(""), 2000);
    } finally {
      e.target.value = null;
    }
  };

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

  const removeFile = (name) => {
    setUploadedFiles((prev) => {
      const nxt = { ...prev };
      delete nxt[name];
      return nxt;
    });
    const keys = Object.keys(uploadedFiles).filter((k) => k !== name);
    setActiveFileTab(keys[0] || null);
    console.log("Removed file:", name, "New active file tab:", keys[0] || null);
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

  
  return (
    <div className="d-flex flex-column gap-4">
 

      <div className="d-flex gap-2 flex-wrap">
        <label
          className="btn px-3 py-2 text-white"
          style={{ backgroundColor: "#0d9488" }}
        >
          <Upload size={16} className="me-2" />
          Upload Project Files
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
          style={{ backgroundColor: "#0d9488" }}
        >
          <FileArchive size={16} className="me-2" />
          Upload Standards Documents
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.txt"
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
          Standards documents uploaded and indexed
        </div>
      )}
      {standardsStatus === "error" && (
        <div className="alert alert-danger d-flex align-items-center">
          <AlertCircle size={16} className="me-2" />
          Standards documents upload failed
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
          {activeFileTab && uploadedFiles[activeFileTab] ? (
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
          ) : (
            <div className="p-3 text-center text-muted">
              No file selected for preview
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded border text-center py-5">
          <FileText size={48} className="text-secondary mb-3" />
          <div>No project files uploaded yet.</div>
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
            setProjectId(null);
            setStandardsStatus(null);
          }}
        >
          <RefreshCw className="me-2" /> Reset
        </button>
        <button
          className="btn px-4 py-2 text-white"
          style={{ backgroundColor: "#0d9488" }}
          onClick={() => handleGenerateRequirements(setActiveTab, sourceCodeJson, projectId)}
          disabled={isGeneratingRequirements || !hasFiles || !projectId}
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