using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using BankingApp.Data;
using BankingApp.Domain.Entities;
using BankingApp.Repositories.Interfaces;

namespace BankingApp.Repositories
{
    public class AccountRepository : IAccountRepository
    {
        private readonly ApplicationDbContext _context;

        public AccountRepository(ApplicationDbContext context)
        {
            _context = context;
        }

        public async Task<IEnumerable<AccountRecord>> GetAllAccountsAsync()
        {
            return await _context.Accounts.ToListAsync();
        }

        public async Task<AccountRecord> GetAccountByIdAsync(long accountNumber)
        {
            return await _context.Accounts.FindAsync(accountNumber);
        }

        public async Task AddAccountAsync(AccountRecord account)
        {
            await _context.Accounts.AddAsync(account);
            await _context.SaveChangesAsync();
        }

        public async Task UpdateAccountAsync(AccountRecord account)
        {
            _context.Accounts.Update(account);
            await _context.SaveChangesAsync();
        }

        public async Task DeleteAccountAsync(long accountNumber)
        {
            var account = await _context.Accounts.FindAsync(accountNumber);
            if (account != null)
            {
                _context.Accounts.Remove(account);
                await _context.SaveChangesAsync();
            }
        }
    }
}