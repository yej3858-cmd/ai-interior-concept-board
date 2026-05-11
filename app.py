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
    return f"https://image.pollinations.ai/prompt/{p}?width={w}&height={h}&nologo=true&seed={seed}"

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

def gemini_call(prompt: str, want_json: bool = False, timeout: int = 25) -> str:
    if not GEMINI_KEY:
        return ""
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.5-flash:generateContent?key={GEMINI_KEY}")
    cfg = {"temperature": 0.85, "maxOutputTokens": 800}
    if want_json:
        cfg["responseMimeType"] = "application/json"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": cfg}).encode("utf-8")
    req = _urlreq.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with _urlreq.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[Gemini] {e}")
        return ""


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
    "Library": {"ko": "독서관", "en_char": "knowledge-rich, contemplative, archival",
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
    "Wood":     "https://images.unsplash.com/photo-1518605380956-de1ab1d8c3e2?w=400&h=400&fit=crop",
    "Concrete": "https://images.unsplash.com/photo-1517502884422-41eaead166d4?w=400&h=400&fit=crop",
    "Glass":    "https://images.unsplash.com/photo-1497366754035-f200968a6e72?w=400&h=400&fit=crop",
    "Fabric":   "https://images.unsplash.com/photo-1620735692151-26a7e0748429?w=400&h=400&fit=crop",
    "Metal":    "https://images.unsplash.com/photo-1535557597501-0fee0a500c57?w=400&h=400&fit=crop",
    "Stone":    "https://images.unsplash.com/photo-1604147495798-57beb5d6af73?w=400&h=400&fit=crop",
    "Brick":    "https://images.unsplash.com/photo-1505765050516-f72dcac9c60e?w=400&h=400&fit=crop",
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
        bg = f'background:#EDE8DF url({photo}) center/cover no-repeat;'
        label_color = "#FFFDF7"
        overlay = '<div style="position:absolute;inset:0;background:linear-gradient(transparent 50%,rgba(20,18,14,0.55));"></div>'
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
        bg_css = f'background:#EDE8DF url({photo}) center/cover no-repeat;'
    else:
        bg_css = f'background:linear-gradient(150deg,{d["hex"]},{d["light"]});'
    return (
        f'<div style="flex:1;min-width:78px;">'
        f'<div style="height:60px;{bg_css}'
        f'border-radius:7px;margin-bottom:6px;position:relative;border:1px solid rgba(0,0,0,0.1);'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
        f'<span style="position:absolute;bottom:4px;left:6px;right:6px;font-size:8px;font-weight:700;'
        f'letter-spacing:1px;text-transform:uppercase;color:#FFFDF7;'
        f'text-shadow:0 1px 2px rgba(0,0,0,0.7);">{name.upper()}</span></div>'
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
<div style="font-family:'Helvetica Neue',Arial,sans-serif;background:#F7F3EA;
            padding:40px;border-radius:14px;max-width:900px;margin:0 auto;
            box-sizing:border-box;color:#263238;border:1px solid #D8D0C3;
            box-shadow:0 2px 20px rgba(38,50,56,0.06);">
  {warning_banner}
  <div style="margin-bottom:30px;padding-bottom:22px;border-bottom:1px solid #D8D0C3;">
    <p style="font-size:9px;letter-spacing:4px;text-transform:uppercase;
              color:#9A9288;margin:0 0 12px;font-weight:600;">
      Interior Concept Board &nbsp;·&nbsp; {space or 'Interior Space'}
    </p>
    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:8px;">
      <h1 style="font-size:28px;font-weight:300;letter-spacing:0.5px;margin:0;
                 color:#263238;font-family:'Georgia','Times New Roman',serif;">{sp['ko']}</h1>
      <span style="display:inline-block;width:1px;height:22px;background:#D8D0C3;"></span>
      <span style="font-size:14px;color:#6F6A60;font-weight:400;">{mood_label}</span>
    </div>
    <p style="font-size:12px;color:#6F6A60;margin:0;line-height:1.7;">
      {sp['en_char'].replace(',', ' &nbsp;·&nbsp;')}
    </p>
    <div style="width:32px;height:2px;background:{accent};border-radius:1px;margin-top:16px;"></div>
  </div>
  <div style="position:relative;height:340px;margin-bottom:28px;padding:14px 6px;">
    <div style="position:absolute;left:2%;top:6px;width:54%;height:308px;transform:rotate(-1.6deg);
                box-shadow:0 6px 20px rgba(38,50,56,0.18);">
      <div style="position:absolute;top:-10px;left:48%;width:60px;height:18px;background:rgba(240,228,200,0.85);
                  transform:rotate(-4deg);border:1px dashed rgba(150,130,90,0.35);"></div>
      {hero_tile}
    </div>
    <div style="position:absolute;right:3%;top:14px;width:40%;height:144px;transform:rotate(2.2deg);
                box-shadow:0 5px 16px rgba(38,50,56,0.15);">
      <div style="position:absolute;top:-8px;left:8px;width:48px;height:16px;background:rgba(240,228,200,0.85);
                  transform:rotate(-6deg);border:1px dashed rgba(150,130,90,0.35);"></div>
      {mid_tile}
    </div>
    <div style="position:absolute;right:6%;bottom:6px;width:40%;height:148px;transform:rotate(-1.4deg);
                box-shadow:0 5px 16px rgba(38,50,56,0.15);">
      <div style="position:absolute;top:-8px;right:14px;width:48px;height:16px;background:rgba(240,228,200,0.85);
                  transform:rotate(5deg);border:1px dashed rgba(150,130,90,0.35);"></div>
      {bot_tile}
    </div>
  </div>
  <div style="background:#FFFDF7;border-radius:10px;padding:20px;margin-bottom:10px;border:1px solid #D8D0C3;">
    {_board_label("Material Palette")}
    <div style="display:flex;gap:12px;flex-wrap:wrap;">{mat_blocks}</div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px;">
    <div style="background:#FFFDF7;border-radius:10px;padding:16px;border:1px solid #D8D0C3;">
      {_board_label("UX Activity")}<div style="line-height:2;">{act_chips}</div></div>
    <div style="background:#FFFDF7;border-radius:10px;padding:16px;border:1px solid #D8D0C3;">
      {_board_label("Lighting")}<div style="line-height:2;">{lit_chips}</div></div>
    <div style="background:#FFFDF7;border-radius:10px;padding:16px;border:1px solid #D8D0C3;">
      {_board_label("Spatial Quality")}<div style="line-height:2;">{spa_chips}</div></div>
  </div>
  {custom_section}
  <div style="background:#FFFDF7;border-radius:10px;padding:20px;margin-bottom:10px;
              border:1px solid #D8D0C3;border-left:3px solid {accent};">
    {_board_label("개념 설명 &nbsp;·&nbsp; Concept Statement")}
    <p style="font-size:14px;color:#3C3830;line-height:1.9;margin:0;">{ko_html}</p>
  </div>
  <div style="background:#FFFDF7;border-radius:10px;padding:16px;margin-bottom:10px;border:1px solid #D8D0C3;">
    {_board_label("Tags")}<div style="line-height:2.2;">{tag_chips}</div>
  </div>
  <div style="border-radius:10px;padding:16px;border:1px solid #D8D0C3;background:rgba(232,216,195,0.18);">
    {_board_label("Main Image Prompt Reference")}
    <p style="font-size:12px;color:#6F6A60;margin:0;line-height:1.8;font-style:italic;">&ldquo;{main_prompt}&rdquo;</p>
  </div>
  <div style="text-align:center;margin-top:24px;padding-top:16px;border-top:1px solid #D8D0C3;">
    <p style="font-size:9px;letter-spacing:3.5px;text-transform:uppercase;color:#C8C4BC;margin:0;">AI Interior Concept Board Generator</p>
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
    if GEMINI_KEY:
        ctx = (f"Space: {space}, Mood: {mood}, Materials: {materials or '-'}, "
               f"Lighting: {lighting or '-'}, Activities: {activities or '-'}, "
               f"Spatial: {spatial or '-'}, Extra: {translated_extra or '-'}")
        gp = gemini_call(
            "당신은 인테리어 디자이너입니다. 아래 컨셉에 대해 출력하세요. "
            "JSON으로만 응답: {\"ko\":\"3-4문장 한국어 컨셉 설명, 시적이고 구체적 (Markdown **bold** 강조)\","
            "\"main\":\"슬롯1 메인 뷰 이미지 프롬프트 영어 한 문장 (cinematic, photographic)\","
            "\"material\":\"슬롯2 재료/디테일 클로즈업 영어 한 문장\","
            "\"atmosphere\":\"슬롯3 분위기/조명 영어 한 문장\"}\n\n" + ctx,
            want_json=True, timeout=20)
        try:
            j = json.loads(gp) if gp else {}
            if j.get("ko"): ko_stmt = j["ko"]
            if j.get("main"): main_prompt = j["main"]
            if j.get("material"): material_prompt = j["material"]
            if j.get("atmosphere"): atmosphere_prompt = j["atmosphere"]
        except Exception:
            pass
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
    upload_note = f" · {n_uploads}장 이미지 사용" if n_uploads else ""
    status_md = f"✓ {space} · {mood}{upload_note} — 콘셀 보드 생성 완료"
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
    out = gemini_call(prompt, want_json=True, timeout=20)
    if not out:
        gr.Warning("Gemini 응답 없음 (네트워크 또는 키 문제)")
        return (gr.update(),) * 6
    try:
        m = re.search(r"\{[\s\S]*\}", out)
        j = json.loads(m.group(0) if m else out)
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

def suggest_materials_from_image(img, current_materials):
    if img is None or not HAS_PIL:
        return current_materials
    try:
        small = img.resize((20, 20)).convert("RGB")
        pixels = list(small.getdata())
        avg = tuple(sum(p[i] for p in pixels) // len(pixels) for i in range(3))
        ranked = sorted(_MAT_COLORS.items(), key=lambda kv: sum((avg[i]-kv[1][i])**2 for i in range(3)))
        top2 = [ranked[0][0], ranked[1][0]]
        return list(dict.fromkeys(top2 + list(current_materials)))[:4]
    except Exception:
        return current_materials


def export_board_html(board_html):
    if not board_html or "dashed" in board_html:
        return None
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>AI Interior Concept Board</title>"
            "<style>body{margin:0;padding:20px;background:#F7F3EA;"
            "font-family:'Helvetica Neue',Arial,sans-serif;}</style>"
            f"</head><body>{board_html}</body></html>")
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8")
    tmp.write(html)
    tmp.close()
    return tmp.name


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
    --body-background-fill: #F7F3EA;
    --block-background-fill: #FFFDF7;
    --block-border-color: #D8D0C3;
    --block-border-width: 1px;
    --block-radius: 12px;
    --block-shadow: 0 1px 8px rgba(38,50,56,0.05);
    --block-label-text-color: #3C3428;
    --block-label-text-size: 11px;
    --block-label-text-weight: 700;
    --block-title-text-color: #3C3428;
    --block-title-text-weight: 700;
    --input-background-fill: #FFFDF7;
    --input-border-color: #D0C8BA;
    --input-border-color-focus: #C57B57;
    --input-text-size: 13px;
    --checkbox-label-background-fill: #F2ECE3;
    --checkbox-label-background-fill-hover: #E4EED8;
    --checkbox-label-background-fill-selected: #4E7040;
    --checkbox-label-border-color: #C8BCAC;
    --checkbox-label-border-color-hover: #7A9868;
    --checkbox-label-border-color-selected: #3C5C30;
    --checkbox-label-text-color: #1E1A14;
    --checkbox-label-text-color-selected: #FFFFFF;
    --button-primary-background-fill: #C57B57;
    --button-primary-background-fill-hover: #A86540;
    --button-primary-text-color: #FFFDF7;
    --button-primary-border-color: transparent;
    --button-secondary-background-fill: #FFFDF7;
    --button-secondary-background-fill-hover: #F0E8DC;
    --button-secondary-text-color: #4A4038;
    --button-secondary-border-color: #D0C8BA;
    --color-accent: #C57B57;
    --slider-color: #6B8A5E;
}
body, .gradio-container { background: #F7F3EA !important; font-family: 'Helvetica Neue', Arial, sans-serif !important; }
.gradio-container { max-width: 1100px !important; margin: 0 auto !important; }
footer { display: none !important; }
.contain, .gap, .panel { background: transparent !important; }
.block, .form { background: #FFFDF7 !important; border: 1px solid #D8D0C3 !important; border-radius: 12px !important; box-shadow: 0 1px 8px rgba(38,50,56,0.05) !important; }
.block .label-wrap > span, label > span, .block label > span, fieldset legend,
.block .label-wrap > label, .block .label-wrap label, .label-wrap label,
.block > label, .form > label, .block label, .wrap label {
    font-size: 10px !important; font-weight: 700 !important; letter-spacing: 2px !important;
    text-transform: uppercase !important; color: #3C3428 !important;
}
textarea, input[type="text"], input[type="number"] {
    background: #FFFDF7 !important; border: 1px solid #D0C8BA !important;
    color: #1E1A14 !important; border-radius: 8px !important; font-size: 13px !important; line-height: 1.7 !important;
}
textarea:focus, input[type="text"]:focus, input[type="number"]:focus {
    border-color: #C57B57 !important; outline: none !important; box-shadow: 0 0 0 3px rgba(197,123,87,0.13) !important;
}
textarea::placeholder, input::placeholder { color: #B8B0A3 !important; font-style: italic !important; }
.wrap-inner, .multiselect, .wrap { background: #FFFDF7 !important; border-color: #D0C8BA !important; color: #1E1A14 !important; }
.token { background: #EDE8DF !important; border: 1px solid #D0C8BA !important; color: #1E1A14 !important; }
.list-items, .options { background: #FFFDF7 !important; border: 1px solid #D0C8BA !important; border-radius: 8px !important; box-shadow: 0 4px 18px rgba(38,50,56,0.10) !important; }
.item, .list-items li { color: #1E1A14 !important; font-size: 13px !important; }
.item:hover, .item.selected, .list-items li:hover { background: #F0EAE0 !important; }
.checkbox-group { gap: 6px !important; flex-wrap: wrap !important; padding: 4px 0 6px !important; }
label.checkbox-label, .checkbox-label {
    background: #F2ECE3 !important; border: 1.5px solid #C8BCAC !important; border-radius: 20px !important;
    padding: 6px 14px !important; color: #1E1A14 !important; font-size: 12.5px !important;
    font-weight: 500 !important; cursor: pointer !important;
    transition: background 0.12s, border-color 0.12s, color 0.12s !important;
    line-height: 1.5 !important; margin: 2px 1px !important; white-space: nowrap !important;
    user-select: none !important; display: inline-flex !important; align-items: center !important;
}
label.checkbox-label span, .checkbox-label span { color: #1E1A14 !important; }
label.checkbox-label:hover, .checkbox-label:hover { background: #E4EED8 !important; border-color: #7A9868 !important; color: #162410 !important; }
label.checkbox-label:hover span, .checkbox-label:hover span { color: #162410 !important; }
label.checkbox-label.selected, .checkbox-label.selected,
label.checkbox-label:has(input[type="checkbox"]:checked), .checkbox-label:has(input[type="checkbox"]:checked) {
    background: #4E7040 !important; border-color: #3C5C30 !important; color: #FFFFFF !important; font-weight: 700 !important;
}
label.checkbox-label.selected span, .checkbox-label.selected span,
label.checkbox-label:has(input[type="checkbox"]:checked) span,
.checkbox-label:has(input[type="checkbox"]:checked) span { color: #FFFFFF !important; }
label.checkbox-label input[type="checkbox"], .checkbox-label input[type="checkbox"] {
    appearance: none !important; -webkit-appearance: none !important;
    width: 0 !important; height: 0 !important; margin: 0 !important; padding: 0 !important;
    border: none !important; opacity: 0 !important; pointer-events: none !important; position: absolute !important;
}
input[type="range"] { accent-color: #6B8A5E !important; }
button.primary, .btn-primary {
    background: #C57B57 !important; background-image: none !important; color: #FFFDF7 !important;
    border: none !important; border-radius: 9px !important; font-size: 14px !important;
    font-weight: 700 !important; letter-spacing: 0.4px !important;
    box-shadow: 0 3px 12px rgba(197,123,87,0.30) !important; transition: background 0.2s, box-shadow 0.2s !important;
}
button.primary:hover { background: #A86540 !important; box-shadow: 0 5px 18px rgba(197,123,87,0.40) !important; }
button.secondary {
    background: #FFFDF7 !important; border: 1.5px solid #D0C8BA !important; color: #4A4038 !important;
    border-radius: 9px !important; font-size: 13px !important; font-weight: 500 !important;
}
button.secondary:hover { background: #F0E8DC !important; border-color: #B0A898 !important; }
.status-ok  { color: #4E7040 !important; font-size: 13px !important; font-weight: 600 !important; }
.status-msg .prose p { color: #4E7040 !important; font-weight: 600 !important; margin: 0 !important; }
.example-card { flex: 1 !important; min-width: 0 !important; }
.example-card > .wrap, .example-card > div { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
.example-card button {
    width: 100% !important; background: #FFFDF7 !important; border: 1.5px solid #D8D0C3 !important;
    border-radius: 10px !important; color: #2A2218 !important; font-size: 12px !important;
    font-weight: 600 !important; padding: 12px 14px !important; min-height: 48px !important;
    height: auto !important; text-align: left !important; white-space: normal !important;
    line-height: 1.45 !important; box-shadow: 0 1px 4px rgba(38,50,56,0.06) !important;
    transition: all 0.15s ease !important; cursor: pointer !important; margin-bottom: 6px !important;
}
.example-card button:hover { background: #FDF5EE !important; border-color: #C57B57 !important; color: #6B2E08 !important; box-shadow: 0 3px 12px rgba(197,123,87,0.15) !important; }
.upload-hint .prose p { color: #7A7268 !important; font-size: 12px !important; }
.tabs { border: none !important; background: transparent !important; }
.tab-nav { background: transparent !important; border-bottom: 1.5px solid #D0C8BA !important; padding: 0 !important; }
.tab-nav button { background: transparent !important; border: none !important; border-bottom: 3px solid transparent !important; border-radius: 0 !important; color: #7A7268 !important; font-size: 13px !important; font-weight: 500 !important; padding: 13px 24px !important; margin: 0 !important; }
.tab-nav button:hover { color: #1E1A14 !important; }
.tab-nav button.selected { color: #1E1A14 !important; font-weight: 700 !important; border-bottom-color: #C57B57 !important; }
.tabitem { background: transparent !important; border: none !important; padding: 20px 0 0 !important; }
.accordion { border: 1px solid #D0C8BA !important; border-radius: 12px !important; background: #FFFDF7 !important; overflow: hidden !important; }
.accordion > .label-wrap { padding: 14px 18px !important; }
.accordion > .label-wrap span { font-size: 13px !important; font-weight: 600 !important; color: #3C3428 !important; letter-spacing: 0 !important; text-transform: none !important; }
.prose, .md { color: #1E1A14 !important; }
.prose p { color: #2A2620 !important; line-height: 1.9 !important; }
.prose em { color: #6F6A60 !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F7F3EA; }
::-webkit-scrollbar-thumb { background: #D0C8BA; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #B8B0A3; }
"""

HEADER_HTML = """
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:20px 28px;margin-bottom:8px;
            background:#FFFDF7;border:1px solid #D8D0C3;border-radius:12px;">
  <div>
    <p style="font-size:9px;letter-spacing:4px;text-transform:uppercase;
              color:#8A8278;margin:0 0 4px;font-weight:600;">Interior Design Studio</p>
    <h1 style="font-size:22px;font-weight:400;letter-spacing:0.5px;
               color:#263238;margin:0;font-family:'Georgia','Times New Roman',serif;">
      AI Concept Board Generator
    </h1>
  </div>
  <p style="font-size:12px;color:#8A8278;margin:0;text-align:right;line-height:1.7;max-width:280px;">
    공간·분위기 선택 후 Generate →<br>3개 프롬프트 + 콘셀 보드 자동 생성
  </p>
</div>
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
<div style="font-family:'Helvetica Neue',Arial,sans-serif;background:#F7F3EA;
            padding:56px 40px;border-radius:14px;border:1.5px dashed #D0C8BA;
            text-align:center;color:#8A8278;">
  <p style="font-size:9px;letter-spacing:4px;text-transform:uppercase;
            margin:0 0 18px;font-weight:600;color:#C0B8B0;">Interior Concept Board</p>
  <div style="font-size:44px;margin-bottom:20px;opacity:0.45;">🏛️</div>
  <p style="font-size:15px;font-family:'Georgia',serif;font-weight:300;
            color:#9A9288;line-height:2.0;margin:0;">
    위에서 공간을 설정하고<br>
    <span style="color:#C57B57;font-weight:600;">Generate Concept ✶</span> 를 클릭하거나<br>
    아래 예시 카드를 선택하세요.
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
              "차분한 독서 공간, 자연광, 목재 서가")},
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

        with gr.Column(scale=1, min_width=260):
            space_in = gr.Dropdown(choices=SPACE_LIST, value="Library", label="Space Type")
            mood_in  = gr.Dropdown(choices=MOOD_LIST,  value="Calm",    label="Mood")
            extra_in = gr.Textbox(label="Custom Keywords / Natural Description",
                                   placeholder="예: 따뜻한 우드 톤의 조용한 도서관, 바이오필릭 요소", lines=3)
            with gr.Row():
                gen_btn   = gr.Button("Generate  ✶", variant="primary")
                ai_btn    = gr.Button("✨ AI 자동입력", variant="secondary", min_width=110)
                reset_btn = gr.Button("↺", variant="secondary", min_width=48)
            status_out = gr.Markdown(value="", elem_classes=["status-msg"])

            gr.HTML(_section_header("Examples"))
            preset_btns = []
            for preset in PRESET_EXAMPLES:
                btn = gr.Button(f"{preset['label']}  {preset['sub']}",
                                elem_classes=["example-card"], size="sm")
                preset_btns.append((btn, preset["data"]))

            gr.HTML(_section_header("History"))
            history_state = gr.State([])
            history_dd = gr.Dropdown(label="Recent Generations", choices=[], interactive=True)

            with gr.Accordion("🔌 Image Generation (Future)", open=False):
                with gr.Row():
                    use_external_in = gr.Checkbox(label="Enable", value=False, scale=1)
                    external_url_in = gr.Textbox(label="Server URL", placeholder="http://127.0.0.1:8188", scale=3)
                neg_prompt_in = gr.Textbox(label="Negative Prompt", lines=2,
                                            placeholder="blurry, low quality, people, text")
                with gr.Row():
                    steps_in = gr.Slider(1, 100, step=1,   value=20,  label="Steps")
                    cfg_in   = gr.Slider(1, 20,  step=0.5, value=7.0, label="CFG")
                with gr.Row():
                    imgsize_in = gr.Dropdown(choices=SIZE_LIST, value="768x768", label="Size")
                    seed_in    = gr.Number(value=-1, label="Seed", precision=0)

        with gr.Column(scale=3):
            with gr.Row():
                activity_in = gr.CheckboxGroup(choices=ACTIVITY_LIST, label="UX / Activity", scale=1)
                material_in = gr.CheckboxGroup(choices=MATERIAL_LIST, label="Material Palette", scale=1)
            with gr.Row():
                lighting_in = gr.CheckboxGroup(choices=LIGHTING_LIST, label="Lighting", scale=1)
                spatial_in  = gr.CheckboxGroup(choices=SPATIAL_LIST,  label="Spatial Quality", scale=1)

            with gr.Tabs(selected=0) as results_tabs:

                with gr.TabItem("🎨  Concept Board", id=0):
                    gr.Markdown("_참고 이미지 업로드 (선택사항)_", elem_classes=["upload-hint"])
                    with gr.Row():
                        upload_main_in       = gr.Image(label="Slot 1 — Main",       type="pil", height=160)
                        upload_material_in   = gr.Image(label="Slot 2 — Material",   type="pil", height=160)
                        upload_atmosphere_in = gr.Image(label="Slot 3 — Atmosphere", type="pil", height=160)
                    board_out = gr.HTML(value=BOARD_PLACEHOLDER)
                    with gr.Row():
                        export_btn  = gr.Button("Export HTML", size="sm", variant="secondary")
                        export_file = gr.File(label="Download", visible=False, scale=2)

                with gr.TabItem("📝  Prompts", id=1):
                    main_prompt_out     = gr.Textbox(label="Slot 1 — Main Concept",      lines=3)
                    material_prompt_out = gr.Textbox(label="Slot 2 — Material / Detail", lines=3)
                    atmo_prompt_out     = gr.Textbox(label="Slot 3 — Atmosphere",        lines=3)

                with gr.TabItem("🏷️  Tags & Korean", id=2):
                    tags_out   = gr.Textbox(label="Hashtags", lines=3)
                    korean_out = gr.Markdown(value="*Generate 후 한국어 개념 설명이 표시됩니다.*")

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
                   main_prompt_out, material_prompt_out, atmo_prompt_out, tags_out, korean_out]

    # Generate button
    (gen_btn.click(fn=generate_concept, inputs=inputs, outputs=outputs)
            .then(fn=lambda: gr.update(selected=0), inputs=[], outputs=[results_tabs])
            .then(fn=add_to_history, inputs=hist_inputs, outputs=[history_state])
            .then(fn=history_choices, inputs=[history_state], outputs=[history_dd]))

    # Enter key
    (extra_in.submit(fn=generate_concept, inputs=inputs, outputs=outputs)
             .then(fn=lambda: gr.update(selected=0), inputs=[], outputs=[results_tabs])
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
            .then(fn=add_to_history, inputs=hist_inputs, outputs=[history_state])
            .then(fn=history_choices, inputs=[history_state], outputs=[history_dd]))

    # Image upload → auto-suggest materials
    for img_in in [upload_main_in, upload_material_in, upload_atmosphere_in]:
        img_in.change(fn=suggest_materials_from_image,
                      inputs=[img_in, material_in], outputs=[material_in])

    # History restore
    history_dd.change(fn=load_history_entry, inputs=[history_state, history_dd],
                      outputs=[board_out, main_prompt_out, material_prompt_out,
                               atmo_prompt_out, tags_out, korean_out])

    # Export
    export_btn.click(fn=export_board_html, inputs=[board_out], outputs=[export_file])
    export_btn.click(fn=lambda: gr.update(visible=True), inputs=[], outputs=[export_file])


FORCE_CSS = """<style>
.gradio-container label, .gradio-container .label-wrap, .gradio-container .label-wrap span,
.gradio-container .block-label, .gradio-container fieldset legend,
.gradio-container span[data-testid="block-label"], .gradio-container [class*="block_label"],
.gradio-container [class*="block-label"], .gradio-container h1, .gradio-container h2,
.gradio-container h3, .gradio-container h4, .gradio-container h5 {
    color: #3C3428 !important; background: transparent !important;
    font-weight: 600 !important; opacity: 1 !important;
}
.gradio-container label.checkbox-label, .gradio-container .checkbox-label,
.gradio-container label[class*="checkbox"], .gradio-container [data-testid="checkbox"],
.gradio-container .wrap label, .gradio-container fieldset label {
    background: #EDE8DF !important; background-color: #EDE8DF !important;
    color: #2A2420 !important; border: 1.5px solid #C8BCAC !important;
}
.gradio-container label.checkbox-label *, .gradio-container .checkbox-label *,
.gradio-container fieldset label *, .gradio-container label[class*="checkbox"] * {
    color: #2A2420 !important;
}
.gradio-container label.checkbox-label:hover, .gradio-container .checkbox-label:hover,
.gradio-container fieldset label:hover {
    background: #E4EED8 !important; background-color: #E4EED8 !important; border-color: #7A9868 !important;
}
.gradio-container label.checkbox-label:has(input:checked),
.gradio-container .checkbox-label:has(input:checked),
.gradio-container fieldset label:has(input:checked),
.gradio-container label[class*="checkbox"]:has(input:checked) {
    background: #4E7040 !important; background-color: #4E7040 !important;
    border-color: #3C5C30 !important; color: #FFFFFF !important;
}
.gradio-container label.checkbox-label:has(input:checked) *,
.gradio-container .checkbox-label:has(input:checked) *,
.gradio-container fieldset label:has(input:checked) *,
.gradio-container label[class*="checkbox"]:has(input:checked) * { color: #FFFFFF !important; }
.gradio-container input, .gradio-container textarea, .gradio-container select,
.gradio-container .wrap-inner {
    background: #FFFDF7 !important; color: #2A2420 !important; border-color: #D0C8BA !important;
}
.gradio-container input::placeholder, .gradio-container textarea::placeholder { color: #9A9288 !important; }
.gradio-container button[role="tab"] { color: #6F6A60 !important; background: transparent !important; }
.gradio-container button[role="tab"][aria-selected="true"] {
    color: #C57B57 !important; border-bottom: 2px solid #C57B57 !important;
}
.gradio-container button.secondary, .gradio-container button[class*="secondary"] {
    background: #FFFDF7 !important; color: #4A4038 !important; border: 1px solid #D0C8BA !important;
}
/* Block/group titles like "Space Type", "UX / Activity" — force dark + bold */
.gradio-container .block-info, .gradio-container .info,
.gradio-container span.svelte-1gfkn6j, .gradio-container .form > label,
.gradio-container .form > label > span, .gradio-container .block > .label-wrap,
.gradio-container [class*="head"] > span, .gradio-container legend {
    color: #2A2420 !important; font-weight: 700 !important;
    font-size: 13px !important; letter-spacing: 0.4px !important; opacity: 1 !important;
}
/* Markdown <strong> in Korean output — kill background highlight */
.gradio-container .prose strong, .gradio-container strong,
.gradio-container .markdown strong, .gradio-container [class*="markdown"] strong {
    background: transparent !important; background-color: transparent !important;
    color: #C57B57 !important; font-weight: 700 !important;
    padding: 0 !important; box-shadow: none !important;
}
/* Markdown body text fallback */
.gradio-container .prose, .gradio-container .prose p,
.gradio-container [class*="markdown"] p { color: #2A2420 !important; }
</style>"""

if __name__ == "__main__":
    demo.launch(head=FORCE_CSS, server_name="127.0.0.1", server_port=7861)
