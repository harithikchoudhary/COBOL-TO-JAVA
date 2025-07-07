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
      language.toLowerCase().includes("c#") ||
      language.toLowerCase().includes("csharp") ||
      language.toLowerCase().includes(".net")
    ) {
      return parseCSharpStructure(code, unitTests);
    } else {
      // Default case - just show as single file
      return {
        name: "root",
        isFolder: true,
        children: ["Main"],
        files: {
          Main: typeof code === "string" ? code : JSON.stringify(code, null, 2),
        },
      };
    }
  };

  const parseCSharpStructure = (backendResponse, includeTests = true) => {
    console.log("Parsing C# structure from backend response", backendResponse);
    
    // Extract the main conversion data
    const codeObj = backendResponse.convertedCode || backendResponse;
    const unitTestsData =  unitTests;
    console.log("backend response",backendResponse);
    console.log("Unit Test cases",unitTestsData);
    
    // Extract class name dynamically from Entity or derive from content
    let className = "Employee";
    let projectName = "Company.Project";

    // Try to extract actual class/project name from the converted code
    if (codeObj.Entity && codeObj.Entity.content) {
        const entityMatch = codeObj.Entity.content.match(/public class (\w+)/);
        if (entityMatch) {
            className = entityMatch[1];
        }
        
        // Extract namespace/project name
        const namespaceMatch = codeObj.Entity.content.match(/namespace ([^\n\r{]+)/);
        if (namespaceMatch) {
            projectName = namespaceMatch[1].trim();
        }
    } else {
        // Fallback: try to derive from any available content
        const allContent = Object.values(codeObj).map(item => 
            typeof item === 'object' && item.content ? item.content : ''
        ).join('\n');
        
        const namespaceMatch = allContent.match(/namespace ([^\n\r{]+)/);
        if (namespaceMatch) {
            projectName = namespaceMatch[1].trim();
        }
        
        const classMatch = allContent.match(/public class (\w+)/);
        if (classMatch) {
            className = classMatch[1];
        }
    }

    // If still default values, try to derive from backend response metadata
    if (projectName === "Company.Project" && backendResponse.sourceLanguage) {
        // Use a more generic project name
        projectName = "ConvertedApp";
    }
    
    if (codeObj.Entity && codeObj.Entity.content) {
        const entityMatch = codeObj.Entity.content.match(/public class (\w+)/);
        if (entityMatch) {
            className = entityMatch[1];
        }
        
        // Extract namespace/project name
        const namespaceMatch = codeObj.Entity.content.match(/namespace ([^\n\r{]+)/);
        if (namespaceMatch) {
            projectName = namespaceMatch[1].trim();
        }
    }
    
    console.log(`Detected class name: ${className}, project: ${projectName}`);
    
    const structure = {
        isFolder: true,
        children: [projectName],
        files: {},
        expanded: {
            [projectName]: true,
            [`${projectName}/Models`]: true,
            [`${projectName}/Controllers`]: true,
            [`${projectName}/Services`]: true,
            [`${projectName}/Services/Interfaces`]: true,
            [`${projectName}/Repositories`]: true,
            [`${projectName}/Repositories/Interfaces`]: true,
            [`${projectName}/Data`]: true,
            [`${projectName}/DTOs`]: true,
            [`${projectName}/Middleware`]: true,
            [`${projectName}/Configuration`]: true,
            [`${projectName}/Validators`]: true,
            [`${projectName}/Helpers`]: true,
            [`${projectName}/Extensions`]: true
        }
    };

    // Helper function to safely extract content
    const getContent = (section) => {
        if (!codeObj[section]) return "";
        return typeof codeObj[section] === "string" 
            ? codeObj[section] 
            : (codeObj[section].content || "");
    };

    // Helper function to safely extract filename
    const getFileName = (section, defaultName = "") => {
        if (!codeObj[section]) return defaultName;
        return codeObj[section].FileName || defaultName;
    };

    // Helper function to safely extract path and normalize it
    const getPath = (section, defaultPath = "") => {
        if (!codeObj[section]) return defaultPath;
        let path = codeObj[section].Path || defaultPath;
        // Normalize path - remove leading/trailing slashes and handle "./"
        path = path.replace(/^\.\//, "").replace(/\/$/, "");
        return path;
    };

    // Helper function to ensure directory structure exists
    const ensureDirectory = (dirPath) => {
        if (dirPath && !structure.expanded[`${projectName}/${dirPath}`]) {
            structure.expanded[`${projectName}/${dirPath}`] = true;
        }
    };

    // Helper function to add file to structure
    const addFileToStructure = (filePath, content) => {
        if (content && content.trim()) {
            structure.files[filePath] = content;
            // Ensure parent directory is expanded
            const dir = filePath.substring(0, filePath.lastIndexOf('/'));
            if (dir && dir !== projectName) {
                structure.expanded[dir] = true;
            }
        }
    };

    // Process all known file types from backend response
    const fileTypeMapping = {
        // Core application files
        'Entity': { defaultPath: 'Models', defaultName: `${className}.cs` },
        'Repository': { defaultPath: 'Repositories/Interfaces', defaultName: `I${className}Repository.cs` },
        'RepositoryImpl': { defaultPath: 'Repositories', defaultName: `${className}Repository.cs` },
        'Service': { defaultPath: 'Services/Interfaces', defaultName: `I${className}Service.cs` },
        'ServiceImpl': { defaultPath: 'Services', defaultName: `${className}Service.cs` },
        'Controller': { defaultPath: 'Controllers', defaultName: `${className}Controller.cs` },
        'DbContext': { defaultPath: 'Data', defaultName: 'ApplicationDbContext.cs' },
        
        // Configuration files
        'Program': { defaultPath: '', defaultName: 'Program.cs' },
        'Startup': { defaultPath: '', defaultName: 'Startup.cs' },
        'AppSettings': { defaultPath: '', defaultName: 'appsettings.json' },
        'AppSettingsDev': { defaultPath: '', defaultName: 'appsettings.Development.json' },
        'AppSettingsProd': { defaultPath: '', defaultName: 'appsettings.Production.json' },
        
        // Additional files that might be present
        'DTO': { defaultPath: 'DTOs', defaultName: `${className}DTO.cs` },
        'Validator': { defaultPath: 'Validators', defaultName: `${className}Validator.cs` },
        'Mapper': { defaultPath: 'Mappers', defaultName: `${className}Mapper.cs` },
        'Middleware': { defaultPath: 'Middleware', defaultName: 'CustomMiddleware.cs' },
        'Extension': { defaultPath: 'Extensions', defaultName: 'ServiceExtensions.cs' },
        'Helper': { defaultPath: 'Helpers', defaultName: 'ApplicationHelper.cs' },
        'Configuration': { defaultPath: 'Configuration', defaultName: 'AppConfiguration.cs' }
    };

    // Process each file type
    Object.keys(fileTypeMapping).forEach(fileType => {
        if (codeObj[fileType]) {
            const mapping = fileTypeMapping[fileType];
            const filePath = getPath(fileType, mapping.defaultPath);
            const fileName = getFileName(fileType, mapping.defaultName);
            const content = getContent(fileType);
            
            if (content) {
                const fullPath = filePath 
                    ? `${projectName}/${filePath}/${fileName}`
                    : `${projectName}/${fileName}`;
                
                addFileToStructure(fullPath, content);
                console.log(`✅ Added ${fileType}: ${fullPath}`);
            }
        }
    });

    // Handle multiple controllers if they exist as an array or object
    if (codeObj.Controllers && typeof codeObj.Controllers === 'object') {
        if (Array.isArray(codeObj.Controllers)) {
            // Handle array of controllers
            codeObj.Controllers.forEach((controller, index) => {
                const controllerName = controller.FileName || `Controller${index + 1}.cs`;
                const controllerPath = controller.Path || 'Controllers';
                const fullPath = `${projectName}/${controllerPath}/${controllerName}`;
                addFileToStructure(fullPath, controller.content);
                console.log(`✅ Added Controller ${index + 1}: ${fullPath}`);
            });
        } else {
            // Handle object with multiple controllers
            Object.keys(codeObj.Controllers).forEach(key => {
                const controller = codeObj.Controllers[key];
                const controllerName = controller.FileName || `${key}Controller.cs`;
                const controllerPath = controller.Path || 'Controllers';
                const fullPath = `${projectName}/${controllerPath}/${controllerName}`;
                addFileToStructure(fullPath, controller.content);
                console.log(`✅ Added Controller ${key}: ${fullPath}`);
            });
        }
    }

    // Handle multiple models/entities
    if (codeObj.Models && typeof codeObj.Models === 'object') {
        if (Array.isArray(codeObj.Models)) {
            codeObj.Models.forEach((model, index) => {
                const modelName = model.FileName || `Model${index + 1}.cs`;
                const modelPath = model.Path || 'Models';
                const fullPath = `${projectName}/${modelPath}/${modelName}`;
                addFileToStructure(fullPath, model.content);
                console.log(`✅ Added Model ${index + 1}: ${fullPath}`);
            });
        } else {
            Object.keys(codeObj.Models).forEach(key => {
                const model = codeObj.Models[key];
                const modelName = model.FileName || `${key}.cs`;
                const modelPath = model.Path || 'Models';
                const fullPath = `${projectName}/${modelPath}/${modelName}`;
                addFileToStructure(fullPath, model.content);
                console.log(`✅ Added Model ${key}: ${fullPath}`);
            });
        }
    }

    // Handle multiple services
    if (codeObj.Services && typeof codeObj.Services === 'object') {
        Object.keys(codeObj.Services).forEach(key => {
            const service = codeObj.Services[key];
            if (service && service.content) {
                const serviceName = service.FileName || `${key}Service.cs`;
                const servicePath = service.Path || 'Services';
                const fullPath = `${projectName}/${servicePath}/${serviceName}`;
                addFileToStructure(fullPath, service.content);
                console.log(`✅ Added Service ${key}: ${fullPath}`);
            }
        });
    }

    // Handle multiple repositories
    if (codeObj.Repositories && typeof codeObj.Repositories === 'object') {
        Object.keys(codeObj.Repositories).forEach(key => {
            const repository = codeObj.Repositories[key];
            if (repository && repository.content) {
                const repoName = repository.FileName || `${key}Repository.cs`;
                const repoPath = repository.Path || 'Repositories';
                const fullPath = `${projectName}/${repoPath}/${repoName}`;
                addFileToStructure(fullPath, repository.content);
                console.log(`✅ Added Repository ${key}: ${fullPath}`);
            }
        });
    }

    // Add default files if not provided by backend
    
    // Add default Program.cs if not provided
    if (!structure.files[`${projectName}/Program.cs`]) {
        const defaultProgramCs = `using Microsoft.AspNetCore.Builder;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using ${projectName}.Data;
using ${projectName}.Repositories;
using ${projectName}.Repositories.Interfaces;
using ${projectName}.Services;
using ${projectName}.Services.Interfaces;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Configure Entity Framework
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlServer(connectionString));

// Register repositories and services
builder.Services.AddScoped<I${className}Repository, ${className}Repository>();
builder.Services.AddScoped<I${className}Service, ${className}Service>();

var app = builder.Build();

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
    app.UseDeveloperExceptionPage();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

// Ensure database is created
using (var scope = app.Services.CreateScope())
{
    var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
    dbContext.Database.EnsureCreated();
}

app.Run();`;
        addFileToStructure(`${projectName}/Program.cs`, defaultProgramCs);
    }

    // Add default project file if not provided
    if (!structure.files[`${projectName}/${projectName}.csproj`]) {
        const defaultProjectFile = `<Project Sdk="Microsoft.NET.Sdk.Web">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Design" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Tools" Version="8.0.0" />
    <PackageReference Include="Swashbuckle.AspNetCore" Version="6.5.0" />
    <PackageReference Include="AutoMapper.Extensions.Microsoft.DependencyInjection" Version="12.0.1" />
    <PackageReference Include="FluentValidation.AspNetCore" Version="11.3.0" />
    <PackageReference Include="Serilog.AspNetCore" Version="7.0.0" />
  </ItemGroup>

</Project>`;
        addFileToStructure(`${projectName}/${projectName}.csproj`, defaultProjectFile);
    }

    // Add default appsettings.json if not provided
    if (!structure.files[`${projectName}/appsettings.json`]) {
        const defaultAppSettings = `{
  "ConnectionStrings": {
    "DefaultConnection": "Server=localhost;Database=${className}DB;User Id=sa;Password=YourPassword123!;TrustServerCertificate=true;"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning",
      "Microsoft.EntityFrameworkCore.Database.Command": "Warning"
    }
  },
  "AllowedHosts": "*"
}`;
        addFileToStructure(`${projectName}/appsettings.json`, defaultAppSettings);
    }



    // Handle Unit Tests
    if (includeTests && (unitTestsData || backendResponse.unitTests)) {
        const testProjectName = `${projectName}.Tests`;
        const testProjectNode = {
            name: testProjectName,
            isFolder: true,
            children: [
                { name: `${testProjectName}/Services`, isFolder: true, children: [] },
                { name: `${testProjectName}/Controllers`, isFolder: true, children: [] },
                { name: `${testProjectName}/Repositories`, isFolder: true, children: [] }
            ]
        };
        structure.children.push(testProjectNode);
        structure.expanded[testProjectName] = true;
        structure.expanded[`${testProjectName}/Services`] = true;
        structure.expanded[`${testProjectName}/Controllers`] = true;
        structure.expanded[`${testProjectName}/Repositories`] = true;

        // Add test project file (updated for NUnit)
        const testProjectFile = `<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
    <IsTestProject>true</IsTestProject>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="NUnit" Version="3.14.0" />
    <PackageReference Include="NUnit3TestAdapter" Version="4.5.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
    <PackageReference Include="Moq" Version="4.20.69" />
    <PackageReference Include="FluentAssertions" Version="6.12.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.InMemory" Version="8.0.0" />
    <PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" Version="8.0.0" />
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\\${projectName}\\${projectName}.csproj" />
  </ItemGroup>

</Project>`;
        addFileToStructure(`${testProjectName}/${testProjectName}.csproj`, testProjectFile);

        // Process unit tests
        const processUnitTests = (tests, source = "unitTests") => {
            if (!tests) return;
            let testFiles = [];
            if (typeof tests === "string") {
                testFiles = [{ content: tests, metadata: {} }];
            } else if (tests.unitTestCode) {
                testFiles = [{
                    content: tests.unitTestCode,
                    metadata: {
                        testDescription: tests.testDescription || "",
                        coverage: tests.coverage || []
                    }
                }];
            } else if (Array.isArray(tests)) {
                testFiles = tests.map(test => ({
                    content: test.content || test,
                    metadata: test.metadata || {}
                }));
            } else if (typeof tests === "object") {
                testFiles = Object.keys(tests).map(key => ({
                    content: tests[key].content || tests[key],
                    metadata: tests[key].metadata || {}
                }));
            }

            testFiles.forEach((test, index) => {
                let unitTestContent = test.content.replace(/^```[a-zA-Z]*\s*/, '').replace(/\s*```$/, '').trim();
                if (!unitTestContent) return;

                // Extract namespace to determine folder
                let testFolder = "Services";
                let testClassName = `${className}ServiceTests`;
                const namespaceMatch = unitTestContent.match(/namespace ([^\n\r{]+)/);
                const testNamespace = namespaceMatch ? namespaceMatch[1].trim() : `${projectName}.Tests.Services`;
                
                if (testNamespace.includes(".Controllers")) {
                    testFolder = "Controllers";
                } else if (testNamespace.includes(".Repositories")) {
                    testFolder = "Repositories";
                }

                const testClassMatch = unitTestContent.match(/public class (\w+)/);
                if (testClassMatch) {
                    testClassName = testClassMatch[1];
                }

                const filePath = `${testProjectName}/${testFolder}/${testClassName}.cs`;
                addFileToStructure(filePath, unitTestContent, test.metadata);
                console.log(`✅ Unit test added: ${filePath} (from ${source})`);

                // Update children for frontend
                const folderNode = testProjectNode.children.find(c => c.name === `${testProjectName}/${testFolder}`);
                if (folderNode && !folderNode.children.some(c => c.name === filePath)) {
                    folderNode.children.push({
                        name: filePath,
                        isFolder: false
                    });
                }
            });
        };

        processUnitTests(unitTestsData, "unitTestDetails");
        processUnitTests(backendResponse.unitTests, "unitTests");

        // Add Global Usings for test project
        const testGlobalUsings = `global using NUnit.Framework;
global using Moq;
global using FluentAssertions;
global using Microsoft.EntityFrameworkCore;
global using Microsoft.Extensions.DependencyInjection;
global using System;
global using System.Collections.Generic;
global using System.Linq;
global using System.Threading.Tasks;
global using ${projectName}.Models;
global using ${projectName}.Services;
global using ${projectName}.Repositories.Interfaces;
global using ${projectName}.Data;`;
        addFileToStructure(`${testProjectName}/GlobalUsings.cs`, testGlobalUsings);

        // Add NUnit configuration
        const nunitConfig = `<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
  </packageSources>
</configuration>`;
        addFileToStructure(`${testProjectName}/nuget.config`, nunitConfig);
    }

    // Add solution file
    const solutionName = projectName.split('.')[0];
    const generateGuid = () => {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        }).toUpperCase();
    };

    const mainProjectGuid = generateGuid();
    const testProjectGuid = includeTests && (unitTestsData || backendResponse.unitTests) ? generateGuid() : null;

    const solutionContent = `Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31903.59
MinimumVisualStudioVersion = 10.0.40219.1
Project("{9A19103F-16F7-4668-BE54-9A1E7A4F7556}") = "${projectName}", "${projectName}\\${projectName}.csproj", "{${mainProjectGuid}}"
EndProject${testProjectGuid ? `
Project("{9A19103F-16F7-4668-BE54-9A1E7A4F7556}") = "${projectName}.Tests", "${projectName}.Tests\\${projectName}.Tests.csproj", "{${testProjectGuid}}"
EndProject` : ''}
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Debug|Any CPU = Debug|Any CPU
		Release|Any CPU = Release|Any CPU
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		{${mainProjectGuid}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{${mainProjectGuid}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{${mainProjectGuid}}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{${mainProjectGuid}}.Release|Any CPU.Build.0 = Release|Any CPU${testProjectGuid ? `
		{${testProjectGuid}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{${testProjectGuid}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{${testProjectGuid}}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{${testProjectGuid}}.Release|Any CPU.Build.0 = Release|Any CPU` : ''}
	EndGlobalSection
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
	GlobalSection(ExtensibilityGlobals) = postSolution
		SolutionGuid = {${generateGuid()}}
	EndGlobalSection
EndGlobal`;

    addFileToStructure(`${solutionName}.sln`, solutionContent);


    console.log("Generated structure:", structure);
    console.log(`✅ Structure generated with ${Object.keys(structure.files).length} files`);
    console.log(`📊 Test project included: ${includeTests && (unitTestsData || backendResponse.unitTests)}`);
    
    return structure;
};

// Helper function to generate GUID-like strings for solution file
function generateGuid() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16).toUpperCase();
    });
}

// Example usage function
function parseBackendResponse(backendData, includeTests = true) {
    try {
        // Handle both string JSON and object inputs
        const parsedData = typeof backendData === 'string' ? JSON.parse(backendData) : backendData;
        
        // Validate the structure
        if (!parsedData || typeof parsedData !== 'object') {
            throw new Error('Invalid backend response format');
        }
        
        // Extract status and check for success
        if (parsedData.status && parsedData.status !== 'success') {
            console.warn('Backend conversion may have issues:', parsedData.status);
        }
        
        // Parse the structure
        const projectStructure = parseCSharpStructure(parsedData, includeTests);
        
        // Log conversion notes and potential issues if available
        if (parsedData.conversionNotes) {
            console.log('Conversion Notes:', parsedData.conversionNotes);
        }
        
        if (parsedData.potentialIssues && parsedData.potentialIssues.length > 0) {
            console.warn('Potential Issues:', parsedData.potentialIssues);
        }
        
        return projectStructure;
        
    } catch (error) {
        console.error('Error parsing backend response:', error);
        throw new Error(`Failed to parse backend response: ${error.message}`);
    }
}

// Export functions for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        parseCSharpStructure,
        parseBackendResponse,
        generateGuid
    };
}

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
