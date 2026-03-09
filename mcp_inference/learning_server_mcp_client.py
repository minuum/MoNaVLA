"""
MCP Client for Learning Server (Inference Server)
- Connects to the Jetson MCP Server
- Retrieves camera frames
- Runs YOLOv11 for object detection
- Overrides VLA velocity if obstacles are too close
"""

import asyncio
import cv2
import numpy as np
import base64
from ultralytics import YOLO
from mcp import ClientSession

# YOLO Model Setup
# We use a lightweight model for realtime performance
YOLO_MODEL = 'yolo11n.pt' 
print(f"Loading YOLO Model: {YOLO_MODEL}")
model = YOLO(YOLO_MODEL)

# Hyperparameters
PROXIMITY_THRESHOLD_PIXELS = 150000  # If bbox area > this, consider it a collision risk
SAFE_LINEAR_X = 0.0
SAFE_ANGULAR_Z = 0.0

async def perform_yolo_detection(image: np.ndarray):
    """Run YOLO on the image and return whether a collision is imminent"""
    results = model(image, verbose=False)
    
    collision_imminent = False
    detected_objects = []

    for result in results:
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            area = (x2 - x1) * (y2 - y1)
            cls_id = int(box.cls[0].cpu().numpy())
            cls_name = model.names[cls_id]
            
            detected_objects.append({"class": cls_name, "area": area})
            
            # Simple heuristic: If an object (e.g., person, box) is taking up a huge portion of the screen
            if area > PROXIMITY_THRESHOLD_PIXELS:
                print(f"[WARNING] 🚨 Collision Imminent! Object: {cls_name}, Area: {area}")
                collision_imminent = True

    return collision_imminent, detected_objects


async def mcp_client_loop(session: ClientSession):
    """Main loop integrating MCP and YOLO"""
    print("MCP Client Loop Started. Connected to Jetson.")
    try:
        while True:
            # 1. Ask Jetson for the latest camera frame
            # Depending on how the Jetson tools are named, we call the appropriate tool.
            try:
                frame_result = await session.call_tool("get_camera_frame", {})
                
                # Assume the tool returns a base64 encoded string
                frame_b64 = frame_result.content[0].text
                
                # Decode base64 to OpenCV image
                img_bytes = base64.b64decode(frame_b64)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if img is None:
                    print("Failed to decode image from Jetson.")
                    await asyncio.sleep(0.1)
                    continue
                
                # 2. Run object detection
                collision_imminent, objects = await perform_yolo_detection(img)

                # 3. Decision Making
                if collision_imminent:
                    # 4. Trigger Safety Override via MCP
                    override_result = await session.call_tool("override_velocity", {
                        "linear_x": SAFE_LINEAR_X,
                        "angular_z": SAFE_ANGULAR_Z
                    })
                    print(f"Override Result: {override_result.content[0].text}")

            except Exception as e:
                print(f"[Error in Loop] {e}")
            
            # Control loop frequency (e.g., 10 Hz)
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        print("MCP Client Loop Stopped.")


async def main():
    # Setup MCP Connection.
    # TODO: In phase 1, we will implement the Jetson MCP Server using SSE over Tailscale.
    # Once Jetson is running (e.g., at http://BILLY_TAILSCALE_IP:8080/sse)
    # we will connect to it here using sse_client.
    import mcp.client.sse as sse
    
    # Replace with actual Jetson IP later
    JETSON_URL = "http://localhost:8080/sse" 
    print(f"Connecting to Jetson MCP Server at {JETSON_URL}...")
    
    async with sse.sse_client(JETSON_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Run the main control loop
            await mcp_client_loop(session)

if __name__ == "__main__":
    asyncio.run(main())
