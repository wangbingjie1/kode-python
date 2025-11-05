#!/usr/bin/env python
"""
Kode AI 启动脚本

简单的入口点，直接启动 Web 服务。
"""

import sys
import subprocess
import time
import uvicorn


def kill_port_process(port: int, max_retries: int = 3) -> bool:
    """清理占用指定端口的进程（Windows），返回是否成功"""
    if sys.platform != "win32":
        return True

    for attempt in range(max_retries):
        killed_pids = []
        try:
            # 查找占用端口的进程
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                check=True,
                encoding='gbk'  # Windows 中文输出
            )

            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    # 提取 PID（最后一列）
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        if pid not in killed_pids:
                            print(f"[尝试 {attempt + 1}/{max_retries}] 发现占用端口 {port} 的进程 PID: {pid}")
                            subprocess.run(
                                ["taskkill", "/F", "/PID", pid],
                                capture_output=True,
                                check=False
                            )
                            killed_pids.append(pid)

            if not killed_pids:
                # 没有找到占用端口的进程
                return True

            # 等待进程完全终止
            time.sleep(1.5)
            print(f"已清理 {len(killed_pids)} 个进程: {', '.join(killed_pids)}")

            # 验证端口是否已释放
            verify = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                check=True,
                encoding='gbk'
            )
            if f":{port}" not in verify.stdout or "LISTENING" not in verify.stdout:
                print(f"端口 {port} 已成功释放")
                return True

        except Exception as e:
            print(f"清理端口时出错: {e}")

    print(f"警告: 端口 {port} 可能仍被占用，但将继续尝试启动...")
    return False

if __name__ == "__main__":
    # 修复 Windows 下 multiprocessing 的问题
    if sys.platform == "win32":
        import multiprocessing
        multiprocessing.freeze_support()

    print("=" * 60)
    print("  Kode AI - AI原生ERP开发平台")
    print("=" * 60)

    # 清理端口（尝试清理，但不影响启动）
    PORT = 8001  
    kill_port_process(PORT)

    print("\n正在启动服务...")
    print(f"  - 后端 API: http://localhost:{PORT}")
    print("  - 前端界面: http://localhost:3000")
    print("\n提示: 按 Ctrl+C 停止服务\n")

    # 简单启动，避免复杂配置
    uvicorn.run(
        "kode.web.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )
