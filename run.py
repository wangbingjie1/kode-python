#!/usr/bin/env python
"""
Kode AI 启动脚本

简单的入口点，直接启动 Web 服务。
"""

import sys
import uvicorn

if __name__ == "__main__":
    # 修复 Windows 下 multiprocessing 的问题
    if sys.platform == "win32":
        import multiprocessing
        multiprocessing.freeze_support()

    print("=" * 60)
    print("  Kode AI - AI原生ERP开发平台")
    print("=" * 60)
    print("\n正在启动服务...")
    print("  - 后端 API: http://localhost:8001")
    print("  - 前端界面: http://localhost:3000")
    print("\n提示: 按 Ctrl+C 停止服务\n")

    # 不使用reload避免多进程问题
    # 如需自动重载，请手动重启
    uvicorn.run(
        "kode.web.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # 禁用reload避免僵尸进程
        log_level="info",
    )
