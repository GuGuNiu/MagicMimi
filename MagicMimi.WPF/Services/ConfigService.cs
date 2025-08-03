using System.Collections.Generic;
using System.IO;
using MagicMimi.WPF.Models;
using Newtonsoft.Json;

namespace MagicMimi.WPF.Services
{
    public class ConfigService
    {
        private const string AccountsFile = "mihoyo_accounts.json";

        public Dictionary<string, Account> LoadAccounts()
        {
            if (!File.Exists(AccountsFile))
            {
                return new Dictionary<string, Account>();
            }
            try
            {
                var json = File.ReadAllText(AccountsFile);
                return JsonConvert.DeserializeObject<Dictionary<string, Account>>(json) ?? new Dictionary<string, Account>();
            }
            catch
            {
                return new Dictionary<string, Account>();
            }
        }

        public void SaveAccounts(Dictionary<string, Account> accounts)
        {
            var json = JsonConvert.SerializeObject(accounts, Formatting.Indented);
            File.WriteAllText(AccountsFile, json);
        }
    }
}