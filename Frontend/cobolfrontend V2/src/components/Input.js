import { useState, useEffect } from "react";
import {
  Upload,
  FileArchive,
  ClipboardList,
  RefreshCw,
  X,
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
  const [showDropdownTarget, setShowDropdownTarget] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState({});
  const [activeFileTab, setActiveFileTab] = useState(null);
  const [standardsUploadStatus, setStandardsUploadStatus] = useState(null);

  // Build JSON payload for code‐analysis endpoints
  const getSourceCodeAsJson = () => JSON.stringify(uploadedFiles, null, 2);
  const sourceCodeJson = getSourceCodeAsJson();
  useEffect(() => {
    setSourceCodeJson(sourceCodeJson);
  }, [sourceCodeJson, setSourceCodeJson]);

  // COBOL/JCL file upload
  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);
    const getFileType = (fileName) => {
      const ext = fileName.split(".").pop().toLowerCase();
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

    const readFiles = await Promise.all(
      files.map(
        (file) =>
          new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) =>
              resolve({
                fileName: file.name,
                content: e.target.result,
                size: file.size,
                type: getFileType(file.name),
                uploadDate: new Date().toISOString(),
              });
            reader.readAsText(file);
          })
      )
    );

    setUploadedFiles((prev) => {
      const updated = { ...prev };
      readFiles.forEach((f) => {
        updated[f.fileName] = f;
      });
      return updated;
    });

    if (!activeFileTab && readFiles.length) {
      setActiveFileTab(readFiles[0].fileName);
    }
    event.target.value = "";
  };

  // Standards docs upload
  const handleStandardsUpload = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));

    try {
      const resp = await fetch("http://localhost:8010/cobo/upload-standards", {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) throw new Error(`Status ${resp.status}`);
      await resp.json();
      setStandardsUploadStatus("success");
    } catch (err) {
      console.error("Standards upload error:", err);
      setStandardsUploadStatus("error");
    } finally {
      event.target.value = null;
      setTimeout(() => setStandardsUploadStatus(null), 3000);
    }
  };

  const removeFile = (fileName) => {
    setUploadedFiles((prev) => {
      const nxt = { ...prev };
      delete nxt[fileName];
      return nxt;
    });
    const remaining = Object.keys(uploadedFiles).filter((n) => n !== fileName);
    setActiveFileTab(remaining[0] || null);
  };

  const getFileTypeIcon = (type) =>
    type === "COBOL"
      ? "📄"
      : type === "JCL"
      ? "⚙️"
      : type === "Copybook"
      ? "📋"
      : "📄";

  const hasValidFiles = Object.keys(uploadedFiles).length > 0;

  return (
    <div className="d-flex flex-column gap-4">
      {/* Upload Buttons */}
      <div className="d-flex align-items-center gap-2 flex-wrap">
        <label
          className="btn rounded px-3 py-2 text-white"
          style={{ backgroundColor: "#0f766e" }}
        >
          <Upload size={16} className="me-2" />
          Upload Files
          <input
            type="file"
            className="d-none"
            onChange={handleFileUpload}
            accept=".txt,.cob,.cobol,.cbl,.jcl,.cpy,.copybook,.bms"
            multiple
          />
        </label>

        <label
          className="btn rounded px-3 py-2 text-white"
          style={{ backgroundColor: "#634d03" }}
        >
          <FileArchive size={16} className="me-2" />
          Upload Standards
          <input
            type="file"
            className="d-none"
            onChange={handleStandardsUpload}
            accept=".pdf,.docx,.pptx,.txt"
            multiple
          />
        </label>

        {/* Target‐language dropdown */}
        <div className="dropdown position-relative">
          <button
            className="btn btn-outline-dark d-flex align-items-center px-3 py-2"
            onClick={() => setShowDropdownTarget((s) => !s)}
          >
            <span className="me-2">
              {targetLanguages.find((l) => l.name === targetLanguage)?.icon}
            </span>
            {targetLanguage} ▼
          </button>
          {showDropdownTarget && (
            <div
              className="dropdown-menu show border border-dark"
              style={{ zIndex: 10 }}
            >
              {targetLanguages.map((lang) => (
                <button
                  key={lang.name}
                  className="dropdown-item"
                  onClick={() => {
                    setTargetLanguage(lang.name);
                    setShowDropdownTarget(false);
                  }}
                >
                  {lang.icon} {lang.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Standards upload feedback */}
      {standardsUploadStatus === "success" && (
        <div className="alert alert-success py-1">Standards uploaded.</div>
      )}
      {standardsUploadStatus === "error" && (
        <div className="alert alert-danger py-1">
          Standards upload failed.
        </div>
      )}

      {/* File Tabs & Content */}
      {hasValidFiles && (
        <div className="bg-white rounded border">
          <div className="d-flex bg-light border-bottom overflow-auto">
            {Object.entries(uploadedFiles).map(([name, f]) => (
              <div
                key={name}
                className={
                  "d-flex align-items-center px-3 py-2 border-end cursor-pointer " +
                  (activeFileTab === name ? "bg-white" : "bg-light")
                }
                onClick={() => setActiveFileTab(name)}
              >
                <span className="me-2">{getFileTypeIcon(f.type)}</span>
                <div className="text-truncate" style={{ maxWidth: "80px" }}>
                  {name}
                </div>
                <X
                  size={12}
                  className="ms-2 text-danger"
                  onClick={(e) => {
                    e.stopPropagation();
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
      )}

      {/* Placeholder when no files */}
      {!hasValidFiles && (
        <div className="bg-white rounded border text-center py-5">
          <Upload size={48} className="text-secondary mb-3" />
          <div>No files uploaded yet.</div>
        </div>
      )}

      {/* Actions */}
      <div className="d-flex justify-content-center gap-3">
        <button
          className="btn btn-outline-dark px-3 py-2"
          onClick={() => {
            handleReset();
            setUploadedFiles({});
            setActiveFileTab(null);
          }}
        >
          <RefreshCw className="me-2" /> Reset
        </button>

        <button
          className="btn text-white px-4 py-2"
          style={{ backgroundColor: "#0d9488" }}
          onClick={() => handleGenerateRequirements(setActiveTab, sourceCodeJson)}
          disabled={isGeneratingRequirements || !hasValidFiles}
        >
          {isGeneratingRequirements ? "Analyzing..." : <ClipboardList className="me-2" />}
          Generate Requirements
        </button>
      </div>
    </div>
  );
}