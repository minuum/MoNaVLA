"""
MCP Server for Jetson (Robot Server)
- Runs VLA internally
- Exposes `get_camera_frame` for the Inference Server (YOLO)
- Exposes `override_velocity` to let the Inference Server trigger emergency stops
"""

import asyncio
import cv2
import numpy as np
import base64
from mcp.server.fastmcp import FastMCP

# Create the Server
mcp = FastMCP("VLA_Jetson_Server")

# Dummy state to hold the latest camera frame globally
# In an actual ROS2 environment, this would be updated by a camera subscriber node.
latest_frame = np.zeros((480, 640, 3), dtype=np.uint8)

@mcp.tool()
async def get_camera_frame() -> str:
    """
    Returns the latest camera frame encode as a Base64 string for YOLO object detection.
    """
    global latest_frame
    # Encode frame to JPEG then Base64
    _, buffer = cv2.imencode('.jpg', latest_frame)
    b64_str = base64.b64encode(buffer).decode('utf-8')
    return b64_str

@mcp.tool()
async def override_velocity(linear_x: float, angular_z: float) -> str:
    """
    Overrides the VLA's planned velocity due to an imminent hazard detected by YOLO.
    """
    print(f"[URGENT] YOLO OVERRIDE RECEIVED: v={linear_x}, w={angular_z}")
    # In an actual ROS2 environment, this would publish to a high-priority muxed /cmd_vel topic.
    return "Velocity successfully overridden."

if __name__ == "__main__":
    # We use SSE (Server-Sent Events) over HTTP to communicate across the Tailscale VPN
    print("Starting FastMCP Jetson Server on port 8080...")
    mcp.run(transport="sse", port=8080)
