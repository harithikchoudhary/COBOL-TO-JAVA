using System.Collections.Generic;
using System.Threading.Tasks;
using BankingApp.Domain.Entities;
using BankingApp.Repositories.Interfaces;
using BankingApp.Services.Interfaces;

namespace BankingApp.Services
{
    public class AccountService : IAccountService
    {
        private readonly IAccountRepository _accountRepository;

        public AccountService(IAccountRepository accountRepository)
        {
            _accountRepository = accountRepository;
        }

        public async Task<IEnumerable<AccountRecord>> GetAllAccountsAsync()
        {
            return await _accountRepository.GetAllAccountsAsync();
        }

        public async Task<AccountRecord> GetAccountByIdAsync(long accountNumber)
        {
            return await _accountRepository.GetAccountByIdAsync(accountNumber);
        }

        public async Task AddAccountAsync(AccountRecord account)
        {
            await _accountRepository.AddAccountAsync(account);
        }

        public async Task UpdateAccountAsync(AccountRecord account)
        {
            await _accountRepository.UpdateAccountAsync(account);
        }

        public async Task DeleteAccountAsync(long accountNumber)
        {
            await _accountRepository.DeleteAccountAsync(accountNumber);
        }
    }
}