import { useState, useEffect } from "react";

const API_BASE_URL = "http://localhost:8010/cobo";

export default function Cobol({ children }) {
  const [targetLanguage, setTargetLanguage] = useState("C#");
  const [convertedCode, setConvertedCode] = useState("");
  const [convertedFiles, setConvertedFiles] = useState({});
  const [unitTests, setUnitTests] = useState("");
  const [functionalTests, setFunctionalTests] = useState("");
  const [businessRequirements, setBusinessRequirements] = useState("");
  const [technicalRequirements, setTechnicalRequirements] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingRequirements, setIsGeneratingRequirements] = useState(false);
  const [copyStatus, setCopyStatus] = useState(false);
  const [error, setError] = useState("");
  const [isBackendAvailable, setIsBackendAvailable] = useState(true);
  const [activeRequirementsTab, setActiveRequirementsTab] = useState("business");
  const [activeOutputTab, setActiveOutputTab] = useState("code");
  const [technicalRequirementsList, setTechnicalRequirementsList] = useState([]);
  const [editingRequirementIndex, setEditingRequirementIndex] = useState(null);
  const [editingRequirementText, setEditingRequirementText] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState({});
  const [sourceCodeJson, setSourceCodeJson] = useState(null);
  const [conversionResponse, setConversionResponse] = useState(null);
  const [projectId, setProjectId] = useState(null);

  const targetLanguages = [
    { name: "C#", icon: "🔷" },
  ];

  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
          setIsBackendAvailable(true);
        } else {
          setIsBackendAvailable(false);
        }
      } catch (error) {
        console.error("Backend health check failed:", error);
        setIsBackendAvailable(false);
      }
    };

    checkBackendStatus();
  }, []);

  const handleGenerateRequirements = async (setActiveTab, sourceCodeJson, projectId) => {
    setError("");
    if (!sourceCodeJson) {
      setError("Please upload COBOL files to analyze");
      return;
    }
    if (!projectId) {
      setError("Project ID is missing. Please upload files first.");
      return;
    }

    setIsGeneratingRequirements(true);

    try {
      if (!isBackendAvailable) {
        setTimeout(() => {
          const simulatedBusinessReqs = `# Business Requirements
1. The system appears to handle financial transactions, specifically account balances and updates.
2. There is a validation process for transaction codes, indicating business rules around transaction types.
3. The code suggests a batch processing system that processes multiple records sequentially.
4. Error handling and reporting requirements exist for invalid transactions.
5. The system needs to maintain audit trails for financial operations.`;

          const simulatedTechReqs = `# Technical Requirements
1. Code needs to be migrated from legacy COBOL to ${targetLanguage} while preserving all business logic.
2. File handling must be converted to appropriate database or file operations in ${targetLanguage}.
3. COBOL's fixed decimal precision must be maintained in the target language.
4. Error handling mechanisms need to be implemented using modern exception handling.
5. Batch processing paradigm should be adapted to object-oriented design.
6. Field validations and business rules should be extracted into separate service classes.`;

          setBusinessRequirements(simulatedBusinessReqs);
          setTechnicalRequirements(simulatedTechReqs);
          setTechnicalRequirementsList(parseRequirementsList(simulatedTechReqs));
          setIsGeneratingRequirements(false);
          setActiveTab("requirements");
        }, 1500);
        return;
      }

      let filesData = sourceCodeJson;
      if (typeof sourceCodeJson === 'string') {
        try {
          filesData = JSON.parse(sourceCodeJson);
        } catch (e) {
          setError("Invalid file data format");
          setIsGeneratingRequirements(false);
          return;
        }
      }

      console.log("🚀 Starting requirements generation");

      const response = await fetch(`${API_BASE_URL}/analyze-requirements`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sourceLanguage: "COBOL",
          targetLanguage,
          file_data: filesData,
          projectId
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Requirements analysis failed:", errorText);
        throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log("✅ Requirements analysis completed:", data);

      setProjectId(data.project_id || projectId);

      let formattedBusinessReqs = "";
      if (data.business_requirements) {
        if (typeof data.business_requirements === "string") {
          formattedBusinessReqs = data.business_requirements;
        } else {
          const br = data.business_requirements;
          formattedBusinessReqs = "# Business Requirements\n\n";

          if (br.Overview) {
            formattedBusinessReqs += "## Overview\n";
            if (br.Overview["Purpose of the System"]) {
              formattedBusinessReqs += `- **Purpose:** ${br.Overview["Purpose of the System"]}\n`;
            }
            if (br.Overview["Context and Business Impact"]) {
              formattedBusinessReqs += `- **Business Impact:** ${br.Overview["Context and Business Impact"]}\n`;
            }
            formattedBusinessReqs += "\n";
          }

          if (br.Objectives) {
            formattedBusinessReqs += "## Objectives\n";
            if (br.Objectives["Primary Objective"]) {
              formattedBusinessReqs += `- **Primary Objective:** ${br.Objectives["Primary Objective"]}\n`;
            }
            if (br.Objectives["Key Outcomes"]) {
              formattedBusinessReqs += `- **Key Outcomes:** ${br.Objectives["Key Outcomes"]}\n`;
            }
            formattedBusinessReqs += "\n";
          }

          if (br["Business Rules & Requirements"]) {
            formattedBusinessReqs += "## Business Rules & Requirements\n";
            if (br["Business Rules & Requirements"]["Business Purpose"]) {
              formattedBusinessReqs += `- **Business Purpose:** ${br["Business Rules & Requirements"]["Business Purpose"]}\n`;
            }
            if (br["Business Rules & Requirements"]["Business Rules"]) {
              formattedBusinessReqs += `- **Business Rules:** ${br["Business Rules & Requirements"]["Business Rules"]}\n`;
            }
            if (br["Business Rules & Requirements"]["Impact on System"]) {
              formattedBusinessReqs += `- **System Impact:** ${br["Business Rules & Requirements"]["Impact on System"]}\n`;
            }
            if (br["Business Rules & Requirements"]["Constraints"]) {
              formattedBusinessReqs += `- **Constraints:** ${br["Business Rules & Requirements"]["Constraints"]}\n`;
            }
            formattedBusinessReqs += "\n";
          }

          if (br["Assumptions & Recommendations"]) {
            formattedBusinessReqs += "## Assumptions & Recommendations\n";
            if (br["Assumptions & Recommendations"]["Assumptions"]) {
              formattedBusinessReqs += `- **Assumptions:** ${br["Assumptions & Recommendations"]["Assumptions"]}\n`;
            }
            if (br["Assumptions & Recommendations"]["Recommendations"]) {
              formattedBusinessReqs += `- **Recommendations:** ${br["Assumptions & Recommendations"]["Recommendations"]}\n`;
            }
            formattedBusinessReqs += "\n";
          }

          if (br["Expected Output"]) {
            formattedBusinessReqs += "## Expected Output\n";
            if (br["Expected Output"]["Output"]) {
              formattedBusinessReqs += `- **Output:** ${br["Expected Output"]["Output"]}\n`;
            }
            if (br["Expected Output"]["Business Significance"]) {
              formattedBusinessReqs += `- **Business Significance:** ${br["Expected Output"]["Business Significance"]}\n`;
            }
            formattedBusinessReqs += "\n";
          }
        }
      }

      let formattedTechReqs = "";
      if (data.technical_requirements) {
        if (typeof data.technical_requirements === "string") {
          formattedTechReqs = data.technical_requirements;
        } else {
          const tr = data.technical_requirements;
          formattedTechReqs = "# Technical Requirements\n\n";

          if (tr.technicalRequirements && Array.isArray(tr.technicalRequirements)) {
            tr.technicalRequirements.forEach((req, index) => {
              formattedTechReqs += `${index + 1}. ${req.description} (Complexity: ${req.complexity || "Medium"})\n\n`;
            });
          }
          else if (tr.Technical_Challenges && Array.isArray(tr.Technical_Challenges)) {
            tr.Technical_Challenges.forEach((challenge, index) => {
              formattedTechReqs += `${index + 1}. The system must ${challenge.description}\n\n`;
            });
          }
          else if (tr.Integration_Requirements && Array.isArray(tr.Integration_Requirements)) {
            tr.Integration_Requirements.forEach((integration, index) => {
              const startIndex = formattedTechReqs.includes("1.") ? 
                (formattedTechReqs.match(/\d+\./g) || []).length + 1 : 1;
              formattedTechReqs += `${startIndex}. The system must integrate with ${integration.name} for ${integration.description}\n\n`;
            });
          }

          if (!formattedTechReqs.includes("1.")) {
            formattedTechReqs += "1. The system must migrate from COBOL to C# while preserving all business logic (Complexity: High)\n\n";
            formattedTechReqs += "2. The system must implement proper error handling using modern exception handling (Complexity: Medium)\n\n";
            formattedTechReqs += "3. The system must use Entity Framework Core for database operations (Complexity: Medium)\n\n";
            formattedTechReqs += "4. The system must implement proper validation using data annotations (Complexity: Low)\n\n";
            formattedTechReqs += "5. The system must follow SOLID principles and C# naming conventions (Complexity: Low)\n\n";
          }
        }
      }
      setBusinessRequirements(formattedBusinessReqs);
      setTechnicalRequirements(formattedTechReqs);
      setTechnicalRequirementsList(parseRequirementsList(formattedTechReqs));
      setActiveTab("requirements");

      console.log("✅ Requirements generation completed successfully");

    } catch (error) {
      console.error("Error during requirements analysis:", error);
      setError(error.message || "Failed to analyze code. Please try again.");
    } finally {
      setIsGeneratingRequirements(false);
    }
  };

  const parseRequirementsList = (requirementsText) => {
    if (!requirementsText) return [];

    const lines = requirementsText.split("\n");
    const reqList = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      const numberedMatch = line.match(/^(\d+\.)\s+(.*)/);
      if (numberedMatch) {
        const description = numberedMatch[2].trim();
        if (description && !description.startsWith("**")) {
          reqList.push({ text: description });
        }
        continue;
      }

      const bulletMatch = line.match(/^([*-•])\s+(.*)/);
      if (bulletMatch) {
        const description = bulletMatch[2].trim();
        if (description && !description.startsWith("**")) {
          reqList.push({ text: description });
        }
        continue;
      }

      const sectionMatch = line.match(/^##\s+(.*)/);
      if (sectionMatch) {
        const sectionName = sectionMatch[1].trim();
        if (sectionName) {
          reqList.push({ text: sectionName });
        }
        continue;
      }
    }

    if (reqList.length === 0) {
      lines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith("#") && !trimmed.startsWith("-") && trimmed.length > 10) {
          reqList.push({ text: trimmed });
        }
      });
    }

    return reqList;
  };

  const flattenConvertedCode = (convertedCode) => {
    const files = {};
    convertedCode.forEach((file) => {
      files[file.file_name] = file.content;
    });
    return files;
  };


const handleConvert = async (setActiveTab) => {
  setError("");
  if (!sourceCodeJson) {
    setError("Please upload COBOL files to convert");
    return;
  }
  if (!projectId) {
    setError("Project ID is missing. Please upload files first.");
    return;
  }

  setIsLoading(true);
  console.log("🚀 Starting code conversion");

  try {
    // Ensure sourceCodeJson is properly formatted
    let sourceCode = sourceCodeJson;
    if (typeof sourceCodeJson === 'string') {
      try {
        sourceCode = JSON.parse(sourceCodeJson);
      } catch (e) {
        console.error("Failed to parse sourceCodeJson:", e);
        setError("Invalid sourceCode format. Expected a JSON object.");
        setIsLoading(false);
        return;
      }
    }

    // Validate that we have content
    if (!sourceCode || Object.keys(sourceCode).length === 0) {
      setError("No COBOL files found. Please upload files first.");
      setIsLoading(false);
      return;
    }

    // Log the data being sent for debugging
    console.log("Sending conversion request with:", {
      projectId,
      sourceCodeKeys: Object.keys(sourceCode),
      businessRequirements: businessRequirements ? "present" : "missing",
      technicalRequirements: technicalRequirements ? "present" : "missing"
    });

    const response = await fetch(`${API_BASE_URL}/convert`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        sourceLanguage: "COBOL",
        targetLanguage: "C#",
        sourceCode: sourceCode, // Pass the parsed object
        projectId,
        cobolFilename: Object.keys(uploadedFiles)[0] || "BANKING.CBL"
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Conversion failed:", errorText);
      let errorMessage = `Conversion failed: ${response.status}`;
      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.error || errorText || errorMessage;
      } catch (e) {
        errorMessage = errorText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    console.log("✅ Conversion completed:", data);

    setConversionResponse(data);

    const files = data.files || {};
    setConvertedFiles(files);
    setConvertedCode(data.converted_code?.[0]?.content || "");
    setUnitTests(data.unit_tests || "");
    setFunctionalTests(data.functional_tests || "");
    setActiveTab("output");

    if (Object.keys(files).length === 0) {
      console.warn("No converted files received in response");
      setError("Conversion completed, but no files were generated. Please check the backend logs.");
    }

    console.log("✅ All conversion data processed successfully");

  } catch (error) {
    console.error("Error during conversion:", error);
    setError(error.message || "Failed to convert code. Please try again.");
  } finally {
    setIsLoading(false);
  }
};


  const handleReset = () => {
    setConvertedCode("");
    setConvertedFiles({});
    setUnitTests("");
    setFunctionalTests("");
    setBusinessRequirements("");
    setTechnicalRequirements("");
    setTechnicalRequirementsList([]);
    setConversionResponse(null);
    setError("");
    setUploadedFiles({});
    setSourceCodeJson(null);
    setProjectId(null);
  };

  const handleCopyRequirements = () => {
    const elementId = activeRequirementsTab === "business" ? "businessReq" : "technicalReq";
    const element = document.getElementById(elementId);

    if (element) {
      const textToCopy = element.innerText;

      navigator.clipboard.writeText(textToCopy)
        .then(() => {
          setCopyStatus(true);
          setTimeout(() => setCopyStatus(false), 2000);
        })
        .catch(err => {
          console.error("Failed to copy: ", err);
        });
    }
  };

  const handleDownloadRequirements = () => {
    const textToDownload =
      activeRequirementsTab === "business"
        ? businessRequirements
        : technicalRequirements;
    if (!textToDownload) return;
    const element = document.createElement("a");
    const file = new Blob([textToDownload], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = `${activeRequirementsTab}_requirements.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleCopyCode = () => {
    let contentToCopy = "";

    switch (activeOutputTab) {
      case "code":
        contentToCopy = convertedCode;
        break;
      case "unit-tests":
        contentToCopy = unitTests;
        break;
      case "functional-tests":
        contentToCopy = functionalTests;
        break;
      default:
        contentToCopy = convertedCode;
    }

    if (contentToCopy) {
      navigator.clipboard.writeText(contentToCopy);
      setCopyStatus(true);
      setTimeout(() => setCopyStatus(false), 2000);
    }
  };

  const handleDownload = () => {
    let contentToDownload = "";
    let filename = "";

    switch (activeOutputTab) {
      case "code":
        contentToDownload = convertedCode;
        filename = `converted_${targetLanguage.toLowerCase()}_code.cs`;
        break;
      case "unit-tests":
        contentToDownload = unitTests;
        filename = `unit_tests_${targetLanguage.toLowerCase()}.cs`;
        break;
      case "functional-tests":
        contentToDownload = functionalTests;
        filename = `functional_tests_${targetLanguage.toLowerCase()}.txt`;
        break;
      default:
        contentToDownload = convertedCode;
        filename = `converted_${targetLanguage.toLowerCase()}_code.cs`;
    }

    if (!contentToDownload) return;
    const element = document.createElement("a");
    const file = new Blob([contentToDownload], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = filename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const enhancedProps = {
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
    convertedFiles,
    unitTests,
    functionalTests,
    activeOutputTab,
    setActiveOutputTab,
    handleCopyCode,
    handleDownload,
    error,
    isBackendAvailable,
    uploadedFiles,
    setUploadedFiles,
    sourceCodeJson,
    setSourceCodeJson,
    conversionResponse,
    setConversionResponse,
    projectId,
    setProjectId,
  };

  return <>{children(enhancedProps)}</>;
}