"""
WebSocket Module

Handles real-time communication with clients.
"""

from .connection import router, ConnectionManager

__all__ = ["router", "ConnectionManager"]
