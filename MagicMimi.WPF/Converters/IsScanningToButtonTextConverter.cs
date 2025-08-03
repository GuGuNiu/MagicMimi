using System;
using System.Globalization;
using System.Windows.Data;

namespace MagicMimi.WPF.Converters
{
    public class IsScanningToButtonTextConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is bool isScanning)
            {
                return isScanning ? "停止扫描" : "开始扫描";
            }
            return "开始扫描";
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}