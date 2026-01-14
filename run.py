#!/usr/bin/env python
"""
Kode AI 启动脚本

简单的入口点，直接启动 Web 服务。
"""

import sys
import os
import subprocess
import time
import uvicorn

# 修复 Windows 控制台 UTF-8 编码问题
if sys.platform == "win32":
    # 设置环境变量（必须在导入其他模块前设置）
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

    # 设置 Python 的默认编码为 UTF-8
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass

    # 尝试设置控制台代码页为 UTF-8
    try:
        import subprocess
        subprocess.run(["chcp", "65001"], shell=True, capture_output=True)
    except:
        pass

    # 重新配置标准输出流
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


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

def start_frontend():
    """启动前端开发服务器"""
    frontend_dir = os.path.join(os.path.dirname(__file__), "web-frontend")

    if not os.path.exists(frontend_dir):
        print("警告: web-frontend 目录不存在，跳过前端启动")
        return None

    node_modules = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules):
        print("警告: node_modules 不存在，请先运行 'cd web-frontend && npm install'")
        return None

    try:
        # 在 Windows 上使用 shell=True 启动 npm
        if sys.platform == "win32":
            process = subprocess.Popen(
                "npm run dev",
                cwd=frontend_dir,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
        print(f"前端服务已启动 (PID: {process.pid})")
        return process
    except FileNotFoundError:
        print("警告: npm 未找到，请确保已安装 Node.js")
        return None
    except Exception as e:
        print(f"警告: 启动前端服务失败: {e}")
        return None


if __name__ == "__main__":
    # 修复 Windows 下 multiprocessing 的问题
    if sys.platform == "win32":
        import multiprocessing
        multiprocessing.freeze_support()

    import signal
    import atexit

    frontend_process = None

    # ========================================
    # 修复 Python traceback 模块的 UTF-8 bug
    # ========================================
    import traceback as tb_module

    # 保存原始函数
    _original_byte_offset = tb_module._byte_offset_to_character_offset

    def safe_byte_offset_to_character_offset(text, offset):
        """安全的字节偏移转换，处理 UTF-8 解码错误"""
        try:
            return _original_byte_offset(text, offset)
        except (UnicodeDecodeError, UnicodeEncodeError):
            # 降级：返回近似值或0
            try:
                # 尝试使用 errors='replace'
                as_utf8 = text.encode('utf-8', errors='replace')[:offset + 1]
                return len(as_utf8.decode('utf-8', errors='replace'))
            except:
                return 0  # 最后的降级

    # Monkey patch
    tb_module._byte_offset_to_character_offset = safe_byte_offset_to_character_offset

    # 设置全局的异常钩子，避免 UTF-8 编码问题
    import logging
    import asyncio

    # 配置 asyncio 的 logger 使用安全的异常处理
    asyncio_logger = logging.getLogger('asyncio')

    # 保存原始的 error 方法
    _original_error = asyncio_logger.error
    _original_warning = asyncio_logger.warning

    def safe_error(msg, *args, **kwargs):
        """安全的 error 日志方法，避免 UTF-8 编码问题"""
        try:
            _original_error(msg, *args, **kwargs)
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            # 降级处理：完全移除 exc_info，使用简单的字符串格式
            # 注意：直接调用 logger 的底层方法，避免循环
            try:
                # 提取异常信息（如果有）
                exc_info = kwargs.get('exc_info')
                error_detail = ""
                if exc_info and exc_info is not True:
                    error_detail = f" | Error: {str(exc_info[1]) if isinstance(exc_info, tuple) else str(exc_info)}"

                # 移除所有可能导致问题的参数
                clean_msg = f"{msg} (traceback omitted due to UTF-8 encoding issue){error_detail}"
                asyncio_logger.log(logging.ERROR, clean_msg)
            except:
                # 最后的降级：直接 print（确保不会完全静默失败）
                print(f"CRITICAL LOGGING ERROR: {msg}", file=sys.stderr)

    def safe_warning(msg, *args, **kwargs):
        """安全的 warning 日志方法"""
        try:
            _original_warning(msg, *args, **kwargs)
        except (UnicodeDecodeError, UnicodeEncodeError):
            asyncio_logger.log(logging.WARNING, f"{msg} (encoding issue)")

    asyncio_logger.error = safe_error
    asyncio_logger.warning = safe_warning

    def cleanup():
        """清理前端进程"""
        global frontend_process
        if frontend_process and frontend_process.poll() is None:
            print("\n正在停止前端服务...")
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        f"taskkill /F /T /PID {frontend_process.pid}",
                        shell=True,
                        capture_output=True
                    )
                else:
                    import signal as sig
                    os.killpg(os.getpgid(frontend_process.pid), sig.SIGTERM)
            except Exception as e:
                print(f"停止前端服务时出错: {e}")

    atexit.register(cleanup)

    print("=" * 60)
    print("  Kode AI")
    print("=" * 60)

    # 清理端口（尝试清理，但不影响启动）
    BACKEND_PORT = 8001
    FRONTEND_PORT = 3000
    kill_port_process(BACKEND_PORT)
    kill_port_process(FRONTEND_PORT)

    print("\n正在启动服务...")

    # 启动前端
    frontend_process = start_frontend()

    print(f"  - 后端 API: http://localhost:{BACKEND_PORT}")
    print(f"  - 前端界面: http://localhost:{FRONTEND_PORT}")
    print("\n提示: 按 Ctrl+C 停止所有服务\n")

    # 启动后端
    try:
        uvicorn.run(
            "kode.web.main:app",
            host="0.0.0.0",
            port=BACKEND_PORT,
            reload=False,
            log_level="info",
        )
    finally:
        cleanup()
