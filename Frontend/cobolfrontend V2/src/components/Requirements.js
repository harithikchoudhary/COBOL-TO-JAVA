import { ClipboardList, Copy, Download, FileCode, Plus, Edit, Trash2, CheckCircle } from "lucide-react";

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
  const handleAddRequirement = () => {
    const newRequirement = { text: "New requirement" };
    setTechnicalRequirementsList([...technicalRequirementsList, newRequirement]);
    setEditingRequirementIndex(technicalRequirementsList.length);
    setEditingRequirementText(newRequirement.text);
  };

  const handleEditRequirement = (index) => {
    setEditingRequirementIndex(index);
    setEditingRequirementText(technicalRequirementsList[index].text);
  };

  const handleSaveRequirement = () => {
    if (editingRequirementIndex !== null) {
      const updatedRequirements = [...technicalRequirementsList];
      updatedRequirements[editingRequirementIndex] = {
        text: editingRequirementText,
      };
      setTechnicalRequirementsList(updatedRequirements);
      setEditingRequirementIndex(null);
      setEditingRequirementText("");
    }
  };

  const handleDeleteRequirement = (index) => {
    const updatedRequirements = technicalRequirementsList.filter((_, i) => i !== index);
    setTechnicalRequirementsList(updatedRequirements);
  };

  const renderEditModal = () => {
    if (editingRequirementIndex === null) return null;

    return (
      <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" style={{ backgroundColor: "rgba(0, 0, 0, 0.5)", zIndex: 1050 }}>
        <div className="bg-white p-4 rounded-3 shadow-lg border border-teal w-75" style={{ maxWidth: "40rem", borderColor: "#0d9488" }}>
          <h3 className="fs-5 fw-medium mb-4 text-dark">Edit Requirement</h3>
          <textarea
            className="form-control border mb-4 p-2"
            value={editingRequirementText}
            onChange={(e) => setEditingRequirementText(e.target.value)}
            style={{ height: "8rem", borderColor: "#0d9488" }}
          />
          <div className="d-flex justify-content-end gap-2">
            <button
              className="btn btn-outline-secondary px-4 py-2 rounded"
              onClick={() => {
                setEditingRequirementIndex(null);
                setEditingRequirementText("");
              }}
            >
              Cancel
            </button>
            <button
              className="btn px-4 py-2 rounded text-white"
              style={{ backgroundColor: "#0d9488" }}
              onClick={handleSaveRequirement}
            >
              Save
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="d-flex flex-column gap-4">
      <div className="d-flex justify-content-between align-items-center">
        <div className="d-flex gap-2">
          <button
            className={`px-4 py-2 border border-dark rounded d-flex align-items-center ${
              activeRequirementsTab === "business"
                ? "text-white"
                : "bg-white text-dark hover-bg-light"
            }`}
            style={{ backgroundColor: activeRequirementsTab === "business" ? "#0d9488" : "" }}
            onClick={() => setActiveRequirementsTab("business")}
          >
            <ClipboardList size={16} className="me-2" />
            Business Requirements
          </button>
          <button
            className={`px-4 py-2 border border-dark rounded d-flex align-items-center ${
              activeRequirementsTab === "technical"
                ? "text-white"
                : "bg-white text-dark hover-bg-light"
            }`}
            style={{ backgroundColor: activeRequirementsTab === "technical" ? "#0d9488" : "" }}
            onClick={() => setActiveRequirementsTab("technical")}
          >
            <ClipboardList size={16} className="me-2" />
            Technical Requirements
          </button>
        </div>

        <div className="d-flex gap-2">
          <button
            className={`d-flex align-items-center ${
              copyStatus ? "text-white" : "bg-secondary text-white"
            } rounded px-4 py-2 fs-sm border border-white ${
              !businessRequirements && !technicalRequirements
                ? "opacity-50 disabled"
                : ""
            }`}
            style={{ backgroundColor: copyStatus ? "#0d9488" : "" }}
            onClick={handleCopyRequirements}
            disabled={!businessRequirements && !technicalRequirements}
          >
            {copyStatus ? (
              <>
                <CheckCircle size={16} className="me-2" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy size={16} className="me-2" />
                <span>Copy Requirements</span>
              </>
            )}
          </button>
          <button
            className={`d-flex align-items-center bg-secondary text-white rounded px-4 py-2 fs-sm border border-white ${
              !businessRequirements && !technicalRequirements
                ? "opacity-50 disabled"
                : ""
            }`}
            disabled={!businessRequirements && !technicalRequirements}
            onClick={handleDownloadRequirements}
          >
            <Download size={16} className="me-2" />
            <span>Download</span>
          </button>
        </div>
      </div>

      <div className="bg-white rounded border border-dark" style={{ height: "28rem" }}>
        {activeRequirementsTab === "business" ? (
          <div className="p-4 h-100 overflow-auto custom-scrollbar">
            <div className="text-dark white-space-pre-wrap">
              {businessRequirements ? (
                <div className="d-flex flex-column gap-2">
                  {businessRequirements.split("\n").map((line, index) => {
                    if (line.trim().startsWith("# ")) {
                      return (
                        <h1
                          key={index}
                          className="fs-2 fw-bold text-dark mt-4 mb-2 border-bottom pb-1"
                          style={{ borderColor: "#0d9488" }}
                        >
                          {line.replace("# ", "")}
                        </h1>
                      );
                    }
                    if (line.trim().startsWith("###**")) {
                      return (
                        <h1
                          key={index}
                          className="fs-2 fw-bold text-dark mt-4 mb-2 border-bottom pb-1"
                          style={{ borderColor: "#0d9488" }}
                        >
                          {line.replace("###**", "")}
                        </h1>
                      );
                    }
                    if (line.trim().startsWith("## ")) {
                      return (
                        <h4
                          key={index}
                          className="fs-5 fw-semibold text-dark mt-3 mb-2"
                        >
                          {line.replace("## ", "")}
                        </h4>
                      );
                    }
                    if (line.trim().startsWith("###")) {
                      return (
                        <p key={index} className="text-dark fw-normal mb-2">
                          {line.replace("###", "").trim()}
                        </p>
                      );
                    }
                    if (line.trim().startsWith("- ")) {
                      const bulletContent = line.replace("- ", "");
                      const parts = [];
                      let currentText = "";
                      let isBold = false;
                      let currentIndex = 0;
                      for (let i = 0; i < bulletContent.length; i++) {
                        if (bulletContent.substring(i, i + 2) === "**") {
                          if (currentText) {
                            parts.push(
                              <span
                                key={`${index}-${currentIndex}`}
                                className={isBold ? "fw-bold text-dark" : "fw-normal"}
                              >
                                {currentText}
                              </span>
                            );
                            currentIndex++;
                            currentText = "";
                          }
                          isBold = !isBold;
                          i++;
                        } else {
                          currentText += bulletContent[i];
                        }
                      }
                      if (currentText) {
                        parts.push(
                          <span
                            key={`${index}-${currentIndex}`}
                            className={isBold ? "fw-bold text-dark" : "fw-normal"}
                          >
                            {currentText}
                          </span>
                        );
                      }
                      return (
                        <div key={index} className="d-flex align-items-start mb-2">
                          <span className="me-2 mt-1" style={{ color: "#0d9488" }}>•</span>
                          <span className="text-dark">{parts}</span>
                        </div>
                      );
                    }
                    if (!line.trim()) {
                      return <div key={index} className="py-1"></div>;
                    }
                    const parts = [];
                    let currentText = "";
                    let isBold = false;
                    let currentIndex = 0;
                    for (let i = 0; i < line.length; i++) {
                      if (line.substring(i, i + 2) === "**") {
                        if (currentText) {
                          parts.push(
                            <span
                              key={`${index}-${currentIndex}`}
                              className={isBold ? "fw-bold text-dark" : "fw-normal"}
                            >
                              {currentText}
                            </span>
                          );
                          currentIndex++;
                          currentText = "";
                        }
                        isBold = !isBold;
                        i++;
                      } else {
                        currentText += line[i];
                      }
                    }
                    if (currentText) {
                      parts.push(
                        <span
                          key={`${index}-${currentIndex}`}
                          className={isBold ? "fw-bold text-dark" : "fw-normal"}
                        >
                          {currentText}
                        </span>
                      );
                    }
                    return (
                      <p key={index} className="text-dark">
                        {parts}
                      </p>
                    );
                  })}
                </div>
              ) : (
                <div className="d-flex flex-column align-items-center justify-content-center h-100 text-secondary">
                  <ClipboardList size={40} className="mb-4 opacity-50" />
                  <p className="text-center">No business requirements generated yet.</p>
                  <p className="fs-6 text-center mt-2">
                    Generate requirements from your COBOL code first.
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="p-4 h-100 overflow-auto custom-scrollbar">
            <div className="border-bottom pb-2 mb-2" style={{ borderColor: "#0d9488" }}>
              <h2 className="fs-4 fw-semibold text-dark">
                Technical Requirements
              </h2>
            </div>
            {technicalRequirementsList.length > 0 ? (
              <div className="d-flex flex-column gap-1">
                {technicalRequirementsList.map((req, index) => (
                  <div
                    key={index}
                    className="d-flex align-items-start p-2 border-bottom border-light rounded"
                  >
                    <span className="me-2" style={{ color: "#0d9488" }}>•</span>
                    <p className="flex-grow-1 text-dark">{req.text}</p>
                    <div className="d-flex gap-1 ms-2">
                      <button
                        className="btn btn-sm border-0"
                        onClick={() => handleEditRequirement(index)}
                        title="Edit"
                        style={{ color: "#0d9488" }}
                      >
                        <Edit size={16} />
                      </button>
                      <button
                        className="btn btn-sm border-0 text-danger"
                        onClick={() => handleDeleteRequirement(index)}
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-5 text-secondary">
                <div className="mb-2">No technical requirements found.</div>
                <div className="fs-6">
                  Generate requirements first or add them manually.
                </div>
              </div>
            )}
            <button
              className="mt-4 px-3 py-1 btn text-white rounded d-flex align-items-center"
              style={{ backgroundColor: "#0d9488" }}
              onClick={handleAddRequirement}
            >
              <Plus size={16} className="me-1" /> Add Requirement
            </button>
          </div>
        )}
      </div>

      <div className="d-flex justify-content-center gap-4 mt-4">
        <button
          className="btn btn-outline-dark fw-medium px-4 py-3 rounded"
          onClick={() => setActiveTab("input")}
        >
          <div className="d-flex align-items-center">
            <FileCode size={18} className="me-2" style={{ color: "#0d9488" }} />
            Back to Code
          </div>
        </button>
        <button
          className="btn text-white fw-medium px-5 py-3 rounded"
          style={{ backgroundColor: "#0d9488", minWidth: "9rem" }}
          onClick={() => handleConvert(setActiveTab)}
          disabled={isLoading}
        >
          {isLoading ? (
            <div className="d-flex align-items-center justify-content-center">
              <div className="spinner-border spinner-border-sm me-2" role="status"></div>
              Converting...
            </div>
          ) : (
            <div className="d-flex align-items-center justify-content-center">
              <span className="me-1">Convert to {targetLanguage}</span>
              <span className="ms-1">→</span>
            </div>
          )}
        </button>
      </div>

      {renderEditModal()}
    </div>
  );
}