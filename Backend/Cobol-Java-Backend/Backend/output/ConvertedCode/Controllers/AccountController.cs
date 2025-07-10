using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using BankingApp.Domain.Entities;
using BankingApp.Services.Interfaces;

namespace BankingApp.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class AccountController : ControllerBase
    {
        private readonly IAccountService _accountService;

        public AccountController(IAccountService accountService)
        {
            _accountService = accountService;
        }

        [HttpGet]
        public async Task<ActionResult<IEnumerable<AccountRecord>>> GetAllAccounts()
        {
            var accounts = await _accountService.GetAllAccountsAsync();
            return Ok(accounts);
        }

        [HttpGet("{accountNumber}")]
        public async Task<ActionResult<AccountRecord>> GetAccountById(long accountNumber)
        {
            var account = await _accountService.GetAccountByIdAsync(accountNumber);
            if (account == null)
            {
                return NotFound();
            }
            return Ok(account);
        }

        [HttpPost]
        public async Task<ActionResult> AddAccount([FromBody] AccountRecord account)
        {
            await _accountService.AddAccountAsync(account);
            return CreatedAtAction(nameof(GetAccountById), new { accountNumber = account.AccountNumber }, account);
        }

        [HttpPut("{accountNumber}")]
        public async Task<ActionResult> UpdateAccount(long accountNumber, [FromBody] AccountRecord account)
        {
            if (accountNumber != account.AccountNumber)
            {
                return BadRequest();
            }
            await _accountService.UpdateAccountAsync(account);
            return NoContent();
        }

        [HttpDelete("{accountNumber}")]
        public async Task<ActionResult> DeleteAccount(long accountNumber)
        {
            await _accountService.DeleteAccountAsync(accountNumber);
            return NoContent();
        }
    }
}