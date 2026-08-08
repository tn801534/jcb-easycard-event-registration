# JCB 悠遊卡登錄程式

## 簡介
自動化 JCB 悠遊卡活動登錄工具，支援多卡批次、排程執行、Line Notify 通知。

## 專案結構

`
jcb-easycard-temp/
├── main.py              ← 程式入口
├── jcb_core.py          ← 核心 API 層（ezweb API 封裝）
├── jcb_config.py        ← 設定檔讀取（支援多組卡片）
├── jcb_scheduler.py     ← 排程與重試邏輯（0.5s 錯開時間）
├── jcb_notify.py        ← Line Notify 通知
├── jcb_recaptcha.py     ← reCAPTCHA 處理（Anticaptcha 自動 / 手動模式）
├── config.ini           ← 卡片設定檔（範例）
├── jcb.ini              ← 實際卡片設定檔（與原版相容）
├── requirements.txt     ← 依賴清單
└── README.md            ← 使用說明
`

## 安裝

`ash
pip install -r requirements.txt
`

## 設定

1. 編輯 jcb.ini 或 config.ini，填入：
   - 信用卡號與悠遊卡號
   - Anticaptcha API Key（可選，如不使用需手動處理驗證碼）
   - Line Notify Token（可選，用於接收通知）
   - 開始時間

2. 設定檔格式說明：

`ini
# 多組卡片範例（信用卡與悠遊卡數量必須一致）
txtCreditCardVal = "['前6碼','中間2碼','後4碼']", "['第二組前6','中間2','後4']"
txtEasyCardVal = "['悠遊卡前4','次4','次4','後4']", "['第二組前4','次4','次4','後4']"
`

## 使用方式

`ash
python main.py
`

程式會自動：
1. 在開始時間前 10 秒開始收集 reCAPTCHA token
2. 到達開始時間後，逐張卡片發送登錄請求（每張間隔 0.5 秒）
3. 成功登錄後自動記錄卡號，避免重複登錄
4. 透過 Line Notify 發送結果通知

## 開發分支

- main — 穩定版本
- develop — 開發中版本
- eature/S1 — S1 階段（基礎功能重構）
- eature/S2 — S2 階段（測試與整合）
- eature/S3 — S3 階段（部署與上線）

## 注意事項

- 需要 Anticaptcha 付費 API Key 或手動處理 reCAPTCHA
- 悠遊卡官網 API 可能變更，需保留應變機制
- 每月登錄活動開始時需清除 cardRecorded 記錄
