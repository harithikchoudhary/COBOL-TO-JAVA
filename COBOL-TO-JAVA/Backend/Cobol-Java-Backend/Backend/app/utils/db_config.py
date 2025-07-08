def get_application_properties_template(database_type="mysql"):
    """
    Generate appsettings.json template for .NET 8 database configuration.
    """
    templates = {
        "mysql": """
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=localhost;Database=your_database_name;User=your_username;Password=your_password;"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.EntityFrameworkCore": "Information"
    }
  }
}
""",
        "postgresql": """
{
  "ConnectionStrings": {
    "DefaultConnection": "Host=localhost;Port=5432;Database=your_database_name;Username=your_username;Password=your_password;"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.EntityFrameworkCore": "Information"
    }
  }
}
"""
    }
    return templates.get(database_type, templates["mysql"])

def get_database_config_class(target_language, database_type="mysql"):
    """
    Generate database configuration class for .NET 8.
    """
    if target_language.lower() == ".net 8":
        return """
// Configuration
public class DatabaseConfig
{
    private readonly IConfiguration _configuration;

    public DatabaseConfig(IConfiguration configuration)
    {
        _configuration = configuration;
    }

    public IServiceCollection AddDatabaseConfig(IServiceCollection services)
    {
        services.AddDbContext<ApplicationDbContext>(options =>
            options.Use{ "MySql" if database_type.lower() == "mysql" else "Npgsql" }(
                _configuration.GetConnectionString("DefaultConnection"),
                { 
                    "ServerVersion.AutoDetect(_configuration.GetConnectionString(\"DefaultConnection\"))" 
                    if database_type.lower() == "mysql" 
                    else "new NpgsqlDataSourceBuilder(_configuration.GetConnectionString(\"DefaultConnection\")).Build()"
                }
            )
        );
        return services;
    }
}
"""
    else:
        raise ValueError("Only .NET 8 is supported as the target language.")

def get_dependencies(target_language, database_type="mysql"):
    """
    Return required dependencies for .NET 8 database configuration.
    """
    if target_language.lower() == ".net 8":
        return f"""
<!-- Add these packages to your .csproj file -->
<ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
    <PackageReference Include="{ 
        'Pomelo.EntityFrameworkCore.MySql' if database_type.lower() == 'mysql' 
        else 'Npgsql.EntityFrameworkCore.PostgreSQL' 
    }" Version="8.0.0" />
</ItemGroup>
"""
    else:
        raise ValueError("Only .NET 8 is supported as the target language.")