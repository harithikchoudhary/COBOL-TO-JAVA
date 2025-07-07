import { useState, useEffect } from "react";

import { RefreshCw, Download, ClipboardList } from "lucide-react";

const API_BASE_URL = "http://localhost:8010/cobo";

export default function Cobol({ children }) {
  const [targetLanguage, setTargetLanguage] = useState("C#");
  const [convertedCode, setConvertedCode] = useState("");
  const [unitTests, setUnitTests] = useState("");
  const [functionalTests, setFunctionalTests] = useState("");
  const [businessRequirements, setBusinessRequirements] = useState("");
  const [technicalRequirements, setTechnicalRequirements] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingRequirements, setIsGeneratingRequirements] =
    useState(false);
  const [copyStatus, setCopyStatus] = useState(false);
  const [error, setError] = useState("");
  const [isBackendAvailable, setIsBackendAvailable] = useState(true);
  const [activeRequirementsTab, setActiveRequirementsTab] =
    useState("business");
  const [activeOutputTab, setActiveOutputTab] = useState("code");
  const [technicalRequirementsList, setTechnicalRequirementsList] = useState(
    []
  );
  const [editingRequirementIndex, setEditingRequirementIndex] = useState(null);
  const [editingRequirementText, setEditingRequirementText] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState({});
  const [sourceCodeJson, setSourceCodeJson] = useState(null);

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

  useEffect(() => {
    console.log("setSourceCodeJson type:", typeof setSourceCodeJson);
  }, [setSourceCodeJson]);

  const handleGenerateRequirements = async (setActiveTab, sourceCodeJson) => {
  setError("");
  if (!sourceCodeJson) {
    setError("Please upload COBOL files to analyze");
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
        setTechnicalRequirementsList(
          parseRequirementsList(simulatedTechReqs)
        );
        setIsGeneratingRequirements(false);
        setActiveTab("requirements");
      }, 1500);
      return;
    }

    // Parse sourceCodeJson if it's a string
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

    // Enhanced flow with comprehensive analysis
    console.log("🚀 Starting enhanced requirements generation with comprehensive analysis");

    const response = await fetch(`${API_BASE_URL}/analyze-requirements`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sourceLanguage: "COBOL",
        targetLanguage,
        file_data: filesData
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Analysis failed");
    }

    const data = await response.json();
    console.log("✅ Enhanced analysis completed:", data);

    // Process business requirements
    let formattedBusinessReqs = "# Business Requirements\n\n";
    if (data.businessRequirements) {
      if (typeof data.businessRequirements === "string") {
        formattedBusinessReqs = data.businessRequirements;
      } else {
        const br = data.businessRequirements;
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
        // Add CICS insights if available
        if (br.CICS_Insights) {
          formattedBusinessReqs += "## CICS Analysis Insights\n";
          if (br.CICS_Insights["Business_Domain"]) {
            formattedBusinessReqs += `- **Business Domain:** ${br.CICS_Insights["Business_Domain"]}\n`;
          }
          if (br.CICS_Insights["Transaction_Patterns"]) {
            formattedBusinessReqs += `- **Transaction Patterns:** ${br.CICS_Insights["Transaction_Patterns"]}\n`;
          }
          if (br.CICS_Insights["Integration_Points"]) {
            formattedBusinessReqs += `- **Integration Points:** ${br.CICS_Insights["Integration_Points"]}\n`;
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
        }
      }
    }

    // Process technical requirements
    let formattedTechReqs = "# Technical Requirements\n\n";
    if (data.technicalRequirements) {
      if (typeof data.technicalRequirements === "string") {
        formattedTechReqs = data.technicalRequirements;
      } else if (Array.isArray(data.technicalRequirements)) {
        data.technicalRequirements.forEach((req, index) => {
          formattedTechReqs += `${index + 1}. ${req.description}\n`;
        });
      } else if (data.technicalRequirements.technicalRequirements) {
        const techReqs = data.technicalRequirements.technicalRequirements;
        if (Array.isArray(techReqs)) {
          techReqs.forEach((req, index) => {
            const complexity = req.complexity ? ` (${req.complexity})` : '';
            const category = req.category ? ` [${req.category}]` : '';
            formattedTechReqs += `${index + 1}. ${req.description}${complexity}${category}\n`;
          });
        }
        
        // Add architecture recommendations if available
        if (data.technicalRequirements.architectureRecommendations) {
          formattedTechReqs += "\n## Architecture Recommendations\n";
          data.technicalRequirements.architectureRecommendations.forEach((rec, index) => {
            formattedTechReqs += `${index + 1}. ${rec}\n`;
          });
        }
        
        // Add technology stack if available
        if (data.technicalRequirements.technologyStack) {
          formattedTechReqs += "\n## Recommended Technology Stack\n";
          const stack = data.technicalRequirements.technologyStack;
          if (stack.database) formattedTechReqs += `- **Database:** ${stack.database}\n`;
          if (stack.caching) formattedTechReqs += `- **Caching:** ${stack.caching}\n`;
          if (stack.messaging) formattedTechReqs += `- **Messaging:** ${stack.messaging}\n`;
        }
      } else {
        formattedTechReqs +=
          "Could not format technical requirements - unexpected data structure.";
        console.error(
          "Unexpected technical requirements format:",
          data.technicalRequirements
        );
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

      const requirementMatch = line.match(/^(\d+\.|[*-])\s+(.*)/);
      if (requirementMatch) {
        reqList.push({ text: requirementMatch[2].trim() });
      }
    }
    if (reqList.length === 0) {
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line && !line.startsWith("#")) {
          reqList.push({ text: line });
        }
      }
    }
    return reqList;
  };

  const handleConvert = async (setActiveTab) => {
    setError("");
    if (!sourceCodeJson) {
      setError("Please upload COBOL files to convert");
      return;
    }

    setIsLoading(true);

    try {
      if (!isBackendAvailable) {
        setTimeout(() => {
          const simulatedCode = `// Simulated C# code\npublic class CobolConverter {\n    public static void Main(string[] args) {\n        Console.WriteLine(\"This is a simulated conversion\");\n    }\n}`;
          const simulatedUnitTests = `// Simulated Unit Tests
@Test
public void testConversion() {
    assertTrue(true);
}`;
          const simulatedFunctionalTests = `// Simulated Functional Tests
Feature: Basic Functionality
  Scenario: Test basic conversion
    Given the COBOL code is valid
    When the conversion is performed
    Then the output should be valid ${targetLanguage} code`;

          setConvertedCode(simulatedCode);
          setUnitTests(simulatedUnitTests);
          setFunctionalTests(simulatedFunctionalTests);
          setIsLoading(false);
          setActiveTab("output");
        }, 1500);
        return;
      }

      const response = await fetch(`${API_BASE_URL}/convert`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sourceLanguage: "COBOL",
          targetLanguage,
          sourceCode: sourceCodeJson,
          businessRequirements,
          technicalRequirements,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Conversion failed");
      }

      const data = await response.json();
      setConvertedCode(data.convertedCode || "");
      setUnitTests(data.unitTests || "");
      setFunctionalTests(data.functionalTests || "");
      setActiveTab("output");
    } catch (error) {
      console.error("Error during conversion:", error);
      setError(error.message || "Failed to convert code. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setConvertedCode("");
    setUnitTests("");
    setFunctionalTests("");
    setBusinessRequirements("");
    setTechnicalRequirements("");
    setTechnicalRequirementsList([]);
    setError("");
    setUploadedFiles({});
  };

  const handleCopyRequirements = () => {
    const textToCopy =
      activeRequirementsTab === "business"
        ? businessRequirements
        : technicalRequirements;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopyStatus(true);
      setTimeout(() => setCopyStatus(false), 2000);
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
  };

  return <>{children(enhancedProps)}</>;
}
