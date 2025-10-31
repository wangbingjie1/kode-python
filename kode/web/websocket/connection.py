"""
WebSocket Connection Manager

Manages WebSocket connections and real-time streaming of AI responses.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import logging
import asyncio

from kode.services.conversation import AsyncConversationService
from kode.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections"""

    def __init__(self):
        # conversation_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()

        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = set()

        self.active_connections[conversation_id].add(websocket)
        logger.info(f"Client connected to conversation {conversation_id}")

    def disconnect(self, websocket: WebSocket, conversation_id: str):
        """Remove WebSocket connection"""
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].discard(websocket)

            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

        logger.info(f"Client disconnected from conversation {conversation_id}")

    async def send_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def broadcast(self, message: dict, conversation_id: str):
        """Broadcast message to all connections in a conversation"""
        if conversation_id not in self.active_connections:
            return

        disconnected = set()

        for connection in self.active_connections[conversation_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, conversation_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/chat/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str,
):
    """
    WebSocket endpoint for real-time chat

    Message format (client -> server):
    {
        "type": "task",
        "content": "user message",
        "metadata": {}
    }

    Message format (server -> client):
    {
        "type": "thinking" | "tool_call" | "chunk" | "complete" | "error",
        "content": "...",
        "metadata": {}
    }
    """
    await manager.connect(websocket, conversation_id)
    conversation_service = AsyncConversationService()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "task":
                task_content = message.get("content", "")

                # Send thinking status
                await manager.send_message(
                    {
                        "type": "thinking",
                        "content": "Processing your request...",
                        "metadata": {},
                    },
                    websocket,
                )

                try:
                    # Stream AI response
                    async for chunk in conversation_service.execute_task_streaming(
                        task=task_content,
                        conversation_id=conversation_id,
                        user_id="default",  # TODO: Get from auth
                    ):
                        await manager.send_message(chunk, websocket)

                except Exception as e:
                    logger.error(f"Error executing task: {e}", exc_info=True)
                    await manager.send_message(
                        {
                            "type": "error",
                            "content": f"Error: {str(e)}",
                            "metadata": {"error": str(e)},
                        },
                        websocket,
                    )

            elif message.get("type") == "ping":
                # Heartbeat response
                await manager.send_message(
                    {"type": "pong", "content": "", "metadata": {}}, websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket, conversation_id)
