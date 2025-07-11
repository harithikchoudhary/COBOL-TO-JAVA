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
          file_data: filesData
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Requirements analysis failed:", errorText);
        throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      console.log("✅ Requirements analysis completed:", data);

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
        // Handle nested structure: { technicalRequirements: [...] }
        if (Array.isArray(data.technicalRequirements.technicalRequirements)) {
          data.technicalRequirements.technicalRequirements.forEach((req, index) => {
            if (req.description) {
              formattedTechReqs += `${index + 1}. ${req.description}\n\n`;
            }
          });
        } else if (typeof data.technicalRequirements === "string") {
          formattedTechReqs = data.technicalRequirements;
        } else if (Array.isArray(data.technicalRequirements)) {
          data.technicalRequirements.forEach((req, index) => {
            if (req.description) {
              formattedTechReqs += `${index + 1}. ${req.description}\n\n`;
            }
          });
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
    
    // Match numbered requirements (1., 2., etc.) and extract everything after the number
    const numberedMatch = line.match(/^(\d+\.)\s+(.*)/);
    if (numberedMatch) {
      const description = numberedMatch[2].trim();
      if (description) {
        reqList.push({ text: description });
      }
      continue;
    }
    
    // Match bullet points (-, *, •)
    const bulletMatch = line.match(/^([*-•])\s+(.*)/);
    if (bulletMatch) {
      reqList.push({ text: bulletMatch[2].trim() });
      continue;
    }
  }
  
  // If no numbered or bulleted requirements found, try to extract substantive lines
  if (reqList.length === 0) {
    lines.forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith("#") && trimmed.length > 10) {
        reqList.push({ text: trimmed });
      }
    });
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
    console.log("🚀 Starting code conversion");

    try {
      if (!isBackendAvailable) {
        setTimeout(() => {
          const simulatedCode = `// Simulated C# code\npublic class CobolConverter {\n    public static void Main(string[] args) {\n        Console.WriteLine(\"This is a simulated conversion\");\n    }\n}`;
          const simulatedUnitTests = `// Simulated Unit Tests\n@Test\npublic void testConversion() {\n    assertTrue(true);\n}`;
          const simulatedFunctionalTests = `// Simulated Functional Tests\nFeature: Basic Functionality\n  Scenario: Test basic conversion\n    Given the COBOL code is valid\n    When the conversion is performed\n    Then the output should be valid ${targetLanguage} code`;

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
        const errorText = await response.text();
        console.error("Conversion failed:", errorText);
        let errorMessage = `Conversion failed: ${response.status}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.message || errorMessage;
        } catch (e) {
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log("✅ Conversion completed:", data);

      // Store the full response
      setConversionResponse(data);

      // Handle the complex convertedCode structure
      setConvertedCode(data.convertedCode || "");
      setUnitTests(data.unitTests || "");
      setFunctionalTests(data.functionalTests || "");
      setConvertedFiles(data.files || {});
      setActiveTab("output");

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
  };

  const handleCopyRequirements = () => {
  // Use a ref or get the element directly
  const elementId = activeRequirementsTab === "business" ? "businessReq" : "technicalReq";
  const element = document.getElementById(elementId);

  if (element) {
    const textToCopy = element.innerText; // Copies what’s actually displayed

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
  };

  return <>{children(enhancedProps)}</>;
}