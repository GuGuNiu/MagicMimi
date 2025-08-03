using System; 
using System.Windows;
using System.Windows.Input;
using MagicMimi.WPF.ViewModels;

namespace MagicMimi.WPF.Views
{
    public partial class LoginWindow : Window
    {
        public event EventHandler<LoginSuccessEventArgs>? LoginSuccess
        {
            add
            {
                if (DataContext is LoginViewModel vm) vm.LoginSuccess += value;
            }
            remove
            {
                if (DataContext is LoginViewModel vm) vm.LoginSuccess -= value;
            }
        }

        public LoginWindow()
        {
            InitializeComponent();
        }

        private void Window_Unloaded(object sender, RoutedEventArgs e)
        {
            if (DataContext is LoginViewModel vm)
            {
                vm.Cleanup();
            }
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