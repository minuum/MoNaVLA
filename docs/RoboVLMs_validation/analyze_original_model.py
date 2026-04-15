
import sys
import os
import torch
import numpy as np
from PIL import Image
import h5py

# Add RoboVLMs_upstream to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../RoboVLMs_upstream")))

# We need to see how to load the original RoboVLMs model.
# Usually it involves loading the VLM backbone and the policy head.
# The original RoboVLMs might use a specific class wrapper.
# Let's try to use the AutoModel loading from transformers if supported, 
# or use the RoboVLMs codebase to load it.

from huggingface_hub import hf_hub_download
import json
from robovlms.model.backbone.robokosmos import RoboKosMos

def analyze_original_robovlms():
    print("Initializing Original RoboVLMs Model (robovlms/RoboVLMs)...")
    
    repo_id = "robovlms/RoboVLMs"
    config_filename = "configs/kosmos_ph_oxe-pretrain.json"
    checkpoint_filename = "checkpoints/kosmos_ph_oxe-pretrain.pt"
    
    print(f"Downloading config: {config_filename}...")
    config_path = hf_hub_download(repo_id=repo_id, filename=config_filename)
    
    print(f"Downloading checkpoint: {checkpoint_filename}...")
    checkpoint_path = hf_hub_download(repo_id=repo_id, filename=checkpoint_filename)
    
    print("Loading config...")
    with open(config_path, 'r') as f:
        configs = json.load(f)
        
    # Adjust config for local environment if needed
    # The config likely points to a local path for the base VLM. 
    # We should point it to the HF model or local cache.
    # configs['model_url'] is usually set.
    # configs['tokenizer']['pretrained_model_name_or_path'] might need adjustment.
    
    # Ensure base model path is correct or let it download
    # We'll assume the code handles download if path doesn't exist, 
    # or we might need to set it to "microsoft/kosmos-2-patch14-224"
    
    # Instantiate Model
    print("Instantiating RoboKosMos...")
    # RoboKosMos __init__ arguments:
    # configs, train_setup_configs, fwd_head_configs, window_size, use_hand_rgb, act_head_configs, fwd_pred_next_n, use_state
    
    model = RoboKosMos(
        configs=configs,
        train_setup_configs=configs["train_setup"],
        fwd_head_configs=configs.get("fwd_head", None),
        window_size=configs["window_size"],
        use_hand_rgb=configs.get("use_hand_rgb", False),
        act_head_configs=configs["act_head"],
        fwd_pred_next_n=configs["fwd_pred_next_n"],
        use_state=True, # Assuming True for now
    )
    
    print("Loading weights...")
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    # Checkpoint might be a full state dict or have 'state_dict' key
    if 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    elif 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    else:
        state_dict = checkpoint
        
    # Load state dict
    # Note: keys might need adjustment (e.g. removing 'module.' prefix)
    new_state_dict = {}
    for k, v in state_dict.items():
        if k.startswith('module.'):
            new_state_dict[k[7:]] = v
        else:
            new_state_dict[k] = v
            
    missing, unexpected = model.load_state_dict(new_state_dict, strict=False)
    print(f"Weights loaded. Missing: {len(missing)}, Unexpected: {len(unexpected)}")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    
    print(f"Model loaded on {device}")
    
    # Hook Registration
    context_vectors = []
    
    def hook_fn(module, input, output):
        # RoboVLMs forward_continuous extracts action_hs.
        # input[0] to act_head should be action_tokens
        action_tokens = input[0]
        
        print(f"\n[HOOK DEBUG] Captured Input to Action Head")
        print(f"  - Type: {type(action_tokens)}")
        if isinstance(action_tokens, torch.Tensor):
            print(f"  - Dtype: {action_tokens.dtype}")
            print(f"  - Device: {action_tokens.device}")
            print(f"  - Layout: {action_tokens.layout}")
            print(f"  - Requires Grad: {action_tokens.requires_grad}")
            print(f"  - Shape: {action_tokens.shape}")
            print(f"  - Stride: {action_tokens.stride()}")
            
        context_vectors.append(action_tokens.detach().cpu().numpy())
        
    # Register hook on act_head
    model.act_head.register_forward_hook(hook_fn)
    print("Hook registered on Action Head")
    
    # Data Loading (Single Sample)
    data_path = "/home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset/episode_20251119_152611_1box_hori_left_core_medium.h5"
    print(f"Loading data from {data_path}")
    
    # We need to process data exactly as RoboVLMs expects.
    # Since we don't have the full dataset loader here, we'll manually construct inputs.
    # RoboKosMos forward expects: vision_x, lang_x, attention_mask, ...
    
    # We need the processor/tokenizer from the model
    tokenizer = model.tokenizer
    image_processor = model.image_processor
    
    with h5py.File(data_path, 'r') as f:
        images = f['images'][:]
        image = images[-1] # [h, w, c]
        image_pil = Image.fromarray(image)
        text = "An object" # Dummy instruction
        
        # Process Image
        # RoboKosMos uses image_processor (likely CLIPImageProcessor or similar)
        # We need to get pixel_values
        
        # Process Text
        # inputs = tokenizer(text=text, images=image_pil, return_tensors="pt") # This failed
        
        # Separate processing
        print("Processing inputs...")
        text_inputs = tokenizer(text, return_tensors="pt")
        lang_x = text_inputs['input_ids'].to(device)
        attention_mask = text_inputs['attention_mask'].to(device)
        
        # Process Image
        # Check what image_processor is
        print(f"Image Processor type: {type(image_processor)}")
        
        try:
            # Try HF style first
            image_inputs = image_processor(images=image_pil, return_tensors="pt")
            vision_x = image_inputs['pixel_values'].to(device)
        except TypeError:
            # Likely torchvision Compose
            print("Falling back to torchvision Compose style...")
            vision_x = image_processor(image_pil)
            # Compose usually returns a tensor [3, 224, 224] if ToTensor is included
            if not isinstance(vision_x, torch.Tensor):
                 # If it returns PIL, convert to tensor
                 import torchvision.transforms.functional as TF
                 vision_x = TF.to_tensor(vision_x)
            
            vision_x = vision_x.to(device)
            # Add batch dimension [1, 3, 224, 224]
            vision_x = vision_x.unsqueeze(0)

        # Add sequence dimension [batch, seq, c, h, w]
        vision_x = vision_x.unsqueeze(1) # [1, 1, 3, 224, 224]
        
        # We need dummy action labels for forward pass if it computes loss, 
        # but we can pass mode='inference' or similar?
        # BaseRoboVLM.forward_continuous checks mode="train". Default is "train".
        # We should set mode="eval" or pass dummy labels.
        
        print("Running Inference...")
        with torch.no_grad():
            # We call forward_continuous directly or model()
            # model() calls forward_continuous if action_space is continuous
            
            # We need to pass required args.
            # vision_x, lang_x, attention_mask
            
            # Create dummy action labels to avoid errors
            # fwd_pred_next_n = 1 (from config usually, or check config)
            fwd_pred_next_n = configs.get("fwd_pred_next_n", 1)
            action_dim = configs['act_head']['action_dim']
            
            bs = 1
            seq_len = 1
            
            # Dummy labels
            # BasePolicyHead.loss expects labels[0] to be [..., 6] (pose) and labels[1] to be [..., 1] or [...] (gripper)
            # action_dim in config is 7 (6+1)
            
            action_labels = (
                torch.zeros(bs, seq_len, fwd_pred_next_n, 6).to(device), # actions (pose only)
                torch.zeros(bs, seq_len, fwd_pred_next_n).to(device) # gripper
            )
            action_mask = torch.ones(bs, seq_len, fwd_pred_next_n).to(device)
            
            model(
                vision_x=vision_x,
                lang_x=lang_x,
                attention_mask=attention_mask,
                action_labels=action_labels,
                action_mask=action_mask,
                mode="eval", # Custom arg to skip loss computation if supported, or just ignore return
                data_source=["action"] # Trigger forward_action
            )
            
    if context_vectors:
        vec = context_vectors[0]
        print("\n" + "="*30)
        print("ORIGINAL MODEL CONTEXT VECTOR DETAILED ANALYSIS")
        print("="*30)
        print(f"Type: {type(vec)}")
        if isinstance(vec, np.ndarray):
             print(f"Dtype: {vec.dtype}")
        
        # We converted to numpy in the hook, let's check the original tensor properties if possible
        # But we only saved numpy. Let's modify hook to print tensor info.
        
        print(f"Shape: {vec.shape}")
        
        vec_flat = vec.reshape(-1) # Flatten for stats
        print(f"Mean: {np.mean(vec_flat):.6f}")
        print(f"Std: {np.std(vec_flat):.6f}")
        print(f"Min: {np.min(vec_flat):.6f}")
        print(f"Max: {np.max(vec_flat):.6f}")
        print("="*30)
        
        np.save("context_vector_original.npy", context_vectors[0])
        print("Saved to context_vector_original.npy")
    else:
        print("No context vector captured!")

if __name__ == "__main__":
    analyze_original_robovlms()
