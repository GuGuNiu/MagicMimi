namespace MagicMimi.WPF.Models
{
    public class WindowInfo
    {
        public string Title { get; set; }
        public long Hwnd { get; set; }

        public override string ToString() => Title;
    }
}