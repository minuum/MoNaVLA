
import sys
import os
import torch
import yaml
import h5py
import numpy as np
from PIL import Image
import cv2
import glob
import random
from tqdm import tqdm

# Add RoboVLMs_upstream to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../RoboVLMs_upstream")))

from robovlms.model.backbone.base_backbone import BaseRoboVLM
from robovlms.model.policy_head.mobile_vla_policy import MobileVLALSTMDecoder
from transformers import AutoProcessor, AutoModelForVision2Seq

def load_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def sampling_test():
    # 1. Configuration
    config_path = "/home/billy/25-1kp/vla/runs/mobile_vla_lora_20251114/kosmos/mobile_vla_finetune/2025-11-18/mobile_vla_lora_20251114/mobile_vla_lora_20251114/version_21/hparams.yaml"
    dataset_dir = "/home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset"
    
    print(f"Loading config from {config_path}")
    config = load_config(config_path)
    
    # 2. Model Setup
    print("Initializing Model...")
    model_path = "/home/billy/25-1kp/vla/.vlms/kosmos-2-patch14-224"
    
    if not os.path.exists(model_path):
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.vlms/kosmos-2-patch14-224"))

    # Load VLM
    vlm = AutoModelForVision2Seq.from_pretrained(model_path, trust_remote_code=True)
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
    
    # Load Action Head
    act_head_config = config['configs']['act_head']
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
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    vlm = vlm.to(device)
    act_head = act_head.to(device)
    
    print(f"Model loaded on {device}")

    # 3. Hook Registration
    context_vectors = []
    
    def hook_fn(module, input, output):
        action_tokens = input[0]
        context_vectors.append(action_tokens.detach().cpu().numpy())
        
    handle = act_head.register_forward_hook(hook_fn)

    # 4. Sampling Strategy
    h5_files = glob.glob(os.path.join(dataset_dir, "*.h5"))
    print(f"Found {len(h5_files)} H5 files.")
    
    # Sample 100 episodes
    num_episodes = 100
    sampled_files = random.sample(h5_files, min(num_episodes, len(h5_files)))
    
    samples_per_episode = 5
    total_samples = 0
    
    print(f"Starting sampling test on {len(sampled_files)} episodes, {samples_per_episode} samples each...")
    
    for h5_file in tqdm(sampled_files):
        try:
            with h5py.File(h5_file, 'r') as f:
                images = f['images'][:] # [frames, h, w, c]
                
                if len(images) < 1:
                    continue
                    
                # Randomly select frames
                indices = sorted(random.sample(range(len(images)), min(samples_per_episode, len(images))))
                
                for idx in indices:
                    image = images[idx]
                    image_pil = Image.fromarray(image)
                    text = "<grounding> An object" 
                    
                    inputs = processor(text=text, images=image_pil, return_tensors="pt")
                    inputs = {k: v.to(device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        outputs = vlm(**inputs, output_hidden_states=True)
                        last_hidden_state = outputs.hidden_states[-1]
                        action_tokens = last_hidden_state[:, -1:, :] 
                        pred_actions = act_head(action_tokens)
                        
                    total_samples += 1
                    
        except Exception as e:
            print(f"Error processing {h5_file}: {e}")
            continue

    handle.remove()
    
    # 5. Analysis
    if context_vectors:
        all_vectors = np.concatenate(context_vectors, axis=0) # [N, 1, 2048]
        all_vectors = all_vectors.reshape(-1, 2048)
        
        print("\n" + "="*30)
        print("SAMPLING TEST RESULTS")
        print("="*30)
        print(f"Total Samples: {total_samples}")
        print(f"Vector Shape: {all_vectors.shape}")
        
        mean_val = np.mean(all_vectors)
        std_val = np.std(all_vectors)
        min_val = np.min(all_vectors)
        max_val = np.max(all_vectors)
        
        print(f"Global Mean: {mean_val:.6f}")
        print(f"Global Std: {std_val:.6f}")
        print(f"Global Min: {min_val:.6f}")
        print(f"Global Max: {max_val:.6f}")
        
        # Check for dead neurons (always 0)
        dead_neurons = np.sum(np.all(all_vectors == 0, axis=0))
        print(f"Dead Neurons (always 0): {dead_neurons}")
        
        # Check for constant neurons (variance 0)
        const_neurons = np.sum(np.var(all_vectors, axis=0) < 1e-6)
        print(f"Constant Neurons (var < 1e-6): {const_neurons}")
        
        print("="*30)
        
        # Save statistics
        np.save("context_vectors_sampled.npy", all_vectors)
        print("Saved sampled vectors to context_vectors_sampled.npy")
        
    else:
        print("No samples collected!")

if __name__ == "__main__":
    sampling_test()
