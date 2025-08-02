using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Input;

namespace MagicMimi
{
    // --- 辅助类 ---
    public class ObservableObject : INotifyPropertyChanged
    {
        public event PropertyChangedEventHandler? PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string? name = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
    }

    public class RelayCommand : ICommand
    {
        private readonly Action _execute;
        public event EventHandler? CanExecuteChanged { add { } remove { } }
        public RelayCommand(Action execute) => _execute = execute;
        public bool CanExecute(object? parameter) => true;
        public void Execute(object? parameter) => _execute();
    }

    // --- 主ViewModel ---
    public class MainViewModel : ObservableObject
    {
        private bool _isScanning;
        public bool IsScanning
        {
            get => _isScanning;
            set { _isScanning = value; OnPropertyChanged(); OnPropertyChanged(nameof(ScanButtonText)); }
        }

        public string ScanButtonText => IsScanning ? "停止扫描" : "开始扫描";

        private string _fps = "0.0";
        public string Fps
        {
            get => _fps;
            set { _fps = value; OnPropertyChanged(); }
        }

        public ObservableCollection<LogEntry> Logs { get; } = new();

        public ICommand ToggleScanCommand { get; }
        public ICommand MinimizeWindowCommand { get; }
        public ICommand CloseWindowCommand { get; }

        public MainViewModel()
        {
            ToggleScanCommand = new RelayCommand(ToggleScan);
            MinimizeWindowCommand = new RelayCommand(() => Application.Current.MainWindow.WindowState = WindowState.Minimized);
            CloseWindowCommand = new RelayCommand(() => Application.Current.MainWindow.Close());

            AddLog("欢迎使用 咕咕牛万能咪咪!", "SUCCESS");
            AddLog("系统初始化完成。", "INFO");
        }

        private void ToggleScan()
        {
            IsScanning = !IsScanning;
            AddLog(IsScanning ? "扫描任务已开始..." : "扫描任务已停止。", "INFO");
        }

        public void AddLog(string message, string level)
        {
            Application.Current.Dispatcher.Invoke(() => Logs.Add(new LogEntry(message, level)));
        }
    }
}