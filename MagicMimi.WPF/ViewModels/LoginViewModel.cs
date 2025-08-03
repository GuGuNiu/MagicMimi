using System;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using MagicMimi.WPF.Models;
using MagicMimi.WPF.Services;

namespace MagicMimi.WPF.ViewModels
{
    public class LoginViewModel : BaseViewModel
    {
        private readonly MihoyoService _mihoyoService;
        private readonly ConfigService _configService;
        private DispatcherTimer? _statusTimer;
        private string _ticket = string.Empty;
        private string _device = string.Empty;

        private BitmapImage? _qrCodeImage;
        public BitmapImage? QrCodeImage { get => _qrCodeImage; set { _qrCodeImage = value; OnPropertyChanged(); } }

        private string _qrStatusText = "正在获取二维码...";
        public string QrStatusText { get => _qrStatusText; set { _qrStatusText = value; OnPropertyChanged(); } }

        private string _accountName = string.Empty;
        public string AccountName { get => _accountName; set { _accountName = value; OnPropertyChanged(); } }

        private bool _isLoginConfirmed;
        public bool IsLoginConfirmed { get => _isLoginConfirmed; set { _isLoginConfirmed = value; OnPropertyChanged(); } }

        private Account? _newAccount;
        public ICommand SaveAccountCommand { get; }
        public event EventHandler<LoginSuccessEventArgs>? LoginSuccess;

        public LoginViewModel(MihoyoService mihoyoService, ConfigService configService)
        {
            _mihoyoService = mihoyoService;
            _configService = configService;
            SaveAccountCommand = new RelayCommand(_ => SaveAccount(), _ => CanSave());
            _ = Initialize();
        }

        private bool CanSave() => !string.IsNullOrWhiteSpace(AccountName) && _newAccount != null;

        private async Task Initialize()
        {
            var qrData = await _mihoyoService.FetchQrCodeAsync();
            if (qrData.HasValue)
            {
                QrCodeImage = qrData.Value.QrImage;
                _ticket = qrData.Value.Ticket;
                _device = qrData.Value.Device;
                QrStatusText = "请使用米游社App扫描二维码";
                StartStatusPolling();
            }
            else
            {
                QrStatusText = "获取二维码失败，请重试。";
            }
        }

        private void StartStatusPolling()
        {
            _statusTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(2) };
            _statusTimer.Tick += async (s, e) => await CheckStatusAsync();
            _statusTimer.Start();
        }

        private async Task CheckStatusAsync()
        {
            if (string.IsNullOrEmpty(_ticket)) return;

            var (message, newAccount) = await _mihoyoService.QueryQrStatusAsync(_ticket, _device);
            QrStatusText = message;
            if (newAccount != null)
            {
                _statusTimer?.Stop();
                _newAccount = newAccount;
                AccountName = $"Mimi_{newAccount.Uid.AsSpan(0, 4)}";
                IsLoginConfirmed = true;
                QrStatusText = "扫码成功！请为新账户命名并保存。";
            }
        }

        private void SaveAccount()
        {
            if (!CanSave()) return;

            var accounts = _configService.LoadAccounts();
            if (accounts.ContainsKey(AccountName))
            {
                MessageBox.Show("该账户名已存在，请使用其他名称。", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            accounts[AccountName] = _newAccount!;
            _configService.SaveAccounts(accounts);

            LoginSuccess?.Invoke(this, new LoginSuccessEventArgs { Name = AccountName });
        }

        public void Cleanup()
        {
            _statusTimer?.Stop();
        }
    }

    public class LoginSuccessEventArgs : EventArgs
    {
        public string Name { get; set; } = string.Empty;
    }
}