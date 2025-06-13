def get_application_properties_template(database_type="mysql"):
    """
    Generate application.properties template for different database types.
    """
    templates = {
        "mysql": """
# MySQL Database Configuration
spring.datasource.url=jdbc:mysql://localhost:3306/your_database_name
spring.datasource.username=your_username
spring.datasource.password=your_password
spring.datasource.driver-class-name=com.mysql.cj.jdbc.Driver

# JPA/Hibernate Configuration
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=true
spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.MySQL8Dialect
spring.jpa.properties.hibernate.format_sql=true

# Connection Pool Configuration
spring.datasource.hikari.maximum-pool-size=10
spring.datasource.hikari.minimum-idle=5
spring.datasource.hikari.idle-timeout=300000
""",
        "postgresql": """
# PostgreSQL Database Configuration
spring.datasource.url=jdbc:postgresql://localhost:5432/your_database_name
spring.datasource.username=your_username
spring.datasource.password=your_password
spring.datasource.driver-class-name=org.postgresql.Driver

# JPA/Hibernate Configuration
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=true
spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.PostgreSQLDialect
spring.jpa.properties.hibernate.format_sql=true
"""
    }
    return templates.get(database_type, templates["mysql"])

def get_database_config_class(target_language, database_type="mysql"):
    """
    Generate database configuration class for the target language.
    """
    if target_language.lower() == "java":
        return f"""
//Configuration
@Configuration
public class DatabaseConfig {{
    @Value("${{spring.datasource.url}}")
    private String url;

    @Value("${{spring.datasource.username}}")
    private String username;

    @Value("${{spring.datasource.password}}")
    private String password;

    @Bean
    public DataSource dataSource() {{
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(url);
        config.setUsername(username);
        config.setPassword(password);
        config.setMaximumPoolSize(10);
        config.setMinimumIdle(5);
        config.setIdleTimeout(300000);
        return new HikariDataSource(config);
    }}

    @Bean
    public JpaVendorAdapter jpaVendorAdapter() {{
        HibernateJpaVendorAdapter adapter = new HibernateJpaVendorAdapter();
        adapter.setShowSql(true);
        adapter.setGenerateDdl(true);
        adapter.setDatabase(Database.{database_type.upper()});
        return adapter;
    }}
}}
"""
    elif target_language.lower() == "c#":
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
            options.UseMySql(
                _configuration.GetConnectionString("DefaultConnection"),
                ServerVersion.AutoDetect(_configuration.GetConnectionString("DefaultConnection"))
            )
        );
        return services;
    }
}
"""

def get_dependencies(target_language, database_type="mysql"):
    """
    Return required dependencies for database configuration.
    """
    if target_language.lower() == "java":
        return """
// Add these dependencies to pom.xml
<dependencies>
    <!-- Spring Data JPA -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>

    <!-- MySQL Connector -->
    <dependency>
        <groupId>mysql</groupId>
        <artifactId>mysql-connector-java</artifactId>
        <scope>runtime</scope>
    </dependency>

    <!-- HikariCP Connection Pool -->
    <dependency>
        <groupId>com.zaxxer</groupId>
        <artifactId>HikariCP</artifactId>
    </dependency>
</dependencies>
"""
    elif target_language.lower() == "c#":
        return """
// Add these packages to your .csproj file
<ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="6.0.0" />
    <PackageReference Include="Pomelo.EntityFrameworkCore.MySql" Version="6.0.0" />
</ItemGroup>
"""