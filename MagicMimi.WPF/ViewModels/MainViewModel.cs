using System;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using MagicMimi.WPF.Models;
using MagicMimi.WPF.Services;
using MagicMimi.WPF.Views;

namespace MagicMimi.WPF.ViewModels
{
    public class MainViewModel : BaseViewModel
    {
        private readonly MihoyoService _mihoyoService;
        private readonly ConfigService _configService;
        private readonly WindowService _windowService;
        private CancellationTokenSource? _scannerCts;

        private bool _isScanning;
        public bool IsScanning { get => _isScanning; set { _isScanning = value; OnPropertyChanged(); OnPropertyChanged(nameof(StatusText)); } }

        private string _fps = "0.0";
        public string Fps { get => _fps; set { _fps = value; OnPropertyChanged(); OnPropertyChanged(nameof(StatusText)); } }

        public string StatusText => IsScanning ? $"扫描中 FPS {Fps}" : "已停止";

        private WindowInfo? _selectedWindow;
        public WindowInfo? SelectedWindow { get => _selectedWindow; set { _selectedWindow = value; OnPropertyChanged(); } }

        private AccountDisplay? _selectedAccount;
        public AccountDisplay? SelectedAccount { get => _selectedAccount; set { _selectedAccount = value; OnPropertyChanged(); } }

        private int _selectedGameType = 4;
        public int SelectedGameType { get => _selectedGameType; set { _selectedGameType = value; OnPropertyChanged(); } }

        public ObservableCollection<WindowInfo> Windows { get; } = new();
        public ObservableCollection<AccountDisplay> Accounts { get; } = new();
        public ObservableCollection<LogEntry> Logs { get; } = new();

        public ICommand RefreshWindowsCommand { get; }
        public ICommand StartStopScanCommand { get; }
        public ICommand ShowLoginDialogCommand { get; }
        public ICommand ShowManualAddDialogCommand { get; }
        public ICommand DeleteAccountCommand { get; }
        public ICommand MinimizeWindowCommand { get; }
        public ICommand CloseWindowCommand { get; }

        public MainViewModel()
        {
            _mihoyoService = new MihoyoService();
            _configService = new ConfigService();
            _windowService = new WindowService();

            RefreshWindowsCommand = new RelayCommand(_ => LoadWindows());
            StartStopScanCommand = new RelayCommand(_ => ToggleScan(), _ => CanScan());
            ShowLoginDialogCommand = new RelayCommand(_ => ShowLoginDialog());
            ShowManualAddDialogCommand = new RelayCommand(_ => ShowManualAddDialog());
            DeleteAccountCommand = new RelayCommand(_ => DeleteAccount(), _ => SelectedAccount != null);

            MinimizeWindowCommand = new RelayCommand(_ => Application.Current.MainWindow.WindowState = WindowState.Minimized);
            CloseWindowCommand = new RelayCommand(_ => Application.Current.MainWindow.Close());

            LoadAccounts();
            LoadWindows();
        }

        private bool CanScan() => SelectedWindow != null && SelectedAccount != null;

        private void LoadWindows()
        {
            Windows.Clear();
            var windows = _windowService.GetAllWindows();
            foreach (var win in windows)
            {
                Windows.Add(win);
            }
            SelectedWindow = Windows.FirstOrDefault(w => w.Title.Contains("原神") || w.Title.Contains("Star Rail"));
        }

        private void LoadAccounts()
        {
            Accounts.Clear();
            var accounts = _configService.LoadAccounts();
            foreach (var acc in accounts)
            {
                Accounts.Add(new AccountDisplay { Name = acc.Key, Uid = acc.Value.Uid, Cookie = acc.Value.Cookie });
            }
            SelectedAccount = Accounts.FirstOrDefault();
        }

        private void DeleteAccount()
        {
            if (SelectedAccount == null) return;
            string name = SelectedAccount.Name;
            if (MessageBox.Show($"确定要删除账户 '{name}' 吗？", "确认删除", MessageBoxButton.YesNo, MessageBoxImage.Warning) == MessageBoxResult.Yes)
            {
                var accounts = _configService.LoadAccounts();
                if (accounts.Remove(name))
                {
                    _configService.SaveAccounts(accounts);
                    LoadAccounts();
                    AddLog("SUCCESS", $"账户 '{name}' 已删除。");
                }
            }
        }
        private void ToggleScan()
        {
            if (IsScanning)
            {
                _scannerCts?.Cancel();
                IsScanning = false;
                AddLog("INFO", "扫描任务已手动停止。");
            }
            else
            {
                if (!CanScan())
                {
                    MessageBox.Show("请先选择目标窗口和账户！", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }
                IsScanning = true;
                _scannerCts = new CancellationTokenSource();
                Task.Run(() => ScanLoop(_scannerCts.Token), _scannerCts.Token);
                AddLog("INFO", "扫描任务已启动。");
            }
        }

        private async Task ScanLoop(CancellationToken token)
        {
            string? lastQrData = null;
            DateTime lastQrTime = DateTime.MinValue;
            var account = new Account { Uid = SelectedAccount!.Uid, Cookie = SelectedAccount!.Cookie };
            var windowHandle = SelectedWindow!.Hwnd;

            while (!token.IsCancellationRequested)
            {
                var startTime = Stopwatch.GetTimestamp();

                using var bmp = _mihoyoService.CaptureWindow(new IntPtr(windowHandle));
                if (bmp != null)
                {
                    var qrData = _mihoyoService.ScanQrCodeFromBitmap(bmp);
                    if (!string.IsNullOrEmpty(qrData) && (qrData != lastQrData || (DateTime.UtcNow - lastQrTime).TotalSeconds > 5))
                    {
                        var match = Regex.Match(qrData, @"ticket=([a-fA-F0-9]+)");
                        if (match.Success)
                        {
                            lastQrData = qrData;
                            lastQrTime = DateTime.UtcNow;
                            AddLog("SUCCESS", "发现有效游戏二维码，正在尝试登录...");

                            var ticket = match.Groups[1].Value;
                            var (success, message) = await _mihoyoService.AttemptGameLoginAsync(ticket, SelectedGameType, account);

                            AddLog(success ? "SUCCESS" : "ERROR", success ? $"抢码成功！账户: {account.Uid}" : $"抢码失败: {message}");
                            if (success)
                            {
                                try { await Task.Delay(5000, token); } catch (TaskCanceledException) { break; }
                            }
                        }
                    }
                }

                var elapsed = Stopwatch.GetElapsedTime(startTime);
                double fps = elapsed.TotalSeconds > 0 ? 1.0 / elapsed.TotalSeconds : 0;
                Application.Current.Dispatcher.Invoke(() => Fps = $"{fps:F1}");

                try { await Task.Delay(500, token); } catch (TaskCanceledException) { break; }
            }
        }

        private void ShowLoginDialog()
        {
            var loginViewModel = new LoginViewModel(_mihoyoService, _configService);
            var loginWindow = new LoginWindow { DataContext = loginViewModel, Owner = Application.Current.MainWindow };

            loginWindow.LoginSuccess += (s, e) =>
            {
                LoadAccounts();
                AddLog("SUCCESS", $"新账户 '{e.Name}' 已成功保存。");
                loginWindow.Close();
            };
            loginWindow.ShowDialog();
        }

        private void ShowManualAddDialog()
        {
            var manualAddWindow = new ManualAddAccountWindow { Owner = Application.Current.MainWindow };
            manualAddWindow.AccountAdded += (sender, args) =>
            {
                var (name, newAccount) = args;
                var accounts = _configService.LoadAccounts();
                if (accounts.ContainsKey(name))
                {
                    MessageBox.Show("该账户名已存在！", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }
                accounts[name] = newAccount;
                _configService.SaveAccounts(accounts);

                LoadAccounts();
                AddLog("SUCCESS", $"新账户 '{name}' 已通过手动方式成功保存。");
            };
            manualAddWindow.ShowDialog();
        }

        private void AddLog(string level, string message)
        {
            var log = new LogEntry { Timestamp = DateTime.Now.ToString("HH:mm:ss"), Level = level, Message = message };
            Application.Current.Dispatcher.Invoke(() =>
            {
                if (Logs.Count > 200) Logs.RemoveAt(0);
                Logs.Add(log);
            });
        }
    }

    public class AccountDisplay : Account
    {
        public string Name { get; set; } = string.Empty;
        public override string ToString() => $"{Name} ({Uid})";
    }
}