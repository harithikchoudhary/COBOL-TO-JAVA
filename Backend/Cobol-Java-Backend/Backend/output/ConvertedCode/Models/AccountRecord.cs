using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace BankingApp.Domain.Entities
{
    public class AccountRecord
    {
        [Key]
        [Column("ACC_NUMBER")]
        public long AccountNumber { get; set; }

        [Required]
        [Column("ACC_HOLDER_NAME")]
        [StringLength(50)]
        public string AccountHolderName { get; set; }

        [Column("ACC_TYPE")]
        [StringLength(2)]
        public string AccountType { get; set; }

        [Column("ACC_BALANCE")]
        public decimal AccountBalance { get; set; }

        [Column("ACC_STATUS")]
        [StringLength(1)]
        public string AccountStatus { get; set; }

        [Column("ACC_OPEN_DATE")]
        public DateTime AccountOpenDate { get; set; }

        [Column("ACC_LAST_ACTIVITY")]
        public DateTime AccountLastActivity { get; set; }
    }
}