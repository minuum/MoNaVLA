
import sys
import os
import torch
import yaml
import h5py
import numpy as np
from PIL import Image
import cv2

# Add RoboVLMs_upstream to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../RoboVLMs_upstream")))

from robovlms.model.backbone.base_backbone import BaseRoboVLM
from robovlms.model.policy_head.mobile_vla_policy import MobileVLALSTMDecoder
from transformers import AutoProcessor, AutoModelForVision2Seq

def load_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def analyze_context_vector():
    # 1. Configuration
    config_path = "/home/billy/25-1kp/vla/runs/mobile_vla_lora_20251114/kosmos/mobile_vla_finetune/2025-11-18/mobile_vla_lora_20251114/mobile_vla_lora_20251114/version_21/hparams.yaml"
    data_path = "/home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset/episode_20251119_152611_1box_hori_left_core_medium.h5"
    
    print(f"Loading config from {config_path}")
    config = load_config(config_path)
    
    # 2. Model Setup
    # We need to reconstruct the model based on the config
    # Since we don't have the full trainer, we'll instantiate BaseRoboVLM manually if possible, 
    # or use the components directly.
    
    print("Initializing Model...")
    # This part mimics BaseRoboVLM initialization
    model_name = config['configs']['model'] # 'kosmos'
    model_path = "/home/billy/25-1kp/vla/.vlms/kosmos-2-patch14-224" # Local path from config
    
    if not os.path.exists(model_path):
        print(f"Warning: Model path {model_path} does not exist. Trying to find it relative to workspace.")
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.vlms/kosmos-2-patch14-224"))
        if not os.path.exists(model_path):
             print(f"Error: Could not find model at {model_path}")
             return

    print(f"Loading backbone from {model_path}")
    
    # Load Backbone
    # Note: BaseRoboVLM is an abstract base class, we usually use a subclass or instantiate components.
    # However, looking at base_backbone.py, it seems we can use it if we set up the components.
    # But it's better to use the specific backbone class if available. 
    # For Kosmos, it seems RoboVLMs uses a wrapper.
    # Let's try to instantiate the components directly to simulate the forward pass up to the action head.
    
    # Load VLM
    vlm = AutoModelForVision2Seq.from_pretrained(model_path, trust_remote_code=True)
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
    
    # Load Action Head
    act_head_config = config['configs']['act_head']
    # We need to instantiate MobileVLALSTMDecoder
    # Assuming it's importable
    # Instantiate MobileVLALSTMDecoder
    # We need to pass arguments explicitly
    # in_features is 2048 (confirmed by debug output)
    in_features = 2048 
    
    act_head = MobileVLALSTMDecoder(
        in_features=in_features,
        action_dim=act_head_config['action_dim'],
        down_sample=act_head_config['down_sample'],
        latent=act_head_config['latent'],
        fwd_pred_next_n=act_head_config['fwd_pred_next_n'],
        window_size=act_head_config['window_size'],
        hidden_size=act_head_config['hidden_size']
    )
    
    # Move to device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    vlm = vlm.to(device)
    act_head = act_head.to(device)
    
    print(f"Model loaded on {device}")

    # 3. Hook Registration
    context_vectors = []
    
    def hook_fn(module, input, output):
        # input is a tuple, input[0] should be the action_tokens (context vector)
        # Check signature of act_head.forward: forward(self, action_tokens, ...)
        action_tokens = input[0]
        context_vectors.append(action_tokens.detach().cpu().numpy())
        
    handle = act_head.register_forward_hook(hook_fn)
    print("Hook registered on Action Head")

    # 4. Data Loading
    print(f"Loading data from {data_path}")
    with h5py.File(data_path, 'r') as f:
        # Structure is flat: ['action_event_types', 'actions', 'images']
        images = f['images'][:] # [frames, h, w, c]
        
        # Preprocess
        # Take the last image of the window as the current observation
        # Window size is 8 (from config)
        window_size = config['configs']['window_size']
        if len(images) > window_size:
             image = images[window_size-1] # Use the image at the end of the window
        else:
             image = images[-1]
             
        # Convert to PIL and process
        image_pil = Image.fromarray(image)
        # Kosmos processor expects text and images
        # We need a dummy text prompt usually used in RoboVLMs
        text = "<grounding> An object" # Dummy prompt
        
        inputs = processor(text=text, images=image_pil, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # 5. Inference Simulation
        # We need to run the VLM to get hidden states, then pass to act_head
        # This is tricky without the full BaseRoboVLM wrapper which handles the logic.
        # Let's try to instantiate BaseRoboVLM if possible, or a subclass.
        # Searching for 'RoboKosMos' class...
        
        # If we can't easily instantiate the full model, we can try to run the VLM and then the head manually.
        # Kosmos forward returns output with hidden_states if specified.
        
        print("Running Inference...")
        with torch.no_grad():
            # VLM Forward
            outputs = vlm(**inputs, output_hidden_states=True)
            last_hidden_state = outputs.hidden_states[-1] # [batch, seq_len, hidden_size]
            
            # Extract action tokens
            # In RoboVLMs, specific tokens are selected as action tokens.
            # Usually it's the last token or specific tokens appended.
            # For simplicity in this analysis, we'll take the last token's hidden state as the context vector.
            # Or if it's a sequence, the whole sequence.
            
            # The act_head expects 'action_tokens'.
            # Let's assume we pass the last hidden state.
            action_tokens = last_hidden_state[:, -1:, :] # [batch, 1, hidden_size]
            
            print(f"DEBUG: action_tokens shape: {action_tokens.shape}")
            
            # Pass to Action Head (this triggers the hook)
            # We need dummy actions for the head if it requires them, but for inference usually not.
            # MobileVLALSTMDecoder forward signature: (self, action_tokens, actions=None, action_masks=None)
            pred_actions = act_head(action_tokens)
            
    # 6. Analysis
    if context_vectors:
        vec = context_vectors[0]
        print("\n" + "="*30)
        print("CONTEXT VECTOR ANALYSIS")
        print("="*30)
        print(f"Shape: {vec.shape}")
        print(f"Mean: {np.mean(vec):.6f}")
        print(f"Std: {np.std(vec):.6f}")
        print(f"Min: {np.min(vec):.6f}")
        print(f"Max: {np.max(vec):.6f}")
        print("="*30)
        
        # Save to file
        np.save("context_vector_sample.npy", vec)
        print("Saved context vector to context_vector_sample.npy")
    else:
        print("No context vector captured!")

    handle.remove()

if __name__ == "__main__":
    analyze_context_vector()
