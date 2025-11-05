# 一键停止所有 Kode/Uvicorn 进程
Write-Host "`n[停止 Kode 服务]`n" -ForegroundColor Yellow

# 方式1：停止所有 python 进程
Write-Host "正在停止 Python 进程..." -ForegroundColor Cyan
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  停止进程 PID: $($_.Id)" -ForegroundColor Gray
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# 等待
Start-Sleep -Seconds 2

# 方式2：清理端口（双保险）
foreach ($port in @(8001, 8002)) {
    $conns = netstat -ano | Select-String ":$port\s+.*LISTENING"
    if ($conns) {
        Write-Host "清理端口 $port..." -ForegroundColor Cyan
        foreach ($line in $conns) {
            if ($line -match '\s+(\d+)\s*$') {
                $pid = $matches[1]
                Write-Host "  停止进程 PID: $pid" -ForegroundColor Gray
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Write-Host "`n[完成] Kode 服务已停止`n" -ForegroundColor Green
