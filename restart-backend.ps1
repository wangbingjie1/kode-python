# Restart Backend Script
# This script forcefully stops all backend processes and restarts

Write-Host "=== 重启后端服务 ===" -ForegroundColor Cyan

# Step 1: Find and kill all processes on port 8000
Write-Host "`n1. 查找端口8000的进程..." -ForegroundColor Yellow
$processes = netstat -ano | findstr ":8000" | findstr "LISTENING"

if ($processes) {
    $pids = @()
    foreach ($line in $processes) {
        if ($line -match '\s+(\d+)\s*$') {
            $pid = $matches[1]
            if ($pid -and $pid -ne "0" -and $pids -notcontains $pid) {
                $pids += $pid
            }
        }
    }

    Write-Host "找到以下进程: $($pids -join ', ')" -ForegroundColor Yellow

    foreach ($pid in $pids) {
        Write-Host "停止进程 $pid..." -ForegroundColor Red
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "✓ 进程 $pid 已停止" -ForegroundColor Green
        } catch {
            Write-Host "✗ 无法停止进程 $pid : $_" -ForegroundColor Red
        }
    }

    # Wait for ports to be released
    Start-Sleep -Seconds 2
} else {
    Write-Host "没有找到运行在8000端口的进程" -ForegroundColor Gray
}

# Step 2: Verify port is free
Write-Host "`n2. 验证端口已释放..." -ForegroundColor Yellow
$check = netstat -ano | findstr ":8000" | findstr "LISTENING"
if ($check) {
    Write-Host "✗ 警告: 端口8000仍被占用!" -ForegroundColor Red
    Write-Host $check -ForegroundColor Red
    Write-Host "`n请手动停止这些进程后重试" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✓ 端口8000已释放" -ForegroundColor Green
}

# Step 3: Check virtual environment
Write-Host "`n3. 检查虚拟环境..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "✓ 找到.venv虚拟环境" -ForegroundColor Green
    $pythonExe = ".venv\Scripts\python.exe"
} elseif (Test-Path ".venv\bin\activate") {
    Write-Host "✓ 找到.venv虚拟环境 (Unix风格)" -ForegroundColor Green
    $pythonExe = ".venv\bin\python"
} else {
    Write-Host "✗ 未找到虚拟环境,使用全局Python" -ForegroundColor Yellow
    $pythonExe = "python"
}

# Step 4: Start backend
Write-Host "`n4. 启动后端服务..." -ForegroundColor Yellow
Write-Host "命令: $pythonExe -m kode.web.main" -ForegroundColor Gray

try {
    # Start in new window
    $process = Start-Process -FilePath $pythonExe -ArgumentList "-m", "kode.web.main" -PassThru -WindowStyle Normal

    # Save PID
    $process.Id | Out-File -FilePath ".backend.pid" -Encoding utf8
    Write-Host "✓ 后端已启动 (PID: $($process.Id))" -ForegroundColor Green

    # Wait and check if it's running
    Start-Sleep -Seconds 3

    Write-Host "`n5. 验证后端状态..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ 后端健康检查通过" -ForegroundColor Green
            Write-Host $response.Content -ForegroundColor Gray
        }
    } catch {
        Write-Host "✗ 后端健康检查失败,但进程已启动" -ForegroundColor Yellow
        Write-Host "请等待几秒后访问 http://localhost:8000/docs 确认" -ForegroundColor Yellow
    }

    Write-Host "`n=== 后端重启完成 ===" -ForegroundColor Cyan
    Write-Host "访问 http://localhost:8000/docs 查看API文档" -ForegroundColor Cyan
    Write-Host "前端地址: http://localhost:3000" -ForegroundColor Cyan

} catch {
    Write-Host "✗ 启动后端失败: $_" -ForegroundColor Red
    exit 1
}
