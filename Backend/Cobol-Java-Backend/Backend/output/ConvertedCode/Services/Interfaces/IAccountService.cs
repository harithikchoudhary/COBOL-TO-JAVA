using System.Collections.Generic;
using System.Threading.Tasks;
using BankingApp.Domain.Entities;

namespace BankingApp.Services.Interfaces
{
    public interface IAccountService
    {
        Task<IEnumerable<AccountRecord>> GetAllAccountsAsync();
        Task<AccountRecord> GetAccountByIdAsync(long accountNumber);
        Task AddAccountAsync(AccountRecord account);
        Task UpdateAccountAsync(AccountRecord account);
        Task DeleteAccountAsync(long accountNumber);
    }
}