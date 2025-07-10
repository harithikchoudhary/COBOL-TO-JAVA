using Microsoft.EntityFrameworkCore;
using BankingApp.Domain.Entities;

namespace BankingApp.Data
{
    public class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        public DbSet<AccountRecord> Accounts { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            modelBuilder.Entity<AccountRecord>().ToTable("ACCOUNTS");
        }
    }
}