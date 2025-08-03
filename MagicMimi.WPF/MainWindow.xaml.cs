using System;
using System.Collections.Specialized;
using System.Drawing;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media.Animation;
using MagicMimi.WPF.ViewModels;

namespace MagicMimi.WPF
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
            // 主窗口的 Loaded 事件只负责它自己的初始化
            this.Loaded += MainWindow_Loaded;
        }

        private void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
           
        }

        private void Window_MouseDown(object sender, MouseButtonEventArgs e)
        {
            if (e.LeftButton == MouseButtonState.Pressed)
            {
                this.DragMove();
            }
        }

        // 动画逻辑移至此处的专用 Loaded 事件处理器
        private void AppTitle_Loaded(object sender, RoutedEventArgs e)
        {
            // 直接使用 sender，它就是触发事件的 TextBlock 控件
            if (sender is TextBlock textBlock)
            {
                // 确保 Foreground 画刷是 LinearGradientBrush
                if (textBlock.Foreground is System.Windows.Media.LinearGradientBrush originalBrush)
                {
                    // 创建画刷的可修改副本，避免 "只读状态" 错误
                    var cloneBrush = (System.Windows.Media.LinearGradientBrush)originalBrush.Clone();

                    var transform = new System.Windows.Media.TranslateTransform();
                    cloneBrush.Transform = transform;

                    // 将控件的画刷设置为新的可修改副本
                    textBlock.Foreground = cloneBrush;

                    // 定义并启动动画
                    var animation = new DoubleAnimation
                    {
                        From = 0,
                        To = -200, // 移动一个完整的色彩循环
                        Duration = TimeSpan.FromSeconds(10),
                        RepeatBehavior = RepeatBehavior.Forever
                    };
                    transform.BeginAnimation(System.Windows.Media.TranslateTransform.XProperty, animation);
                }
            }
        }

        // 日志自动滚动逻辑
        private void LogScrollViewer_Loaded(object sender, RoutedEventArgs e)
        {
            if (DataContext is MainViewModel vm && sender is ScrollViewer viewer)
            {
                // 订阅 ViewModel 中 Logs 集合的变化
                vm.Logs.CollectionChanged += (s, args) =>
                {
                    // 当有新日志添加时，滚动到底部
                    if (args.Action == NotifyCollectionChangedAction.Add)
                    {
                        viewer.ScrollToBottom();
                    }
                };
            }
        }
    }
}