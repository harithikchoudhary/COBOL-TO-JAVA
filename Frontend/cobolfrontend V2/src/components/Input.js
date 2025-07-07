import { useState, useEffect } from "react";
import {
  Upload,
  ClipboardList,
  RefreshCw,
  FileText,
  X,
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
  const [activeFileTab, setActiveFileTab] = useState(null);

  // Store JSON data for backend (send filename-to-content mapping)
  const getSourceCodeAsJson = () => {
    const fileData = {};
    Object.entries(uploadedFiles).forEach(([fileName, fileObj]) => {
      fileData[fileName] = fileObj.content;
    });
    return fileData;
  };

  const sourceCodeJson = getSourceCodeAsJson();
  useEffect(() => {
    console.log("Setting sourceCodeJson:", sourceCodeJson);
    setSourceCodeJson(sourceCodeJson);
  }, [sourceCodeJson, setSourceCodeJson]);

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);

    // Function to determine file type based on extension
    const getFileType = (fileName) => {
      const extension = fileName.split('.').pop().toLowerCase();
      const typeMap = {
        'cob': 'COBOL',
        'cobol': 'COBOL',
        'cbl': 'COBOL',
        'jcl': 'JCL',
        'cpy': 'Copybook',
        'copybook': 'Copybook',
        'bms': 'BMS',
        'txt': 'Text'
      };
      return typeMap[extension] || 'Unknown';
    };

    const readFiles = await Promise.all(
      files.map(
        (file) =>
          new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
              resolve({
                fileName: file.name,
                content: e.target.result,
                size: file.size,
                type: getFileType(file.name),
                uploadDate: new Date().toISOString()
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

    // Set the first uploaded file as active if no active tab
    if (!activeFileTab && readFiles.length > 0) {
      setActiveFileTab(readFiles[0].fileName);
    }

    // Clear input
    event.target.value = "";
  };

  const removeFile = (fileName) => {
    setUploadedFiles((prev) => {
      const newFiles = { ...prev };
      delete newFiles[fileName];
      return newFiles;
    });

    // Handle active tab when file is removed
    const fileNames = Object.keys(uploadedFiles).filter(name => name !== fileName);
    if (activeFileTab === fileName) {
      setActiveFileTab(fileNames.length > 0 ? fileNames[0] : null);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const getFileTypeIcon = (type) => {
    switch (type) {
      case 'COBOL':
        return '📄';
      case 'JCL':
        return '⚙️';
      case 'Copybook':
        return '📋';
      default:
        return '📄';
    }
  };

  const hasValidFiles = Object.keys(uploadedFiles).length > 0;

  return (
    <div className="d-flex flex-column gap-4">
      {/* File Upload Section */}
      <div className="d-flex align-items-center gap-2 flex-wrap">
        <label
          className="d-flex align-items-center btn rounded px-3 py-2 cursor-pointer"
          style={{ backgroundColor: "#0f766e", color: "white" }}
        >
          <Upload size={16} className="me-2" />
          <span>Upload Files</span>
          <input
            type="file"
            className="d-none"
            onChange={handleFileUpload}
            accept=".txt,.cob,.cobol,.cbl,.jcl,.cpy,.copybook,.bms"
            multiple
          />
        </label>

        <div className="dropdown position-relative">
          <button
            className="d-flex align-items-center gap-2 px-3 py-2 btn btn-outline-dark rounded"
            onClick={() => setShowDropdownTarget(!showDropdownTarget)}
          >
            <span
              className="d-flex align-items-center justify-content-center text-primary"
              style={{ width: "1rem", height: "1rem" }}
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

      {/* File Tabs and Content Display */}
      {hasValidFiles && (
        <div className="bg-white rounded border">
          {/* File Tabs */}
          <div className="d-flex border-bottom bg-light rounded-top overflow-auto">
            {Object.entries(uploadedFiles).map(([fileName, fileData]) => (
              <div
                key={fileName}
                className={`d-flex align-items-center px-3 py-2 border-end cursor-pointer position-relative ${activeFileTab === fileName
                  ? 'bg-white border-bottom-0'
                  : 'bg-light'
                  }`}
                style={{
                  minWidth: "120px",
                  borderBottom: activeFileTab === fileName ? '2px solid transparent' : '1px solid #dee2e6'
                }}
                onClick={() => setActiveFileTab(fileName)}
              >
                <span className="me-2">{getFileTypeIcon(fileData.type)}</span>
                <div className="fw-medium text-truncate me-2" style={{ maxWidth: "80px" }}>
                  {fileName}
                </div>
                <button
                  className="btn btn-sm p-1 ms-auto"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(fileName);
                  }}
                  title="Remove file"
                  style={{ width: "20px", height: "20px" }}
                >
                  <X size={12} className="text-danger" />
                </button>
              </div>
            ))}
          </div>

          {/* File Content Display */}
          {activeFileTab && uploadedFiles[activeFileTab] && (
            <div className="p-0">
              {/* Code Content */}
              <div
                className="overflow-auto"
                style={{
                  maxHeight: "400px",
                  backgroundColor: "#f8f9fa",
                }}
              >
                <pre
                  className="p-3 mb-0"
                  style={{
                    fontFamily: 'Consolas, "Courier New", monospace',
                    fontSize: "14px",
                    lineHeight: "1.5",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    margin: 0,
                  }}
                >
                  {uploadedFiles[activeFileTab].content}
                </pre>
              </div>
            </div>
          )}
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
                accept=".txt,.cob,.cobol,.cbl,.jcl,.cpy,.copybook,.bms"
                multiple
              />
            </label>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="d-flex justify-content-center gap-3">
        <button
          className="btn btn-outline-dark fw-medium px-3 py-2 rounded"
          onClick={() => {
            handleReset();
            setUploadedFiles({});
            setActiveFileTab(null);
          }}
        >
          <div className="d-flex align-items-center">
            <RefreshCw size={16} className="me-2 text-danger" />
            Reset
          </div>
        </button>

        <button
          className="btn text-white fw-medium px-3 py-2 rounded"
          style={{
            backgroundColor: "#0d9488",
            minWidth: "10rem",
          }}
          onClick={() =>
            handleGenerateRequirements(setActiveTab, sourceCodeJson)
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
              <ClipboardList size={16} className="me-2" />
              Generate Requirements
            </div>
          )}
        </button>
      </div>
    </div>
  );
}