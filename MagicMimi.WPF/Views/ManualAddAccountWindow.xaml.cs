using System;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Input;
using MagicMimi.WPF.Models;

namespace MagicMimi.WPF.Views
{
    public partial class ManualAddAccountWindow : Window
    {
        public event EventHandler<(string Name, Account Account)>? AccountAdded;

        public ManualAddAccountWindow()
        {
            InitializeComponent();
        }

        private void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            string name = AccountNameTextBox.Text.Trim();
            string cookie = StokenCookieTextBox.Text.Trim();

            if (string.IsNullOrWhiteSpace(name) || string.IsNullOrWhiteSpace(cookie))
            {
                MessageBox.Show("账户名称和 Stoken Cookie 均不能为空！", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            // 从 Cookie 中提取 stuid
            var match = Regex.Match(cookie, @"stuid=(\d+);");
            if (!match.Success)
            {
                MessageBox.Show("无效的 Stoken Cookie 格式，必须包含 'stuid=...' 部分。", "格式错误", MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }
            string uid = match.Groups[1].Value;

            var newAccount = new Account { Uid = uid, Cookie = cookie };

            // 触发事件，将新账户数据传回给 MainViewModel
            AccountAdded?.Invoke(this, (name, newAccount));
            this.Close();
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        private void Window_MouseDown(object sender, MouseButtonEventArgs e)
        {
            if (e.LeftButton == MouseButtonState.Pressed)
            {
                this.DragMove();
            }
        }
    }
}