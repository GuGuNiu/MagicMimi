# MagicMini - 咕咕牛的手提箱 🧰

**一个多技术栈实现的通用游戏扫码登录工具。**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-217346?style=for-the-badge&logo=Qt&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Vue.js](https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vue.js&logoColor=4FC08D)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![C#](https://img.shields.io/badge/C%23-239120?style=for-the-badge&logo=c-sharp&logoColor=white)
![.NET](https://img.shields.io/badge/.NET-512BD4?style=for-the-badge&logo=dotnet&logoColor=white)
![WPF](https://img.shields.io/badge/WPF-512BD4?style=for-the-badge&logo=.net&logoColor=white)

本项目旨在探索和展示使用不同技术栈构建同一款桌面或Web应用的可能性。其核心功能是通过扫描屏幕上的二维码，自动化完成特定游戏的账号登录流程，并提供了便捷的多账户管理功能。

当前项目包含以下三种实现版本：

1.  **Python PySide6 桌面版**
2.  **Web 版 (Python Flask 后端 + Vue.js 前端)**
3.  **WPF 桌面版 (C# .NET)**

---

## 核心功能

*   **智能扫码**: 可选择扫描整个屏幕中心区域，或指定特定应用程序窗口进行后台扫描。
*   **多账户管理**: 支持动态添加、保存、切换和删除多个账户凭据 (Stoken)。
*   **游戏支持**: 可在不同游戏（如"原神"、"星穹铁道"）之间切换。
*   **实时反馈**: 提供操作日志和实时扫描帧率(FPS)显示。
*   **窗口置顶**: 方便在游戏时将工具窗口保持在最前。

---

## 项目版本详情

### 1. 🖥️ PySide6 桌面版 (Python)

这是一个使用 Python 和 PySide6 (Qt for Python) 构建的现代化、跨平台桌面应用程序。它将所有功能打包在一个独立的可执行文件中，是功能最完善、最稳定的版本。

#### 截图预览
![PySide6 Version Screenshot](https://s2.loli.net/2025/08/09/t8PwSsEJZfzNFCk.png) 

#### 环境要求
*   Python 3.8+

#### 安装与运行
1.  **克隆或下载项目**
2.  **进入该版本目录**
    ```bash
    cd /path/to/your/project/pyside6_version
    ```
3.  **安装依赖库**
    建议创建一个虚拟环境。项目依赖库如下：
    ```
    PySide6
    opencv-python
    pyzbar
    pywin32
    numpy
    ```
    可以通过以下命令快速安装：
    ```bash
    pip install PySide6 opencv-python pyzbar pywin32 numpy
    ```
4.  **运行程序**
    ```bash
    python main.py
    ```

---

### 2. 🌐 Web 版 (Python Flask + Vue.js)

这是一个前后端分离的Web应用。后端使用轻量级的 Flask 框架处理扫码和API请求，前端使用流行的 Vue.js 框架构建用户交互界面。此版本允许通过浏览器访问工具，甚至可以部署在局域网内的其他机器上。

#### 环境要求
*   Python 3.8+ (用于后端)
*   Node.js 16+ (用于前端)

#### 安装与运行

需要分别启动后端和前端服务。

**后端 (Flask):**
1.  进入后端目录: `cd /path/to/your/project/flask_backend`
2.  安装Python依赖: `pip install Flask Pillow pyzbar opencv-python`
3.  启动后端服务: `flask run`
    *   默认情况下，后端会运行在 `http://127.0.0.1:5000`。

**前端 (Vue.js):**
1.  进入前端目录: `cd /path/to/your/project/vue_frontend`
2.  安装Node.js依赖: `npm install`
3.  启动前端开发服务: `npm run serve`
    *   默认情况下，前端会运行在 `http://localhost:8080`。
4.  在浏览器中打开前端地址 (`http://localhost:8080`) 即可使用。

---

### 3. ⌨️ WPF 桌面版 (C# .NET)

这是一个使用 C# 和 Windows Presentation Foundation (WPF) 构建的原生Windows桌面应用程序。它提供了最佳的Windows系统集成度和性能。

#### 环境要求
*   .NET Framework 4.7.2 或 .NET 6+ (取决于项目配置)
*   Visual Studio 2019 或更高版本

#### 安装与运行
1.  **打开解决方案**: 使用 Visual Studio 打开项目目录下的 `.sln` 文件。
2.  **还原依赖**: 在 Visual Studio 中，右键点击解决方案并选择 "还原 NuGet 包" (通常在首次生成时会自动执行)。
3.  **生成项目**: 点击菜单栏的 "生成" -> "生成解决方案" (快捷键 `Ctrl+Shift+B`)。
4.  **运行程序**:
    *   直接在 Visual Studio 中按 `F5` 启动调试运行。
    *   或在项目目录的 `bin/Debug` (或 `bin/Release`) 文件夹下找到生成的 `.exe` 文件并双击运行。

---

## 全局配置

本工具的所有账户信息都保存在程序目录下的 `accounts.json` 文件中，通过界面添加第一个账户时程序会自动生成。

## 免责声明

*   本软件仅供学习和技术研究使用，请勿用于商业或非法用途。
*   使用者应对自己的账户安全负责。建议在理解代码工作原理的基础上使用本工具。
*   因使用本软件而造成的任何账户损失或法律纠纷，作者概不负责。
