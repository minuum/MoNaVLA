import json
import os
import time
from datetime import datetime
import numpy as np

class InferenceLogger:
    def __init__(self, log_dir=None):
        if log_dir is None:
            default_root = os.getenv("VLA_ROOT", os.getenv("HOME", "/tmp"))
            log_dir = os.path.join(default_root, "docs/inference_reports")
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"session_{self.session_id}.json")
        self.data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "model_name": "unknown",
            "instruction": "unknown",
            "history": []
        }
            
    def start_session(self, model_name, instruction):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"session_{self.session_id}.json")
        self.image_log_dir = os.path.join(self.log_dir, f"session_{self.session_id}_images")
        
        # Create directory for images
        os.makedirs(self.image_log_dir, exist_ok=True)
        
        self.data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "model_name": model_name,
            "instruction": instruction,
            "history": []
        }
        print(f"📝 Logging session started: {self.log_file}")
        print(f"📸 Image directory: {self.image_log_dir}")


    def update_instruction(self, instruction):
        if hasattr(self, "data"):
            self.data["instruction"] = instruction
            print(f"📝 Instruction updated: {instruction}")
            
    def log_image(self, step_idx, image):
        if not hasattr(self, "image_log_dir") or not self.image_log_dir:
            return None
            
        try:
            img_filename = f"frame_{step_idx:03d}.jpg"
            img_path = os.path.join(self.image_log_dir, img_filename)
            
            if hasattr(image, 'save'): # PIL Image
                image.save(img_path, format="JPEG", quality=90)
            elif isinstance(image, np.ndarray):
                from PIL import Image
                # Assume BGR if from OpenCV, convert to RGB for saving
                if len(image.shape) == 3:
                    if image.shape[2] == 3:
                        Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.dtype == np.uint8 else image).save(img_path, format="JPEG")
            
            return img_path
        except Exception as e:
            print(f"⚠️ Failed to log image at step {step_idx}: {e}")
            return None
        
    def log_step(self, step_idx, action, latency, chunk=None, image=None):
        if not hasattr(self, "data") or self.data is None:
            self.data = {"history": []}

        step_data = {
            "step": step_idx,
            "timestamp": datetime.now().isoformat(),
            "action": action.tolist() if isinstance(action, np.ndarray) else action,
            "latency_ms": latency,
        }
        if chunk is not None:
             step_data["chunk_preview"] = chunk.tolist() if isinstance(chunk, np.ndarray) else chunk
             
        if image is not None:
             img_path = self.log_image(step_idx, image)
             if img_path:
                 # Ensure we log relative path into JSON
                 step_data["image_file"] = os.path.relpath(img_path, self.log_dir)
             
        self.data["history"].append(step_data)
        
    def end_session(self, status="completed"):
        if not hasattr(self, "data") or self.data is None:
             print("⚠️ No session data to save.")
             return None
             
        self.data["status"] = status
        self.data["end_time"] = datetime.now().isoformat()
        
        # Calculate summary statistics
        if self.data["history"]:
            # Filter for numeric latencies only
            latencies = [
                h["latency_ms"] for h in self.data["history"] 
                if isinstance(h["latency_ms"], (int, float))
            ]
            
            avg_lat = sum(latencies) / len(latencies) if latencies else 0
            
            self.data["summary"] = {
                "avg_latency": avg_lat,
                "total_steps": len(self.data["history"]),
                "last_action": self.data["history"][-1]["action"]
            }
        
        with open(self.log_file, 'w') as f:
            json.dump(self.data, f, indent=4)
        print(f"✅ Session log saved: {self.log_file}")
        return self.log_file

# Singleton instance
_logger = InferenceLogger()

def get_logger():
    return _logger
