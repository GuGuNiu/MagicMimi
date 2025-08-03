using System;
using System.Globalization;
using System.Windows.Data;

namespace MagicMimi.WPF.Converters
{
    public class EnumToBooleanConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            // object? 表示参数可能为 null
            if (value == null || parameter == null)
            {
                return false;
            }

            string currentValue = value.ToString() ?? "";
            string parameterValue = parameter.ToString() ?? "";

            return currentValue.Equals(parameterValue);
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is true && parameter != null)
            {
                if (int.TryParse(parameter.ToString(), out int result))
                {
                    return result;
                }
            }
            return Binding.DoNothing;
        }
    }
}