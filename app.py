import gradio as gr
import json
import re
import time
import uuid
import copy
import base64
import random
import tempfile
import os
from io import BytesIO
from pathlib import Path

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import urllib.request as _urlreq
from urllib.parse import quote as _urlquote

def _ai_photo_url(prompt: str, w: int = 800, h: int = 600, seed: int = 0) -> str:
    p = _urlquote((prompt or "interior architecture concept")[:280])
    model = os.environ.get("POLLINATIONS_MODEL", "flux").strip() or "flux"
    return (f"https://image.pollinations.ai/prompt/{p}"
            f"?width={w}&height={h}&nologo=true&seed={seed}&model={model}&enhance=true")


HF_KEY = os.environ.get("HF_API_KEY", "").strip()

def hf_sdxl_generate(prompt: str):
    if not HF_KEY or not HAS_PIL:
        return None
    url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    body = json.dumps({"inputs": prompt[:500],
                       "parameters": {"num_inference_steps": 25, "guidance_scale": 7.0}}).encode("utf-8")
    req = _urlreq.Request(url, data=body, headers={
        "Authorization": f"Bearer {HF_KEY}", "Content-Type": "application/json"})
    try:
        with _urlreq.urlopen(req, timeout=60) as r:
            return PILImage.open(BytesIO(r.read())).convert("RGB")
    except Exception as e:
        print(f"[HF SDXL] {e}")
        return None

def _load_env():
    p = Path(__file__).parent / ".env"
    if not p.exists():
        return
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "utf-8", "latin-1"):
        try:
            txt = raw.decode(enc)
            if "GEMINI_API_KEY" in txt or "=" in txt:
                break
        except Exception:
            continue
    else:
        txt = raw.decode("utf-8", errors="ignore")
    for line in txt.splitlines():
        line = line.strip().lstrip("﻿")
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_env()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
print(f"[Gemini] API key loaded: {'yes' if GEMINI_KEY else 'NO — autofill/narrative disabled'}")


def _safe_json(text: str) -> dict:
    if not text:
        return {}
    # strip markdown fences
    text = re.sub(r"```[a-z]*\n?", "", text).strip()
    # extract first {...}
    m = re.search(r"\{[\s\S]*\}", text)
    blob = m.group(0) if m else text
    # try strict parse first
    try:
        return json.loads(blob)
    except Exception:
        pass
    # fix single-quoted strings → double-quoted
    try:
        fixed = re.sub(r"'([^']*)'", r'"\1"', blob)
        return json.loads(fixed)
    except Exception:
        pass
    # fix unquoted keys
    try:
        fixed = re.sub(r'(\s*)(\w+)(\s*):', r'\1"\2"\3:', blob)
        return json.loads(fixed)
    except Exception:
        return {}

OLLAMA_URL   = os.environ.get("OLLAMA_URL",   "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2").strip()


def ollama_call(prompt: str, want_json: bool = False, timeout: int = 40) -> str:
    url = f"{OLLAMA_URL}/api/generate"
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt,
                       "stream": False, "format": "json" if want_json else ""}).encode()
    req = _urlreq.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with _urlreq.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())["response"].strip()
    except Exception as e:
        print(f"[Ollama] {e}")
        return ""


def gemini_call(prompt: str, want_json: bool = False, timeout: int = 25) -> str:
    if not GEMINI_KEY:
        return ""
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.5-flash:generateContent?key={GEMINI_KEY}")
    cfg = {"temperature": 0.7, "maxOutputTokens": 800,
           "thinkingConfig": {"thinkingBudget": 0}}
    if want_json:
        cfg["responseMimeType"] = "application/json"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": cfg}).encode("utf-8")
    req = _urlreq.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with _urlreq.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        parts = data["candidates"][0]["content"]["parts"]
        return next((p["text"].strip() for p in parts if "text" in p), "")
    except Exception as e:
        print(f"[Gemini] {e}")
        return ""


def llm_call(prompt: str, want_json: bool = False) -> str:
    """Gemini first, fallback to Ollama."""
    if GEMINI_KEY:
        result = gemini_call(prompt, want_json=want_json)
        if result:
            return result
    return ollama_call(prompt, want_json=want_json)


KO_DICT = {
    "도서관": "library", "라운지": "lounge", "갤러리": "gallery",
    "카페": "cafe", "오피스": "office",
    "러닝 스페이스": "learning space", "커뮤니티 스페이스": "community space",
    "커뮤니티": "community",
    "차분한": "calm", "미니멀한": "minimal", "미래지향적인": "futuristic",
    "아늘한": "cozy", "우아한": "elegant", "역동적인": "dynamic",
    "뫰입감 있는": "immersive", "뫰입": "immersive",
    "목재": "wood", "콘크리트": "concrete", "유리": "glass",
    "패브릭": "fabric", "금속": "metal", "석재": "stone", "벨돌": "brick",
    "자연 채광": "natural light", "자연광": "natural light",
    "따뜻한 조명": "warm lighting", "간접 조명": "indirect lighting",
    "드라마틱 조명": "dramatic lighting", "확산 조명": "diffused lighting",
    "포인트 조명": "accent lighting",
    "독서": "reading", "소셔": "social", "창작": "creative",
    "휴식": "rest", "학습": "learning", "전시": "exhibition", "협업": "collaboration",
    "개방형": "open", "레이어드": "layered", "높은 천장": "high ceiling",
    "콤팩트": "compact", "유연한": "flexible", "폐쇄형": "enclosed", "유동적인": "flowing",
    "개방감": "open space", "서가": "bookshelves", "물결": "wave",
    "천장": "ceiling", "바닥": "floor", "벽": "wall", "창문": "window",
    "조명": "lighting", "가구": "furniture", "텍스처": "texture",
    "바이오필릭": "biophilic", "미니멀리즘": "minimalism",
    "인더스트리얼": "industrial", "테라코타": "terracotta",
    "대리석": "marble", "황동": "brass", "린넬": "linen",
    "루버": "louvre", "루프탑": "rooftop", "파티션": "partition",
}

SPACE_TYPES = {
    "Library": {"ko": "도서관", "en_char": "knowledge-rich, contemplative, archival",
                "ko_intro": "지식과 사색이 공존하는",
                "img_labels": ["Reading Alcove", "Book Wall", "Study Nook"],
                "img_icons": ["📚", "🗂️", "🔭"]},
    "Lounge": {"ko": "라운지", "en_char": "relaxed, social, comfortable",
               "ko_intro": "편안한 휴식과 교류가 이루어지는",
               "img_labels": ["Social Seating", "Relaxation Zone", "Feature Corner"],
               "img_icons": ["🛋️", "☕", "🪴"]},
    "Gallery": {"ko": "갤러리", "en_char": "curated, light-focused, contemplative",
                "ko_intro": "예술과 감상이 만나는",
                "img_labels": ["Exhibition Wall", "Display Zone", "Gallery Walk"],
                "img_icons": ["🖼️", "💡", "🎨"]},
    "Cafe": {"ko": "카페", "en_char": "warm, community-oriented, sensory",
             "ko_intro": "따뜻한 커뮤니티 감성이 흔르는",
             "img_labels": ["Seating Area", "Counter Detail", "Ambient Corner"],
             "img_icons": ["☕", "🌿", "🕯️"]},
    "Office": {"ko": "오피스", "en_char": "focused, productive, professional",
               "ko_intro": "생산성과 창의성이 공존하는",
               "img_labels": ["Work Zone", "Collaboration Hub", "Focus Area"],
               "img_icons": ["🖥️", "📐", "🌱"]},
    "Shop / Retail": {"ko": "쇼핑 공간", "en_char": "inviting, curated, brand-expressive",
                      "ko_intro": "브랜드 감성과 경험이 살아있는",
                      "img_labels": ["Display Zone", "Feature Wall", "Customer Flow"],
                      "img_icons": ["🛍️", "🏷️", "✨"]},
    "Restaurant": {"ko": "레스토랑", "en_char": "atmospheric, sensory, intimate",
                   "ko_intro": "미식과 감각이 어우러지는",
                   "img_labels": ["Dining Area", "Bar Counter", "Ambient Lighting"],
                   "img_icons": ["🍽️", "🕯️", "🌿"]},
    "Hotel Lobby": {"ko": "호텔 로비", "en_char": "grand, welcoming, luxurious",
                    "ko_intro": "격조와 환영이 공존하는",
                    "img_labels": ["Reception Zone", "Lounge Seating", "Feature Ceiling"],
                    "img_icons": ["🏨", "🛎️", "💎"]},
    "Studio": {"ko": "스튜디오", "en_char": "creative, flexible, raw",
               "ko_intro": "창의적 작업과 영감이 넘치는",
               "img_labels": ["Work Surface", "Storage Wall", "Creative Zone"],
               "img_icons": ["🎨", "📐", "💡"]},
    "Wellness / Spa": {"ko": "웰니스·스파", "en_char": "serene, restorative, sensory",
                       "ko_intro": "회복과 고요함이 흐르는",
                       "img_labels": ["Treatment Area", "Relaxation Zone", "Water Feature"],
                       "img_icons": ["🧘", "🪷", "💧"]},
    "Learning Space": {"ko": "러닝 스페이스", "en_char": "stimulating, structured, adaptive",
                       "ko_intro": "배움과 성장이 일어나는",
                       "img_labels": ["Teaching Area", "Workshop Zone", "Breakout Space"],
                       "img_icons": ["🎓", "🔬", "💡"]},
    "Community Space": {"ko": "커뮤니티 스페이스", "en_char": "inclusive, flexible, vibrant",
                        "ko_intro": "다양한 만남과 활동이 공존하는",
                        "img_labels": ["Gathering Area", "Event Zone", "Social Hub"],
                        "img_icons": ["🤝", "🎦", "🌐"]},
}

MATERIAL_DATA = {
    "Wood":     {"hex": "#A0784A", "light": "#C9A87A", "ko": "목재",    "finish": "warm grain texture"},
    "Concrete": {"hex": "#8E8E82", "light": "#B8B8AE", "ko": "콘크리트", "finish": "raw poured finish"},
    "Glass":    {"hex": "#90B8C0", "light": "#B8D4D8", "ko": "유리",    "finish": "clear / frosted"},
    "Fabric":   {"hex": "#C4A882", "light": "#DCC8A8", "ko": "패브릭",  "finish": "soft woven textile"},
    "Metal":    {"hex": "#8A8A96", "light": "#B4B4C0", "ko": "금속",    "finish": "brushed matte finish"},
    "Stone":    {"hex": "#9E8C7A", "light": "#C0B0A0", "ko": "석재",    "finish": "honed natural surface"},
    "Brick":    {"hex": "#B46040", "light": "#D4906A", "ko": "벨돌",   "finish": "exposed rough texture"},
}

MOOD_DATA = {
    "Calm":       {"ko": "차분한",       "en_adj": "serene, tranquil, quietly composed"},
    "Minimal":    {"ko": "미니멀한",     "en_adj": "restrained, precise, uncluttered"},
    "Futuristic": {"ko": "미래지향적인", "en_adj": "forward-looking, innovative, sleek"},
    "Cozy":       {"ko": "아늘한",       "en_adj": "warm, inviting, intimate"},
    "Elegant":    {"ko": "우아한",       "en_adj": "refined, sophisticated, graceful"},
    "Dynamic":    {"ko": "역동적인",     "en_adj": "energetic, bold, expressive"},
    "Immersive":  {"ko": "뫰입감 있는",  "en_adj": "atmospheric, enveloping, layered"},
}

MOOD_PHOTO_STYLE = {
    "Calm":       "soft natural daylight, calm and still composition, film photography aesthetic",
    "Minimal":    "clean architectural photography, neutral palette, precise symmetrical framing",
    "Futuristic": "cinematic architectural render, volumetric lighting, high-tech material surfaces",
    "Cozy":       "warm interior photography, shallow depth of field, golden hour ambient light",
    "Elegant":    "luxury interior photography, high-fashion editorial, polished refined surfaces",
    "Dynamic":    "bold architectural photography, dramatic angles, vivid material contrast",
    "Immersive":  "atmospheric interior photography, moody and enveloping, layered spatial depth",
}

LIGHTING_DATA = {
    "Natural Light":   {"ko": "자연 채광",     "desc": "floor-to-ceiling glazing and skylights"},
    "Warm":            {"ko": "따뜻한 조명",   "desc": "warm-toned incandescent and LED sources"},
    "Indirect":        {"ko": "간접 조명",     "desc": "cove lighting and diffused wall washing"},
    "Dramatic":        {"ko": "드라마틱 조명", "desc": "high-contrast spotlighting with deep shadows"},
    "Diffused":        {"ko": "확산 조명",     "desc": "soft even illumination, glare-free"},
    "Accent Lighting": {"ko": "포인트 조명",   "desc": "directional accent and display spotlights"},
}

ACTIVITY_DATA = {
    "Reading":       {"ko": "독서",  "desc": "focused individual reading"},
    "Social":        {"ko": "소셔",  "desc": "casual social interaction"},
    "Creative":      {"ko": "창작",  "desc": "hands-on creative work"},
    "Rest":          {"ko": "휴식",  "desc": "quiet rest and reflection"},
    "Learning":      {"ko": "학습",  "desc": "structured learning and study"},
    "Exhibition":    {"ko": "전시",  "desc": "curated display and exhibition"},
    "Collaboration": {"ko": "협업",  "desc": "group collaboration and teamwork"},
}

SPATIAL_DATA = {
    "Open":         {"ko": "개방형",    "desc": "expansive open-plan layout"},
    "Layered":      {"ko": "레이어드",  "desc": "layered spatial zones and levels"},
    "High Ceiling": {"ko": "높은 천장", "desc": "voluminous high-ceiling atmosphere"},
    "Compact":      {"ko": "콤팩트",    "desc": "intimate compact arrangement"},
    "Flexible":     {"ko": "유연한",    "desc": "adaptable multi-use configuration"},
    "Enclosed":     {"ko": "폐쇄형",    "desc": "defined enclosed spatial volumes"},
    "Flowing":      {"ko": "유동적인",  "desc": "fluid, continuous spatial transitions"},
}


def translate_korean(text: str) -> str:
    for ko, en in KO_DICT.items():
        text = text.replace(ko, en)
    return text


def extract_custom_descriptors(extra: str) -> tuple:
    if not extra or not extra.strip():
        return "", []
    translated = translate_korean(extra.strip())
    parts = re.split(r"[,;\n]+", translated)
    descriptors = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]
    return translated, descriptors


WORKFLOW_PATH = Path("comfyui_workflow.json")


def _future_load_workflow():
    if WORKFLOW_PATH.exists():
        try:
            with open(WORKFLOW_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _future_patch_workflow(workflow, pos_prompt, neg_prompt, width, height, steps, cfg, seed):
    wf = copy.deepcopy(workflow)
    # FLUX models require cfg=1.0 — detect by checkpoint name
    is_flux = any("flux" in str(node.get("inputs", {}).get("ckpt_name", "")).lower()
                  for node in wf.values())
    if is_flux:
        cfg = 1.0
    pos_id = neg_id = latent_id = None
    for node_id, node in wf.items():
        ct  = node.get("class_type", "")
        inp = node.get("inputs", {})
        if ct in ("KSampler", "KSamplerAdvanced"):
            if "steps"      in inp: inp["steps"]      = int(steps)
            if "cfg"        in inp: inp["cfg"]         = float(cfg)
            if "seed"       in inp: inp["seed"]        = int(seed)
            if "noise_seed" in inp: inp["noise_seed"]  = int(seed)
            if isinstance(inp.get("positive"),     list): pos_id    = str(inp["positive"][0])
            if isinstance(inp.get("negative"),     list): neg_id    = str(inp["negative"][0])
            if isinstance(inp.get("latent_image"), list): latent_id = str(inp["latent_image"][0])
    if pos_id and pos_id in wf:
        n = wf[pos_id]
        if n.get("class_type") == "CLIPTextEncode" and "text" in n.get("inputs", {}):
            n["inputs"]["text"] = pos_prompt
    if neg_id and neg_id in wf:
        n = wf[neg_id]
        if n.get("class_type") == "CLIPTextEncode" and "text" in n.get("inputs", {}):
            n["inputs"]["text"] = neg_prompt
    if latent_id and latent_id in wf:
        n   = wf[latent_id]
        inp = n.get("inputs", {})
        if n.get("class_type") in ("EmptyLatentImage", "EmptySD3LatentImage",
                                   "EmptyHunyuanLatentVideo", "EmptyMochiLatentVideo"):
            if "width"  in inp: inp["width"]  = int(width)
            if "height" in inp: inp["height"] = int(height)
    return wf


def _future_comfyui_generate(server_url: str, workflow: dict, timeout: int = 300):
    if not HAS_REQUESTS:
        raise RuntimeError("'requests' not installed")
    if not HAS_PIL:
        raise RuntimeError("'Pillow' not installed")
    url       = server_url.rstrip("/")
    client_id = str(uuid.uuid4())
    resp = _requests.post(f"{url}/prompt",
                          json={"prompt": workflow, "client_id": client_id}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ComfyUI rejected prompt: {data['error']}")
    prompt_id = data["prompt_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2.5)
        try:
            hist = _requests.get(f"{url}/history/{prompt_id}", timeout=10).json()
        except Exception:
            continue
        entry = hist.get(prompt_id)
        if entry is None:
            continue
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            raise RuntimeError(f"ComfyUI error: {status.get('messages', [])}")
        for node_out in entry.get("outputs", {}).values():
            for img_info in node_out.get("images", []):
                img_resp = _requests.get(f"{url}/view",
                    params={"filename": img_info["filename"],
                            "subfolder": img_info.get("subfolder", ""),
                            "type": img_info.get("type", "output")}, timeout=60)
                img_resp.raise_for_status()
                return PILImage.open(BytesIO(img_resp.content)).convert("RGB")
    raise TimeoutError(f"ComfyUI did not finish within {timeout} seconds")


def pil_to_b64(img) -> str:
    if not (HAS_PIL and isinstance(img, PILImage.Image)):
        return ""
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def parse_image_size(size_str: str) -> tuple:
    w, h = size_str.strip().split("x")
    return int(w), int(h)


def build_prompts(space, activities, materials, lighting, mood, spatial,
                  translated_extra, custom_descriptors):
    sp  = SPACE_TYPES.get(space,  {"en_char": "contemporary interior architecture"})
    md  = MOOD_DATA.get(mood,     {"en_adj":  "calm and refined"})
    photo_style = MOOD_PHOTO_STYLE.get(mood, "editorial interior photography, professional staging")
    mat = ", ".join(m.lower() for m in materials) if materials else "contemporary materials"
    lit = ", ".join(LIGHTING_DATA[l]["desc"] for l in lighting if l in LIGHTING_DATA) if lighting else "balanced, purposeful lighting"
    spt = ", ".join(SPATIAL_DATA[s]["desc"]  for s in spatial  if s in SPATIAL_DATA)  if spatial  else "thoughtfully composed space"
    act = ", ".join(a.lower() for a in activities) if activities else "multipurpose use"
    custom_str  = f" Additional elements: {', '.join(custom_descriptors)}." if custom_descriptors else ""
    space_label = (space or "interior space").lower()
    main_prompt = (
        f"A {md['en_adj']} {space_label}, {sp['en_char']}. "
        f"Spatial quality: {spt}. Primary materials: {mat}. "
        f"Lighting: {lit}. Programmed for {act}.{custom_str} "
        f"{photo_style}, architectural portfolio quality."
    )
    material_prompt = (
        f"Material and texture detail study for a {md['en_adj']} {space_label}. "
        f"Close-up surfaces: {mat}. {sp['en_char']}.{custom_str} "
        f"Illuminated by {lit}. "
        f"Macro interior photography, material palette reference, {photo_style}."
    )
    atmosphere_prompt = (
        f"Atmospheric interior mood: {md['en_adj']} ambiance in a {space_label}. "
        f"{spt}. Lit by {lit}.{custom_str} Designed for {act}. "
        f"Experiential space photography, human-scale interior perspective, {photo_style}."
    )
    return main_prompt, material_prompt, atmosphere_prompt


def build_tags(space, activities, materials, lighting, mood, spatial, custom_descriptors):
    parts = []
    if space: parts.append(f"#{space.replace(' ', '')}")
    parts += [f"#{a.lower()}" for a in activities]
    parts += [f"#{m.lower()}" for m in materials]
    parts += [f"#{l.replace(' ', '').lower()}" for l in lighting]
    if mood: parts.append(f"#{mood.lower()}design")
    parts += [f"#{s.replace(' ', '').lower()}" for s in spatial]
    for desc in custom_descriptors:
        tag = re.sub(r"[^a-zA-Z0-9]", "", desc).lower()
        if tag: parts.append(f"#{tag}")
    parts += ["#interiordesign", "#conceptboard", "#spacedesign", "#designinspiration"]
    return "  ".join(parts)


def build_korean(space, activities, materials, lighting, mood, spatial,
                 translated_extra, custom_descriptors):
    sp = SPACE_TYPES.get(space)
    md = MOOD_DATA.get(mood, {"ko": "차분하고 세련된"})
    sp_ko    = sp["ko"]       if sp else (space or "인테리어 공간")
    sp_intro = sp["ko_intro"] if sp else "섬세하게 계획된"
    mat_ko = " · ".join(MATERIAL_DATA[m]["ko"] for m in materials  if m in MATERIAL_DATA) or "현대적 소재"
    act_ko = " · ".join(ACTIVITY_DATA[a]["ko"] for a in activities if a in ACTIVITY_DATA) or "다목적"
    spt_ko = " · ".join(SPATIAL_DATA[s]["ko"]  for s in spatial    if s in SPATIAL_DATA)  or "개방형"
    lit_ko = " · ".join(LIGHTING_DATA[l]["ko"] for l in lighting   if l in LIGHTING_DATA) or "균형 조명"
    custom_str = ""
    if custom_descriptors:
        listed = ", ".join(custom_descriptors)
        custom_str = f" **{listed}** 등의 특별한 개념 요소가 공간에 통합됩니다."
    return (
        f"{sp_intro} **{sp_ko}**은 **{md['ko']}** 분위기를 중심으로 "
        f"{mat_ko} 소재와 {lit_ko}을 통해 공간의 정체성을 형성합니다. "
        f"{spt_ko} 공간 구성 속에서 {act_ko} 활동을 지원하며, "
        f"사용자에게 목적과 감성이 공존하는 경험을 제공합니다.{custom_str}"
    )


def resolve_image_slot(future_img, uploaded_img, label, icon, mat_hex, photo=""):
    if future_img is not None:
        b64 = pil_to_b64(future_img)
        if b64: return _generated_tile(b64, source_label="Generated")
    if uploaded_img is not None:
        b64 = pil_to_b64(uploaded_img)
        if b64: return _generated_tile(b64, source_label="Uploaded")
    return _img_tile(label, icon, mat_hex, photo=photo)


def _md_bold_to_html(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def _pale_tint(hex_color: str, mix: float = 0.14, base: tuple = (247, 243, 234)) -> str:
    r = int(int(hex_color[1:3], 16) * mix + base[0] * (1 - mix))
    g = int(int(hex_color[3:5], 16) * mix + base[1] * (1 - mix))
    b = int(int(hex_color[5:7], 16) * mix + base[2] * (1 - mix))
    return f"#{min(r,255):02X}{min(g,255):02X}{min(b,255):02X}"


_MATERIAL_PHOTO = {
    "Wood":     _ai_photo_url("oak wood grain texture surface close-up, warm brown, macro", 400, 240, seed=11),
    "Concrete": _ai_photo_url("polished concrete surface texture, grey minimalist, macro", 400, 240, seed=22),
    "Glass":    _ai_photo_url("frosted glass panel texture, translucent light, architectural, macro", 400, 240, seed=33),
    "Fabric":   _ai_photo_url("linen fabric woven texture close-up, natural beige textile, macro", 400, 240, seed=44),
    "Metal":    _ai_photo_url("brushed stainless steel surface texture, metallic sheen, macro", 400, 240, seed=55),
    "Stone":    _ai_photo_url("white marble stone texture, grey veining, interior material, macro", 400, 240, seed=66),
    "Brick":    _ai_photo_url("exposed red brick wall texture, rough mortar, interior, macro", 400, 240, seed=77),
}
_SPACE_PHOTO = {
    "Library":          "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=800&h=600&fit=crop",
    "Lounge":           "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800&h=600&fit=crop",
    "Gallery":          "https://images.unsplash.com/photo-1545987796-200677ee1011?w=800&h=600&fit=crop",
    "Cafe":             "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800&h=600&fit=crop",
    "Office":           "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&h=600&fit=crop",
    "Learning Space":   "https://images.unsplash.com/photo-1497486751825-1233686d5d80?w=800&h=600&fit=crop",
    "Community Space":  "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?w=800&h=600&fit=crop",
}


def _img_tile(label: str, icon: str, mat_hex: str, height: str = "100%", photo: str = "") -> str:
    if photo:
        bg = "background:#D8D2C8;"
        label_color = "#FFFDF7"
        overlay = (f'<img src="{photo}" style="position:absolute;inset:0;width:100%;height:100%;'
                   f'object-fit:cover;display:block;" loading="lazy" '
                   f'onerror="this.style.display=\'none\'" />'
                   '<div style="position:absolute;inset:0;background:linear-gradient(transparent 50%,rgba(20,18,14,0.55));pointer-events:none;"></div>'
                   '<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
                   'font-size:11px;color:rgba(80,70,60,0.5);letter-spacing:1px;pointer-events:none;'
                   'background:rgba(255,253,247,0.6);padding:4px 10px;border-radius:20px;z-index:-1;">'
                   'Generating AI image…</div>')
    else:
        pale  = _pale_tint(mat_hex, 0.12)
        light = _pale_tint(mat_hex, 0.22)
        r, g, b = int(mat_hex[1:3], 16), int(mat_hex[3:5], 16), int(mat_hex[5:7], 16)
        label_color = f"#{int(r*0.55):02X}{int(g*0.55):02X}{int(b*0.55):02X}"
        bg = f'background:linear-gradient(145deg,{pale},{light});'
        overlay = ('<div style="position:absolute;inset:0;background-image:'
                   'repeating-linear-gradient(0deg,transparent 0 28px,rgba(38,50,56,0.04) 28px 29px),'
                   'repeating-linear-gradient(90deg,transparent 0 28px,rgba(38,50,56,0.04) 28px 29px);"></div>')
    return (
        f'<div style="border:1px solid #D8D0C3;border-radius:10px;height:{height};'
        f'min-height:128px;position:relative;overflow:hidden;{bg}">'
        f'{overlay}'
        f'<span style="position:absolute;top:8px;left:10px;font-size:14px;'
        f'background:rgba(255,253,247,0.92);border-radius:50%;width:24px;height:24px;'
        f'display:flex;align-items:center;justify-content:center;">{icon}</span>'
        f'<span style="position:absolute;bottom:8px;left:10px;right:10px;font-size:10px;font-weight:700;'
        f'letter-spacing:2px;text-transform:uppercase;color:{label_color};">{label}</span>'
        f'</div>'
    )


def _generated_tile(b64: str, height: str = "100%", source_label: str = "Uploaded") -> str:
    return (
        f'<div style="border-radius:10px;overflow:hidden;height:{height};'
        f'min-height:128px;border:1px solid #D8D0C3;position:relative;">'
        f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;height:100%;object-fit:cover;display:block;"/>'
        f'<div style="position:absolute;bottom:0;left:0;right:0;padding:6px 10px;'
        f'background:linear-gradient(transparent,rgba(38,50,56,0.45));border-radius:0 0 10px 10px;">'
        f'<span style="font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;'
        f'color:rgba(255,253,247,0.9);">{source_label}</span></div></div>'
    )


def _material_block(name: str) -> str:
    d = MATERIAL_DATA[name]
    photo = _MATERIAL_PHOTO.get(name, "")
    if photo:
        inner = (
            f'<img src="{photo}" style="position:absolute;inset:0;width:100%;height:100%;'
            f'object-fit:cover;border-radius:7px;" loading="lazy" '
            f'onerror="this.style.display=\'none\'" />'
            f'<div style="position:absolute;inset:0;background:linear-gradient(transparent 40%,rgba(0,0,0,0.45));border-radius:7px;pointer-events:none;"></div>'
        )
        container_bg = "background:#C8C0B4;"
    else:
        inner = ""
        container_bg = f'background:linear-gradient(150deg,{d["hex"]},{d["light"]});'
    return (
        f'<div style="flex:1;min-width:78px;">'
        f'<div style="height:60px;{container_bg}'
        f'border-radius:7px;margin-bottom:6px;position:relative;border:1px solid rgba(0,0,0,0.1);'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.08);overflow:hidden;">'
        f'{inner}'
        f'<span style="position:absolute;bottom:4px;left:6px;right:6px;font-size:8px;font-weight:700;'
        f'letter-spacing:1px;text-transform:uppercase;color:#FFFDF7;'
        f'text-shadow:0 1px 2px rgba(0,0,0,0.8);z-index:2;">{name.upper()}</span></div>'
        f'<div style="font-size:11px;color:#3C3428;font-weight:600;margin-bottom:2px;">{d["ko"]}</div>'
        f'<div style="font-size:10px;color:#6F6A60;">{d["finish"]}</div></div>'
    )


def _chip(label: str, bg: str = "#EEE8DF", fg: str = "#4A4038", border: str = "#D8D0C3") -> str:
    return (
        f'<span style="display:inline-block;padding:5px 12px;margin:3px;'
        f'background:{bg};border:1px solid {border};border-radius:20px;'
        f'font-size:11px;font-weight:500;color:{fg};letter-spacing:0.2px;">{label}</span>'
    )


def _board_label(text: str) -> str:
    return (f'<p style="font-size:9px;letter-spacing:2.5px;text-transform:uppercase;'
            f'color:#7A7268;margin:0 0 12px;font-weight:700;">{text}</p>')


def extract_palette(img, n: int = 5):
    if img is None or not HAS_PIL:
        return []
    try:
        small = img.convert("RGB").resize((150, 150))
        q = small.quantize(colors=n, method=2)
        pal = q.getpalette()[: n * 3]
        return [f"#{pal[i]:02X}{pal[i+1]:02X}{pal[i+2]:02X}" for i in range(0, n * 3, 3)]
    except Exception:
        return []


def _palette_strip_html(hex_list):
    if not hex_list:
        return ""
    swatches = "".join(
        f'<div style="flex:1;min-width:50px;height:54px;background:{h};'
        f'border-radius:6px;position:relative;border:1px solid rgba(0,0,0,0.08);'
        f'box-shadow:0 1px 2px rgba(0,0,0,0.05);">'
        f'<span style="position:absolute;bottom:4px;left:6px;font-size:9px;font-weight:600;'
        f'color:#FFFDF7;text-shadow:0 1px 2px rgba(0,0,0,0.6);letter-spacing:0.5px;">{h}</span>'
        f'</div>' for h in hex_list)
    return (f'<div style="background:#FFFDF7;border-radius:10px;padding:16px;margin-bottom:10px;'
            f'border:1px solid #D8D0C3;">{_board_label("Color Palette · 추출 색상")}'
            f'<div style="display:flex;gap:8px;">{swatches}</div></div>')


def build_html_board(
    space, activities, materials, lighting, mood, spatial,
    translated_extra, main_prompt,
    custom_descriptors=None,
    future_main=None, future_material=None, future_atmosphere=None,
    uploaded_main=None, uploaded_material=None, uploaded_atmosphere=None,
    warning="", ko_override="",
    material_prompt="", atmo_prompt="", seed_base=0,
):
    custom_descriptors = custom_descriptors or []
    sp = SPACE_TYPES.get(space, {"ko": space or "Interior Space",
                                  "en_char": "contemporary interior architecture",
                                  "ko_intro": "세심하게 계획된",
                                  "img_labels": ["Main View", "Detail", "Ambience"],
                                  "img_icons":  ["🏛️", "✨", "🌿"]})
    md = MOOD_DATA.get(mood, {"ko": "차분한", "en_adj": "calm and refined"})
    first_mat = materials[0] if materials else "Wood"
    accent    = MATERIAL_DATA.get(first_mat, MATERIAL_DATA["Wood"])["hex"]
    tile_mats = ((materials or ["Wood", "Concrete", "Stone"]) * 3)[:3]
    sb = seed_base or random.randint(1, 999999)
    hero_photo = _ai_photo_url(main_prompt, 800, 600, seed=sb)
    mid_photo  = _ai_photo_url(material_prompt or main_prompt, 600, 400, seed=sb + 1)
    bot_photo  = _ai_photo_url(atmo_prompt or main_prompt, 600, 400, seed=sb + 2)
    hero_tile = resolve_image_slot(future_main, uploaded_main, sp["img_labels"][0], sp["img_icons"][0],
                                   MATERIAL_DATA.get(tile_mats[0], MATERIAL_DATA["Wood"])["hex"],
                                   photo=hero_photo)
    mid_tile  = resolve_image_slot(future_material, uploaded_material, sp["img_labels"][1], sp["img_icons"][1],
                                   MATERIAL_DATA.get(tile_mats[1], MATERIAL_DATA["Concrete"])["hex"],
                                   photo=mid_photo)
    bot_tile  = resolve_image_slot(future_atmosphere, uploaded_atmosphere, sp["img_labels"][2], sp["img_icons"][2],
                                   MATERIAL_DATA.get(tile_mats[2], MATERIAL_DATA["Stone"])["hex"],
                                   photo=bot_photo)
    palette_hex = []
    for src in (uploaded_main, uploaded_material, uploaded_atmosphere, future_main, future_material, future_atmosphere):
        if src is not None and not palette_hex:
            palette_hex = extract_palette(src, 5)
            break
    if not palette_hex:
        palette_hex = [MATERIAL_DATA.get(m, MATERIAL_DATA["Wood"])["hex"]
                       for m in (materials or ["Wood", "Concrete", "Stone"])[:5]]
    palette_html = _palette_strip_html(palette_hex)
    mat_blocks = "".join(_material_block(m) for m in (materials or ["Wood"]))
    act_chips  = "".join(_chip(a, "#EDE8DF", "#4A3C30") for a in activities) or _chip("—", "#F5F2EE", "#AAA8A4")
    lit_chips  = "".join(_chip(l, "#EDE8DF", "#3C3830") for l in lighting)   or _chip("—", "#F5F2EE", "#AAA8A4")
    spa_chips  = "".join(_chip(s, "#E6EDE8", "#303C38") for s in spatial)    or _chip("—", "#F5F2EE", "#AAA8A4")
    custom_section = ""
    if custom_descriptors:
        cc = "".join(_chip(d, "#F5EDE6", "#6B3E28", "#D4B8A8") for d in custom_descriptors)
        custom_section = (f'<div style="background:#FFFDF7;border-radius:10px;padding:16px;'
                          f'margin-bottom:10px;border:1px solid #D8D0C3;border-left:3px solid #C57B57;">'
                          f'{_board_label("Custom Concept Elements")}'
                          f'<div style="line-height:2;">{cc}</div></div>')
    ko_raw = ko_override or build_korean(space, activities, materials, lighting, mood, spatial,
                                          translated_extra, custom_descriptors)
    ko_html = _md_bold_to_html(ko_raw)
    tags_str  = build_tags(space, activities, materials, lighting, mood, spatial, custom_descriptors)
    tag_chips = "".join(_chip(t, "#F2EDE8", "#6B5E54", "#D8D0C3") for t in tags_str.split("  "))
    warning_banner = ""
    if warning:
        warning_banner = (f'<div style="background:#FDF3EE;border:1px solid #E8C4A8;'
                          f'border-radius:8px;padding:12px 16px;margin-bottom:16px;'
                          f'font-size:12px;color:#8B4A2A;line-height:1.6;">{warning}</div>')
    mood_label = f"{mood} · {md['en_adj'].split(',')[0].strip().title()}"
    return f"""
<div style="font-family:'Helvetica Neue',Arial,sans-serif;background:#FFFFFF;
            border-radius:16px;max-width:960px;margin:0 auto;
            box-sizing:border-box;color:#1E1A14;border:1px solid #E0D8CC;
            box-shadow:0 4px 32px rgba(38,50,56,0.08);overflow:hidden;">

  <!-- HEADER -->
  <div style="padding:32px 36px 24px;border-bottom:1px solid #EDE6DA;">
    {warning_banner}
    <p style="font-size:8px;letter-spacing:5px;text-transform:uppercase;color:#A09888;margin:0 0 14px;font-weight:700;">
      Interior Concept Board &nbsp;·&nbsp; {space or 'Interior Space'}
    </p>
    <div style="display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:10px;">
      <h1 style="font-size:36px;font-weight:300;letter-spacing:-0.5px;margin:0;
                 color:#1E1A14;font-family:'Georgia','Times New Roman',serif;">{sp['ko']}</h1>
      <span style="font-size:15px;color:#7A7268;font-weight:400;letter-spacing:0.3px;">{mood_label}</span>
    </div>
    <p style="font-size:12px;color:#8A8278;margin:0 0 16px;line-height:1.6;letter-spacing:0.3px;">
      {sp['en_char'].replace(',', ' &nbsp;·&nbsp;')}
    </p>
    <div style="width:40px;height:3px;background:{accent};border-radius:2px;"></div>
  </div>

  <!-- DESIGN INTENT -->
  <div style="padding:28px 36px;background:linear-gradient(135deg,#FFFDF7,#FBF4EA);border-bottom:1px solid #EDE6DA;">
    <div style="display:flex;align-items:flex-start;gap:16px;">
      <div style="flex-shrink:0;width:36px;height:36px;border-radius:50%;background:{accent};
                  display:flex;align-items:center;justify-content:center;margin-top:2px;">
        <span style="font-size:16px;">✦</span>
      </div>
      <div style="flex:1;">
        <p style="font-size:8px;letter-spacing:4px;text-transform:uppercase;color:#B0A898;margin:0 0 12px;font-weight:700;">Design Intent</p>
        <p style="font-size:15px;color:#2E2418;line-height:2.1;margin:0;font-family:'Georgia','Times New Roman',serif;font-weight:400;">{ko_html}</p>
      </div>
    </div>
  </div>

  <!-- MAIN IMAGE PROMPT -->
  <div style="padding:16px 36px;background:#F9F4EC;border-bottom:1px solid #EDE6DA;">
    <p style="font-size:8px;letter-spacing:4px;text-transform:uppercase;color:#B0A898;margin:0 0 8px;font-weight:700;">Main Image Prompt</p>
    <p style="font-size:12px;color:#6F6A60;margin:0;line-height:1.8;font-style:italic;">&ldquo;{main_prompt}&rdquo;</p>
  </div>

  <!-- IMAGE GRID -->
  <div style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:240px 240px;gap:3px;background:#E0D8CC;">
    <div style="grid-row:1/3;overflow:hidden;position:relative;">{hero_tile}</div>
    <div style="overflow:hidden;position:relative;">{mid_tile}</div>
    <div style="overflow:hidden;position:relative;">{bot_tile}</div>
  </div>

  <!-- COLOR + MATERIAL -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0;border-bottom:1px solid #EDE6DA;">
    <div style="padding:20px 24px;border-right:1px solid #EDE6DA;">
      {palette_html}
    </div>
    <div style="padding:20px 24px;">
      {_board_label("Material Palette")}
      <div style="display:flex;gap:10px;flex-wrap:wrap;">{mat_blocks}</div>
    </div>
  </div>

  <!-- ACTIVITY / LIGHTING / SPATIAL -->
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;border-bottom:1px solid #EDE6DA;">
    <div style="padding:18px 20px;border-right:1px solid #EDE6DA;">
      {_board_label("UX Activity")}<div style="line-height:2;">{act_chips}</div></div>
    <div style="padding:18px 20px;border-right:1px solid #EDE6DA;">
      {_board_label("Lighting")}<div style="line-height:2;">{lit_chips}</div></div>
    <div style="padding:18px 20px;">
      {_board_label("Spatial Quality")}<div style="line-height:2;">{spa_chips}</div></div>
  </div>

  <!-- CUSTOM + TAGS -->
  {f'<div style="padding:18px 24px;border-bottom:1px solid #EDE6DA;">{custom_section}</div>' if custom_descriptors else ''}
  <div style="padding:18px 24px;border-bottom:1px solid #EDE6DA;">
    {_board_label("Tags")}<div style="line-height:2.2;">{tag_chips}</div>
  </div>

  <!-- FOOTER -->
  <div style="padding:14px 24px;text-align:center;background:#F9F4EC;">
    <p style="font-size:8px;letter-spacing:4px;text-transform:uppercase;color:#C8C4BC;margin:0;">AI Interior Concept Board Generator</p>
  </div>
</div>
"""


def generate_concept(
    space, activities, materials, lighting, mood, spatial, extra,
    upload_main, upload_material, upload_atmosphere,
    use_external, external_url, neg_prompt, steps, cfg, img_size, seed,
):
    space      = space or "Library"
    mood       = mood  or "Calm"
    activities = activities or []
    materials  = materials  or []
    lighting   = lighting   or []
    spatial    = spatial    or []
    extra      = extra      or ""
    translated_extra, custom_descriptors = extract_custom_descriptors(extra)
    main_prompt, material_prompt, atmosphere_prompt = build_prompts(
        space, activities, materials, lighting, mood, spatial,
        translated_extra, custom_descriptors,
    )
    tags    = build_tags(space, activities, materials, lighting, mood, spatial, custom_descriptors)
    ko_stmt = build_korean(space, activities, materials, lighting, mood, spatial,
                           translated_extra, custom_descriptors)
    if GEMINI_KEY or OLLAMA_URL:
        ctx = (f"Space: {space}, Mood: {mood}, Materials: {materials or '-'}, "
               f"Lighting: {lighting or '-'}, Activities: {activities or '-'}, "
               f"Spatial: {spatial or '-'}, Extra: {translated_extra or '-'}")
        gp = llm_call(
            "You are an interior design director. Output JSON only.\n"
            f"Context: {ctx}\n"
            "JSON: {\"statement\":\"3-4 sentence English concept statement, poetic and specific (use **bold** for key terms)\","
            f"\"main\":\"{space} interior — main view, cinematic architectural photography, one sentence\","
            f"\"material\":\"{space} — material and detail close-up, one sentence\","
            f"\"atmosphere\":\"{space} — lighting and atmosphere, one sentence\"}}",
            want_json=True)
        j = _safe_json(gp)
        if j.get("statement"): ko_stmt = j["statement"]
        if j.get("main"): main_prompt = j["main"]
        if j.get("material"): material_prompt = j["material"]
        if j.get("atmosphere"): atmosphere_prompt = j["atmosphere"]
    future_main = future_material = future_atmosphere = None
    warning = ""
    if use_external and external_url and external_url.strip():
        try:
            workflow = _future_load_workflow()
            if workflow:
                w, h     = parse_image_size(img_size)
                seed_val = int(seed) if int(seed) >= 0 else random.randint(0, 2**31 - 1)
                neg      = neg_prompt or ""
                wf1 = _future_patch_workflow(workflow, main_prompt, neg, w, h, int(steps), float(cfg), seed_val)
                future_main = _future_comfyui_generate(external_url.strip(), wf1)
                wf2 = _future_patch_workflow(workflow, material_prompt, neg, w, h, int(steps), float(cfg), seed_val + 1)
                future_material = _future_comfyui_generate(external_url.strip(), wf2)
                wf3 = _future_patch_workflow(workflow, atmosphere_prompt, neg, w, h, int(steps), float(cfg), seed_val + 2)
                future_atmosphere = _future_comfyui_generate(external_url.strip(), wf3)
            else:
                warning = "⚠️ comfyui_workflow.json not found — place workflow file in app directory"
        except Exception as e:
            warning = f"⚠️ ComfyUI connection failed: {str(e)[:120]}"
    board = build_html_board(
        space, activities, materials, lighting, mood, spatial,
        translated_extra, main_prompt,
        custom_descriptors=custom_descriptors,
        future_main=future_main, future_material=future_material, future_atmosphere=future_atmosphere,
        uploaded_main=upload_main, uploaded_material=upload_material, uploaded_atmosphere=upload_atmosphere,
        warning=warning, ko_override=ko_stmt,
        material_prompt=material_prompt, atmo_prompt=atmosphere_prompt,
        seed_base=int(seed) if seed and int(seed) >= 0 else 0,
    )
    n_uploads = sum(1 for x in [upload_main, upload_material, upload_atmosphere] if x is not None)
    upload_note = f" · {n_uploads} image{'s' if n_uploads>1 else ''} used" if n_uploads else ""
    status_md = f"✓ {space} · {mood}{upload_note} — Concept board generated"
    return main_prompt, material_prompt, atmosphere_prompt, tags, ko_stmt, board, status_md


def reset_inputs():
    return "Library", [], [], [], "Calm", [], "", None, None, None


def ai_autofill(text):
    if not GEMINI_KEY:
        gr.Warning("Gemini API 키가 로드되지 않았습니다. .env 파일 확인하세요.")
        return (gr.update(),) * 6
    if not text or not text.strip():
        gr.Warning("Custom Keywords 입력란에 자연어 설명을 먼저 적어주세요.")
        return (gr.update(),) * 6
    prompt = (
        "사용자의 자연어 설명을 분석해 인테리어 컨셉 필드를 자동 선택하세요. "
        "각 다중 필드는 최소 2개 이상 선택. 응답은 반드시 아래 형식의 순수 JSON 한 개.\n"
        f"입력: \"{text}\"\n"
        f"space (1개, 택1): {SPACE_LIST}\n"
        f"mood (1개, 택1): {MOOD_LIST}\n"
        f"materials (배열): {MATERIAL_LIST}\n"
        f"lighting (배열): {LIGHTING_LIST}\n"
        f"activities (배열): {ACTIVITY_LIST}\n"
        f"spatial (배열): {SPATIAL_LIST}\n"
        "형식: {\"space\":\"\",\"mood\":\"\",\"materials\":[],\"lighting\":[],\"activities\":[],\"spatial\":[]}"
    )
    out = llm_call(prompt, want_json=True)
    if not out:
        gr.Warning("No AI response (check Gemini API key or Ollama connection)")
        return (gr.update(),) * 6
    try:
        j = _safe_json(out)
        if not j:
            raise ValueError("empty")
        gr.Info(f"AI 자동입력 완료: {j.get('space','')} · {j.get('mood','')}")
        return (
            j.get("space") or gr.update(),
            j.get("mood") or gr.update(),
            [m for m in (j.get("materials") or []) if m in MATERIAL_LIST],
            [l for l in (j.get("lighting") or []) if l in LIGHTING_LIST],
            [a for a in (j.get("activities") or []) if a in ACTIVITY_LIST],
            [s for s in (j.get("spatial") or []) if s in SPATIAL_LIST],
        )
    except Exception as e:
        gr.Warning(f"AI 응답 파싱 실패: {str(e)[:80]}")
        return (gr.update(),) * 6


_MAT_COLORS = {
    "Wood": (140, 90, 60), "Concrete": (140, 140, 130), "Glass": (150, 190, 200),
    "Fabric": (180, 155, 115), "Metal": (150, 150, 155), "Stone": (140, 120, 100), "Brick": (180, 80, 55),
}

def gemini_vision_tags(img):
    if img is None or not HAS_PIL or not GEMINI_KEY:
        return {}
    try:
        buf = BytesIO()
        img.convert("RGB").resize((512, 512)).save(buf, format="JPEG", quality=80)
        b64img = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return {}
    prompt = (
        "이 인테리어 참고 이미지를 분석해서 보이는 요소를 분류하세요. "
        "순수 JSON으로만 응답.\n"
        f"materials (배열, 보이는 재료 모두): {MATERIAL_LIST}\n"
        f"lighting (배열): {LIGHTING_LIST}\n"
        f"mood (택1 문자열): {MOOD_LIST}\n"
        f"spatial (배열): {SPATIAL_LIST}\n"
        "형식: {\"materials\":[],\"lighting\":[],\"mood\":\"\",\"spatial\":[]}"
    )
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.5-flash:generateContent?key={GEMINI_KEY}")
    body = json.dumps({
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": b64img}},
            {"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "temperature": 0.3, "maxOutputTokens": 400}
    }).encode("utf-8")
    req = _urlreq.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with _urlreq.urlopen(req, timeout=25) as r:
            data = json.loads(r.read().decode("utf-8"))
        txt = data["candidates"][0]["content"]["parts"][0]["text"]
        m = re.search(r"\{[\s\S]*\}", txt)
        return json.loads(m.group(0) if m else txt)
    except Exception as e:
        print(f"[Gemini Vision] {e}")
        return {}


def suggest_materials_from_image(img, cur_mat, cur_light, cur_mood, cur_spatial):
    if img is None or not HAS_PIL:
        return cur_mat, cur_light, cur_mood, cur_spatial
    j = gemini_vision_tags(img) if GEMINI_KEY else {}
    if j:
        mats   = [m for m in (j.get("materials") or []) if m in MATERIAL_LIST]
        lights = [l for l in (j.get("lighting")  or []) if l in LIGHTING_LIST]
        spat   = [s for s in (j.get("spatial")   or []) if s in SPATIAL_LIST]
        mood   = j.get("mood") if j.get("mood") in MOOD_LIST else cur_mood
        gr.Info(f"AI 비전 태깅: {', '.join(mats[:3]) or '재료없음'} · {mood}")
        merged_mat = list(dict.fromkeys(mats + list(cur_mat or [])))[:5]
        merged_light = list(dict.fromkeys(lights + list(cur_light or [])))[:4]
        merged_spat = list(dict.fromkeys(spat + list(cur_spatial or [])))[:4]
        return merged_mat, merged_light, mood, merged_spat
    try:
        small = img.resize((20, 20)).convert("RGB")
        pixels = list(small.getdata())
        avg = tuple(sum(p[i] for p in pixels) // len(pixels) for i in range(3))
        ranked = sorted(_MAT_COLORS.items(), key=lambda kv: sum((avg[i]-kv[1][i])**2 for i in range(3)))
        top2 = [ranked[0][0], ranked[1][0]]
        return list(dict.fromkeys(top2 + list(cur_mat or [])))[:4], cur_light, cur_mood, cur_spatial
    except Exception:
        return cur_mat, cur_light, cur_mood, cur_spatial


def export_board_html(board_html):
    if not board_html or "Material Palette" not in board_html:
        gr.Warning("Generate a concept board first.")
        return gr.update(visible=False)
    png_btn = (
        "<div style='text-align:center;margin:20px 0;'>"
        "<button onclick=\"(function(){"
        "var s=document.createElement('script');"
        "s.src='https://html2canvas.hertzen.com/dist/html2canvas.min.js';"
        "s.onload=function(){"
        "html2canvas(document.querySelector('.board-export'),{scale:2,useCORS:true}).then(function(c){"
        "var a=document.createElement('a');a.download='concept-board.png';"
        "a.href=c.toDataURL('image/png');a.click();});};"
        "document.head.appendChild(s);}())\" "
        "style='padding:10px 28px;background:#C57B57;color:#fff;border:none;border-radius:8px;"
        "font-size:13px;font-weight:600;cursor:pointer;letter-spacing:0.5px;'>⬇ Download as PNG</button></div>"
    )
    wrapped = f'<div class="board-export">{board_html}</div>'
    html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>AI Interior Concept Board</title>"
            f"<style>body{{margin:0;padding:20px;background:#F7F3EA;"
            f"font-family:'Helvetica Neue',Arial,sans-serif;}}</style>"
            f"</head><body>{png_btn}{wrapped}</body></html>")
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(html)
    tmp.close()
    return gr.update(visible=True, value=tmp.name)


def add_to_history(history, space, mood, board, main_p, mat_p, atmo_p, tags, ko):
    entry = {"key": f"{space} · {mood} — {time.strftime('%H:%M')}",
             "board": board, "main": main_p, "mat": mat_p,
             "atmo": atmo_p, "tags": tags, "ko": ko}
    return ([entry] + history)[:5]


def load_history_entry(history, key):
    for e in history:
        if e["key"] == key:
            return e["board"], e["main"], e["mat"], e["atmo"], e["tags"], e["ko"]
    return (gr.update(),) * 6


def history_choices(history):
    return gr.update(choices=[e["key"] for e in history], value=None)


CSS = """
:root {
    --cream: #F7F2E8;
    --ivory: #FFFDF7;
    --border: #DDD5C5;
    --brown: #2E2418;
    --muted: #7A7268;
    --terra: #C57B57;
    --olive: #4E7040;
    --olive-light: #6B8A5E;
}
body, .gradio-container { background: var(--cream) !important; font-family: 'Helvetica Neue', Arial, sans-serif !important; }
.gradio-container { max-width: 1280px !important; margin: 0 auto !important; }
footer { display: none !important; }
.contain, .gap, .panel { background: transparent !important; }

/* ── Panels ─────────────────────────────────────────────── */
.left-panel > .block, .left-panel .form { background: var(--ivory) !important; }
.left-panel { background: var(--ivory) !important; border-right: 1px solid var(--border) !important; padding: 0 !important; }

/* ── Block containers ───────────────────────────────────── */
.block, .form {
    background: var(--ivory) !important; border: 1px solid var(--border) !important;
    border-radius: 12px !important; box-shadow: 0 1px 6px rgba(38,50,56,0.04) !important;
}

/* ── Labels ─────────────────────────────────────────────── */
.block .label-wrap > span, label > span, .block label > span, fieldset legend,
.block > label, .form > label, .block label, .wrap label {
    font-size: 10px !important; font-weight: 700 !important; letter-spacing: 2px !important;
    text-transform: uppercase !important; color: #3C3428 !important;
}

/* ── Inputs ─────────────────────────────────────────────── */
textarea, input[type="text"], input[type="number"] {
    background: var(--ivory) !important; border: 1px solid #D0C8BA !important;
    color: var(--brown) !important; border-radius: 8px !important;
    font-size: 13px !important; line-height: 1.7 !important;
}
textarea:focus, input[type="text"]:focus, input[type="number"]:focus {
    border-color: var(--terra) !important; outline: none !important;
    box-shadow: 0 0 0 3px rgba(197,123,87,0.13) !important;
}
textarea::placeholder, input::placeholder { color: #B8B0A3 !important; font-style: italic !important; }
.wrap-inner, .multiselect, .wrap { background: var(--ivory) !important; border-color: #D0C8BA !important; color: var(--brown) !important; }
.token { background: #EDE8DF !important; border: 1px solid #D0C8BA !important; color: var(--brown) !important; }
.list-items, .options { background: var(--ivory) !important; border: 1px solid #D0C8BA !important; border-radius: 8px !important; box-shadow: 0 4px 18px rgba(38,50,56,0.10) !important; }
.item, .list-items li { color: var(--brown) !important; font-size: 13px !important; }
.item:hover, .item.selected, .list-items li:hover { background: #F0EAE0 !important; }

/* ── Checkbox pills ─────────────────────────────────────── */
.checkbox-group { gap: 5px !important; flex-wrap: wrap !important; padding: 4px 0 6px !important; }
label.checkbox-label, .checkbox-label {
    background: #F2ECE3 !important; border: 1.5px solid #C8BCAC !important; border-radius: 20px !important;
    padding: 5px 13px !important; color: var(--brown) !important; font-size: 12px !important;
    font-weight: 500 !important; cursor: pointer !important;
    transition: background 0.12s, border-color 0.12s, color 0.12s !important;
    line-height: 1.5 !important; margin: 2px 1px !important; white-space: nowrap !important;
    user-select: none !important; display: inline-flex !important; align-items: center !important;
}
label.checkbox-label span, .checkbox-label span { color: var(--brown) !important; }
label.checkbox-label:hover, .checkbox-label:hover { background: #E4EED8 !important; border-color: #7A9868 !important; }
label.checkbox-label:has(input[type="checkbox"]:checked), .checkbox-label:has(input[type="checkbox"]:checked) {
    background: var(--olive) !important; border-color: #3C5C30 !important; color: #FFFFFF !important; font-weight: 700 !important;
}
label.checkbox-label:has(input[type="checkbox"]:checked) span,
.checkbox-label:has(input[type="checkbox"]:checked) span { color: #FFFFFF !important; }
label.checkbox-label input[type="checkbox"], .checkbox-label input[type="checkbox"] {
    appearance: none !important; -webkit-appearance: none !important;
    width: 0 !important; height: 0 !important; margin: 0 !important; padding: 0 !important;
    border: none !important; opacity: 0 !important; pointer-events: none !important; position: absolute !important;
}

/* ── Sliders ─────────────────────────────────────────────── */
input[type="range"] { accent-color: var(--olive-light) !important; }

/* ── Buttons ─────────────────────────────────────────────── */
button.primary, .btn-primary {
    background: var(--terra) !important; background-image: none !important; color: var(--ivory) !important;
    border: none !important; border-radius: 10px !important; font-size: 14px !important;
    font-weight: 700 !important; letter-spacing: 0.5px !important;
    box-shadow: 0 3px 12px rgba(197,123,87,0.30) !important;
    transition: background 0.2s, box-shadow 0.2s, transform 0.15s !important;
}
button.primary:hover { background: #A86540 !important; box-shadow: 0 5px 18px rgba(197,123,87,0.40) !important; transform: translateY(-1px) !important; }
button.secondary {
    background: var(--ivory) !important; border: 1.5px solid #D0C8BA !important; color: #4A4038 !important;
    border-radius: 10px !important; font-size: 13px !important; font-weight: 500 !important;
}
button.secondary:hover { background: #F0E8DC !important; border-color: #B0A898 !important; }

/* ── Status ─────────────────────────────────────────────── */
.status-msg .prose p { color: var(--olive) !important; font-weight: 600 !important; margin: 0 !important; font-size: 12px !important; }

/* ── Example cards ──────────────────────────────────────── */
.example-card { flex: 1 !important; min-width: 0 !important; }
.example-card > .wrap, .example-card > div { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
.example-card button {
    width: 100% !important; background: var(--ivory) !important; border: 1.5px solid var(--border) !important;
    border-radius: 10px !important; color: #2A2218 !important; font-size: 12px !important;
    font-weight: 600 !important; padding: 11px 14px !important; min-height: 44px !important;
    height: auto !important; text-align: left !important; white-space: normal !important;
    line-height: 1.45 !important; box-shadow: 0 1px 4px rgba(38,50,56,0.05) !important;
    transition: all 0.15s ease !important; cursor: pointer !important; margin-bottom: 6px !important;
}
.example-card button:hover { background: #FDF5EE !important; border-color: var(--terra) !important; color: #6B2E08 !important; box-shadow: 0 3px 12px rgba(197,123,87,0.15) !important; }

/* ── Tabs ───────────────────────────────────────────────── */
.tabs { border: none !important; background: transparent !important; }
.tab-nav { background: transparent !important; border-bottom: 1.5px solid var(--border) !important; padding: 0 !important; }
.tab-nav button { background: transparent !important; border: none !important; border-bottom: 3px solid transparent !important; border-radius: 0 !important; color: var(--muted) !important; font-size: 13px !important; font-weight: 500 !important; padding: 12px 22px !important; margin: 0 !important; }
.tab-nav button:hover { color: var(--brown) !important; }
.tab-nav button.selected { color: var(--brown) !important; font-weight: 700 !important; border-bottom-color: var(--terra) !important; }
.tabitem { background: transparent !important; border: none !important; padding: 18px 0 0 !important; }

/* ── Upload section ─────────────────────────────────────── */
.upload-section-header { margin-bottom: 12px !important; }

/* ── Image gen settings card ────────────────────────────── */
.gen-settings .block { background: #F5EFE6 !important; border-color: #DDD3C0 !important; }

/* ── Markdown ───────────────────────────────────────────── */
.prose, .md { color: var(--brown) !important; }
.prose p { color: #2A2620 !important; line-height: 1.95 !important; }
.prose em { color: var(--muted) !important; }

/* ── Scrollbar ──────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--cream); }
::-webkit-scrollbar-thumb { background: #D0C8BA; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #B8B0A3; }
"""

HEADER_HTML = """
<div style="display:flex;align-items:flex-end;justify-content:space-between;
            padding:24px 32px 20px;margin-bottom:0;
            background:#FFFDF7;border:1px solid #DDD5C5;border-radius:14px 14px 0 0;
            border-bottom:none;">
  <div>
    <p style="font-size:8px;letter-spacing:5px;text-transform:uppercase;
              color:#A09888;margin:0 0 6px;font-weight:700;
              font-family:'Helvetica Neue',Arial,sans-serif;">Interior Design Studio</p>
    <h1 style="font-size:26px;font-weight:300;letter-spacing:0.3px;
               color:#1E1A14;margin:0;font-family:'Georgia','Times New Roman',serif;
               line-height:1.2;">
      AI Concept Board <em style="font-style:italic;color:#7A7268;">Generator</em>
    </h1>
  </div>
  <div style="text-align:right;">
    <p style="font-size:11px;color:#9A9288;margin:0;line-height:1.8;
              font-family:'Helvetica Neue',Arial,sans-serif;">
      Space &amp; mood → Generate → 3 image prompts<br>
      <span style="color:#C57B57;">✶ AI-powered concept board</span>
    </p>
  </div>
</div>
<div style="height:3px;background:linear-gradient(90deg,#C57B57 0%,#D4A574 40%,#6B8A5E 100%);
            margin-bottom:20px;border-radius:0 0 4px 4px;border:1px solid #DDD5C5;border-top:none;"></div>
"""


def _section_header(title: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;gap:12px;margin:16px 0 10px;">'
        f'<span style="font-size:9px;font-weight:700;letter-spacing:2.5px;'
        f'text-transform:uppercase;color:#8A8278;white-space:nowrap;">{title}</span>'
        f'<div style="flex:1;height:1px;background:#E4DDD4;border-radius:1px;"></div>'
        f'</div>'
    )


def _col_header(number: str, title: str) -> str:
    return (
        f'<p style="font-size:10px;font-weight:700;letter-spacing:2.5px;'
        f'text-transform:uppercase;color:#3C3428;margin:0 0 16px;'
        f'padding-bottom:10px;border-bottom:1px solid #E4DDD4;">'
        f'<span style="color:#C57B57;margin-right:6px;">{number}</span>{title}</p>'
    )


BOARD_PLACEHOLDER = """
<div style="font-family:'Helvetica Neue',Arial,sans-serif;background:linear-gradient(160deg,#F9F5ED,#F2EBE0);
            padding:72px 40px;border-radius:14px;border:1.5px dashed #D0C8BA;
            text-align:center;color:#8A8278;min-height:340px;display:flex;flex-direction:column;
            align-items:center;justify-content:center;">
  <p style="font-size:8px;letter-spacing:5px;text-transform:uppercase;
            margin:0 0 24px;font-weight:700;color:#C0B8B0;font-family:'Helvetica Neue',sans-serif;">
    Interior Concept Board
  </p>
  <div style="font-size:48px;margin-bottom:24px;opacity:0.35;">🏛</div>
  <p style="font-size:16px;font-family:'Georgia',serif;font-weight:300;
            color:#9A9288;line-height:2.1;margin:0 0 8px;">
    Configure your space parameters, then click
  </p>
  <p style="font-size:18px;font-family:'Georgia',serif;font-weight:400;color:#C57B57;margin:0;">
    Generate Concept ✶
  </p>
</div>
"""

PRESET_EXAMPLES = [
    {"label": "📚  Creative Library Lounge", "sub": "Wood · Fabric · Layered · Cozy",
     "data": ("Library", ["Reading", "Creative", "Social"], ["Wood", "Fabric", "Stone"],
              ["Warm", "Indirect"], "Cozy", ["Layered", "High Ceiling"],
              "Warm oak shelving, reading alcove nooks, biophilic wall")},
    {"label": "🌿  Calm Reading Room", "sub": "Wood · Stone · Natural Light · Calm",
     "data": ("Library", ["Reading", "Rest"], ["Wood", "Stone"],
              ["Natural Light", "Diffused"], "Calm", ["Compact", "Enclosed"],
              "calm reading space, natural light, oak shelving")},
    {"label": "🔮  Futuristic Gallery Space", "sub": "Glass · Metal · Concrete · Dramatic",
     "data": ("Gallery", ["Exhibition", "Creative"], ["Glass", "Metal", "Concrete"],
              ["Dramatic", "Accent Lighting"], "Futuristic", ["Open", "High Ceiling"],
              "sleek surfaces, exhibition lighting, sculptural installation")},
]

SPACE_LIST    = list(SPACE_TYPES.keys())
ACTIVITY_LIST = list(ACTIVITY_DATA.keys())
MATERIAL_LIST = list(MATERIAL_DATA.keys())
LIGHTING_LIST = list(LIGHTING_DATA.keys())
MOOD_LIST     = list(MOOD_DATA.keys())
SPATIAL_LIST  = list(SPATIAL_DATA.keys())
SIZE_LIST     = ["768x768", "1024x768", "768x1024", "512x512", "1024x1024"]

with gr.Blocks(
    title="AI Interior Concept Board",
    theme=gr.themes.Base(
        primary_hue=gr.themes.colors.orange,
        neutral_hue=gr.themes.colors.stone,
        font=gr.themes.GoogleFont("Inter"),
    ).set(
        checkbox_label_background_fill="#EDE8DF",
        checkbox_label_background_fill_hover="#E4EED8",
        checkbox_label_background_fill_selected="#4E7040",
        checkbox_label_text_color="#1E1A14",
        checkbox_label_text_color_selected="#FFFFFF",
        checkbox_label_border_color="#C8BCAC",
        checkbox_label_border_color_hover="#7A9868",
        checkbox_label_border_color_selected="#3C5C30",
        body_text_color="#1E1A14",
        body_text_color_subdued="#5A5248",
    ),
    css=CSS,
) as demo:

    gr.HTML(HEADER_HTML)

    with gr.Row(equal_height=False):

        # ── LEFT SIDEBAR ────────────────────────────────────────
        with gr.Column(scale=1, min_width=300, elem_classes=["left-panel"]):

            gr.HTML(_section_header("01 · Space & Mood"))
            space_in = gr.Dropdown(choices=SPACE_LIST, value="Library", label="Space Type",
                                   allow_custom_value=True, info="Select or type a custom space")
            mood_in  = gr.Dropdown(choices=MOOD_LIST, value="Calm", label="Mood")

            gr.HTML(_section_header("02 · Concept Prompt"))
            extra_in = gr.Textbox(label="Custom Keywords / Natural Description",
                                   placeholder="예: 따뜻한 우드 톤의 조용한 도서관, 바이오필릭 요소", lines=3)
            with gr.Row():
                ai_btn = gr.Button("✨ AI 자동입력", variant="secondary", min_width=120)

            gr.HTML(_section_header("03 · Generate"))
            gen_btn   = gr.Button("Generate Concept  ✶", variant="primary", size="lg")
            with gr.Row():
                reset_btn = gr.Button("↺ Reset", variant="secondary", min_width=90)
            status_out = gr.Markdown(value="", elem_classes=["status-msg"])

            gr.HTML(_section_header("04 · Image Generation"))
            gr.HTML('<p style="font-size:11px;color:#9A9288;margin:-4px 0 10px;line-height:1.6;">Connect to ComfyUI to generate images via FLUX</p>')
            with gr.Row():
                use_external_in = gr.Checkbox(label="Enable", value=True, scale=1)
                external_url_in = gr.Textbox(label="Server URL", placeholder="http://127.0.0.1:8188", scale=3)
            neg_prompt_in = gr.Textbox(label="Negative Prompt", lines=2,
                                        placeholder="blurry, low quality, people, text")
            with gr.Group(elem_classes=["gen-settings"]):
                with gr.Row():
                    steps_in   = gr.Slider(1, 100, step=1,   value=20,  label="Steps")
                    cfg_in     = gr.Slider(1, 20,  step=0.5, value=1.0, label="CFG")
                with gr.Row():
                    imgsize_in = gr.Dropdown(choices=SIZE_LIST, value="768x768", label="Size")
                    seed_in    = gr.Number(value=-1, label="Seed", precision=0)

            gr.HTML(_section_header("05 · Examples"))
            preset_btns = []
            for preset in PRESET_EXAMPLES:
                btn = gr.Button(f"{preset['label']}  {preset['sub']}",
                                elem_classes=["example-card"], size="sm")
                preset_btns.append((btn, preset["data"]))

            gr.HTML(_section_header("06 · History"))
            history_state = gr.State([])
            concept_state = gr.State("")
            history_dd = gr.Dropdown(label="Recent Generations", choices=[], interactive=True)

        # ── RIGHT MAIN PANEL ─────────────────────────────────────
        with gr.Column(scale=2, elem_classes=["right-panel"]):

            gr.HTML(_section_header("Design Parameters"))
            with gr.Row():
                activity_in = gr.CheckboxGroup(choices=ACTIVITY_LIST, label="UX / Activity", scale=1)
                material_in = gr.CheckboxGroup(choices=MATERIAL_LIST, label="Material Palette", scale=1)
            with gr.Row():
                lighting_in = gr.CheckboxGroup(choices=LIGHTING_LIST, label="Lighting", scale=1)
                spatial_in  = gr.CheckboxGroup(choices=SPATIAL_LIST,  label="Spatial Quality", scale=1)

            with gr.Tabs(selected=0) as results_tabs:

                with gr.TabItem("🎨  Concept Board", id=0):
                    with gr.Accordion("📎 Reference Images (optional)", open=False):
                        gr.HTML('<p style="font-size:12px;color:#7A7268;margin:0 0 12px;line-height:1.7;">Upload reference photos — leave empty to auto-generate via AI. Each slot has a role: <strong>Main view</strong>, <strong>Material detail</strong>, <strong>Atmosphere</strong>.</p>')
                        with gr.Row():
                            upload_main_in       = gr.Image(
                                label="Slot 1 · Main View",
                                type="pil", height=140)
                            upload_material_in   = gr.Image(
                                label="Slot 2 · Material Detail",
                                type="pil", height=140)
                            upload_atmosphere_in = gr.Image(
                                label="Slot 3 · Atmosphere",
                                type="pil", height=140)

                    board_out = gr.HTML(value=BOARD_PLACEHOLDER)

                    gr.HTML('<div style="height:1px;background:#DDD5C5;margin:16px 0 14px;"></div>')
                    with gr.Row():
                        export_btn  = gr.Button("⬇  Export as HTML + PNG", variant="secondary")
                        export_file = gr.File(label="Download", visible=False, scale=2)

                with gr.TabItem("📝  Prompts", id=1):
                    main_prompt_out     = gr.Textbox(label="Slot 1 — Main Concept",      lines=3)
                    material_prompt_out = gr.Textbox(label="Slot 2 — Material / Detail", lines=3)
                    atmo_prompt_out     = gr.Textbox(label="Slot 3 — Atmosphere",        lines=3)

                with gr.TabItem("🏷️  Tags & Statement", id=2):
                    tags_out   = gr.Textbox(label="Hashtags", lines=3)
                    korean_out = gr.Markdown(value="*Concept statement will appear after Generate.*")

    inputs = [
        space_in, activity_in, material_in, lighting_in,
        mood_in, spatial_in, extra_in,
        upload_main_in, upload_material_in, upload_atmosphere_in,
        use_external_in, external_url_in, neg_prompt_in,
        steps_in, cfg_in, imgsize_in, seed_in,
    ]
    outputs = [main_prompt_out, material_prompt_out, atmo_prompt_out,
               tags_out, korean_out, board_out, status_out]
    hist_inputs = [history_state, space_in, mood_in, board_out,
                   main_prompt_out, material_prompt_out, atmo_prompt_out, tags_out, concept_state]

    def _sync_concept(txt): return txt

    # Generate button
    (gen_btn.click(fn=generate_concept, inputs=inputs, outputs=outputs)
            .then(fn=lambda: gr.update(selected=0), inputs=[], outputs=[results_tabs])
            .then(fn=_sync_concept, inputs=[korean_out], outputs=[concept_state])
            .then(fn=add_to_history, inputs=hist_inputs, outputs=[history_state])
            .then(fn=history_choices, inputs=[history_state], outputs=[history_dd]))

    # Enter key
    (extra_in.submit(fn=generate_concept, inputs=inputs, outputs=outputs)
             .then(fn=lambda: gr.update(selected=0), inputs=[], outputs=[results_tabs])
             .then(fn=_sync_concept, inputs=[korean_out], outputs=[concept_state])
             .then(fn=add_to_history, inputs=hist_inputs, outputs=[history_state])
             .then(fn=history_choices, inputs=[history_state], outputs=[history_dd]))

    # Reset
    reset_btn.click(fn=reset_inputs, inputs=[],
                    outputs=[space_in, activity_in, material_in, lighting_in,
                             mood_in, spatial_in, extra_in,
                             upload_main_in, upload_material_in, upload_atmosphere_in])

    # AI 자동입력
    ai_btn.click(fn=ai_autofill, inputs=[extra_in],
                 outputs=[space_in, mood_in, material_in, lighting_in, activity_in, spatial_in])

    # Preset cards
    preset_outputs = [space_in, activity_in, material_in, lighting_in, mood_in, spatial_in, extra_in]
    for btn, data in preset_btns:
        (btn.click(fn=lambda d=data: d, inputs=[], outputs=preset_outputs)
            .then(fn=generate_concept, inputs=inputs, outputs=outputs)
            .then(fn=lambda: gr.update(selected=0), inputs=[], outputs=[results_tabs])
            .then(fn=_sync_concept, inputs=[korean_out], outputs=[concept_state])
            .then(fn=add_to_history, inputs=hist_inputs, outputs=[history_state])
            .then(fn=history_choices, inputs=[history_state], outputs=[history_dd]))

    # Image upload → Gemini Vision auto-tagging (materials, lighting, mood, spatial)
    for img_in in [upload_main_in, upload_material_in, upload_atmosphere_in]:
        img_in.change(fn=suggest_materials_from_image,
                      inputs=[img_in, material_in, lighting_in, mood_in, spatial_in],
                      outputs=[material_in, lighting_in, mood_in, spatial_in])

    # History restore — also update concept_state so statement is recoverable
    history_dd.change(fn=load_history_entry, inputs=[history_state, history_dd],
                      outputs=[board_out, main_prompt_out, material_prompt_out,
                               atmo_prompt_out, tags_out, korean_out])

    # Export
    export_btn.click(fn=export_board_html, inputs=[board_out], outputs=[export_file])


FORCE_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet">
<style>
/* ── Base font ─────────────────────────────────────────── */
.gradio-container, .gradio-container * {
    font-family: 'DM Sans', 'Helvetica Neue', Arial, sans-serif !important;
}

/* ── Page background ────────────────────────────────────── */
body, .gradio-container, .main, footer { background: #F5F0E8 !important; }

/* ── All labels & headings ──────────────────────────────── */
.gradio-container label, .gradio-container .label-wrap,
.gradio-container .label-wrap span, .gradio-container .block-label,
.gradio-container fieldset legend,
.gradio-container span[data-testid="block-label"],
.gradio-container [class*="block_label"], .gradio-container [class*="block-label"],
.gradio-container h1, .gradio-container h2, .gradio-container h3,
.gradio-container h4, .gradio-container h5 {
    color: #2E2820 !important; background: transparent !important;
    font-weight: 600 !important; opacity: 1 !important;
    letter-spacing: 0.2px !important;
}

/* ── Block group containers ─────────────────────────────── */
.gradio-container .block, .gradio-container .form,
.gradio-container fieldset {
    background: #FFFCF5 !important;
    border: 1px solid #E0D8CC !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 4px rgba(60,50,40,0.06) !important;
}

/* ── Block/group field labels ───────────────────────────── */
.gradio-container .block-info, .gradio-container .info,
.gradio-container .form > label, .gradio-container .form > label > span,
.gradio-container .block > .label-wrap, .gradio-container legend,
.gradio-container [class*="head"] > span {
    color: #2E2820 !important; font-weight: 700 !important;
    font-size: 11px !important; letter-spacing: 1px !important;
    text-transform: uppercase !important; opacity: 1 !important;
}

/* ── Checkbox pills ─────────────────────────────────────── */
.gradio-container label.checkbox-label, .gradio-container .checkbox-label,
.gradio-container label[class*="checkbox"], .gradio-container .wrap label,
.gradio-container fieldset label {
    background: #EDE7DC !important; background-color: #EDE7DC !important;
    color: #2E2820 !important; border: 1.5px solid #C8BCAA !important;
    border-radius: 20px !important; padding: 5px 14px !important;
    font-size: 12px !important; font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
.gradio-container label.checkbox-label *, .gradio-container .checkbox-label *,
.gradio-container fieldset label *, .gradio-container label[class*="checkbox"] * {
    color: #2E2820 !important;
}
.gradio-container label.checkbox-label:hover, .gradio-container .checkbox-label:hover,
.gradio-container fieldset label:hover {
    background: #DFF0D2 !important; background-color: #DFF0D2 !important;
    border-color: #7A9868 !important;
}
.gradio-container label.checkbox-label:has(input:checked),
.gradio-container .checkbox-label:has(input:checked),
.gradio-container fieldset label:has(input:checked),
.gradio-container label[class*="checkbox"]:has(input:checked) {
    background: #4E7040 !important; background-color: #4E7040 !important;
    border-color: #3A5830 !important; color: #FFFFFF !important;
    box-shadow: 0 2px 6px rgba(78,112,64,0.3) !important;
}
.gradio-container label.checkbox-label:has(input:checked) *,
.gradio-container .checkbox-label:has(input:checked) *,
.gradio-container fieldset label:has(input:checked) *,
.gradio-container label[class*="checkbox"]:has(input:checked) * { color: #FFFFFF !important; }

/* ── Inputs / Textareas ─────────────────────────────────── */
.gradio-container input, .gradio-container textarea, .gradio-container select,
.gradio-container .wrap-inner {
    background: #FFFCF5 !important; color: #2E2820 !important;
    border-color: #D0C8B8 !important; border-radius: 8px !important;
    font-size: 13px !important;
}
.gradio-container input::placeholder, .gradio-container textarea::placeholder {
    color: #A09888 !important;
}
.gradio-container input:focus, .gradio-container textarea:focus {
    border-color: #C57B57 !important;
    box-shadow: 0 0 0 3px rgba(197,123,87,0.12) !important;
    outline: none !important;
}

/* ── Dropdown / select ──────────────────────────────────── */
.gradio-container .wrap, .gradio-container [class*="dropdown"] {
    background: #FFFCF5 !important; color: #2E2820 !important;
    border-color: #D0C8B8 !important;
}
.gradio-container [class*="option"]:hover, .gradio-container [class*="item"]:hover {
    background: #F0EBE0 !important;
}

/* ── Tabs ───────────────────────────────────────────────── */
.gradio-container button[role="tab"] {
    color: #7A7268 !important; background: transparent !important;
    font-weight: 500 !important; font-size: 13px !important;
    letter-spacing: 0.3px !important; padding: 8px 16px !important;
    border-radius: 0 !important;
}
.gradio-container button[role="tab"][aria-selected="true"] {
    color: #C57B57 !important;
    border-bottom: 2px solid #C57B57 !important;
    font-weight: 600 !important;
}
.gradio-container [role="tablist"] {
    border-bottom: 1px solid #DDD5C5 !important;
}

/* ── Primary / Secondary buttons ───────────────────────── */
.gradio-container button.primary, .gradio-container button[class*="primary"],
.gradio-container button[variant="primary"] {
    background: linear-gradient(135deg, #C57B57, #A86040) !important;
    color: #FFFFFF !important; border: none !important;
    border-radius: 10px !important; font-weight: 600 !important;
    font-size: 13px !important; letter-spacing: 0.4px !important;
    box-shadow: 0 3px 10px rgba(197,123,87,0.35) !important;
    transition: all 0.2s ease !important;
}
.gradio-container button.primary:hover, .gradio-container button[class*="primary"]:hover {
    background: linear-gradient(135deg, #D48A64, #C57B57) !important;
    box-shadow: 0 5px 14px rgba(197,123,87,0.45) !important;
    transform: translateY(-1px) !important;
}
.gradio-container button.secondary, .gradio-container button[class*="secondary"] {
    background: #FFFCF5 !important; color: #4A4038 !important;
    border: 1.5px solid #D0C8B8 !important; border-radius: 10px !important;
    font-weight: 500 !important; font-size: 13px !important;
}
.gradio-container button.secondary:hover {
    background: #F0EBE0 !important; border-color: #C8B89A !important;
}

/* ── Slider ─────────────────────────────────────────────── */
.gradio-container input[type="range"] { accent-color: #C57B57 !important; }
.gradio-container .range-slider [class*="fill"] { background: #C57B57 !important; }

/* ── Markdown ───────────────────────────────────────────── */
.gradio-container .prose strong, .gradio-container strong,
.gradio-container .markdown strong, .gradio-container [class*="markdown"] strong {
    background: transparent !important; background-color: transparent !important;
    color: #C57B57 !important; font-weight: 700 !important;
    padding: 0 !important; box-shadow: none !important;
}
.gradio-container .prose, .gradio-container .prose p,
.gradio-container [class*="markdown"] p {
    color: #2E2820 !important; line-height: 1.7 !important;
}
.gradio-container .prose em, .gradio-container em {
    font-family: 'DM Serif Display', Georgia, serif !important;
    color: #6B5A48 !important;
}

/* ── Scrollbar ──────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F0EBE0; }
::-webkit-scrollbar-thumb { background: #C8B89A; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #A89878; }

/* ── Upload zones ───────────────────────────────────────── */
.gradio-container [data-testid="image"] {
    background: #FFFCF5 !important; border: 1.5px dashed #C8BCAA !important;
    border-radius: 12px !important;
}

/* ── Accordion / Collapsible ────────────────────────────── */
.gradio-container .block.accordion, .gradio-container details {
    border-radius: 10px !important;
}
</style>"""

if __name__ == "__main__":
    demo.launch(head=FORCE_CSS, server_name="127.0.0.1", server_port=7861)
