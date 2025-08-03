using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Media.Imaging;
using MagicMimi.WPF.Models;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using QRCoder;
using ZXing;
using ZXing.Common;
using ZXing.Windows.Compatibility;

namespace MagicMimi.WPF.Services
{
    public class MihoyoService
    {
        private readonly HttpClient _httpClient;
        private const string AppVersion = "2.73.1";
        private const string SaltApp = "x6v3p3p354y2h4y2t4w4x2y2y4y2h4y2";
        private const int QrLoginAppId = 4;

        public MihoyoService()
        {
            var handler = new HttpClientHandler
            {
                ServerCertificateCustomValidationCallback = (message, cert, chain, errors) => true,
                UseProxy = false,
                Proxy = null
            };
            _httpClient = new HttpClient(handler);
            _httpClient.DefaultRequestHeaders.Add("x-rpc-client_type", "2");
            _httpClient.DefaultRequestHeaders.Add("x-rpc-app_version", AppVersion);
            _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("okhttp/4.8.0");
        }

        private string GetDs(string query = "", string body = "")
        {
            long t = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            string r = GetRandomString(6);
            string checkString = $"salt={SaltApp}&t={t}&r={r}&b={body}&q={query}";
            using var md5 = MD5.Create();
            byte[] hashBytes = md5.ComputeHash(Encoding.UTF8.GetBytes(checkString));
            string c = BitConverter.ToString(hashBytes).Replace("-", "").ToLower();
            return $"{t},{r},{c}";
        }

        private string GetRandomString(int length)
        {
            const string chars = "abcdefghijklmnopqrstuvwxyz0123456789";
            var random = new Random();
            return new string(Enumerable.Repeat(chars, length)
              .Select(s => s[random.Next(s.Length)]).ToArray());
        }

        public async Task<(string Ticket, string Device, BitmapImage QrImage)?> FetchQrCodeAsync()
        {
            string deviceId = Guid.NewGuid().ToString().ToUpper();
            var payload = new { app_id = QrLoginAppId, device = deviceId };
            string jsonPayload = JsonConvert.SerializeObject(payload);

            var request = new HttpRequestMessage(HttpMethod.Post, "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/fetch")
            {
                Content = new StringContent(jsonPayload, Encoding.UTF8, "application/json")
            };
            request.Headers.Add("x-rpc-device_id", deviceId);
            request.Headers.Add("DS", GetDs(body: jsonPayload));

            try
            {
                var response = await _httpClient.SendAsync(request);
                response.EnsureSuccessStatusCode();
                var content = await response.Content.ReadAsStringAsync();
                var data = JObject.Parse(content);

                if (data["retcode"]?.Value<int>() == 0)
                {
                    string url = data["data"]?["url"]?.Value<string>() ?? "";
                    string ticket = data["data"]?["ticket"]?.Value<string>() ?? "";
                    if (!string.IsNullOrEmpty(url) && !string.IsNullOrEmpty(ticket))
                    {
                        var qrImage = GenerateQrBitmapImage(url);
                        return (ticket, deviceId, qrImage);
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Fetch QR Code failed: {ex.Message}");
            }
            return null;
        }

        public async Task<(string Message, Account? NewAccount)> QueryQrStatusAsync(string ticket, string deviceId)
        {
            var payload = new { app_id = QrLoginAppId, device = deviceId, ticket };
            string jsonPayload = JsonConvert.SerializeObject(payload);

            var request = new HttpRequestMessage(HttpMethod.Post, "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/query")
            {
                Content = new StringContent(jsonPayload, Encoding.UTF8, "application/json")
            };
            request.Headers.Add("x-rpc-device_id", deviceId);
            request.Headers.Add("DS", GetDs(body: jsonPayload));

            try
            {
                var response = await _httpClient.SendAsync(request);
                response.EnsureSuccessStatusCode();
                var content = await response.Content.ReadAsStringAsync();
                var data = JObject.Parse(content);
                string message = data["data"]?["message"]?.Value<string>() ?? "查询中...";

                if (data["retcode"]?.Value<int>() == 0 && data["data"]?["stat"]?.Value<string>() == "Confirmed")
                {
                    string rawPayload = data["data"]?["payload"]?["raw"]?.Value<string>() ?? "";
                    var payloadData = JObject.Parse(rawPayload);
                    string uid = payloadData["uid"]?.Value<string>() ?? "";
                    string gameToken = payloadData["token"]?.Value<string>() ?? "";

                    if (!string.IsNullOrEmpty(uid) && !string.IsNullOrEmpty(gameToken))
                    {
                        var (cookie, error) = await GetStokenFromGameTokenAsync(uid, gameToken);
                        if (!string.IsNullOrEmpty(cookie))
                        {
                            return ("扫码成功！", new Account { Uid = uid, Cookie = cookie });
                        }
                        return ($"获取Stoken失败: {error}", null);
                    }
                }
                return (message, null);
            }
            catch (Exception ex)
            {
                return ($"查询状态失败: {ex.Message}", null);
            }
        }

        private async Task<(string? Cookie, string? Error)> GetStokenFromGameTokenAsync(string uid, string gameToken)
        {
            var payload = new { account_id = long.Parse(uid), game_token = gameToken };
            var content = new StringContent(JsonConvert.SerializeObject(payload), Encoding.UTF8, "application/json");

            try
            {
                var response = await _httpClient.PostAsync("https://passport-api.mihoyo.com/account/ma-cn-session/app/getTokenByGameToken", content);
                response.EnsureSuccessStatusCode();
                var json = await response.Content.ReadAsStringAsync();
                var data = JObject.Parse(json);
                if (data["retcode"]?.Value<int>() == 0)
                {
                    string? stoken = data["data"]?["token"]?["token"]?.Value<string>();
                    string? mid = data["data"]?["user_info"]?["mid"]?.Value<string>();
                    if (stoken != null && mid != null)
                    {
                        return ($"stuid={uid};stoken={stoken};mid={mid};", null);
                    }
                }
                return (null, data["message"]?.Value<string>() ?? "未知错误");
            }
            catch (Exception ex)
            {
                return (null, ex.Message);
            }
        }

        private BitmapImage GenerateQrBitmapImage(string text)
        {
            using var qrGenerator = new QRCodeGenerator();
            using var qrCodeData = qrGenerator.CreateQrCode(text, QRCodeGenerator.ECCLevel.Q);
            using var qrCode = new PngByteQRCode(qrCodeData);
            byte[] qrCodeAsPngByteArr = qrCode.GetGraphic(20);

            using var stream = new MemoryStream(qrCodeAsPngByteArr);
            var bitmapImage = new BitmapImage();
            bitmapImage.BeginInit();
            bitmapImage.CacheOption = BitmapCacheOption.OnLoad;
            bitmapImage.StreamSource = stream;
            bitmapImage.EndInit();
            bitmapImage.Freeze();
            return bitmapImage;
        }

        [System.Runtime.InteropServices.DllImport("user32.dll")]
        private static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);
        [System.Runtime.InteropServices.DllImport("user32.dll")]
        private static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);

        public Bitmap? CaptureWindow(IntPtr hWnd)
        {
            try
            {
                if (!GetClientRect(hWnd, out RECT rect) || rect.Width <= 0 || rect.Height <= 0)
                {
                    return null;
                }
                var bmp = new Bitmap(rect.Width, rect.Height, PixelFormat.Format32bppRgb);
                using (var g = Graphics.FromImage(bmp))
                {
                    var hdc = g.GetHdc();
                    PrintWindow(hWnd, hdc, 3);
                    g.ReleaseHdc(hdc);
                }
                return bmp;
            }
            catch { return null; }
        }

        public string? ScanQrCodeFromBitmap(Bitmap? bmp)
        {
            if (bmp == null) return null;
            var reader = new BarcodeReader
            {
                AutoRotate = true,
                Options = new DecodingOptions { TryHarder = true, TryInverted = true }
            };
            var result = reader.Decode(bmp);
            return result?.Text;
        }

        public async Task<(bool Success, string Message)> AttemptGameLoginAsync(string ticket, int gameType, Account account)
        {
            string device = Guid.NewGuid().ToString();
            string host = "api-sdk.mihoyo.com";
            string scanPath = gameType == 4 ? "/hk4e_cn/combo/panda/qrcode/scan" : "/hkrpg_cn/combo/panda/qrcode/scan";

            try
            {
                var scanPayload = new { app_id = gameType, device, ticket };
                var scanContent = new StringContent(JsonConvert.SerializeObject(scanPayload), Encoding.UTF8, "application/json");
                var scanRes = await _httpClient.PostAsync($"https://{host}{scanPath}", scanContent);
                scanRes.EnsureSuccessStatusCode();
                var scanData = JObject.Parse(await scanRes.Content.ReadAsStringAsync());
                if (scanData["retcode"]?.Value<int>() != 0) return (false, $"Scan失败: {scanData["message"]}");

                var gtRequest = new HttpRequestMessage(HttpMethod.Get, "https://api-takumi.mihoyo.com/auth/api/getGameToken");
                gtRequest.Headers.Add("Cookie", account.Cookie);
                var gtRes = await _httpClient.SendAsync(gtRequest);
                gtRes.EnsureSuccessStatusCode();
                var gtData = JObject.Parse(await gtRes.Content.ReadAsStringAsync());
                if (gtData["retcode"]?.Value<int>() != 0) return (false, $"获取GameToken失败: {gtData["message"]}");
                string gameToken = gtData["data"]?["game_token"]?.Value<string>() ?? "";

                string confirmPath = gameType == 4 ? "/hk4e_cn/combo/panda/qrcode/confirm" : "/hkrpg_cn/combo/panda/qrcode/confirm";
                var confirmPayloadRaw = new { uid = account.Uid, token = gameToken };
                var confirmPayload = new
                {
                    app_id = gameType,
                    device,
                    ticket,
                    payload = new { proto = "Account", raw = JsonConvert.SerializeObject(confirmPayloadRaw) }
                };
                var confirmContent = new StringContent(JsonConvert.SerializeObject(confirmPayload), Encoding.UTF8, "application/json");
                var confirmRes = await _httpClient.PostAsync($"https://{host}{confirmPath}", confirmContent);
                confirmRes.EnsureSuccessStatusCode();
                var confirmData = JObject.Parse(await confirmRes.Content.ReadAsStringAsync());

                return (confirmData["retcode"]?.Value<int>() == 0, confirmData["message"]?.Value<string>() ?? "登录确认成功");
            }
            catch (Exception ex)
            {
                return (false, $"网络请求异常: {ex.Message}");
            }
        }

        [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
        private struct RECT
        {
            public int Left, Top, Right, Bottom;
            public int Width => Right - Left;
            public int Height => Bottom - Top;
        }
    }
}