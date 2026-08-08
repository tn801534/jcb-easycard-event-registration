# =============================================================================
# schedule_jcb.ps1 — JCB 悠遊卡登錄程式 Windows 工作排程器安裝腳本
# 以系統管理員身分執行：右鍵 → 使用 PowerShell 執行
# =============================================================================

$TaskName = "JCB EasyCard Registration"
$ScriptPath = $PSScriptRoot
$PythonPath = (Get-Command python).Source
$MainScript = Join-Path $ScriptPath "main.py"

Write-Host "=== JCB 悠遊卡登錄程式 — 工作排程器安裝 ===" -ForegroundColor Cyan
Write-Host ""

# 檢查 Python 是否可用
if (-not (Test-Path $PythonPath)) {
    Write-Host "錯誤: 找不到 Python 執行檔" -ForegroundColor Red
    exit 1
}

# 檢查 main.py 是否存在
if (-not (Test-Path $MainScript)) {
    Write-Host "錯誤: 找不到 $MainScript" -ForegroundColor Red
    exit 1
}

# 檢查設定檔
$ConfigFiles = @("jcb.ini", "config.ini")
$ConfigFound = $false
foreach ($cfg in $ConfigFiles) {
    $cfgPath = Join-Path $ScriptPath $cfg
    if (Test-Path $cfgPath) {
        $ConfigFound = $true
        Write-Host "✓ 找到設定檔: $cfg" -ForegroundColor Green
        break
    }
}
if (-not $ConfigFound) {
    Write-Host "警告: 未找到 jcb.ini 或 config.ini，請先完成設定" -ForegroundColor Yellow
}

# 檢查 requirements.txt 依賴
$ReqFile = Join-Path $ScriptPath "requirements.txt"
if (Test-Path $ReqFile) {
    Write-Host "正在檢查 Python 依賴..." -ForegroundColor Yellow
    pip install -r $ReqFile -q 2>&1 | Out-Null
    Write-Host "✓ 依賴已安裝" -ForegroundColor Green
}

# 設定 log 目錄
$LogDir = Join-Path $ScriptPath "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host "✓ 建立日誌目錄: $LogDir" -ForegroundColor Green
}

# 檢查是否已有排程
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "⚠ 已有現有排程工作 [$TaskName]，將重新建立..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 建立排程工作
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$MainScript`"" `
    -WorkingDirectory $ScriptPath

# 每天執行，設定為開始時間前 5 分鐘啟動
# 使用者可依實際需要修改此處觸發時間
$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "08:55:00"

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Limited

Write-Host ""
Write-Host "正在註冊排程工作..." -ForegroundColor Yellow
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

if ($?) {
    Write-Host ""
    Write-Host "✓ 排程工作已建立成功!" -ForegroundColor Green
    Write-Host "  工作名稱: $TaskName" -ForegroundColor Green
    Write-Host "  執行時間: 每日 08:55" -ForegroundColor Green
    Write-Host "  執行命令: $PythonPath `"$MainScript`"" -ForegroundColor Green
    Write-Host "  工作目錄: $ScriptPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "=== 提醒 ===" -ForegroundColor Yellow
    Write-Host "1. 請先編輯 jcb.ini 填入正確的卡片資訊與 Anticaptcha API Key" -ForegroundColor Yellow
    Write-Host "2. 如需修改執行時間，請開啟工作排程器 → 工作排程器程式庫 → JCB EasyCard Registration" -ForegroundColor Yellow
    Write-Host "3. 排程會以目前使用者身分執行，請保持登入狀態" -ForegroundColor Yellow
    Write-Host "4. 如要手動測試，請直接執行: python main.py" -ForegroundColor Yellow
    Write-Host "5. 如需取消排程，請執行: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor Yellow
} else {
    Write-Host "錯誤: 排程工作註冊失敗" -ForegroundColor Red
    Write-Host "請以系統管理員身分重新執行此腳本" -ForegroundColor Red
    exit 1
}
