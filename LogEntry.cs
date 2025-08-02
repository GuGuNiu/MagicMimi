using System;

namespace MagicMimi
{
    public class LogEntry
    {
        public DateTime Timestamp { get; set; }
        public string Message { get; set; }
        public string Level { get; set; }

        public LogEntry(string message, string level)
        {
            Timestamp = DateTime.Now;
            Message = message;
            Level = level;
        }
    }
}