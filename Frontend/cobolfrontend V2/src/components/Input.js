import { useState, useEffect } from "react";
import {
  Upload,
  ClipboardList,
  RefreshCw,
  FileText,
  X,
  Eye,
  Code,
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
  const [viewingFile, setViewingFile] = useState(null);

  // Store JSON data for backend
  const getSourceCodeAsJson = () => {
    return JSON.stringify(uploadedFiles, null, 2);
  };
  const sourceCodeJson = getSourceCodeAsJson();
  useEffect(() => {
    setSourceCodeJson(sourceCodeJson);
  }, [sourceCodeJson, setSourceCodeJson]);

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);

    const readFiles = await Promise.all(
      files.map(
        (file) =>
          new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
              resolve({
                fileName: file.name,
                content: e.target.result,
              });
            };
            reader.readAsText(file);
          })
      )
    );

    setUploadedFiles((prev) => {
      const updated = { ...prev };
      readFiles.forEach((fileData) => {
        updated[fileData.fileName] = fileData;
      });
      return updated;
    });

    // Clear input
    event.target.value = "";
  };

  const removeFile = (fileName) => {
    setUploadedFiles((prev) => {
      const newFiles = { ...prev };
      delete newFiles[fileName];
      return newFiles;
    });
    // Close viewer if the file being viewed is removed
    if (viewingFile && viewingFile.fileName === fileName) {
      setViewingFile(null);
    }
  };

  const viewFile = (fileName) => {
    setViewingFile(uploadedFiles[fileName]);
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const hasValidFiles = Object.keys(uploadedFiles).length > 0;

  return (
    <div className="d-flex flex-column gap-4">
      {/* File Upload Section */}
      <div className="d-flex align-items-center gap-2 flex-wrap">
        <label
          className="d-flex align-items-center btn rounded px-4 py-2 cursor-pointer"
          style={{ backgroundColor: "#0f766e", color: "white" }}
        >
          <Upload size={18} className="me-2" />
          <span>Upload Files</span>
          <input
            type="file"
            className="d-none"
            onChange={handleFileUpload}
            accept=".txt,.cob,.cobol,.cbl,.jcl,.cpy,.copybook"
            multiple
          />
        </label>

        <div className="dropdown position-relative">
          <button
            className="d-flex align-items-center gap-2 px-4 py-2 btn btn-outline-dark rounded"
            onClick={() => setShowDropdownTarget(!showDropdownTarget)}
          >
            <span
              className="d-flex align-items-center justify-content-center text-primary"
              style={{ width: "1.25rem", height: "1.25rem" }}
            >
              {targetLanguages.find((lang) => lang.name === targetLanguage)
                ?.icon || ""}
            </span>
            <span className="fw-medium">{targetLanguage}</span>
            <span className="ms-2">▼</span>
          </button>

          {showDropdownTarget && (
            <div
              className="position-absolute mt-1 dropdown-menu show border border-dark"
              style={{ width: "12rem", zIndex: 10 }}
            >
              {targetLanguages.map((lang) => (
                <button
                  key={lang.name}
                  className="dropdown-item px-3 py-2"
                  onClick={() => {
                    setTargetLanguage(lang.name);
                    setShowDropdownTarget(false);
                  }}
                >
                  <span
                    className="d-inline-block text-center me-2"
                    style={{ width: "1.25rem" }}
                  >
                    {lang.icon}
                  </span>
                  {lang.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Uploaded Files Display */}
      {hasValidFiles && (
        <div className="bg-light rounded border p-3">
          <h6 className="mb-3 text-dark">
            Uploaded Files ({Object.keys(uploadedFiles).length})
          </h6>
          <div className="d-flex flex-wrap gap-2 mb-3">
            {Object.entries(uploadedFiles).map(([fileName, fileData]) => (
              <div
                key={fileName}
                className="d-flex align-items-center px-3 py-2 rounded border bg-white position-relative"
              >
                <FileText size={16} className="me-2" />
                <div className="d-flex flex-column me-2">
                  <span className="fw-medium">{fileName}</span>
                  <small className="text-muted">
                    {formatFileSize(fileData.size)}
                  </small>
                </div>
                <span className="badge bg-secondary me-2">{fileData.type}</span>

                <div className="d-flex gap-1">
                  <button
                    className="btn btn-sm p-1"
                    onClick={(e) => {
                      e.stopPropagation();
                      viewFile(fileName);
                    }}
                    title="View file content"
                    style={{ width: "24px", height: "24px" }}
                  >
                    <Eye size={14} className="text-primary" />
                  </button>
                  <button
                    className="btn btn-sm p-1"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(fileName);
                    }}
                    title="Remove file"
                    style={{ width: "24px", height: "24px" }}
                  >
                    <X size={14} className="text-danger" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* File Viewer Modal */}
      {viewingFile && (
        <div
          className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
          style={{
            backgroundColor: "rgba(0, 0, 0, 0.7)",
            zIndex: 1050,
          }}
          onClick={() => setViewingFile(null)}
        >
          <div
            className="bg-white rounded shadow-lg p-0"
            style={{
              width: "90%",
              maxWidth: "800px",
              height: "80%",
              display: "flex",
              flexDirection: "column",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="d-flex justify-content-between align-items-center p-3 border-bottom">
              <div className="d-flex align-items-center gap-2">
                <Code size={20} className="text-primary" />
                <div>
                  <h6 className="mb-0">{viewingFile.fileName}</h6>
                  <small className="text-muted">
                    {viewingFile.type} • {formatFileSize(viewingFile.size)}
                  </small>
                </div>
              </div>
              <button
                className="btn btn-sm p-2"
                onClick={() => setViewingFile(null)}
                style={{ width: "32px", height: "32px" }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-grow-1 p-3 overflow-hidden">
              <div
                className="h-100 w-100 overflow-auto"
                style={{
                  backgroundColor: "#f8f9fa",
                  border: "1px solid #dee2e6",
                  borderRadius: "4px",
                }}
              >
                <pre
                  className="p-3 mb-0 text-sm"
                  style={{
                    fontFamily: 'Consolas, "Courier New", monospace',
                    fontSize: "14px",
                    lineHeight: "1.4",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {viewingFile.content}
                </pre>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-3 border-top bg-light">
              <div className="d-flex justify-content-between align-items-center">
                <small className="text-muted">
                  Uploaded: {new Date(viewingFile.uploadDate).toLocaleString()}
                </small>
                <button
                  className="btn btn-secondary"
                  onClick={() => setViewingFile(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Section */}
      {!hasValidFiles && (
        <div
          className="bg-white rounded border border-dark d-flex flex-column align-items-center justify-content-center"
          style={{ height: "24rem" }}
        >
          <div className="text-center">
            <Upload size={64} className="text-secondary mb-3" />
            <h5 className="text-dark mb-2">Upload Your Files</h5>
            <p className="text-muted mb-4">
              Upload COBOL, JCL, Copybook, or other related files
            </p>
            <label
              className="btn btn-lg px-4 py-2 cursor-pointer"
              style={{ backgroundColor: "#0f766e", color: "white" }}
            >
              <Upload size={20} className="me-2" />
              Choose Files
              <input
                type="file"
                className="d-none"
                onChange={handleFileUpload}
                accept=".txt,.cob,.cobol,.cbl,.jcl,.cpy,.copybook"
                multiple
              />
            </label>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="d-flex justify-content-center gap-4">
        <button
          className="btn btn-outline-dark fw-medium px-4 py-3 rounded"
          onClick={() => {
            handleReset();
            setUploadedFiles({});
            setViewingFile(null);
          }}
        >
          <div className="d-flex align-items-center">
            <RefreshCw size={18} className="me-2 text-danger" />
            Reset
          </div>
        </button>

        <button
          className="btn text-white fw-medium px-4 py-3 rounded"
          style={{
            backgroundColor: "#0d9488",
            minWidth: "12rem",
          }}
          onClick={() =>
            handleGenerateRequirements(setActiveTab, getSourceCodeAsJson())
          }
          disabled={isGeneratingRequirements || !hasValidFiles}
        >
          {isGeneratingRequirements ? (
            <div className="d-flex align-items-center justify-content-center">
              <span
                className="spinner-border spinner-border-sm me-2"
                role="status"
                aria-hidden="true"
              ></span>
              Analyzing...
            </div>
          ) : (
            <div className="d-flex align-items-center justify-content-center">
              <ClipboardList size={18} className="me-2" />
              Generate Requirements
            </div>
          )}
        </button>
      </div>
    </div>
  );
}
