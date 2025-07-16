import { useState, useEffect, useRef } from "react";
import {
  FileCode,
  FileSearch,
  Copy,
  Download,
  ClipboardList,
  RefreshCw,
  CheckCircle,
  Folder,
  FolderOpen,
  FileText,
  ChevronRight,
  ChevronDown,
  FileArchive,
} from "lucide-react";
import JSZip from "jszip";
import { saveAs } from "file-saver";

export default function Output({
  convertedCode,
  unitTests,
  functionalTests,
  activeOutputTab,
  setActiveOutputTab,
  copyStatus,
  setActiveTab,
  handleReset,
  targetLanguage,
  convertedFiles,
}) {
  useEffect(() => {
    console.log("convertedFiles in Output:", convertedFiles);
  }, [convertedFiles]);
  const [fileStructure, setFileStructure] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedFileContent, setSelectedFileContent] = useState("");
  const [expandedFolders, setExpandedFolders] = useState({});
  const [isGeneratingZip, setIsGeneratingZip] = useState(false);
  const [localCopyStatus, setLocalCopyStatus] = useState(false);

  // Refs for code content containers
  const codeContentRef = useRef(null);
  const functionalTestsContentRef = useRef(null);

  useEffect(() => {
    console.log("convertedFiles in Output:", convertedFiles);
    if (convertedFiles && Object.keys(convertedFiles).length > 0) {
      const structure = {
        files: convertedFiles
      };
      setFileStructure(structure);
      const firstFilePath = Object.keys(convertedFiles)[0];
      setSelectedFile(firstFilePath);
      setSelectedFileContent(convertedFiles[firstFilePath]);
    } else {
      setFileStructure({ files: {} });
      setSelectedFile(null);
      setSelectedFileContent("");
      console.warn("No converted files received from backend");
    }
  }, [convertedFiles]);

  // Reset local copy status when the parent component's copy status changes
  useEffect(() => {
    setLocalCopyStatus(copyStatus);
  }, [copyStatus]);

  // Enhanced copy function that selects all content and copies to clipboard
  const enhancedCopyCode = () => {
    let contentToCopy = "";
    let contentElement = null;

    // Determine which content to copy based on active tab
    if (activeOutputTab === "code") {
      contentToCopy = selectedFileContent;
      contentElement = codeContentRef.current;
    } else if (activeOutputTab === "functional-tests") {
      contentToCopy = functionalTests;
      contentElement = functionalTestsContentRef.current;
    }

    if (contentToCopy && contentElement) {
      try {
        // First try to select the text in the DOM
        if (document.body.createTextRange) {
          // For IE
          const range = document.body.createTextRange();
          range.moveToElementText(contentElement);
          range.select();
        } else if (window.getSelection) {
          // For other browsers
          const selection = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(contentElement);
          selection.removeAllRanges();
          selection.addRange(range);
        }

        // Then copy to clipboard
        navigator.clipboard
          .writeText(contentToCopy)
          .then(() => {
            setLocalCopyStatus(true);
            // Reset copy status after 3 seconds
            setTimeout(() => {
              setLocalCopyStatus(false);
            }, 3000);
          })
          .catch((err) => {
            console.error("Failed to copy: ", err);
            // Fallback for older browsers
            document.execCommand("copy");
            setLocalCopyStatus(true);
            setTimeout(() => {
              setLocalCopyStatus(false);
            }, 3000);
          });
      } catch (err) {
        console.error("Copy failed: ", err);
      }
    }
  };

  // Selects all content in the current view
  const selectAllContent = () => {
    let contentElement = null;

    if (activeOutputTab === "code") {
      contentElement = codeContentRef.current;
    } else if (activeOutputTab === "functional-tests") {
      contentElement = functionalTestsContentRef.current;
    }

    if (contentElement) {
      if (document.body.createTextRange) {
        // For IE
        const range = document.body.createTextRange();
        range.moveToElementText(contentElement);
        range.select();
      } else if (window.getSelection) {
        // For other browsers
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(contentElement);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }
  };

  // Remove generateGuid and parseBackendResponse and any remaining references to old file tree logic
  // Only use convertedFiles for file tree and content display.
  // The original code had these functions, but they are no longer used.
  // The new_code_to_apply_from block implies they are removed.
  // Therefore, I will remove them from the file.

  const toggleFolder = (path) => {
    setExpandedFolders((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  const selectFile = (path) => {
    setSelectedFile(path);
    setSelectedFileContent(fileStructure.files[path]);
  };

  const renderFileTree = (structure, path = "", level = 0) => {
    if (!structure) return null;

    const files = structure.files || {};
    const filePaths = Object.keys(files);

    // Group files by folders
    const filesByFolder = {};

    filePaths.forEach((filePath) => {
      const parts = filePath.split(/[\\/]/); // Split on both / and \
      let currentPath = "";

      // Build folder structure
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        const parentPath = currentPath;
        currentPath = currentPath ? `${currentPath}/${part}` : part;

        if (!filesByFolder[currentPath]) {
          filesByFolder[currentPath] = {
            name: part,
            isFolder: true,
            parent: parentPath,
            children: [],
          };

          // Add to parent's children
          if (parentPath && filesByFolder[parentPath]) {
            if (!filesByFolder[parentPath].children.includes(currentPath)) {
              filesByFolder[parentPath].children.push(currentPath);
            }
          }
        }
      }

      // Add the file to its parent folder
      const fileName = parts[parts.length - 1];
      const parentFolder = parts.slice(0, -1).join("/");

      if (parentFolder && filesByFolder[parentFolder]) {
        if (!filesByFolder[parentFolder].children.includes(filePath)) {
          filesByFolder[parentFolder].children.push(filePath);
        }
      }

      // Add file entry
      filesByFolder[filePath] = {
        name: fileName,
        isFolder: false,
        parent: parentFolder,
        content: files[filePath],
      };
    });

    // Render the root level
    let rootFolders = Object.entries(filesByFolder)
      .filter(([path, item]) => !item.parent && item.isFolder)
      .map(([path, item]) => path);

    // Custom sort: main project folder first, then .Tests, then others
    if (rootFolders.length > 1) {
      const mainProject = rootFolders.find(name => !name.endsWith('.Tests'));
      if (mainProject) {
        rootFolders = rootFolders.sort((a, b) => {
          if (a === mainProject) return -1;
          if (b === mainProject) return 1;
          if (a === `${mainProject}.Tests`) return 1;
          if (b === `${mainProject}.Tests`) return -1;
          return a.localeCompare(b);
        });
      }
    }

    // Get root files (not in any folder)
    let rootFiles = Object.entries(filesByFolder)
      .filter(([path, item]) => !item.isFolder && !item.parent)
      .map(([path, item]) => path);

    // Custom sort: .sln files last
    rootFiles = rootFiles.sort((a, b) => {
      const aIsSln = a.endsWith('.sln');
      const bIsSln = b.endsWith('.sln');
      if (aIsSln && !bIsSln) return 1;
      if (!aIsSln && bIsSln) return -1;
      return a.localeCompare(b);
    });

    return (
      <div className="file-tree ps-2">
        {rootFolders.map((folderPath) => {
          const folder = filesByFolder[folderPath];
          return renderFileTreeItem(folderPath, folder, filesByFolder);
        })}
        {rootFiles.map((filePath) => {
          const file = filesByFolder[filePath];
          return renderFileTreeItem(filePath, file, filesByFolder);
        })}
      </div>
    );
  };

  const renderFileTreeItem = (path, item, filesByFolder) => {
    if (!item) return null;

    const isExpanded = expandedFolders[path];
    const paddingLeft = path.split("/").length * 10;

    if (item.isFolder) {
      return (
        <div key={path} className="folder">
          <div
            className={`d-flex align-items-center py-1 px-2 rounded ${
              expandedFolders[path] ? "fw-semibold" : ""
            }`}
            style={{ paddingLeft: `${paddingLeft}px`, cursor: "pointer" }}
            onClick={() => toggleFolder(path)}
          >
            {isExpanded ? (
              <ChevronDown size={16} className="text-secondary me-1" />
            ) : (
              <ChevronRight size={16} className="text-secondary me-1" />
            )}
            {isExpanded ? (
              <FolderOpen size={16} className="text-warning me-2" />
            ) : (
              <Folder size={16} className="text-warning me-2" />
            )}
            <span className="text-truncate">{item.name}</span>
          </div>

          {isExpanded && item.children && (
            <div className="ps-4">
              {item.children
                .sort((a, b) => {
                  const aItem = filesByFolder[a];
                  const bItem = filesByFolder[b];
                  // Sort folders first, then files
                  if (aItem.isFolder && !bItem.isFolder) return -1;
                  if (!aItem.isFolder && bItem.isFolder) return 1;
                  return aItem.name.localeCompare(bItem.name);
                })
                .map((childPath) => {
                  return renderFileTreeItem(
                    childPath,
                    filesByFolder[childPath],
                    filesByFolder
                  );
                })}
            </div>
          )}
        </div>
      );
    } else {
      return (
        <div
          key={path}
          className={`d-flex align-items-center py-1 px-2 rounded ${
            selectedFile === path ? "bg-primary-subtle" : ""
          }`}
          style={{ paddingLeft: `${paddingLeft + 20}px`, cursor: "pointer" }}
          onClick={() => selectFile(path)}
        >
          <FileText size={16} className="text-primary me-2" />
          <span className="text-truncate">{item.name}</span>
        </div>
      );
    }
  };

  async function handleDownloadZip() {
    setIsGeneratingZip(true);
  
    try {
      const zip = new JSZip();
  
      // Add all files to the zip
      const files = fileStructure.files || {};
      Object.entries(files).forEach(([path, content]) => {
        zip.file(path, content);
      });
  
      // Generate the zip file
      const zipBlob = await zip.generateAsync({ type: "blob" });
  
      // Save the zip file
      saveAs(zipBlob, "dotnet8-project.zip");
    } catch (error) {
      console.error("Error generating zip file:", error);
    } finally {
      setIsGeneratingZip(false);
    }
  }

  const handleDoubleClick = (e) => {
    selectAllContent();
  };

  return (
    <div className="mb-4">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <div className="d-flex align-items-center gap-2">
          <button
            className={`px-4 py-2 rounded-3 ${
              activeOutputTab === "code"
                ? "text-white"
                : "bg-white text-dark border border-dark"
            }`}
            style={{
              backgroundColor: activeOutputTab === "code" ? "#0d9488" : "",
            }}
            onClick={() => setActiveOutputTab("code")}
          >
            <div className="d-flex align-items-center">
              <FileCode size={16} className="me-2" />
              Converted Code
            </div>
          </button>
          <button
            className={`px-4 py-2 rounded-3 ${
              activeOutputTab === "functional-tests"
                ? "text-white"
                : "bg-white text-dark border border-dark"
            }`}
            style={{
              backgroundColor:
                activeOutputTab === "functional-tests" ? "#0d9488" : "",
            }}
            onClick={() => setActiveOutputTab("functional-tests")}
          >
            <div className="d-flex align-items-center">
              <FileSearch size={16} className="me-2" />
              Functional Tests
            </div>
          </button>
        </div>

        <div className="d-flex justify-content-end gap-2">
          <button
            className={`d-flex align-items-center ${
              localCopyStatus ? "" : "bg-secondary"
            } text-white rounded px-4 py-2 border border-white ${
              !convertedCode ? "opacity-50 disabled" : ""
            }`}
            style={{ backgroundColor: localCopyStatus ? "#0d9488" : "" }}
            onClick={enhancedCopyCode}
            disabled={!convertedCode}
          >
            {localCopyStatus ? (
              <>
                <CheckCircle size={16} className="me-2" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy size={16} className="me-2" />
                <span>Copy Code</span>
              </>
            )}
          </button>
          <button
            className={`d-flex align-items-center bg-secondary text-white rounded px-3 py-2 border border-white ${
              !convertedCode || isGeneratingZip ? "opacity-50 disabled" : ""
            }`}
            disabled={!convertedCode || isGeneratingZip}
            onClick={handleDownloadZip}
          >
            <FileArchive size={16} className="me-1 text-white" />
            <span>{isGeneratingZip ? "Generating..." : "Download ZIP"}</span>
          </button>
        </div>
      </div>

      {activeOutputTab === "code" ? (
        <div
          className="bg-white rounded-3 border border-dark shadow overflow-hidden"
          style={{ height: "500px" }}
        >
          <div className="d-flex align-items-center bg-light px-4 py-2 border-bottom">
            <span className="text-dark fw-medium">
              {`${targetLanguage} Project Structure`}
            </span>
          </div>
          <div className="d-flex" style={{ height: "calc(100% - 43px)" }}>
            {/* File tree section */}
            <div
              className="w-25 border-end bg-light"
              style={{ height: "100%", overflowY: "auto" }}
            >
              {renderFileTree(fileStructure)}
            </div>

            {/* File content section */}
            <div className="w-75" style={{ height: "100%" }}>
              {selectedFile ? (
                <div className="h-100 d-flex flex-column">
                  <div className="bg-light px-4 py-2 fs-6 font-monospace border-bottom d-flex justify-content-between align-items-center">
                    <span>{selectedFile}</span>
                  </div>
                  <div
                    className="overflow-auto flex-grow-1"
                    onDoubleClick={handleDoubleClick}
                    ref={codeContentRef}
                  >
                    <div className="d-flex">
                      <div
                        className="pe-2 text-end text-secondary user-select-none font-monospace fs-6 border-end border-secondary me-2"
                        style={{ minWidth: "32px" }}
                      >
                        {Array.from(
                          {
                            length: Math.max(
                              selectedFileContent.split("\n").length,
                              1
                            ),
                          },
                          (_, i) => (
                            <div key={i} style={{ height: "24px" }}>
                              {i + 1}
                            </div>
                          )
                        )}
                      </div>
                      <pre
                        className="text-dark font-monospace fs-6 w-100"
                        style={{ lineHeight: "1.5" }}
                      >
                        {selectedFileContent}
                      </pre>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="d-flex align-items-center justify-content-center h-100 text-secondary">
                  Select a file to view its content
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div
          className="bg-white rounded-3 border border-dark shadow overflow-hidden"
          style={{ height: "500px" }}
        >
          <div className="d-flex align-items-center bg-light px-4 py-2 border-bottom">
            <span className="text-dark fw-medium">Functional Test Cases</span>
          </div>
          <div
            className="p-2 overflow-auto"
            style={{ height: "calc(100% - 43px)" }}
            onDoubleClick={handleDoubleClick}
            ref={functionalTestsContentRef}
          >
            <div className="text-dark font-monospace fs-6 w-100">
              {typeof functionalTests === 'string' ? (
                functionalTests.split("\n").map((line, index) => {
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
                        className="fs-4 fw-semibold text-dark mt-3 mb-2"
                      >
                        {line.replace("## ", "")}
                      </h4>
                    );
                  }
                  return <div key={index}>{line}</div>;
                })
              ) : (
                // Handle JSON object format
                <div>
                  {functionalTests.functionalTests && functionalTests.functionalTests.map((test, index) => (
                    <div key={index} className="mb-4">
                      <h4 className="fs-4 fw-semibold text-dark mt-3 mb-2">
                        {test.id}: {test.title}
                      </h4>
                      <div className="ms-3">
                        <h5 className="fs-5 fw-medium">Steps:</h5>
                        <ol>
                          {test.steps.map((step, stepIndex) => (
                            <li key={stepIndex}>{step}</li>
                          ))}
                        </ol>
                        <h5 className="fs-5 fw-medium">Expected Result:</h5>
                        <p>{test.expectedResult}</p>
                      </div>
                    </div>
                  ))}
                  {functionalTests.testStrategy && (
                    <div className="mt-4">
                      <h4 className="fs-4 fw-semibold text-dark">Test Strategy</h4>
                      <p>{functionalTests.testStrategy}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="d-flex justify-content-center gap-5 mt-3">
        <button
          className="bg-white text-dark fw-medium px-4 py-2 rounded-3 border border-dark"
          onClick={() => setActiveTab("requirements")}
        >
          <div className="d-flex align-items-center">
            <ClipboardList
              size={18}
              className="me-2"
              style={{ color: "#0d9488" }}
            />
            View Requirements
          </div>
        </button>
        <button
          className="bg-white text-dark fw-medium px-4 py-2 rounded-3 border border-dark"
          onClick={handleReset}
        >
          <div className="d-flex align-items-center">
            <RefreshCw size={18} className="me-2 text-danger" />
            Start New Conversion
          </div>
        </button>
      </div>
    </div>
  );
}
