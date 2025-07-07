import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

class CICSConverter:
    """
    Professional CICS Converter focused on .NET code generation
    """

    def __init__(self, azure_config: Dict[str, str], output_dir: str = "cics_analysis"):
        self.output_dir = output_dir
        self.dotnet_output_dir = os.path.join(output_dir, "dotnet_solution")
        
        # Create directories
        os.makedirs(self.dotnet_output_dir, exist_ok=True)
        
        # Initialize Azure OpenAI client
        self.azure_config = azure_config
        self.client = AzureOpenAI(
            api_key=azure_config["AZURE_OPENAI_API_KEY"],
            api_version=azure_config["AZURE_OPENAI_API_VERSION"],
            azure_endpoint=azure_config["AZURE_OPENAI_ENDPOINT"]
        )
        
        self.model_name = azure_config.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        logger.info("🚀 CICS Converter initialized")

    def convert_project(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Convert analyzed project to .NET solution"""
        
        logger.info("💻 Generating complete .NET solution...")
        
        solution_structure = {
            "Domain": self._generate_domain_layer(analysis),
            "Application": self._generate_application_layer(analysis),
            "Infrastructure": self._generate_infrastructure_layer(analysis),
            "WebAPI": self._generate_webapi_layer(analysis),
            "Tests": self._generate_test_layer(analysis),
            "Configuration": self._generate_solution_files(analysis)
        }
        
        # Save all generated files
        self._save_complete_solution(solution_structure)
        
        # Save summary
        self._save_conversion_summary(analysis, solution_structure)
        
        return solution_structure

    def _generate_domain_layer(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate domain layer (entities, value objects, domain services)"""
        
        domain_layer = {
            "Entities": {},
            "ValueObjects": {},
            "DomainServices": {},
            "Repositories": {}
        }
        
        # Generate entities from copybooks and control includes
        all_data_structures = {}
        all_data_structures.update(analysis.get("copybooks", {}))
        all_data_structures.update(analysis.get("control_includes", {}))

        
        for filename, data_structure in all_data_structures.items():
            entity_name = self._to_pascal_case(filename.replace(".cpy", "").replace(".ctl", ""))
            
            if self._is_entity(data_structure):
                domain_layer["Entities"][entity_name] = self._generate_entity_class(entity_name, data_structure)
            else:
                domain_layer["ValueObjects"][entity_name] = self._generate_value_object_class(entity_name, data_structure)
        
        # Generate repository interfaces
        for entity_name in domain_layer["Entities"]:
            repo_name = f"I{entity_name}Repository"
            domain_layer["Repositories"][repo_name] = self._generate_repository_interface(entity_name)
        
        return domain_layer

    def _generate_application_layer(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate application layer (services, DTOs, commands, queries)"""
        
        application_layer = {
            "Services": {},
            "DTOs": {},
            "Commands": {},
            "Queries": {},
            "Handlers": {},
            "Validators": {}
        }
        
        # Generate DTOs from copybooks
        for filename, copybook_data in analysis.get("copybooks", {}).items():
            dto_name = self._to_pascal_case(filename.replace(".cpy", "")) + "Dto" 
            application_layer["DTOs"][dto_name] = self._generate_dto_class(dto_name, copybook_data)
        
        # Generate services from CICS programs
        for filename, program_data in analysis.get("programs", {}).items():
            service_name = program_data.get("dotnet_suggestions", {}).get("service_name", "UnknownService")
            
            # Generate service interface and implementation
            application_layer["Services"][f"I{service_name}"] = self._generate_service_interface(service_name, program_data)
            application_layer["Services"][service_name] = self._generate_service_implementation(service_name, program_data)
            
            # Generate commands and queries based on CICS operations
            for cics_cmd in program_data.get("cics_commands", []):
                if cics_cmd.get("command_type") in ["WRITEQ_TS", "WRITEQ_TD", "WRITE"]:
                    cmd_name = f"{service_name}Command"
                    application_layer["Commands"][cmd_name] = self._generate_command_class(cmd_name, cics_cmd)
                    application_layer["Handlers"][f"{cmd_name}Handler"] = self._generate_command_handler(cmd_name, cics_cmd)
                
                elif cics_cmd.get("command_type") in ["READQ_TS", "READQ_TD", "READ"]:
                    query_name = f"{service_name}Query"
                    application_layer["Queries"][query_name] = self._generate_query_class(query_name, cics_cmd)
                    application_layer["Handlers"][f"{query_name}Handler"] = self._generate_query_handler(query_name, cics_cmd)
        
        return application_layer

    def _generate_infrastructure_layer(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate infrastructure layer"""
        
        return {
            "Repositories": self._generate_repository_implementations(analysis),
            "Services": self._generate_infrastructure_services(analysis),
            "Configuration": self._generate_infrastructure_config(analysis),
            "Persistence": self._generate_persistence_config(analysis)
        }

    def _generate_webapi_layer(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Web API layer (controllers, middleware)"""
        
        webapi_layer = {
            "Controllers": {},
            "Middleware": {},
            "Configuration": {}
        }
        
        # Generate controllers for each CICS program
        for filename, program_data in analysis.get("programs", {}).items():
            controller_name = program_data.get("dotnet_suggestions", {}).get("controller_name", "UnknownController")
            webapi_layer["Controllers"][controller_name] = self._generate_controller_class(controller_name, program_data)
        
        # Generate common middleware
        webapi_layer["Middleware"]["ErrorHandlingMiddleware"] = self._generate_error_middleware()
        webapi_layer["Middleware"]["LoggingMiddleware"] = self._generate_logging_middleware()
        
        return webapi_layer

    def _generate_test_layer(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test projects"""
        
        return {
            "UnitTests": {"placeholder": {"filename": "UnitTests.cs", "content": "// Unit tests placeholder"}},
            "IntegrationTests": {"placeholder": {"filename": "IntegrationTests.cs", "content": "// Integration tests placeholder"}}
        }

    def _generate_solution_files(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate solution and project files"""
        
        # Get dynamic project name instead of hard-coded
        project_name = self._get_project_namespace()
        
        return {
            "SolutionFile": {
                "filename": f"{project_name}.sln",
                "content": self._generate_solution_file_content(project_name)
            },
            "GlobalConfig": {
                "filename": "Directory.Build.props",
                "content": self._generate_global_config()
            }
        }
    
    
    # === CODE GENERATION METHODS ===

    def _generate_entity_class(self, entity_name: str, data_structure: Dict[str, Any]) -> Dict[str, str]:
        """Generate entity class"""
        
        fields = data_structure.get("fields", [])
        
        content = f"""using System;
using System.ComponentModel.DataAnnotations;

namespace {self._get_project_namespace()}.Domain.Entities
{{
    /// <summary>
    /// Entity generated from COBOL data structure
    /// </summary>
    public class {entity_name}
    {{
"""
        
        for field in fields:
            prop_info = field.get("dotnet_property", {})
            prop_name = prop_info.get("name", field["name"])
            prop_type = prop_info.get("type", "string")
            
            if field.get("is_key_field", False):
                content += f"        [Key]\n"
            
            if field.get("is_required", False):
                content += f"        [Required]\n"
            
            content += f"""        /// <summary>
        /// COBOL field: {field['name']} PIC {field.get('pic', '')}
        /// </summary>
        public {prop_type} {prop_name} {{ get; set; }}

"""
        
        content += "    }\n}\n"
        
        return {
            "filename": f"{entity_name}.cs",
            "content": content
        }

    def _generate_value_object_class(self, vo_name: str, data_structure: Dict[str, Any]) -> Dict[str, str]:
        """Generate value object class"""
        
        content = f"""using System;

namespace {self._get_project_namespace()}.Domain.ValueObjects
{{
    /// <summary>
    /// Value object generated from COBOL control structure
    /// </summary>
    public record {vo_name}
    {{
"""
        
        for field in data_structure.get("fields", []):
            prop_info = field.get("dotnet_property", {})
            prop_name = prop_info.get("name", field["name"])
            prop_type = prop_info.get("type", "string")
            
            content += f"        public {prop_type} {prop_name} {{ get; init; }}\n"
        
        content += "    }\n}\n"
        
        return {
            "filename": f"{vo_name}.cs",
            "content": content
        }

    def _generate_dto_class(self, dto_name: str, copybook_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate DTO class"""
        
        content = f"""using System;
using System.ComponentModel.DataAnnotations;

namespace {self._get_project_namespace()}.Application.DTOs
{{
    /// <summary>
    /// DTO generated from COBOL copybook
    /// </summary>
    public class {dto_name}
    {{
"""
        
        for field in copybook_data.get("fields", []):
            prop_info = field.get("dotnet_property", {})
            prop_name = prop_info.get("name", field["name"])
            prop_type = prop_info.get("type", "string")
            
            content += f"""        /// <summary>
        /// COBOL field: {field['name']} PIC {field.get('pic', '')}
        /// </summary>
        public {prop_type} {prop_name} {{ get; set; }}

"""
        
        content += "    }\n}\n"
        
        return {
            "filename": f"{dto_name}.cs",
            "content": content
        }

    def _generate_service_interface(self, service_name: str, program_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate service interface"""
        
        content = f"""using System;
using System.Threading.Tasks;
using {self._get_project_namespace()}.Application.DTOs;

namespace {self._get_project_namespace()}.Application.Services
{{
    /// <summary>
    /// Service interface for {program_data.get('program_id', 'Unknown')} CICS program
    /// </summary>
    public interface I{service_name}
    {{
        Task<ServiceResult<T>> ProcessAsync<T>(object request);
"""
        
        # Add specific methods based on CICS commands
        for cics_cmd in program_data.get("cics_commands", [])[:3]:  # Limit to first 3
            method_name = cics_cmd.get("dotnet_method", "ProcessAsync")
            content += f"        Task<ServiceResult> {method_name}(object request);\n"
        
        content += "    }\n}\n"
        
        return {
            "filename": f"I{service_name}.cs",
            "content": content
        }

    def _generate_service_implementation(self, service_name: str, program_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate service implementation"""
        
        content = f"""using System;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using {self._get_project_namespace()}.Application.Services;

namespace {self._get_project_namespace()}.Application.Services
{{
    /// <summary>
    /// Service implementation for {program_data.get('program_id', 'Unknown')} CICS program
    /// </summary>
    public class {service_name} : I{service_name}
    {{
        private readonly ILogger<{service_name}> _logger;

        public {service_name}(ILogger<{service_name}> logger)
        {{
            _logger = logger;
        }}

        public async Task<ServiceResult<T>> ProcessAsync<T>(object request)
        {{
            try
            {{
                _logger.LogInformation("Processing CICS program: {program_data.get('program_id', 'Unknown')}");
                
                // TODO: Implement business logic
                // CICS Commands: {len(program_data.get('cics_commands', []))}
                // SQL Operations: {len(program_data.get('sql_blocks', []))}
                
                return new ServiceResult<T> {{ Success = true }};
            }}
            catch (Exception ex)
            {{
                _logger.LogError(ex, "Error processing request");
                return new ServiceResult<T> {{ Success = false, Error = ex.Message }};
            }}
        }}
"""
        
        # Add specific method implementations
        for cics_cmd in program_data.get("cics_commands", [])[:3]:  # Limit to first 3
            method_name = cics_cmd.get("dotnet_method", "ProcessAsync")
            content += f"""
        public async Task<ServiceResult> {method_name}(object request)
        {{
            // TODO: Implement {cics_cmd.get('command_type', 'Unknown')} operation
            // {cics_cmd.get('conversion_hint', 'No conversion hint available')}
            return new ServiceResult {{ Success = true }};
        }}
"""
        
        content += "    }\n}\n"
        
        return {
            "filename": f"{service_name}.cs",
            "content": content
        }

    def _generate_controller_class(self, controller_name: str, program_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate controller class"""
        
        service_name = program_data.get("dotnet_suggestions", {}).get("service_name", "UnknownService")
        
        content = f"""using Microsoft.AspNetCore.Mvc;
using System.Threading.Tasks;
using {self._get_project_namespace()}.Application.Services;

namespace {self._get_project_namespace()}.WebAPI.Controllers
{{
    /// <summary>
    /// Controller for {program_data.get('program_id', 'Unknown')} CICS program
    /// </summary>
    [ApiController]
    [Route("api/[controller]")]
    public class {controller_name} : ControllerBase
    {{
        private readonly I{service_name} _{service_name.lower()};

        public {controller_name}(I{service_name} {service_name.lower()})
        {{
            _{service_name.lower()} = {service_name.lower()};
        }}

        [HttpPost("process")]
        public async Task<IActionResult> Process([FromBody] object request)
        {{
            var result = await _{service_name.lower()}.ProcessAsync<object>(request);
            
            if (result.Success)
                return Ok(result.Data);
            else
                return BadRequest(result.Error);
        }}
"""
        
        # Add specific endpoints based on CICS commands
        endpoint_count = 0
        for cics_cmd in program_data.get("cics_commands", []):
            if endpoint_count >= 3:  # Limit endpoints
                break
                
            command_type = cics_cmd.get("command_type", "")
            if command_type in ["WRITEQ_TS", "WRITEQ_TD", "WRITE"]:
                content += f"""
        [HttpPost("{command_type.lower()}")]
        public async Task<IActionResult> {command_type.replace('_', '')}([FromBody] object request)
        {{
            // TODO: Implement {command_type} endpoint
            return Ok();
        }}
"""
                endpoint_count += 1
            elif command_type in ["READQ_TS", "READQ_TD", "READ"]:
                content += f"""
        [HttpGet("{command_type.lower()}")]
        public async Task<IActionResult> {command_type.replace('_', '')}()
        {{
            // TODO: Implement {command_type} endpoint
            return Ok();
        }}
"""
                endpoint_count += 1
        
        content += "    }\n}\n"
        
        return {
            "filename": f"{controller_name}.cs",
            "content": content
        }

    def _generate_repository_interface(self, entity_name: str) -> Dict[str, str]:
        """Generate repository interface"""
        
        content = f"""using System;
using System.Threading.Tasks;
using System.Collections.Generic;
using {self._get_project_namespace()}.Domain.Entities;

namespace {self._get_project_namespace()}.Domain.Repositories
{{
    /// <summary>
    /// Repository interface for {entity_name}
    /// </summary>
    public interface I{entity_name}Repository
    {{
        Task<{entity_name}> GetByIdAsync(int id);
        Task<IEnumerable<{entity_name}>> GetAllAsync();
        Task<{entity_name}> CreateAsync({entity_name} entity);
        Task<{entity_name}> UpdateAsync({entity_name} entity);
        Task DeleteAsync(int id);
    }}
}}
"""
        
        return {
            "filename": f"I{entity_name}Repository.cs",
            "content": content
        }

    def _generate_command_class(self, cmd_name: str, cics_cmd: Dict[str, Any]) -> Dict[str, str]:
        """Generate command class"""
        
        content = f"""using MediatR;

namespace {self._get_project_namespace()}.Application.Commands
{{
    /// <summary>
    /// Command for {cics_cmd.get('command_type', 'Unknown')} operation
    /// </summary>
    public class {cmd_name} : IRequest<ServiceResult>
    {{
        public object Data {{ get; set; }}
        public string Queue {{ get; set; }}
        
        // TODO: Add specific properties based on CICS command parameters
        // Parameters: {', '.join(cics_cmd.get('parameters', {}).keys())}
    }}
}}
"""
        
        return {
            "filename": f"{cmd_name}.cs",
            "content": content
        }

    def _generate_command_handler(self, cmd_name: str, cics_cmd: Dict[str, Any]) -> Dict[str, str]:
        """Generate command handler"""
        
        content = f"""using MediatR;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace {self._get_project_namespace()}.Application.Handlers
{{
    /// <summary>
    /// Handler for {cmd_name}
    /// </summary>
    public class {cmd_name}Handler : IRequestHandler<{cmd_name}, ServiceResult>
    {{
        private readonly ILogger<{cmd_name}Handler> _logger;

        public {cmd_name}Handler(ILogger<{cmd_name}Handler> logger)
        {{
            _logger = logger;
        }}

        public async Task<ServiceResult> Handle({cmd_name} request, CancellationToken cancellationToken)
        {{
            try
            {{
                _logger.LogInformation("Handling {cics_cmd.get('command_type', 'Unknown')} command");
                
                // TODO: Implement {cics_cmd.get('conversion_hint', 'conversion logic')}
                
                return new ServiceResult {{ Success = true }};
            }}
            catch (Exception ex)
            {{
                _logger.LogError(ex, "Error handling command");
                return new ServiceResult {{ Success = false, Error = ex.Message }};
            }}
        }}
    }}
}}
"""
        
        return {
            "filename": f"{cmd_name}Handler.cs",
            "content": content
        }

    def _generate_query_class(self, query_name: str, cics_cmd: Dict[str, Any]) -> Dict[str, str]:
        """Generate query class"""
        
        content = f"""using MediatR;

namespace {self._get_project_namespace()}.Application.Queries
{{
    /// <summary>
    /// Query for {cics_cmd.get('command_type', 'Unknown')} operation
    /// </summary>
    public class {query_name} : IRequest<ServiceResult<object>>
    {{
        public string Queue {{ get; set; }}
        public int? Item {{ get; set; }}
        
        // TODO: Add specific properties based on CICS command parameters
    }}
}}
"""
        
        return {
            "filename": f"{query_name}.cs",
            "content": content
        }

    def _generate_query_handler(self, query_name: str, cics_cmd: Dict[str, Any]) -> Dict[str, str]:
        """Generate query handler"""
        
        content = f"""using MediatR;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace {self._get_project_namespace()}.Application.Handlers
{{
    /// <summary>
    /// Handler for {query_name}
    /// </summary>
    public class {query_name}Handler : IRequestHandler<{query_name}, ServiceResult<object>>
    {{
        private readonly ILogger<{query_name}Handler> _logger;

        public {query_name}Handler(ILogger<{query_name}Handler> logger)
        {{
            _logger = logger;
        }}

        public async Task<ServiceResult<object>> Handle({query_name} request, CancellationToken cancellationToken)
        {{
            try
            {{
                _logger.LogInformation("Handling {cics_cmd.get('command_type', 'Unknown')} query");
                
                // TODO: Implement {cics_cmd.get('conversion_hint', 'query logic')}
                
                return new ServiceResult<object> {{ Success = true, Data = new object() }};
            }}
            catch (Exception ex)
            {{
                _logger.LogError(ex, "Error handling query");
                return new ServiceResult<object> {{ Success = false, Error = ex.Message }};
            }}
        }}
    }}
}}
"""
        
        return {
            "filename": f"{query_name}Handler.cs",
            "content": content
        }

    def _generate_repository_implementations(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate repository implementations"""
        
        repositories = {}
        
        # Generate for each entity
        for filename, data_structure in analysis.get("copybooks", {}).items():
            if self._is_entity(data_structure):
                entity_name = self._to_pascal_case(filename.replace(".cpy", ""))
                repo_name = f"{entity_name}Repository"
                
                repositories[repo_name] = {
                    "filename": f"{repo_name}.cs",
                    "content": f"""using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using {self._get_project_namespace()}.Domain.Entities;
using {self._get_project_namespace()}.Domain.Repositories;

namespace {self._get_project_namespace()}.Infrastructure.Repositories
{{
    public class {repo_name} : I{entity_name}Repository
    {{
        private readonly ApplicationDbContext _context;

        public {repo_name}(ApplicationDbContext context)
        {{
            _context = context;
        }}

        public async Task<{entity_name}> GetByIdAsync(int id)
        {{
            return await _context.{entity_name}s.FindAsync(id);
        }}

        public async Task<IEnumerable<{entity_name}>> GetAllAsync()
        {{
            return await _context.{entity_name}s.ToListAsync();
        }}

        public async Task<{entity_name}> CreateAsync({entity_name} entity)
        {{
            _context.{entity_name}s.Add(entity);
            await _context.SaveChangesAsync();
            return entity;
        }}

        public async Task<{entity_name}> UpdateAsync({entity_name} entity)
        {{
            _context.{entity_name}s.Update(entity);
            await _context.SaveChangesAsync();
            return entity;
        }}

        public async Task DeleteAsync(int id)
        {{
            var entity = await GetByIdAsync(id);
            if (entity != null)
            {{
                _context.{entity_name}s.Remove(entity);
                await _context.SaveChangesAsync();
            }}
        }}
    }}
}}
"""
                }
        
        return repositories

    def _generate_infrastructure_services(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate infrastructure services"""
        
        return {
            "CacheService": {
                "filename": "CacheService.cs",
                "content": f"""using System;
using System.Threading.Tasks;
using Microsoft.Extensions.Caching.Distributed;
using System.Text.Json;

namespace {self._get_project_namespace()}.Infrastructure.Services
{{
    public interface ICacheService
    {{
        Task WriteToTempStorageAsync(string queue, object data);
        Task<T> ReadFromTempStorageAsync<T>(string queue, int item);
        Task DeleteTempStorageAsync(string queue);
    }}

    public class CacheService : ICacheService
    {{
        private readonly IDistributedCache _cache;

        public CacheService(IDistributedCache cache)
        {{
            _cache = cache;
        }}

        public async Task WriteToTempStorageAsync(string queue, object data)
        {{
            var json = JsonSerializer.Serialize(data);
            await _cache.SetStringAsync(queue, json);
        }}

        public async Task<T> ReadFromTempStorageAsync<T>(string queue, int item)
        {{
            var json = await _cache.GetStringAsync($"{{queue}}_{{item}}");
            return json != null ? JsonSerializer.Deserialize<T>(json) : default(T);
        }}

        public async Task DeleteTempStorageAsync(string queue)
        {{
            await _cache.RemoveAsync(queue);
        }}
    }}
}}
"""
            },
            "MessageQueueService": {
                "filename": "MessageQueueService.cs",
                "content": f"""using System;
using System.Threading.Tasks;

namespace {self._get_project_namespace()}.Infrastructure.Services
{{
    public interface IMessageQueueService
    {{
        Task PublishMessageAsync(string queue, object message);
        Task<T> ConsumeMessageAsync<T>(string queue);
    }}

    public class MessageQueueService : IMessageQueueService
    {{
        public async Task PublishMessageAsync(string queue, object message)
        {{
            // TODO: Implement message queue publishing (Azure Service Bus, RabbitMQ, etc.)
            await Task.CompletedTask;
        }}

        public async Task<T> ConsumeMessageAsync<T>(string queue)
        {{
            // TODO: Implement message queue consumption
            await Task.CompletedTask;
            return default(T);
        }}
    }}
}}
"""
            }
        }

    def _generate_infrastructure_config(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate infrastructure configuration"""
        
        return {
            "DependencyInjection": {
                "filename": "ServiceCollectionExtensions.cs",
                "content": f"""using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Configuration;
using Microsoft.EntityFrameworkCore;
using {self._get_project_namespace()}.Infrastructure.Services;
using {self._get_project_namespace()}.Infrastructure.Repositories;

namespace {self._get_project_namespace()}.Infrastructure.Configuration
{{
    public static class ServiceCollectionExtensions
    {{
        public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration configuration)
        {{
            // Database
            services.AddDbContext<ApplicationDbContext>(options =>
                options.UseSqlServer(configuration.GetConnectionString("DefaultConnection")));

            // Services
            services.AddScoped<ICacheService, CacheService>();
            services.AddScoped<IMessageQueueService, MessageQueueService>();

            // Repositories
            // TODO: Add repository registrations

            // Caching
            services.AddStackExchangeRedisCache(options =>
            {{
                options.Configuration = configuration.GetConnectionString("Redis");
            }});

            return services;
        }}
    }}
}}
"""
            }
        }

    def _generate_persistence_config(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate persistence configuration"""
        
        # Get all entities
        entities = []
        for filename, data_structure in analysis.get("copybooks", {}).items():
            if self._is_entity(data_structure):
                entity_name = self._to_pascal_case(filename.replace(".cpy", ""))
                entities.append(entity_name)
        
        dbsets = "\n        ".join([f"public DbSet<{entity}> {entity}s {{ get; set; }}" for entity in entities])
        
        return {
            "ApplicationDbContext": {
                "filename": "ApplicationDbContext.cs",
                "content": f"""using Microsoft.EntityFrameworkCore;
using {self._get_project_namespace()}.Domain.Entities;

namespace {self._get_project_namespace()}.Infrastructure.Persistence
{{
    public class ApplicationDbContext : DbContext
    {{
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options)
        {{
        }}

        {dbsets}

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {{
            base.OnModelCreating(modelBuilder);
            
            // TODO: Configure entity relationships and constraints
        }}
    }}
}}
"""
            }
        }

    def _generate_error_middleware(self) -> Dict[str, str]:
        """Generate error handling middleware"""
        
        return {
            "filename": "ErrorHandlingMiddleware.cs",
            "content": f"""using System;
using System.Net;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace {self._get_project_namespace()}.WebAPI.Middleware
{{
    public class ErrorHandlingMiddleware
    {{
        private readonly RequestDelegate _next;
        private readonly ILogger<ErrorHandlingMiddleware> _logger;

        public ErrorHandlingMiddleware(RequestDelegate next, ILogger<ErrorHandlingMiddleware> logger)
        {{
            _next = next;
            _logger = logger;
        }}

        public async Task InvokeAsync(HttpContext context)
        {{
            try
            {{
                await _next(context);
            }}
            catch (Exception ex)
            {{
                _logger.LogError(ex, "An unhandled exception occurred");
                await HandleExceptionAsync(context, ex);
            }}
        }}

        private static async Task HandleExceptionAsync(HttpContext context, Exception exception)
        {{
            context.Response.ContentType = "application/json";
            context.Response.StatusCode = (int)HttpStatusCode.InternalServerError;

            var response = new
            {{
                message = "An error occurred while processing your request.",
                details = exception.Message
            }};

            await context.Response.WriteAsync(JsonSerializer.Serialize(response));
        }}
    }}
}}
"""
        }

    def _generate_logging_middleware(self) -> Dict[str, str]:
        """Generate logging middleware"""
        
        return {
            "filename": "LoggingMiddleware.cs",
            "content": f"""using System;
using System.Diagnostics;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace {self._get_project_namespace()}.WebAPI.Middleware
{{
    public class LoggingMiddleware
    {{
        private readonly RequestDelegate _next;
        private readonly ILogger<LoggingMiddleware> _logger;

        public LoggingMiddleware(RequestDelegate next, ILogger<LoggingMiddleware> logger)
        {{
            _next = next;
            _logger = logger;
        }}

        public async Task InvokeAsync(HttpContext context)
        {{
            var stopwatch = Stopwatch.StartNew();
            
            _logger.LogInformation("Request {{Method}} {{Path}} started", 
                context.Request.Method, context.Request.Path);

            await _next(context);

            stopwatch.Stop();
            _logger.LogInformation("Request {{Method}} {{Path}} completed in {{Elapsed}}ms with status {{StatusCode}}", 
                context.Request.Method, context.Request.Path, stopwatch.ElapsedMilliseconds, context.Response.StatusCode);
        }}
    }}
}}
"""
        }

    def _generate_solution_file_content(self, project_name: str) -> str:
        """Generate solution file content"""
        
        return f"""Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31903.59
MinimumVisualStudioVersion = 10.0.40219.1

Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}.Domain", "{project_name}.Domain\\{project_name}.Domain.csproj", "{{11111111-1111-1111-1111-111111111111}}"
EndProject

Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}.Application", "{project_name}.Application\\{project_name}.Application.csproj", "{{22222222-2222-2222-2222-222222222222}}"
EndProject

Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}.Infrastructure", "{project_name}.Infrastructure\\{project_name}.Infrastructure.csproj", "{{33333333-3333-3333-3333-333333333333}}"
EndProject

Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}.WebAPI", "{project_name}.WebAPI\\{project_name}.WebAPI.csproj", "{{44444444-4444-4444-4444-444444444444}}"
EndProject

Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Debug|Any CPU = Debug|Any CPU
		Release|Any CPU = Release|Any CPU
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		{{11111111-1111-1111-1111-111111111111}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{11111111-1111-1111-1111-111111111111}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{22222222-2222-2222-2222-222222222222}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{22222222-2222-2222-2222-222222222222}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{33333333-3333-3333-3333-333333333333}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{33333333-3333-3333-3333-333333333333}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{44444444-4444-4444-4444-444444444444}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{44444444-4444-4444-4444-444444444444}}.Debug|Any CPU.Build.0 = Debug|Any CPU
	EndGlobalSection
EndGlobal
"""

    def _generate_global_config(self) -> str:
        """Generate global configuration"""
        
        return """<Project>
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>false</TreatWarningsAsErrors>
  </PropertyGroup>
</Project>
"""

    def _save_complete_solution(self, solution_structure: Dict[str, Any]):
        """Save complete .NET solution to disk"""
        
        for layer_name, layer_content in solution_structure.items():
            if not layer_content:  # Skip empty layers
                continue
                
            layer_dir = os.path.join(self.dotnet_output_dir, layer_name)
            os.makedirs(layer_dir, exist_ok=True)
            
            for category_name, category_content in layer_content.items():
                if not category_content:  # Skip empty categories
                    continue
                    
                category_dir = os.path.join(layer_dir, category_name)
                os.makedirs(category_dir, exist_ok=True)
                
                for class_name, class_content in category_content.items():
                    if isinstance(class_content, dict) and "content" in class_content:
                        file_path = os.path.join(category_dir, class_content["filename"])
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(class_content["content"])

    def _save_conversion_summary(self, analysis: Dict[str, Any], solution_structure: Dict[str, Any]):
        """Save conversion summary"""
        
        summary = {
            "conversion_timestamp": datetime.now().isoformat(),
            "source_analysis": {
                "total_programs": len(analysis.get("programs", {})),
                "total_copybooks": len(analysis.get("copybooks", {})),
                "business_domain": analysis.get("project_metadata", {}).get("business_domain", "Unknown")
            },
            "generated_solution": {
                "layers": list(solution_structure.keys()),
                "total_files": sum(
                    len([f for f in category.values() if isinstance(f, dict) and "content" in f])
                    for layer in solution_structure.values()
                    for category in layer.values()
                    if isinstance(category, dict)
                )
            }
        }
        
        summary_file = os.path.join(self.output_dir, "dotnet_solution_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Generate comprehensive report
        self._generate_comprehensive_report(analysis, solution_structure)

    def _generate_comprehensive_report(self, analysis: Dict[str, Any], solution_structure: Dict[str, Any]):
        """Generate comprehensive conversion report"""
        
        report_file = os.path.join(self.output_dir, "comprehensive_report.md")
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# CICS to .NET Modernization Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Executive summary
            f.write("## Executive Summary\n\n")
            summary = analysis.get("summary", {})
            f.write(f"- **Programs Analyzed:** {summary.get('total_programs', 0)}\n")
            f.write(f"- **Copybooks:** {summary.get('total_copybooks', 0)}\n")
            f.write(f"- **Control Includes:** {summary.get('total_control_includes', 0)}\n")
            f.write(f"- **JCL Files:** {summary.get('total_jcl_files', 0)}\n")
            f.write(f"- **Business Domain:** {analysis.get('project_metadata', {}).get('business_domain', 'Unknown')}\n\n")
            
            # AI insights
            if "ai_insights" in analysis:
                ai_insights = analysis["ai_insights"]
                f.write("## AI Business Analysis\n\n")
                f.write(f"**Business Domain:** {ai_insights.get('business_domain', 'Not identified')}\n\n")
                
            # .NET solution overview
            f.write("## .NET Solution Architecture\n\n")
            for category, items in solution_structure.items():
                if items:  # Only show non-empty categories
                    f.write(f"### {category}\n")
                    f.write(f"Generated {len(items)} components:\n")
                    for item_name in items.keys():
                        f.write(f"- {item_name}\n")
                    f.write("\n")

    # === HELPER METHODS ===

    def _get_project_namespace(self) -> str:
        """
        Get project namespace dynamically from analysis or file content.
        Priority: 1) Business domain 2) Program names 3) File names 4) Default
        """
        try:
            from ..routes.analysis import analysis_manager
            
            # Priority 1: Business domain from analysis (if not generic)
            if hasattr(analysis_manager, 'analysis_results') and analysis_manager.analysis_results:
                cics_results = analysis_manager.analysis_results.get("cics_results", {})
                pm = cics_results.get("project_metadata", {})
                domain = pm.get("business_domain", "").strip()
                
                if domain and domain not in ["GENERAL", "Unknown", ""]:
                    namespace = "".join(w.capitalize() for w in domain.lower().split())
                    logger.info(f"Using business domain for namespace: {namespace}")
                    return namespace
            
            # Priority 2: Extract from COBOL program IDs
            if hasattr(analysis_manager, 'analysis_results') and analysis_manager.analysis_results:
                programs = analysis_manager.analysis_results.get("cics_results", {}).get("programs", {})
                for prog_name, prog_data in programs.items():
                    program_id = prog_data.get("program_id")
                    if program_id:
                        clean_name = ''.join(c for c in program_id if c.isalnum())
                        if clean_name and len(clean_name) > 2:
                            namespace = f"{clean_name.capitalize()}App"
                            logger.info(f"Using program ID for namespace: {namespace}")
                            return namespace
            
            # Priority 3: Extract from file names
            if hasattr(analysis_manager, 'project_files') and analysis_manager.project_files:
                for filename in analysis_manager.project_files.keys():
                    if filename.lower().endswith(('.cbl', '.cob', '.cobol')):
                        base_name = os.path.splitext(filename)[0]
                        clean_name = ''.join(c for c in base_name if c.isalnum())
                        if clean_name and len(clean_name) > 2:
                            namespace = f"{clean_name.capitalize()}App"
                            logger.info(f"Using filename for namespace: {namespace}")
                            return namespace
            
            # Priority 4: Extract from file content
            if hasattr(analysis_manager, 'project_files') and analysis_manager.project_files:
                import re
                for content in analysis_manager.project_files.values():
                    prog_match = re.search(r'PROGRAM-ID\.\s*([A-Z0-9-]+)', content, re.I)
                    if prog_match:
                        prog_name = prog_match.group(1).replace('-', '').replace('_', '')
                        if len(prog_name) > 2:
                            namespace = f"{prog_name.capitalize()}App"
                            logger.info(f"Using PROGRAM-ID for namespace: {namespace}")
                            return namespace
                            
        except Exception as e:
            logger.debug(f"Error deriving dynamic namespace: {e}")
        
        # Final fallback
        logger.info("Using default namespace: ModernizedApp")
        return "ModernizedApp"

    def _is_entity(self, data_structure: Dict[str, Any]) -> bool:
        """Determine if data structure should be an entity or value object"""
        fields = data_structure.get("fields", [])
        
        # Look for ID fields or primary key indicators
        for field in fields:
            field_name = field.get("name", "").upper()
            if any(id_indicator in field_name for id_indicator in ["ID", "KEY", "NUM", "NO"]):
                return True
        
        # If more than 5 fields, likely an entity
        return len(fields) > 5

    def _to_pascal_case(self, text: str) -> str:
        """Convert to PascalCase"""
        import re
        parts = re.split(r"[\s_-]+", text)
        return "".join(p.capitalize() for p in parts if p)