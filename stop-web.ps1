# Kode AI Web 停止脚本 (Windows PowerShell)

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Kode AI Web 停止脚本" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# 停止后端服务
if (Test-Path ".backend.pid") {
    $backendPid = Get-Content ".backend.pid"
    $process = Get-Process -Id $backendPid -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "停止后端服务 (PID: $backendPid)..." -ForegroundColor Yellow
        Stop-Process -Id $backendPid -Force
        Write-Host "✓ 后端服务已停止" -ForegroundColor Green
    } else {
        Write-Host "后端服务未运行" -ForegroundColor Yellow
    }
    Remove-Item ".backend.pid" -ErrorAction SilentlyContinue
} else {
    Write-Host "未找到后端服务 PID 文件" -ForegroundColor Yellow
}

# 停止前端服务
if (Test-Path ".frontend.pid") {
    $frontendPid = Get-Content ".frontend.pid"
    $process = Get-Process -Id $frontendPid -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "停止前端服务 (PID: $frontendPid)..." -ForegroundColor Yellow
        Stop-Process -Id $frontendPid -Force
        Write-Host "✓ 前端服务已停止" -ForegroundColor Green
    } else {
        Write-Host "前端服务未运行" -ForegroundColor Yellow
    }
    Remove-Item ".frontend.pid" -ErrorAction SilentlyContinue
} else {
    Write-Host "未找到前端服务 PID 文件" -ForegroundColor Yellow
}

# 额外检查：按端口查找并停止进程
Write-Host ""
Write-Host "检查端口 8000 和 3000..." -ForegroundColor Yellow

$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000) {
    $pid = $port8000.OwningProcess
    Write-Host "发现端口 8000 被进程 $pid 占用，正在停止..." -ForegroundColor Yellow
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}

$port3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($port3000) {
    $pid = $port3000.OwningProcess
    Write-Host "发现端口 3000 被进程 $pid 占用，正在停止..." -ForegroundColor Yellow
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "所有服务已停止" -ForegroundColor Green
