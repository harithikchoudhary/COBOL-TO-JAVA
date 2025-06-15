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
}) {
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
    if (convertedCode && targetLanguage) {
      const structure = parseCodeToFileStructure(
        convertedCode,
        targetLanguage,
        unitTests
      );
      setFileStructure(structure);

      // Select first file by default
      if (structure && Object.keys(structure.files || {}).length > 0) {
        const firstFilePath = Object.keys(structure.files)[0];
        setSelectedFile(firstFilePath);
        setSelectedFileContent(structure.files[firstFilePath]);
      }
    }
  }, [convertedCode, targetLanguage, unitTests]);

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

  const parseCodeToFileStructure = (code, language, unitTests) => {
    if (!code) return {};

    if (
      language.toLowerCase().includes("spring") ||
      language.toLowerCase().includes("java")
    ) {
      return parseJavaSpringStructure(code, unitTests);
    } else if (
      language.toLowerCase().includes("c#") ||
      language.toLowerCase().includes("csharp") ||
      language.toLowerCase().includes(".net")
    ) {
      return parseCSharpStructure(code);
    } else {
      // Default case - just show as single file
      return {
        name: "root",
        isFolder: true,
        children: ["Main"],
        files: {
          Main: code,
        },
      };
    }
  };

  const parseJavaSpringStructure = (code, unitTests) => {
    console.log("Parsing Java Spring structure", code);
    const structure = {
      name: "src",
      isFolder: true,
      children: ["main", "test"],
      files: {},
    };

    const fileNameMatch = code.match(/FileName:\s*(\w+)\.java/);
    const className = fileNameMatch ? fileNameMatch[1] : "Employee";

    const cleanCode = (codeContent) => {
      if (!codeContent) return "";

      // Remove FileName header and footer, along with any surrounding whitespace
      let cleaned = codeContent
        .replace(/FileName:\s*\w+\.java\s*\n?/g, "") // Remove all occurrences of FileName
        .replace(/\s*FileName:\s*\w+\.java\s*$/g, "") // Remove FileName from end of file
        .trim();

      // Remove section markers
      cleaned = cleaned.replace(
        /##(Entity|Repository|Service|Controller|Tests|Dependencies|application\.properties)\s*/g,
        ""
      );

      // Clean up extra whitespace and newlines
      cleaned = cleaned
        .replace(/\n{3,}/g, "\n\n") // Replace multiple newlines with double newlines
        .replace(/[ \t]+$/gm, ""); // Remove trailing whitespace from each line

      return cleaned;
    };

    // Extract different components from the code
    const entityMatch = code.match(/##Entity([\s\S]*?)(?=##|$)/);
    const repositoryMatch = code.match(/##Repository([\s\S]*?)(?=##|$)/);
    const serviceMatch = code.match(/##Service([\s\S]*?)(?=##|$)/);
    const controllerMatch = code.match(/##Controller([\s\S]*?)(?=##|$)/);
    const configMatch = code.match(
      /##application\.properties([\s\S]*?)(?=##|$)/
    );
    const dependenciesMatch = code.match(/##Dependencies([\s\S]*?)(?=##|$)/);
    const testMatch = code.match(/##Tests([\s\S]*?)(?=##|$)/);

    console.log("Entity Match:", entityMatch);
    console.log("Repository Match:", repositoryMatch);
    console.log("Service Match:", serviceMatch);
    console.log("Controller Match:", controllerMatch);
    console.log("Config Match:", configMatch);
    console.log("Dependencies Match:", dependenciesMatch);
    console.log("Test Match:", testMatch);

    const cleanCode2 = (codeContent) => {
      if (!codeContent) return codeContent;
      return codeContent.replace(/FileName:\s*\w+\.java\s*\n?/, "").trim();
    };

    // Create the file structure
    structure.children = ["main", "test"];
    structure.expanded = {
      src: true,
      "src/main": true,
      "src/test": true,
      "src/test/java": true,
      "src/test/java/com": true,
      "src/test/java/com/demo": true,
      "src/main/java": true,
      "src/main/java/com": true,
      "src/main/java/com/demo": true,
    };

    // Populate files
    structure.files = {};

    if (entityMatch) {
      structure.files[`src/main/java/com/demo/entity/${className}.java`] =
        cleanCode(entityMatch[1].trim());
    }

    if (repositoryMatch) {
      structure.files[
        `src/main/java/com/demo/repository/${className}Repository.java`
      ] = cleanCode(repositoryMatch[1].trim());
    }

    if (serviceMatch) {
      structure.files[
        `src/main/java/com/demo/service/${className}Service.java`
      ] = cleanCode(serviceMatch[1].trim());
    }

    if (controllerMatch) {
      structure.files[
        `src/main/java/com/demo/controller/${className}Controller.java`
      ] = cleanCode(controllerMatch[1].trim());
    }

    if (configMatch) {
      structure.files["src/main/resources/application.properties"] = cleanCode(
        configMatch[1].trim()
      );
    } else {
      structure.files[
        "src/main/resources/application.properties"
      ] = `spring.datasource.url=jdbc:mysql://localhost:3306/yourDatabaseName?useSSL=false&serverTimezone=UTC&createDatabaseIfNotExist=true
spring.datasource.username=root
spring.datasource.password=password
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=true
spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.MySQLDialect`;
    }

    if (dependenciesMatch) {
      structure.files["pom.xml"] = `<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.4.5</version>
    <relativePath/> <!-- lookup parent from repository -->
  </parent>
  <groupId>com.example</groupId>
  <artifactId>${className.toLowerCase()}-management</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <name>${className.toLowerCase()}-management</name>
  <description>${className} Management System</description>
  <url />
  <licenses>
    <license/>
  </licenses>
  <developers>
    <developer/>
  </developers>
  <scm>
    <connection/>
    <developerConnection/>
    <tag/>
    <url/>
  </scm>
  <properties>
    <java.version>17</java.version>
  </properties>
    ${dependenciesMatch[1].trim()}
  
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>`;
    }

    // Add main application class
    structure.files[
      `src/main/java/com/${className}ManagementApplication.java`
    ] = `package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class ${className}ManagementApplication {
    public static void main(String[] args) {
        SpringApplication.run(${className}ManagementApplication.class, args);
    }
}`;

    // Add test files
    if (unitTests || testMatch) {
      // Use unitTests prop if available, otherwise fall back to testMatch
      const testContent = unitTests || (testMatch ? testMatch[1].trim() : "");
      if (testContent) {
        structure.files[`src/test/java/com/${className}ServiceTest.java`] =
          testContent;
      } else {
        // Create default test files to ensure the test structure is visible
        structure.files[
          `src/test/java/com/${className}ServiceTest.java`
        ] = `Test Cases Not Generated`;
      }
    }

    // Add .gitignore file
    structure.files[".gitignore"] = `HELP.md
target/
!.mvn/wrapper/maven-wrapper.jar
!**/src/main/**/target/
!**/src/test/**/target/

### STS ###
.apt_generated
.classpath
.factorypath
.project
.settings
.springBeans
.sts4-cache

### IntelliJ IDEA ###
.idea
*.iws
*.iml
*.ipr

### NetBeans ###
/nbproject/private/
/nbbuild/
/dist/
/nbdist/
/.nb-gradle/
build/
!**/src/main/**/build/
!**/src/test/**/build/

### VS Code ###
.vscode/`;

    // Add .gitattributes file
    structure.files[
      ".gitattributes"
    ] = `# Set default behavior to automatically normalize line endings
* text=auto

# Explicitly declare text files you want to always be normalized and converted to native line endings on checkout
*.java text
*.xml text
*.properties text
*.md text

# Declare files that will always have CRLF line endings on checkout
*.bat text eol=crlf
mvnw.cmd text eol=crlf

# Declare files that will always have LF line endings on checkout
*.sh text eol=lf
mvnw text eol=lf

# Denote all files that are truly binary and should not be modified
*.jar binary
*.png binary
*.jpg binary`;

    // Add mvnw script
    structure.files["mvnw"] = `#!/bin/sh
# ----------------------------------------------------------------------------
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
# ----------------------------------------------------------------------------

# Maven wrapper script for Unix platforms - actual content truncated for brevity
# In a real implementation, this would contain the full Maven wrapper shell script`;

    // Add mvnw.cmd script
    structure.files[
      "mvnw.cmd"
    ] = `@REM ----------------------------------------------------------------------------
@REM Licensed to the Apache Software Foundation (ASF) under one
@REM or more contributor license agreements.  See the NOTICE file
@REM distributed with this work for additional information
@REM regarding copyright ownership.  The ASF licenses this file
@REM to you under the Apache License, Version 2.0 (the
@REM "License"); you may not use this file except in compliance
@REM with the License.  You may obtain a copy of the License at
@REM
@REM    https://www.apache.org/licenses/LICENSE-2.0
@REM
@REM Unless required by applicable law or agreed to in writing,
@REM software distributed under the License is distributed on an
@REM "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
@REM KIND, either express or implied.  See the License for the
@REM specific language governing permissions and limitations
@REM under the License.
@REM ----------------------------------------------------------------------------

@REM Maven wrapper script for Windows - actual content truncated for brevity
@REM In a real implementation, this would contain the full Maven wrapper batch script`;

    // Add .mvn/wrapper/maven-wrapper.properties
    // First, create the directory structure in the expanded property if it doesn't exist
    structure.expanded[".mvn"] = true;
    structure.expanded[".mvn/wrapper"] = true;

    // Then add the file
    structure.files[
      ".mvn/wrapper/maven-wrapper.properties"
    ] = `# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
wrapperVersion=3.3.2
distributionType=only-script
distributionUrl=https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.9/apache-maven-3.9.9-bin.zip`;

    return structure;
  };

  const parseCSharpStructure = (code) => {
    console.log("Parsing C# structure", code);
    const structure = {
      name: "src",
      isFolder: true,
      children: ["YourNamespace"],
      files: {},
    };

    const cleanCode = (codeContent) => {
      if (!codeContent) return "";

      // Remove FileName header and footer, along with any surrounding whitespace
      let cleaned = codeContent
        .replace(/FileName:\s*\w+\.cs\s*\n?/g, "") // Remove all occurrences of FileName
        .replace(/\s*FileName:\s*\w+\.cs\s*$/g, "") // Remove FileName from end of file
        .trim();

      // Remove section markers
      cleaned = cleaned.replace(
        /##(Entity|Repository|Service|Controller|application\.properties|Dependencies)\s*/g,
        ""
      );

      // Clean up extra whitespace and newlines
      cleaned = cleaned
        .replace(/\n{3,}/g, "\n\n") // Replace multiple newlines with double newlines
        .replace(/[ \t]+$/gm, ""); // Remove trailing whitespace from each line

      return cleaned;
    };

    // Extract different components from the code
    const entityMatch = code.match(/##Entity([\s\S]*?)(?=##|$)/);
    const repositoryMatch = code.match(/##Repository([\s\S]*?)(?=##|$)/);
    const serviceMatch = code.match(/##Service([\s\S]*?)(?=##|$)/);
    const controllerMatch = code.match(/##Controller([\s\S]*?)(?=##|$)/);
    const appSettingsMatch = code.match(/##application\.properties([\s\S]*?)(?=##|$)/);
    const dependenciesMatch = code.match(/##Dependencies([\s\S]*?)(?=##|$)/);

    console.log("Entity Match:", entityMatch);
    console.log("Repository Match:", repositoryMatch);
    console.log("Service Match:", serviceMatch);
    console.log("Controller Match:", controllerMatch);
    console.log("AppSettings Match:", appSettingsMatch);
    console.log("Dependencies Match:", dependenciesMatch);

    // Create the file structure
    structure.children = ["YourNamespace"];
    structure.expanded = {
      src: true,
      "src/YourNamespace": true,
      "src/YourNamespace/Models": true,
      "src/YourNamespace/Controllers": true,
      "src/YourNamespace/Services": true,
      "src/YourNamespace/Repositories": true,
    };

    // Populate files
    structure.files = {};

    if (entityMatch) {
      const entityContent = entityMatch[1].trim();
      const fileNameMatch = entityContent.match(/FileName:\s*(\w+)\.cs/);
      const fileName = fileNameMatch ? fileNameMatch[1] : "User";
      structure.files[`src/YourNamespace/Models/${fileName}.cs`] = cleanCode(entityContent);
    }

    if (repositoryMatch) {
      const repositoryContent = repositoryMatch[1].trim();
      const files = repositoryContent.split(/FileName:\s*/).filter(Boolean);
      
      files.forEach(file => {
        const fileNameMatch = file.match(/^(\w+)\.cs/);
        if (fileNameMatch) {
          const fileName = fileNameMatch[1];
          structure.files[`src/YourNamespace/Repositories/${fileName}.cs`] = cleanCode(file);
        }
      });
    }

    if (serviceMatch) {
      const serviceContent = serviceMatch[1].trim();
      const files = serviceContent.split(/FileName:\s*/).filter(Boolean);
      
      files.forEach(file => {
        const fileNameMatch = file.match(/^(\w+)\.cs/);
        if (fileNameMatch) {
          const fileName = fileNameMatch[1];
          structure.files[`src/YourNamespace/Services/${fileName}.cs`] = cleanCode(file);
        }
      });
    }

    if (controllerMatch) {
      const controllerContent = controllerMatch[1].trim();
      const fileNameMatch = controllerContent.match(/FileName:\s*(\w+)\.cs/);
      const fileName = fileNameMatch ? fileNameMatch[1] : "LoginController";
      structure.files[`src/YourNamespace/Controllers/${fileName}.cs`] = cleanCode(controllerContent);
    }

    if (appSettingsMatch) {
      structure.files[`src/YourNamespace/appsettings.json`] = cleanCode(appSettingsMatch[1].trim());
    }

    if (dependenciesMatch) {
      structure.files[`src/YourNamespace/YourNamespace.csproj`] = cleanCode(dependenciesMatch[1].trim());
    }

    // Add Program.cs
    structure.files[`src/YourNamespace/Program.cs`] = `using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using YourNamespace.Services;
using YourNamespace.Repositories;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Register services
builder.Services.AddScoped<IUserRepository, UserRepository>();
builder.Services.AddScoped<ILoginService, LoginService>();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();`;

    // Add ApplicationDbContext.cs
    structure.files[`src/YourNamespace/Data/ApplicationDbContext.cs`] = `using Microsoft.EntityFrameworkCore;
using YourNamespace.Models;

namespace YourNamespace.Data
{
    public class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        public DbSet<User> Users { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);
            
            modelBuilder.Entity<User>()
                .HasKey(u => u.UserId);
        }
    }
}`;

    return structure;
  };

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
      const parts = filePath.split("/");
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
    const rootFolders = Object.entries(filesByFolder)
      .filter(([path, item]) => !item.parent)
      .map(([path, item]) => path);

    return (
      <div className="file-tree ps-2">
        {rootFolders.map((folderPath) => {
          const folder = filesByFolder[folderPath];
          return renderFileTreeItem(folderPath, folder, filesByFolder);
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

  const handleDownloadZip = async () => {
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
      saveAs(
        zipBlob,
        `${
          targetLanguage.toLowerCase().includes("java")
            ? "spring-java"
            : "csharp"
        }-project.zip`
      );
    } catch (error) {
      console.error("Error generating zip file:", error);
    } finally {
      setIsGeneratingZip(false);
    }
  };

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
