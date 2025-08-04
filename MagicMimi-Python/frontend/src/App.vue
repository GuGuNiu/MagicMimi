<template>
  <el-config-provider>
    <!-- 整个应用容器，设为可拖动区域，并应用桌面背景 -->
    <div id="app" class="pywebview-drag-region" :style="{ backgroundImage: `url(${desktopBgUrl})` }">
      
      <!-- 左侧面板 -->
      <div class="content-panel left-panel">
        <!-- 标题区域 -->
        <h1 class="app-title">咕咕牛万能咪咪</h1>
        
        <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 15px; overflow-y: auto; padding-right: 5px;">
          <div class="config-section">
            <h2 class="section-title">账户管理</h2>
            <el-button class="mimi-button mimi-button-primary" type="primary" :icon="User" @click="handleLogin" :loading="loginLoading" style="width: 100%; margin-bottom: 15px;">
              扫码登录 获取Stoken
            </el-button>
            <el-form label-width="80px" @submit.prevent>
              <el-form-item label="使用账户">
                <div class="compact-line">
                  <el-select 
                    v-model="scanForm.account_name" placeholder="请选择账户" style="flex-grow: 1;"
                    class="mimi-select" popper-class="mimi-dropdown"
                  >
                    <el-option v-for="(acc, name) in accounts" :key="name" :label="`${name} (UID ${acc.uid})`" :value="name" />
                  </el-select>
                  <el-button class="mimi-button mimi-button-danger" :icon="Delete" @click="handleDeleteAccount" :disabled="!scanForm.account_name" />
                </div>
              </el-form-item>
            </el-form>
          </div>

          <div class="config-section">
            <h2 class="section-title">扫描任务</h2>
            <el-form label-width="80px" @submit.prevent>
              <el-form-item label="目标窗口">
                <div class="compact-line">
                  <el-select 
                    v-model="scanForm.hwnd" placeholder="请选择窗口" filterable style="flex-grow: 1;"
                    class="mimi-select" popper-class="mimi-dropdown"
                  >
                    <el-option v-for="win in windows" :key="win.hwnd" :label="win.title" :value="win.hwnd" />
                  </el-select>
                  <el-button class="mimi-button mimi-button-secondary" :icon="Refresh" @click="fetchWindows" :loading="windowsLoading" />
                </div>
              </el-form-item>
              <el-form-item label="目标游戏">
                <el-radio-group v-model="scanForm.game_type" class="mimi-radio-group">
                  <el-radio-button :label="4">原神</el-radio-button>
                  <el-radio-button :label="8">星穹铁道</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-form>
          </div>
          
          <el-button @click="apiSettingsDialogVisible = true" :icon="Setting" class="mimi-button mimi-button-secondary" style="width: 100%;">
            高级设置 API参数
          </el-button>
        </div>

        <div class="config-section" style="margin-top: auto; padding-top: 15px; border-top: 2px solid var(--magic-border-light);">
          <el-button 
            class="mimi-button"
            :class="isScanning ? 'mimi-button-danger' : 'mimi-button-action'"
            @click="toggleScan" :loading="scanToggleLoading" style="width: 100%;"
          >
            {{ isScanning ? '停止扫描' : '开始扫描' }}
          </el-button>
        </div>
      </div>

      <!-- 右侧面板 -->
      <div class="content-panel right-panel">
        <!-- 窗口控制按钮 固定在右上角 -->
        <div class="window-controls">
          <el-button class="mimi-button mimi-button-secondary" :icon="SemiSelect" @click="minimizeWindow" circle />
          <el-button class="mimi-button mimi-button-danger" :icon="CloseBold" @click="closeWindow" circle />
        </div>

        <div class="log-panel-header">
          <h2 class="section-title">实时日志</h2>
          <div style="display: flex; align-items: center; gap: 20px;">
            <el-tag :type="isScanning ? 'success' : 'info'" size="large">
              状态 {{ isScanning ? `扫描中 FPS ${fps}` : '已停止' }}
            </el-tag>
            <el-switch
              v-model="isDark" style="--el-switch-on-color: #2c2c2c; --el-switch-off-color: #f2f2f2"
              inline-prompt :active-icon="Moon" :inactive-icon="Sunny" @change="toggleDark"
            />
          </div>
        </div>
        <div class="log-box" ref="logBoxRef">
          <div v-for="(log, index) in logs" :key="index" class="log-line" :class="log.level">
            <span class="timestamp">[{{ log.timestamp }}] </span>
            <span class="message">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>
  </el-config-provider>

  <!-- 对话框区域 -->
  <el-dialog v-model="qrDialogVisible" title="请用米游社App扫描" width="350px" @closed="onQrDialogClose" :close-on-click-modal="false" class="mimi-dialog" align-center>
    <div style="text-align: center;">
      <!-- 直接显示后端生成的Base64二维码图片 -->
      <el-image :src="qrCodeImage" style="width: 250px; height: 250px;"/>
      <p style="font-size: 16px; margin-top: 15px;">{{ qrStatusText }}</p>
    </div>
  </el-dialog>
  
  <el-dialog v-model="apiSettingsDialogVisible" title="高级设置 API参数" width="450px" class="mimi-dialog" align-center>
    <div class="mimi-input">
      <el-form :model="apiSettingsForm" label-width="130px">
        <el-form-item label="米游社App版本号">
          <el-input v-model="apiSettingsForm.app_version" />
        </el-form-item>
        <el-form-item label="网页 Salt">
          <el-input v-model="apiSettingsForm.salt_web" />
        </el-form-item>
        <el-form-item label="App Salt">
          <el-input v-model="apiSettingsForm.salt_app" />
        </el-form-item>
        <el-form-item label="扫码登录App ID">
           <el-select 
            v-model="apiSettingsForm.qr_login_app_id"
            class="mimi-select" popper-class="mimi-dropdown" style="width: 100%;"
          >
            <el-option v-for="item in qrAppIdOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-form>
    </div>
    <template #footer>
      <div class="compact-line">
        <el-button class="mimi-button mimi-button-secondary" @click="resetApiSettings">恢复默认</el-button>
        <el-button class="mimi-button mimi-button-primary" @click="saveApiSettings" style="flex-grow: 1;">保存并关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Delete, Refresh, Sunny, Moon, Setting, SemiSelect, CloseBold } from '@element-plus/icons-vue'
import { useDark, useToggle } from '@vueuse/core'

// --- 核心状态 ---
const desktopBgUrl = ref('')
const isDark = useDark()
const toggleDark = useToggle(isDark)
const accounts = ref({})
const windows = ref([])
const logs = ref([])
const logBoxRef = ref(null)
const apiSettingsDialogVisible = ref(false)

// --- 表单与状态标记 ---
const scanForm = reactive({ account_name: '', hwnd: null, game_type: 4 })
const isScanning = ref(false)
const fps = ref('0.0')
const windowsLoading = ref(false)
const loginLoading = ref(false)
const scanToggleLoading = ref(false)
const apiSettingsForm = reactive({ app_version: '', salt_web: '', salt_app: '', qr_login_app_id: 2 });
const defaultApiSettings = ref({});

// --- 静态选项 ---
const qrAppIdOptions = ref([
  { value: 2, label: '未定事件簿 2' },
  { value: 1, label: '米游社 1' },
  { value: 4, label: '原神社区 4' },
  { value: 8, label: '星铁社区 8' },
]);

// --- Python 接口 ---
const minimizeWindow = () => { if (window.pywebview?.api.minimize) window.pywebview.api.minimize() }
const closeWindow = () => { if (window.pywebview?.api.close) window.pywebview.api.close() }

// --- 后端 API 调用 ---
const fetchApiSettings = async () => {
  try {
    const response = await axios.get('/api/settings');
    Object.assign(apiSettingsForm, response.data);
    if (Object.keys(defaultApiSettings.value).length === 0) {
      defaultApiSettings.value = { ...response.data };
    }
    addLog({ message: '成功加载API参数', level: 'INFO' });
  } catch (error) { ElMessage.error('获取API参数失败'); }
};

const resetApiSettings = async () => {
    Object.assign(apiSettingsForm, defaultApiSettings.value);
    ElMessage.info('API参数已重置为默认值');
}

const saveApiSettings = async () => {
  try {
    await axios.post('/api/settings', apiSettingsForm);
    defaultApiSettings.value = { ...apiSettingsForm };
    apiSettingsDialogVisible.value = false;
    ElMessage.success('API参数已保存');
  } catch (error) { ElMessage.error('保存API参数失败'); }
};

let ws = null
const setupWebSocket = () => {
  const wsProtocol = window.location.protocol === 'https' ? 'wss' : 'ws';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;
  ws = new WebSocket(wsUrl);
  ws.onopen = () => { addLog({ message: '成功连接到后端日志服务', level: 'SUCCESS' }); };
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'log') { addLog(data); } 
      else if (data.type === 'fps') { fps.value = data.value; }
    } catch (e) { console.error("WebSocket message parse error", event.data); }
  };
  ws.onclose = () => {
    addLog({ message: '与后端日志服务断开连接 5秒后重连', level: 'ERROR' });
    setTimeout(setupWebSocket, 5000);
  };
  ws.onerror = () => { addLog({ message: 'WebSocket连接出错', level: 'ERROR' }); };
}

const addLog = (logData) => {
  const newLog = { timestamp: logData.timestamp || new Date().toTimeString().split(' ')[0], ...logData };
  logs.value.push(newLog);
  nextTick(() => { if (logBoxRef.value) { logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight; } });
}

const fetchAccounts = async () => {
  try {
    const response = await axios.get('/api/accounts');
    accounts.value = response.data;
    if (Object.keys(accounts.value).length > 0 && !scanForm.account_name) {
      scanForm.account_name = Object.keys(accounts.value)[0];
    }
  } catch (error) { ElMessage.error('获取账户列表失败'); }
}

const fetchWindows = async () => {
  windowsLoading.value = true;
  try {
    const response = await axios.get('/api/windows');
    windows.value = response.data;
    if (windows.value.length > 0 && !scanForm.hwnd) {
      scanForm.hwnd = windows.value[0].hwnd;
    }
  } catch (error) { ElMessage.error('获取窗口列表失败'); } 
  finally { windowsLoading.value = false; }
}

// --- 二维码登录流程 ---
const qrDialogVisible = ref(false);
const qrCodeImage = ref(''); // 直接存储base64图片数据
const qrStatusText = ref('等待扫描');
let qrPollInterval = null;

const handleLogin = async () => {
  loginLoading.value = true;
  qrCodeImage.value = ''; // 清空旧二维码
  try {
    // 后端应返回包含base64图片的完整数据
    const response = await axios.get('/api/login/qr');
    const qrData = response.data;
    
    // 直接使用后端生成的二维码
    qrCodeImage.value = qrData.qr_image; // 例如 data:image/png;base64,iVBORw0...
    qrDialogVisible.value = true;
    startQrPolling(qrData.ticket, qrData.device);

  } catch (error) { 
    ElMessage.error(`请求二维码失败 ${error.response?.data?.detail || error.message}`); 
  } finally { 
    loginLoading.value = false; 
  }
}

const startQrPolling = (ticket, device) => {
  qrStatusText.value = '等待扫描';
  qrPollInterval = setInterval(async () => {
    try {
      const response = await axios.get(`/api/login/status?ticket=${ticket}&device=${device}`);
      const data = response.data;
      const stat = data.data?.stat || '';
      qrStatusText.value = `状态 ${stat}`;
      if (stat === 'Confirmed') {
        clearInterval(qrPollInterval);
        qrStatusText.value = '已确认 正在获取凭证';
        const newAccount = data.new_account;
        if (newAccount) {
          const { value: accountName } = await ElMessageBox.prompt('登录成功 请输入账户名称', '保存账户', {
            confirmButtonText: '保存', cancelButtonText: '取消',
            inputValue: `账户_${newAccount.uid}`,
          });
          if (accountName) {
            await axios.post('/api/login/save', { name: accountName, ...newAccount });
            ElMessage.success(`账户 ${accountName} 已保存`);
            await fetchAccounts();
            scanForm.account_name = accountName;
          }
        }
        qrDialogVisible.value = false;
      } else if (stat === 'Expired') {
        clearInterval(qrPollInterval);
        ElMessage.warning('二维码已过期');
        qrDialogVisible.value = false;
      }
    } catch (error) {
      clearInterval(qrPollInterval);
      ElMessage.error(`查询状态失败 ${error.response?.data?.detail || error.message}`);
      qrDialogVisible.value = false;
    }
  }, 2000);
}

const onQrDialogClose = () => { if (qrPollInterval) { clearInterval(qrPollInterval); } };

const handleDeleteAccount = async () => {
  if (!scanForm.account_name) return;
  try {
    await ElMessageBox.confirm(`确定要删除账户 "${scanForm.account_name}" 吗`, '警告', { type: 'warning' });
    await axios.delete(`/api/accounts/${scanForm.account_name}`);
    ElMessage.success('账户已删除');
    scanForm.account_name = '';
    await fetchAccounts();
  } catch(e) { /* 用户取消操作 */ }
}

const toggleScan = async () => {
  scanToggleLoading.value = true;
  try {
    if (isScanning.value) {
      await axios.post('/api/scan/stop');
      isScanning.value = false;
      ElMessage.info('扫描已停止');
    } else {
      if (!scanForm.account_name || !scanForm.hwnd) {
        ElMessage.warning('请先选择账户和目标窗口'); return;
      }
      await axios.post('/api/scan/start', scanForm);
      isScanning.value = true;
      ElMessage.success('扫描已开始 请切换到目标窗口');
    }
  } catch (error) {
    ElMessage.error(`操作失败 ${error.response?.data?.detail || error.message}`);
    isScanning.value = false;
  } finally { scanToggleLoading.value = false; }
}

// --- 生命周期钩子 ---
onMounted(async () => {
  // 监听pywebview API就绪事件
  window.addEventListener('pywebviewready', async () => {
    if (window.pywebview?.api.get_desktop_background) {
      const path = await window.pywebview.api.get_desktop_background();
      // pywebview 返回的路径直接使用 file 协议
      desktopBgUrl.value = path;
    }
  });
  
  fetchAccounts();
  fetchWindows();
  setupWebSocket();
  fetchApiSettings();
  
  // 定时与后端同步扫描状态
  const statusInterval = setInterval(async () => {
      try {
        const response = await axios.get('/api/scan/status');
        if (isScanning.value !== response.data.is_scanning) {
            isScanning.value = response.data.is_scanning;
            if (!isScanning.value) { addLog({message: "后端扫描任务已停止", level: "WARN"}); }
        }
      } catch (e) { /* 忽略网络错误 */ }
  }, 5000);

  onUnmounted(() => clearInterval(statusInterval));
})

onUnmounted(() => { if (ws) { ws.close(); } });
</script>

<style>
@import './style.css';

.content-panel {
    background-color: transparent;
    background-image: none;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
}

/* 
  拖动与窗口控制
  -webkit-app-region 是CEF和Electron等内嵌浏览器实现无边框拖动的标准方式 
*/
.pywebview-drag-region {
  -webkit-app-region: drag; /* 标记此区域为可拖动 */
}

/* 确保所有可交互的UI元素都标记为不可拖动 这样它们才能响应点击事件 */
button, a, input, .el-select, .el-radio-group, .el-switch {
  -webkit-app-region: no-drag;
}

.window-controls {
  position: absolute;
  top: 15px;
  right: 15px;
  display: flex;
  gap: 10px;
  z-index: 1000;
  -webkit-app-region: no-drag; /* 控制按钮本身不可拖动 */
}
</style>