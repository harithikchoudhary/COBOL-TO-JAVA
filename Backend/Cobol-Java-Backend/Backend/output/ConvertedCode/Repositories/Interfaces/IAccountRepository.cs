using System.Collections.Generic;
using System.Threading.Tasks;
using BankingApp.Domain.Entities;

namespace BankingApp.Repositories.Interfaces
{
    public interface IAccountRepository
    {
        Task<IEnumerable<AccountRecord>> GetAllAccountsAsync();
        Task<AccountRecord> GetAccountByIdAsync(long accountNumber);
        Task AddAccountAsync(AccountRecord account);
        Task UpdateAccountAsync(AccountRecord account);
        Task DeleteAccountAsync(long accountNumber);
    }
}