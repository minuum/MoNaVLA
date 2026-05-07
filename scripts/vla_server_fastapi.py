import os, sys, torch, numpy as np, base64, io, glob, json, gc, re, time
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image, ImageDraw
from pathlib import Path
import uvicorn

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from robovlms.train.mobile_vla_trainer import MobileVLATrainer
from robovlms.utils.config_utils import load_config

# ── Constants ─────────────────────────────────────────────────────
ACTION_NAMES  = {0:"STOP",1:"FORWARD",2:"LEFT",3:"RIGHT",4:"FWD+L",5:"FWD+R",6:"TURN_L",7:"TURN_R"}
ACTION_COLORS = {0:"#ef4444",1:"#22c55e",2:"#3b82f6",3:"#f97316",4:"#06b6d4",5:"#f59e0b",6:"#8b5cf6",7:"#ec4899"}
DATASET_DIR   = "/home/minum/minum/26CS/MoNa-pi/mobile_vla_dataset_v5"
VLA_CKPT      = "/home/minum/26CS/MoNaVLA/runs/v5_nav/kosmos/mobile_vla_v5_exp39/2026-05-01/v5-exp39-exp25-last4-lora/epoch_epoch=epoch=14-val_loss=val_loss=8.229.ckpt"
VLA_CFG       = "configs/mobile_vla_v5_exp39_exp25_last4_lora.json"
VLM_CFG       = "configs/mobile_vla_pretrained.json"
VLM_NAMES     = ["moondream", "paligemma-mix", "paligemma2-mix", "kosmos"]
GT_PATH       = os.path.join(ROOT_DIR, "docs/v5/bbox_truth_mini.json")

# ── Global Metadata (Lazy Load) ────────────────────────────────────
_mini_gt: dict = {}

def _get_gt():
    global _mini_gt
    if not _mini_gt and os.path.exists(GT_PATH):
        try:
            with open(GT_PATH, 'r') as f:
                data = json.load(f)
            
            def find_episodes(obj):
                if isinstance(obj, dict):
                    if 'episode' in obj and 'bbox_xyxy_norm' in obj:
                        ep = obj['episode']
                        f_idx = obj.get('frame_idx', 0)
                        if ep not in _mini_gt: _mini_gt[ep] = {}
                        _mini_gt[ep][f_idx] = {
                            "bbox": obj['bbox_xyxy_norm'],
                            "notes": obj.get('notes', ''),
                            "anchor": obj.get('anchor_tag', 'unknown')
                        }
                        _mini_gt[ep + ".h5"] = _mini_gt[ep]
                    for v in obj.values(): find_episodes(v)
                elif isinstance(obj, list):
                    for v in obj: find_episodes(v)
            
            find_episodes(data)
            print(f"✅ Indexed Mini GT: {len(_mini_gt)} episodes")
        except Exception as e: print(f"❌ GT Load Error: {e}")
    return _mini_gt

def _parse_grounding_tokens(text):
    """PaliGemma/Kosmos 스타일의 <locXXXX> 토큰을 [ymin, xmin, ymax, xmax]로 변환"""
    # <loc012><loc345><loc678><loc901> 패턴 찾기
    locs = re.findall(r'<loc(\d{4})>', text)
    if len(locs) >= 4:
        # 1024 스케일 기준
        return [[int(locs[0])/1024, int(locs[1])/1024, int(locs[2])/1024, int(locs[3])/1024]]
    return []

def _calculate_iou(box1, box2):
    """[xmin, ymin, xmax, ymax] 형식의 두 박스 간 IoU 계산"""
    if not box1 or not box2: return 0.0
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    union = area1 + area2 - intersection
    return round(intersection / union, 4) if union > 0 else 0.0

# ── Model cache (lazy load) ────────────────────────────────────────
_cache: dict = {}

def _load_model(mode: str, vlm_name: str = None) -> MobileVLATrainer:
    key = mode if mode == "vla" else f"vlm_{vlm_name}"
    if key in _cache:
        return _cache[key]
    # evict previous model to avoid OOM
    for k in list(_cache.keys()):
        del _cache[k]
    gc.collect(); torch.cuda.empty_cache()

    if mode == "vla":
        cfg = load_config(VLA_CFG)
        m   = MobileVLATrainer(cfg)
        ckpt = torch.load(VLA_CKPT, map_location='cpu', weights_only=False)
        sd   = ckpt.get('state_dict', ckpt.get('model_state_dict', ckpt))
        m.load_state_dict(sd, strict=False)
    else:
        cfg = load_config(VLM_CFG)
        m   = MobileVLATrainer(cfg)
        ckpt = torch.load(VLA_CKPT, map_location='cpu', weights_only=False)
        sd   = ckpt.get('state_dict', ckpt.get('model_state_dict', ckpt))
        filtered = {k.replace('model.','',1) if k.startswith('model.') else k: v
                    for k,v in sd.items() if 'act_head' not in k and 'policy_head' not in k}
        m.load_state_dict(filtered, strict=False)

    m.to("cuda").eval()
    _cache[key] = m
    print(f"✅ Loaded: {key}")
    return m

def _infer(model, pil_img, instruction, mode):
    proc = getattr(model.model, "processor", getattr(model.model, "image_processor", None))
    tok  = getattr(model.model, "tokenizer", getattr(model.model, "processor", None))
    pv   = proc(images=pil_img, return_tensors="pt")["pixel_values"].to("cuda")
    ti   = tok(text=instruction, return_tensors="pt", padding=True)
    with torch.no_grad():
        out = model.inference_step({'rgb': pv,
                                    'text': ti["input_ids"].cuda(),
                                    'text_mask': ti["attention_mask"].cuda()})
    while isinstance(out, tuple): out = out[0]
    act = out['action']
    while isinstance(act, tuple): act = act[0]
    vec = act.cpu().numpy().flatten()
    if mode == "vla":
        action_id = int(np.argmax(vec))
        action_name = ACTION_NAMES.get(action_id, f"ID_{action_id}")
        return {"mode":"vla","action_id":action_id,
                "action_name":action_name,
                "logits":[round(float(v),4) for v in vec]}
    else:
        # VLM 모드에서는 텍스트 응답(Grounding)도 함께 시도
        pred_bboxes = []
        
        # 모델 직접 실행하여 텍스트 결과 확인 (VLM Zero-shot용)
        try:
            # PaliGemma 등은 특정 프롬프트 필요
            grounding_prompt = f"detect the gray basket in the center" if "gray basket" in instruction.lower() else instruction
            # 실제 모델의 generate 호출 (robovlms 호환 레이어)
            if hasattr(model.model, "generate"):
                proc = model.model.processor
                inputs = proc(text=grounding_prompt, images=pil_img, return_tensors="pt").to("cuda")
                gen_out = model.model.generate(**inputs, max_new_tokens=64)
                gen_text = proc.decode(gen_out[0], skip_special_tokens=False)
                pred_bboxes = _parse_grounding_tokens(gen_text)
                print(f"🔍 VLM Gen Text: {gen_text} -> Bboxes: {pred_bboxes}")
        except Exception as e:
            print(f"⚠️ Grounding Generation Error: {e}")
        
        return {"mode":"vlm","raw_action":[round(float(v),4) for v in vec[:3]],
                "pred_bboxes": pred_bboxes}

def _vis(pil_img, result, filename=None, mode="pred", force_idx=None):
    img  = pil_img.copy().convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    
    gt_all = _get_gt().get(filename, {})
    # 특정 프레임 인덱스가 지정되지 않았다면 첫 번째 GT 사용
    f_idx = force_idx if force_idx is not None else (sorted(gt_all.keys())[0] if gt_all else 0)
    gt_info = gt_all.get(f_idx, {})
    gt_box = gt_info.get("bbox")
    
    if mode == "gt":
        if gt_box:
            xmin, ymin, xmax, ymax = gt_box
            draw.rectangle([xmin*w, ymin*h, xmax*w, ymax*h], outline=(34, 197, 94, 255), width=4)
            draw.rectangle([xmin*w, ymin*h-20, xmin*w+160, ymin*h], fill=(34, 197, 94, 200))
            draw.text((xmin*w + 5, ymin*h - 18), f"GT: {gt_info.get('anchor','anchor')}".upper(), fill=(255, 255, 255))
            draw.rectangle([0, h-40, w, h], fill=(0,0,0,160))
            draw.text((20, h-30), f"✅ VERIFIED FRAME: {f_idx}", fill=(255,255,255))
        else:
            draw.rectangle([0, h-40, w, h], fill=(153, 27, 27, 160))
            draw.text((20, h-30), f"❌ NO GT FOR FRAME {f_idx}", fill=(255,255,255))
    else:
        # (Pred visualization logic...)
        pred_boxes = result.get("pred_bboxes", [])
        if pred_boxes:
            for box in pred_boxes:
                ymin, xmin, ymax, xmax = box
                iou = _calculate_iou(gt_box, [xmin, ymin, xmax, ymax]) if gt_box else 0.0
                result["iou"] = iou
                draw.rectangle([xmin*w, ymin*h, xmax*w, ymax*h], outline=(239, 68, 68, 255), width=4)
                draw.rectangle([xmin*w, ymin*h-20, xmin*w+120, ymin*h], fill=(239, 68, 68, 200))
                draw.text((xmin*w + 5, ymin*h - 18), f"PRED (IoU: {iou:.2f})", fill=(255, 255, 255))

        draw.rectangle([0, h-60, w, h], fill=(255,255,255,220))
        if result["mode"] == "vla":
            c = ACTION_COLORS.get(result["action_id"],"#333")
            draw.text((20, h-45), f"▶ ACTION: {result['action_name']}", fill=c)
            draw.text((w-180, h-45), f"Conf: {result['logits'][result['action_id']]:.2f}", fill="#666")
        else:
            v = result["raw_action"]
            draw.text((20, h-45), f"V: {v[0]:.3f} | W: {v[2]:.3f}", fill="#333")
            draw.text((w-180, h-45), "Zero-shot VLM", fill="#999")
        
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()

# ── FastAPI ────────────────────────────────────────────────────────
app = FastAPI(title="MoNaVLA Demo")

@app.get("/api/health")
def health():
    return {"status":"online","cuda":torch.cuda.is_available(),"loaded":list(_cache.keys())}

def _parse_episode(fname: str) -> dict:
    """에피소드 파일명에서 메타데이터 파싱
    형식: episode_{date}_{time}_target_{target}_{path_type}_path__{variant}__{core}
    """
    name = fname.replace('.h5', '')
    m = re.match(
        r'episode_(\d+)_(\d+)_target_(\w+?)_(\w+?)_path(?:__(\w+?))?(?:__(\w+))?$',
        name
    )
    if m:
        return {
            'filename': fname,
            'date': m.group(1),
            'time': m.group(2),
            'target_pos': m.group(3),   # center, left, right
            'path_type': m.group(4),    # straight, left, right, ...
            'variant': m.group(5) or 'core',
            'suffix': m.group(6) or '',
            'label': f"{m.group(3)}·{m.group(4)}",
        }
    return {'filename': fname, 'date':'?','time':'?',
            'target_pos':'unknown','path_type':'unknown',
            'variant':'unknown','suffix':'','label':'unknown'}

@app.get("/api/samples")
def samples(limit:int=40):
    files = sorted(glob.glob(os.path.join(DATASET_DIR,"*.h5")))[:limit]
    return [os.path.basename(f) for f in files]

@app.get("/api/samples_parsed")
def samples_parsed(limit:int=300):
    gt_data = _get_gt()
    files = sorted(glob.glob(os.path.join(DATASET_DIR,"*.h5")))[:limit]
    
    parsed = []
    for f in files:
        fname = os.path.basename(f)
        p = _parse_episode(fname)
        # GT 보유 여부 확인
        fkey = fname.replace('.h5', '').replace('episode_', '')
        p['has_gt'] = any(k in gt_data for k in [fname, fkey, "episode_"+fkey])
        parsed.append(p)
    # 카테고리 집계
    path_types  = sorted(set(p['path_type']  for p in parsed))
    target_pos  = sorted(set(p['target_pos'] for p in parsed))
    variants    = sorted(set(p['variant']    for p in parsed))
    return {
        'episodes': parsed,
        'meta': {
            'total': len(parsed),
            'path_types': path_types,
            'target_positions': target_pos,
            'variants': variants,
        }
    }

@app.post("/api/preview_sample")
async def preview_sample(body: dict):
    import h5py
    fname   = body.get("filename","")
    req_idx = body.get("frame_idx") # 특정 프레임 요청 시
    
    h5_path = os.path.join(DATASET_DIR, fname)
    if not os.path.exists(h5_path):
        raise HTTPException(404, f"Not found: {fname}")
    
    gt_data = _get_gt().get(fname, {})
    # 사용할 프레임 결정
    if req_idx is not None and int(req_idx) in gt_data:
        f_idx = int(req_idx)
    else:
        f_idx = sorted(gt_data.keys())[0] if gt_data else 0
        
    with h5py.File(h5_path,'r') as f:
        imgs = f['observations/images'] if 'observations' in f else f['images']
        frame = imgs[f_idx]
    img = Image.fromarray(frame).convert("RGB")
    
    gt_base64 = _vis(img, {}, fname, mode="gt", force_idx=f_idx)
    
    # 가용한 앵커 리스트 반환
    anchors = []
    for k, v in sorted(gt_data.items()):
        anchors.append({"frame_idx": k, "anchor": v.get("anchor", "unknown")})
        
    return {
        "gt_image": gt_base64, 
        "notes": gt_data.get(f_idx, {}).get("notes", ""),
        "anchor": gt_data.get(f_idx, {}).get("anchor", ""),
        "frame_idx": f_idx,
        "available_anchors": anchors
    }

@app.post("/api/predict")
async def predict(
    file: UploadFile = File(...),
    instruction: str = Form("Navigate toward the gray basket"),
    mode: str = Form("vla"),
    vlm_name: str = Form("moondream"),
    frame_idx: int = Form(0)
):
    data  = await file.read()
    img   = Image.open(io.BytesIO(data)).convert("RGB")
    model = _load_model(mode, vlm_name)
    
    t0 = time.time()
    res   = _infer(model, img, instruction, mode)
    latency = (time.time() - t0) * 1000
    
    res["vis_image"] = _vis(img, res, mode="pred")
    res["gt_image"]  = _vis(img, res, mode="gt")
    res["latency_ms"] = round(latency, 2)
    return res

@app.post("/api/predict_sample")
async def predict_sample(body: dict):
    import h5py
    fname = body.get("filename", "")
    instr = body.get("instruction", "")
    mode  = body.get("mode", "vla")
    vlm   = body.get("vlm_name", "paligemma-mix")
    req_idx = body.get("frame_idx")
    
    h5_path = os.path.join(DATASET_DIR, fname)
    if not os.path.exists(h5_path):
        raise HTTPException(404, f"Not found: {fname}")
        
    gt_data = _get_gt().get(fname, {})
    if req_idx is not None and int(req_idx) in gt_data:
        f_idx = int(req_idx)
    else:
        f_idx = sorted(gt_data.keys())[0] if gt_data else 0
    
    with h5py.File(h5_path,'r') as f:
        imgs = f['observations/images'] if 'observations' in f else f['images']
        frame = imgs[f_idx]
    img   = Image.fromarray(frame).convert("RGB")
    model = _load_model(mode, vlm)
    
    t0 = time.time()
    res   = _infer(model, img, instr, mode)
    latency = (time.time() - t0) * 1000
    
    res["vis_image"] = _vis(img, res, fname, mode="pred", force_idx=f_idx)
    res["gt_image"]  = _vis(img, res, fname, mode="gt", force_idx=f_idx)
    res["latency_ms"] = round(latency, 2)
    return res

# serve HTML
@app.get("/", response_class=HTMLResponse)
def index():
    html_path = Path(__file__).parent / "demo_ui.html"
    return HTMLResponse(html_path.read_text())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9292)
