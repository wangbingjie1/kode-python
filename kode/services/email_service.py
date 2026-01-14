"""
Email Service

SMTP-based email service for sending verification codes.
"""

import os
import random
import string
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from threading import Lock
import logging

logger = logging.getLogger(__name__)

# SMTP Configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
SMTP_SENDER_NAME = os.getenv("SMTP_SENDER_NAME", "DataMind AI")

# Verification code settings
CODE_LENGTH = 6
CODE_EXPIRE_MINUTES = 10
CODE_RESEND_COOLDOWN_SECONDS = 60


@dataclass
class VerificationRecord:
    """Verification code record"""
    code: str
    email: str
    created_at: datetime
    expires_at: datetime
    attempts: int = 0


class VerificationCodeStore:
    """In-memory verification code storage with TTL"""

    def __init__(self):
        self._store: dict[str, VerificationRecord] = {}
        self._lock = Lock()

    def generate_code(self) -> str:
        """Generate a random 6-digit verification code"""
        return "".join(random.choices(string.digits, k=CODE_LENGTH))

    def store_code(self, email: str) -> tuple[str, bool, str]:
        """
        Store a new verification code for email.

        Returns:
            (code, success, message)
        """
        email = email.lower().strip()
        now = datetime.utcnow()

        with self._lock:
            # Check cooldown
            existing = self._store.get(email)
            if existing:
                cooldown_end = existing.created_at + timedelta(seconds=CODE_RESEND_COOLDOWN_SECONDS)
                if now < cooldown_end:
                    remaining = int((cooldown_end - now).total_seconds())
                    return "", False, f"请等待 {remaining} 秒后重试"

            # Generate and store new code
            code = self.generate_code()
            self._store[email] = VerificationRecord(
                code=code,
                email=email,
                created_at=now,
                expires_at=now + timedelta(minutes=CODE_EXPIRE_MINUTES),
            )
            return code, True, "验证码已发送"

    def verify_code(self, email: str, code: str) -> tuple[bool, str]:
        """
        Verify the code for email.

        Returns:
            (success, message)
        """
        email = email.lower().strip()
        now = datetime.utcnow()

        with self._lock:
            record = self._store.get(email)
            if not record:
                return False, "请先获取验证码"

            # Check expiration
            if now > record.expires_at:
                del self._store[email]
                return False, "验证码已过期，请重新获取"

            # Check attempts (max 5)
            if record.attempts >= 5:
                del self._store[email]
                return False, "验证码尝试次数过多，请重新获取"

            # Verify code
            record.attempts += 1
            if record.code != code:
                return False, "验证码错误"

            # Success - remove the record
            del self._store[email]
            return True, "验证成功"

    def cleanup_expired(self):
        """Remove expired records"""
        now = datetime.utcnow()
        with self._lock:
            expired = [k for k, v in self._store.items() if now > v.expires_at]
            for k in expired:
                del self._store[k]


# Global store instance
verification_store = VerificationCodeStore()


class EmailService:
    """Email sending service"""

    @staticmethod
    def is_configured() -> bool:
        """Check if SMTP is configured"""
        return bool(SMTP_USER and SMTP_PASSWORD)

    @staticmethod
    async def send_verification_code(email: str) -> tuple[bool, str]:
        """
        Generate and send verification code to email.

        Returns:
            (success, message)
        """
        if not EmailService.is_configured():
            logger.warning("SMTP not configured, using mock mode")
            # Mock mode for development
            code, success, msg = verification_store.store_code(email)
            if success:
                logger.info(f"[MOCK] Verification code for {email}: {code}")
                return True, f"验证码已发送（开发模式，验证码: {code}）"
            return False, msg

        # Generate code
        code, success, msg = verification_store.store_code(email)
        if not success:
            return False, msg

        # Send email
        try:
            await EmailService._send_email(
                to_email=email,
                subject="DataMind AI 验证码",
                body=EmailService._build_verification_email_body(code),
            )
            return True, "验证码已发送到您的邮箱"
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {e}")
            return False, f"邮件发送失败: {str(e)}"

    @staticmethod
    def verify_code(email: str, code: str) -> tuple[bool, str]:
        """
        Verify the code for email.

        Returns:
            (success, message)
        """
        return verification_store.verify_code(email, code)

    @staticmethod
    def _build_verification_email_body(code: str) -> str:
        """Build verification email HTML body"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 480px; margin: 0 auto; padding: 40px 20px; }}
        .header {{ text-align: center; margin-bottom: 32px; }}
        .header h1 {{ color: #4a7c8a; font-size: 28px; margin: 0; }}
        .code-box {{
            background: linear-gradient(135deg, #e8f4f8 0%, #d5e8ed 100%);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            margin: 24px 0;
        }}
        .code {{
            font-size: 36px;
            font-weight: bold;
            letter-spacing: 8px;
            color: #2c5f6d;
            font-family: monospace;
        }}
        .info {{ color: #666; font-size: 14px; line-height: 1.6; }}
        .footer {{
            margin-top: 32px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 12px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>DataMind AI</h1>
        </div>
        <p>您好！</p>
        <p>您正在登录 DataMind AI，以下是您的验证码：</p>
        <div class="code-box">
            <div class="code">{code}</div>
        </div>
        <p class="info">
            此验证码将在 {CODE_EXPIRE_MINUTES} 分钟后失效。<br>
            如果这不是您的操作，请忽略此邮件。
        </p>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿直接回复。</p>
            <p>&copy; 2024 DataMind AI. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

    @staticmethod
    async def _send_email(to_email: str, subject: str, body: str):
        """Send email via SMTP"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_SENDER_NAME} <{SMTP_USER}>"
        msg["To"] = to_email

        # Attach HTML body
        msg.attach(MIMEText(body, "html", "utf-8"))

        # Send in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, EmailService._send_smtp, msg, to_email)

    @staticmethod
    def _send_smtp(msg: MIMEMultipart, to_email: str):
        """Synchronous SMTP send"""
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, to_email, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, to_email, msg.as_string())
