using System.Windows;
using MagicMimi.WPF.Services;

namespace MagicMimi.WPF
{
    public partial class App : Application
    {
        public static MihoyoService MihoyoService { get; private set; } = new MihoyoService();
    }
}