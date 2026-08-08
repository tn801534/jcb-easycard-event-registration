# JCB 悠遊卡登錄程式

## 簡介
自動化 JCB 悠遊卡活動登錄工具，支援多卡批次、排程執行、Line Notify 通知。

## 專案結構

`
jcb-easycard/
├── main.py                  ← 程式入口
├── jcb_core.py              ← 核心 API 層（ezweb API 封裝）
├── jcb_config.py            ← 設定檔讀取（支援多組卡片）
├── jcb_scheduler.py         ← 排程與重試邏輯（0.5s 錯開時間）
├── jcb_notify.py            ← Line Notify 通知
├── jcb_recaptcha.py         ← reCAPTCHA 處理（Anticaptcha 自動 / 手動模式）
├── schedule_jcb.ps1         ← Windows 工作排程器安裝腳本
├── config.ini               ← 卡片設定檔（範例）
├── jcb.ini                  ← 實際卡片設定檔（與原版相容）
├── requirements.txt         ← 依賴清單
├── .gitignore
├── README.md                ← 使用說明
├── logs/                    ← 日誌目錄（自動建立，每日輪替保留 30 天）
│   └── jcb.log
└── tests/                   ← pytest 測試（36 個）
    ├── conftest.py
    ├── test_jcb_config.py
    ├── test_jcb_core.py
    ├── test_jcb_scheduler.py
    ├── test_jcb_notify.py
    ├── test_jcb_recaptcha.py
    └── test_integration.py
`

## 安裝

### 需求
- Python 3.8+
- pip

### 安裝步驟

`ash
# 1. 安裝相依套件
pip install -r requirements.txt

# 2. 複製設定檔
cp config.ini jcb.ini
# 或直接編輯 jcb.ini
`

## 設定

編輯 jcb.ini 或 config.ini，填入以下資訊：

### 基本設定

`ini
# 模式: 0=登錄, 1=查詢
mode = 0
testing = False

# 開始時間 (HH:MM:SS) — 建議設為活動開始時間 +1 秒
start_time = 09:00:01

# 使用者名稱（用於 Line Notify 訊息辨識）
myname = 我的名稱
`

### Line Notify 通知（選用）

1. 前往 https://notify-bot.line.me/my/ 建立個人存取權杖
2. 將權杖填入 linetoken 欄位

`ini
linetoken = YOUR_LINE_NOTIFY_TOKEN
`

### Anticaptcha 設定（選用，但強烈建議使用）

1. 前往 https://anticaptcha.com/ 註冊並儲值
2. 取得 API Key 填入 pi_key 欄位

`ini
# Anticaptcha 設定
api_key = YOUR_ANTICAPTCHA_API_KEY
max_token = 1
get_token_semaphore = 30
shoot_semaphore = 7
`

若不使用 Anticaptcha，需手動處理 reCAPTCHA 驗證碼。

### 多組卡片設定

信用卡與悠遊卡數量必須一致，每組用雙引號包住、逗號分隔：

`ini
# 信用卡格式: ['前6碼','中間2碼','後4碼']
txtCreditCardVal = "['123456','78','9012']", "['654321','09','8765']"

# 悠遊卡格式: ['前4碼','次4碼','次4碼','後4碼']
txtEasyCardVal = "['1234','5678','9012','3456']", "['6543','2109','8765','4321']"
`

### 排除特定卡號（選用）

`ini
excludeCard = "['1234','5678','9012','3456']"
`

## 使用方式

### 手動執行

`ash
python main.py
`

程式會自動：
1. 在開始時間前 10 秒開始收集 reCAPTCHA token
2. 到達開始時間後，逐張卡片發送登錄請求（每張間隔 0.5 秒）
3. 成功登錄後自動記錄卡號，避免重複登錄
4. 透過 Line Notify 發送結果通知

### 工作排程器自動執行

`powershell
# 以系統管理員身分執行：
# 右鍵 → 使用 PowerShell 執行
.\schedule_jcb.ps1
`

腳本會自動：
- 檢查 Python 環境與相依套件
- 設定每日 08:55 定時執行（活動開始前 5 分鐘）
- 建立 logs/ 日誌目錄
- 失敗時自動重試（最多 3 次，間隔 1 分鐘）

## 日誌

日誌存放在 logs/jcb.log，每日自動輪替，保留 30 天。

查看最近日誌：
`ash
# PowerShell
Get-Content logs/jcb.log -Tail 50

# CMD
tail logs/jcb.log
`

## 開發分支策略 (master-rounter)

`
main ─── 穩定版本（僅合併經過完整測試的 develop）
  │
  └── develop ─── 開發主線
        │
        ├── feature/S1 ─── S1 階段：基礎功能重構（模組化）
        ├── feature/S2 ─── S2 階段：測試與整合（36 個測試）
        └── feature/S3 ─── S3 階段：部署與上線（目前）
`

- **S1**: 基礎功能開發（jcb_core, jcb_config, jcb_scheduler, etc.）
- **S2**: 測試與整合（pytest 單元/整合測試，36 個全部通過）
- **S3**: 部署與上線（Windows 排程、日誌輪替、文件）

## 測試

`ash
# 執行所有測試
python -m pytest tests/ -v

# 執行特定測試
python -m pytest tests/test_jcb_core.py -v
python -m pytest tests/test_integration.py -v
`

## 注意事項

- **reCAPTCHA**: 需要 Anticaptcha 付費 API Key 或手動處理。未設定時程式會等待手動輸入
- **API 變更**: 悠遊卡官網 API 可能變更，需保留應變機制
- **每月重置**: 每月登錄活動開始時需清除 cardRecorded 記錄（程式會自動管理）
- **排程**: 工作排程器以目前使用者身分執行，請保持登入或設定為「不論使用者登入與否均執行」
- **多卡間隔**: 每張卡片間隔 0.5 秒，避免觸發 API 限流
- **系統時間**: 請確保系統時間與 NTP 同步，以免錯過活動開始時間

## 免責聲明

本程式僅供個人學習與研究使用。使用者應遵守 JCB 與悠遊卡公司之服務條款，自負使用責任。
