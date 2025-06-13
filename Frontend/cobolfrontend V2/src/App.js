import { useState } from "react";
import { FileText, ClipboardList, FileCode } from "lucide-react";
import Input from "./components/Input";
import Requirements from "./components/Requirements";
import Output from "./components/Output";
import Cobol from "./Cobol";
import "bootstrap/dist/css/bootstrap.min.css";
import { Container, Button, Alert } from "react-bootstrap";

export default function App() {
  const [activeTab, setActiveTab] = useState("input");

  return (
    <Cobol>
      {({
        targetLanguage,
        setTargetLanguage,
        targetLanguages,
        handleReset,
        handleGenerateRequirements,
        isGeneratingRequirements,
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
        handleConvert,
        isLoading,
        convertedCode,
        unitTests,
        functionalTests,
        activeOutputTab,
        setActiveOutputTab,
        handleCopyCode,
        handleDownload,
        error,
        isBackendAvailable,
        setSourceCodeJson,
      }) => (
        <div className="min-vh-100" style={{ backgroundColor: "#f0fffa" }}>
          <Container className="px-4 py-5">
            <div className="text-center mb-5">
              <div className="d-flex justify-content-center align-items-center mb-4">
                <h1 className="display-5 fw-bold text-dark">
                  COBOL Code Converter
                </h1>
              </div>
              <p className="fs-4 text-secondary">
                Transform COBOL code to Java or C# with AI precision
              </p>
              {!isBackendAvailable && (
                <Alert variant="warning" className="mt-2">
                  Backend connection unavailable. Using simulated mode.
                </Alert>
              )}
            </div>

            {error && (
              <Alert variant="danger" className="mb-4">
                {error}
              </Alert>
            )}

            <div className="d-flex gap-3 mb-4">
              <Button
                onClick={() => setActiveTab("input")}
                variant={activeTab === "input" ? "primary" : "light"}
                className="px-4 py-2 rounded-3 d-flex align-items-center"
                style={{
                  backgroundColor: activeTab === "input" ? "#0d9488" : "",
                  border: activeTab !== "input" ? "1px solid #000" : "none",
                }}
              >
                <FileText size={20} className="me-2" />
                Input
              </Button>
              <Button
                onClick={() => setActiveTab("requirements")}
                variant={activeTab === "requirements" ? "primary" : "light"}
                className="px-4 py-2 rounded-3 d-flex align-items-center"
                style={{
                  backgroundColor:
                    activeTab === "requirements" ? "#0d9488" : "",
                  border:
                    activeTab !== "requirements" ? "1px solid #000" : "none",
                }}
              >
                <ClipboardList size={20} className="me-2" />
                Requirements
              </Button>
              <Button
                onClick={() => setActiveTab("output")}
                variant={activeTab === "output" ? "primary" : "light"}
                className="px-4 py-2 rounded-3 d-flex align-items-center"
                style={{
                  backgroundColor: activeTab === "output" ? "#0d9488" : "",
                  border: activeTab !== "output" ? "1px solid #000" : "none",
                }}
              >
                <FileCode size={20} className="me-2" />
                Output
              </Button>
            </div>

            <div
              className="bg-white rounded-4 border border-dark shadow p-4"
              style={{ boxShadow: "0 4px 6px rgba(13, 148, 136, 0.2)" }}
            >
              {activeTab === "input" && (
                <Input
                  targetLanguage={targetLanguage}
                  setTargetLanguage={setTargetLanguage}
                  targetLanguages={targetLanguages}
                  handleReset={handleReset}
                  handleGenerateRequirements={handleGenerateRequirements}
                  isGeneratingRequirements={isGeneratingRequirements}
                  setActiveTab={setActiveTab}
                  setSourceCodeJson={setSourceCodeJson}
                />
              )}
              {activeTab === "requirements" && (
                <Requirements
                  businessRequirements={businessRequirements}
                  technicalRequirements={technicalRequirements}
                  technicalRequirementsList={technicalRequirementsList}
                  setTechnicalRequirementsList={setTechnicalRequirementsList}
                  activeRequirementsTab={activeRequirementsTab}
                  setActiveRequirementsTab={setActiveRequirementsTab}
                  editingRequirementIndex={editingRequirementIndex}
                  setEditingRequirementIndex={setEditingRequirementIndex}
                  editingRequirementText={editingRequirementText}
                  setEditingRequirementText={setEditingRequirementText}
                  handleCopyRequirements={handleCopyRequirements}
                  handleDownloadRequirements={handleDownloadRequirements}
                  copyStatus={copyStatus}
                  setActiveTab={setActiveTab}
                  handleConvert={handleConvert}
                  isLoading={isLoading}
                  targetLanguage={targetLanguage}
                />
              )}
              {activeTab === "output" && (
                <Output
                  convertedCode={convertedCode}
                  unitTests={unitTests}
                  functionalTests={functionalTests}
                  activeOutputTab={activeOutputTab}
                  setActiveOutputTab={setActiveOutputTab}
                  copyStatus={copyStatus}
                  handleCopyCode={handleCopyCode}
                  handleDownload={handleDownload}
                  setActiveTab={setActiveTab}
                  handleReset={handleReset}
                  targetLanguage={targetLanguage}
                />
              )}
            </div>
          </Container>
        </div>
      )}
    </Cobol>
  );
}
