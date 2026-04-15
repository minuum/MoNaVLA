
import sys
import os
import torch
import numpy as np
from PIL import Image, ImageDraw
import h5py
import cv2
from scipy.spatial.distance import cosine, euclidean
from huggingface_hub import hf_hub_download
import json

# Add RoboVLMs_upstream to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../RoboVLMs_upstream")))

from robovlms.model.backbone.robokosmos import RoboKosMos

def verify_box_learning():
    print("Initializing Original RoboVLMs Model for Box Verification...")
    
    # 1. Load Model (Same as analyze_original_model.py)
    repo_id = "robovlms/RoboVLMs"
    config_filename = "configs/kosmos_ph_oxe-pretrain.json"
    checkpoint_filename = "checkpoints/kosmos_ph_oxe-pretrain.pt"
    
    # Ensure files are downloaded (should be cached)
    config_path = hf_hub_download(repo_id=repo_id, filename=config_filename)
    checkpoint_path = hf_hub_download(repo_id=repo_id, filename=checkpoint_filename)
    
    with open(config_path, 'r') as f:
        configs = json.load(f)
        
    model = RoboKosMos(
        configs=configs,
        train_setup_configs=configs["train_setup"],
        fwd_head_configs=configs.get("fwd_head", None),
        window_size=configs["window_size"],
        use_hand_rgb=configs.get("use_hand_rgb", False),
        act_head_configs=configs["act_head"],
        fwd_pred_next_n=configs["fwd_pred_next_n"],
        use_state=True,
    )
    
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    if 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    elif 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    else:
        state_dict = checkpoint
        
    new_state_dict = {}
    for k, v in state_dict.items():
        if k.startswith('module.'):
            new_state_dict[k[7:]] = v
        else:
            new_state_dict[k] = v
            
    model.load_state_dict(new_state_dict, strict=False)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    print(f"Model loaded on {device}")

    # 2. Register Hook
    context_vectors = []
    def hook_fn(module, input, output):
        action_tokens = input[0]
        context_vectors.append(action_tokens.detach().cpu().numpy())
    model.act_head.register_forward_hook(hook_fn)

    # 3. Load Data & Create Variations
    data_path = "/home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset/episode_20251119_152611_1box_hori_left_core_medium.h5"
    print(f"Loading data from {data_path}")
    
    with h5py.File(data_path, 'r') as f:
        images = f['images'][:]
        # Pick a frame where the box is likely visible (e.g., middle of episode)
        idx = len(images) // 2
        original_image_np = images[idx]
        original_image_pil = Image.fromarray(original_image_np)
        
        # Create "No Box" / Masked version
        # Since we don't have segmentation, we'll mask the center region or a likely box region.
        # Assuming box is somewhat central or in the lower half.
        # Let's create a few variations.
        
        # Variation 1: Mask Center (Simulate box occlusion)
        masked_image_pil = original_image_pil.copy()
        draw = ImageDraw.Draw(masked_image_pil)
        w, h = masked_image_pil.size
        # Mask a rectangle in the center-bottom
        draw.rectangle([w//4, h//2, 3*w//4, h], fill=(128, 128, 128))
        
        # Variation 2: Random Noise (Control)
        noise_image_np = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        noise_image_pil = Image.fromarray(noise_image_np)
        
        test_images = {
            "Original": original_image_pil,
            "Masked (Box Occluded)": masked_image_pil,
            "Random Noise": noise_image_pil
        }
        
        # Save images for report
        artifact_dir = "/home/billy/25-1kp/vla/docs/images"
        original_image_pil.save(f"{artifact_dir}/experiment_original.png")
        masked_image_pil.save(f"{artifact_dir}/experiment_masked.png")
        print(f"Saved experiment images to {artifact_dir}")
        
        results = {}
        
        tokenizer = model.tokenizer
        image_processor = model.image_processor
        
        text = "An object"
        
        for name, img_pil in test_images.items():
            print(f"Processing {name}...")
            
            # Prepare Inputs
            text_inputs = tokenizer(text, return_tensors="pt")
            lang_x = text_inputs['input_ids'].to(device)
            attention_mask = text_inputs['attention_mask'].to(device)
            
            try:
                image_inputs = image_processor(images=img_pil, return_tensors="pt")
                vision_x = image_inputs['pixel_values'].to(device)
            except TypeError:
                vision_x = image_processor(img_pil)
                if not isinstance(vision_x, torch.Tensor):
                     import torchvision.transforms.functional as TF
                     vision_x = TF.to_tensor(vision_x)
                vision_x = vision_x.to(device).unsqueeze(0)
            
            vision_x = vision_x.unsqueeze(1) # [1, 1, 3, 224, 224]
            
            # Dummy labels
            bs, seq_len = 1, 1
            fwd_pred_next_n = configs.get("fwd_pred_next_n", 1)
            action_labels = (
                torch.zeros(bs, seq_len, fwd_pred_next_n, 6).to(device),
                torch.zeros(bs, seq_len, fwd_pred_next_n).to(device)
            )
            action_mask = torch.ones(bs, seq_len, fwd_pred_next_n).to(device)
            
            # Inference
            context_vectors.clear() # Clear previous
            with torch.no_grad():
                model(
                    vision_x=vision_x,
                    lang_x=lang_x,
                    attention_mask=attention_mask,
                    action_labels=action_labels,
                    action_mask=action_mask,
                    mode="eval",
                    data_source=["action"]
                )
            
            if context_vectors:
                results[name] = context_vectors[0].flatten()
            else:
                print(f"Failed to capture vector for {name}")

    # 4. Analysis & Raw Output
    print("\n" + "="*40)
    print("DETAILED CONTEXT VECTOR ANALYSIS (NO HALLUCINATION)")
    print("="*40)
    
    if "Original" in results:
        orig_vec = results["Original"]
        masked_vec = results["Masked (Box Occluded)"]
        
        # 1. Raw Output (Subset)
        print(f"Vector Shape: {orig_vec.shape}")
        print(f"Vector Norm (L2): {np.linalg.norm(orig_vec):.4f}")
        
        print("\n[Raw Values - First 20 dimensions]")
        print(orig_vec[:20])
        
        print("\n[Raw Values - Last 20 dimensions]")
        print(orig_vec[-20:])
        
        # 2. Differential Analysis
        diff = np.abs(orig_vec - masked_vec)
        
        print("\n[Differential Analysis: Original vs Masked]")
        print(f"Mean Absolute Difference: {np.mean(diff):.6f}")
        print(f"Max Absolute Difference: {np.max(diff):.6f}")
        
        # Top changing dimensions
        top_k = 10
        top_indices = np.argsort(diff)[-top_k:][::-1]
        
        print(f"\n[Top {top_k} Dimensions Changed by Masking]")
        print(f"{'Index':<10} | {'Original':<12} | {'Masked':<12} | {'Diff':<12}")
        print("-" * 50)
        for idx in top_indices:
            print(f"{idx:<10} | {orig_vec[idx]:.6f}     | {masked_vec[idx]:.6f}     | {diff[idx]:.6f}")
            
        # 3. Distribution of Changes
        # How many dimensions changed significantly?
        threshold = 0.1
        changed_dims = np.sum(diff > threshold)
        print(f"\nNumber of dimensions with diff > {threshold}: {changed_dims} / {len(diff)}")
        
        # 4. Cosine Similarity (Re-verify)
        cos_sim = 1 - cosine(orig_vec, masked_vec)
        print(f"\nCosine Similarity: {cos_sim:.6f}")

        # Save for manual inspection if needed
        np.save("context_vector_original_full.npy", orig_vec)
        np.save("context_vector_masked_full.npy", masked_vec)
        print("\nSaved full vectors to .npy files for further inspection.")

if __name__ == "__main__":
    verify_box_learning()
