import gradio as gr
import json
import re
import time
import uuid
import copy
import base64
import random
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


# ─── Korean Mini-Dictionary ───────────────────────────────────────────────────
# Covers all knowledge-base terms + common interior design vocabulary.

KO_DICT = {
    # Space types
    "도서관": "library",
    "라운지": "lounge",
    "갤러리": "gallery",
    "카페":   "cafe",
    "오피스": "office",
    "러닝 스페이스": "learning space",
    "커뮤니티 스페이스": "community space",
    "커뮤니티": "community",
    # Moods
    "차분한":       "calm",
    "미니멀한":     "minimal",
    "미래지향적인": "futuristic",
    "아늑한":       "cozy",
    "우아한":       "elegant",
    "역동적인":     "dynamic",
    "몰입감 있는":  "immersive",
    "몰입":         "immersive",
    # Materials
    "목재":    "wood",
    "콘크리트": "concrete",
    "유리":    "glass",
    "패브릭":  "fabric",
    "금속":    "metal",
    "석재":    "stone",
    "벽돌":    "brick",
    # Lighting
    "자연 채광":     "natural light",
    "자연광":        "natural light",
    "따뜻한 조명":   "warm lighting",
    "간접 조명":     "indirect lighting",
    "드라마틱 조명": "dramatic lighting",
    "확산 조명":     "diffused lighting",
    "포인트 조명":   "accent lighting",
    # Activities
    "독서":  "reading",
    "소셜":  "social",
    "창작":  "creative",
    "휴식":  "rest",
    "학습":  "learning",
    "전시":  "exhibition",
    "협업":  "collaboration",
    # Spatial
    "개방형":    "open",
    "레이어드":  "layered",
    "높은 천장": "high ceiling",
    "컴팩트":    "compact",
    "유연한":    "flexible",
    "폐쇄형":    "enclosed",
    "유동적인":  "flowing",
    # General interior design terms
    "개방감":       "open space",
    "서가":         "bookshelves",
    "물결":         "wave",
    "천장":         "ceiling",
    "바닥":         "floor",
    "벽":           "wall",
    "창문":         "window",
    "조명":         "lighting",
    "가구":         "furniture",
    "텍스처":       "texture",
    "바이오필릭":   "biophilic",
    "미니멀리즘":   "minimalism",
    "인더스트리얼": "industrial",
    "테라코타":     "terracotta",
    "대리석":       "marble",
    "황동":         "brass",
    "린넨":         "linen",
    "루버":         "louvre",
    "루프탑":       "rooftop",
    "파티션":       "partition",
}


# ─── Knowledge Base ───────────────────────────────────────────────────────────

SPACE_TYPES = {
    "Library": {
        "ko": "도서관",
        "en_char": "knowledge-rich, contemplative, archival",
        "ko_intro": "지식과 사색이 공존하는",
        "img_labels": ["Reading Alcove", "Book Wall", "Study Nook"],
        "img_icons":  ["📚", "🗂️", "🔭"],
    },
    "Lounge": {
        "ko": "라운지",
        "en_char": "relaxed, social, comfortable",
        "ko_intro": "편안한 휴식과 교류가 이루어지는",
        "img_labels": ["Social Seating", "Relaxation Zone", "Feature Corner"],
        "img_icons":  ["🛋️", "☕", "🪴"],
    },
    "Gallery": {
        "ko": "갤러리",
        "en_char": "curated, light-focused, contemplative",
        "ko_intro": "예술과 감상이 만나는",
        "img_labels": ["Exhibition Wall", "Display Zone", "Gallery Walk"],
        "img_icons":  ["🖼️", "💡", "🎨"],
    },
    "Cafe": {
        "ko": "카페",
        "en_char": "warm, community-oriented, sensory",
        "ko_intro": "따뜻한 커뮤니티 감성이 흐르는",
        "img_labels": ["Seating Area", "Counter Detail", "Ambient Corner"],
        "img_icons":  ["☕", "🌿", "🕯️"],
    },
    "Office": {
        "ko": "오피스",
        "en_char": "focused, productive, professional",
        "ko_intro": "생산성과 창의성이 공존하는",
        "img_labels": ["Work Zone", "Collaboration Hub", "Focus Area"],
        "img_icons":  ["🖥️", "📐", "🌱"],
    },
    "Learning Space": {
        "ko": "러닝 스페이스",
        "en_char": "stimulating, structured, adaptive",
        "ko_intro": "배움과 성장이 일어나는",
        "img_labels": ["Teaching Area", "Workshop Zone", "Breakout Space"],
        "img_icons":  ["🎓", "🔬", "💡"],
    },
    "Community Space": {
        "ko": "커뮤니티 스페이스",
        "en_char": "inclusive, flexible, vibrant",
        "ko_intro": "다양한 만남과 활동이 공존하는",
        "img_labels": ["Gathering Area", "Event Zone", "Social Hub"],
        "img_icons":  ["🤝", "🎪", "🌐"],
    },
}

MATERIAL_DATA = {
    "Wood":     {"hex": "#A0784A", "light": "#C9A87A", "ko": "목재",    "finish": "warm grain texture"},
    "Concrete": {"hex": "#8E8E82", "light": "#B8B8AE", "ko": "콘크리트", "finish": "raw poured finish"},
    "Glass":    {"hex": "#90B8C0", "light": "#B8D4D8", "ko": "유리",    "finish": "clear / frosted"},
    "Fabric":   {"hex": "#C4A882", "light": "#DCC8A8", "ko": "패브릭",  "finish": "soft woven textile"},
    "Metal":    {"hex": "#8A8A96", "light": "#B4B4C0", "ko": "금속",    "finish": "brushed matte finish"},
    "Stone":    {"hex": "#9E8C7A", "light": "#C0B0A0", "ko": "석재",    "finish": "honed natural surface"},
    "Brick":    {"hex": "#B46040", "light": "#D4906A", "ko": "벽돌",   "finish": "exposed rough texture"},
}

MOOD_DATA = {
    "Calm":       {"ko": "차분한",       "en_adj": "serene, tranquil, quietly composed"},
    "Minimal":    {"ko": "미니멀한",     "en_adj": "restrained, precise, uncluttered"},
    "Futuristic": {"ko": "미래지향적인", "en_adj": "forward-looking, innovative, sleek"},
    "Cozy":       {"ko": "아늑한",       "en_adj": "warm, inviting, intimate"},
    "Elegant":    {"ko": "우아한",       "en_adj": "refined, sophisticated, graceful"},
    "Dynamic":    {"ko": "역동적인",     "en_adj": "energetic, bold, expressive"},
    "Immersive":  {"ko": "몰입감 있는",  "en_adj": "atmospheric, enveloping, layered"},
}

# Mood-specific photography/rendering style cues for image prompts
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
    "Social":        {"ko": "소셜",  "desc": "casual social interaction"},
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
    "Compact":      {"ko": "컴팩트",    "desc": "intimate compact arrangement"},
    "Flexible":     {"ko": "유연한",    "desc": "adaptable multi-use configuration"},
    "Enclosed":     {"ko": "폐쇄형",    "desc": "defined enclosed spatial volumes"},
    "Flowing":      {"ko": "유동적인",  "desc": "fluid, continuous spatial transitions"},
}


# ─── Utility: Free-form Keyword Processing ───────────────────────────────────

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


# ── [FUTURE] External Image Generation ───────────────────────────────────────
#
# Scaffolded for future connection to a remote GPU server (e.g. ComfyUI).
# NOT called in the current MVP.
# To activate: wire into generate_concept() at the FUTURE INTEGRATION HOOK.

WORKFLOW_PATH = Path("comfyui_workflow.json")


def _future_load_workflow():
    """[FUTURE] Load ComfyUI workflow JSON from disk. Returns dict or None."""
    if WORKFLOW_PATH.exists():
        try:
            with open(WORKFLOW_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _future_patch_workflow(workflow, pos_prompt, neg_prompt, width, height, steps, cfg, seed):
    """[FUTURE] Inject generation params into workflow nodes without touching checkpoint names."""
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
    """[FUTURE] Submit workflow to ComfyUI REST API, poll until done, return PIL Image."""
    if not HAS_REQUESTS:
        raise RuntimeError("'requests' not installed")
    if not HAS_PIL:
        raise RuntimeError("'Pillow' not installed")

    url       = server_url.rstrip("/")
    client_id = str(uuid.uuid4())
    resp = _requests.post(
        f"{url}/prompt",
        json={"prompt": workflow, "client_id": client_id},
        timeout=15,
    )
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
            raise RuntimeError(f"ComfyUI execution error: {status.get('messages', [])}")
        for node_out in entry.get("outputs", {}).values():
            for img_info in node_out.get("images", []):
                img_resp = _requests.get(
                    f"{url}/view",
                    params={
                        "filename": img_info["filename"],
                        "subfolder": img_info.get("subfolder", ""),
                        "type":     img_info.get("type", "output"),
                    },
                    timeout=60,
                )
                img_resp.raise_for_status()
                return PILImage.open(BytesIO(img_resp.content)).convert("RGB")

    raise TimeoutError(f"ComfyUI did not finish within {timeout} seconds")

# ── End [FUTURE] ─────────────────────────────────────────────────────────────


# ─── PIL Utilities ────────────────────────────────────────────────────────────

def pil_to_b64(img) -> str:
    if not (HAS_PIL and isinstance(img, PILImage.Image)):
        return ""
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def parse_image_size(size_str: str) -> tuple:
    w, h = size_str.strip().split("x")
    return int(w), int(h)


# ══ PROMPT GENERATION LAYER ══════════════════════════════════════════════════
#
#   Slot 1 — Main Concept Image   : full architectural / spatial view
#   Slot 2 — Material / Detail    : close-up textures, material palette
#   Slot 3 — Atmosphere / Experience: mood, lighting, human scale
#
# Each prompt is self-contained and usable with any image-generation model.
# Photography style is differentiated per mood via MOOD_PHOTO_STYLE.
#
# ════════════════════════════════════════════════════════════════════════════

def build_prompts(space, activities, materials, lighting, mood, spatial,
                  translated_extra, custom_descriptors):
    """Return (main_prompt, material_prompt, atmosphere_prompt)."""
    sp  = SPACE_TYPES.get(space,  {"en_char": "contemporary interior architecture"})
    md  = MOOD_DATA.get(mood,     {"en_adj":  "calm and refined"})
    photo_style = MOOD_PHOTO_STYLE.get(mood, "editorial interior photography, professional staging")

    mat = ", ".join(m.lower() for m in materials)                        if materials  else "contemporary materials"
    lit = ", ".join(LIGHTING_DATA[l]["desc"] for l in lighting
                    if l in LIGHTING_DATA)                               if lighting   else "balanced, purposeful lighting"
    spt = ", ".join(SPATIAL_DATA[s]["desc"]  for s in spatial
                    if s in SPATIAL_DATA)                                if spatial    else "thoughtfully composed space"
    act = ", ".join(a.lower() for a in activities)                       if activities else "multipurpose use"

    custom_str  = f" Additional elements: {', '.join(custom_descriptors)}." if custom_descriptors else ""
    space_label = (space or "interior space").lower()

    # Slot 1 — full spatial composition
    main_prompt = (
        f"A {md['en_adj']} {space_label}, {sp['en_char']}. "
        f"Spatial quality: {spt}. Primary materials: {mat}. "
        f"Lighting: {lit}. Programmed for {act}.{custom_str} "
        f"{photo_style}, architectural portfolio quality."
    )

    # Slot 2 — material and texture close-up
    material_prompt = (
        f"Material and texture detail study for a {md['en_adj']} {space_label}. "
        f"Close-up surfaces: {mat}. {sp['en_char']}.{custom_str} "
        f"Illuminated by {lit}. "
        f"Macro interior photography, material palette reference, architectural finish detail, "
        f"{photo_style}."
    )

    # Slot 3 — atmospheric mood and experience
    atmosphere_prompt = (
        f"Atmospheric interior mood: {md['en_adj']} ambiance in a {space_label}. "
        f"{spt}. Lit by {lit}.{custom_str} Designed for {act}. "
        f"Experiential space photography, human-scale interior perspective, "
        f"{photo_style}."
    )

    return main_prompt, material_prompt, atmosphere_prompt


# ─── Supporting Text Builders ─────────────────────────────────────────────────

def build_tags(space, activities, materials, lighting, mood, spatial, custom_descriptors):
    parts = []
    if space:
        parts.append(f"#{space.replace(' ', '')}")
    parts += [f"#{a.lower()}"                  for a in activities]
    parts += [f"#{m.lower()}"                  for m in materials]
    parts += [f"#{l.replace(' ', '').lower()}" for l in lighting]
    if mood:
        parts.append(f"#{mood.lower()}design")
    parts += [f"#{s.replace(' ', '').lower()}" for s in spatial]
    for desc in custom_descriptors:
        tag = re.sub(r"[^a-zA-Z0-9]", "", desc).lower()
        if tag:
            parts.append(f"#{tag}")
    parts += ["#interiordesign", "#conceptboard", "#spacedesign", "#designinspiration"]
    return "  ".join(parts)


def build_korean(space, activities, materials, lighting, mood, spatial,
                 translated_extra, custom_descriptors):
    sp = SPACE_TYPES.get(space)
    md = MOOD_DATA.get(mood, {"ko": "차분하고 세련된"})

    sp_ko    = sp["ko"]       if sp else (space or "인테리어 공간")
    sp_intro = sp["ko_intro"] if sp else "섬세하게 계획된"
    mat_ko   = " · ".join(MATERIAL_DATA[m]["ko"] for m in materials  if m in MATERIAL_DATA) or "현대적 소재"
    act_ko   = " · ".join(ACTIVITY_DATA[a]["ko"] for a in activities if a in ACTIVITY_DATA) or "다목적"
    spt_ko   = " · ".join(SPATIAL_DATA[s]["ko"]  for s in spatial    if s in SPATIAL_DATA)  or "개방형"
    lit_ko   = " · ".join(LIGHTING_DATA[l]["ko"] for l in lighting   if l in LIGHTING_DATA) or "균형 조명"

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


# ══ IMAGE SOURCE LAYER ════════════════════════════════════════════════════════
#
# Priority per slot:
#   1. future_img  — external generator (not active yet)
#   2. uploaded    — user-uploaded PIL image
#   3. placeholder — styled material/icon tile
#
# ════════════════════════════════════════════════════════════════════════════

def resolve_image_slot(future_img, uploaded_img, label, icon, mat_hex):
    """Return HTML for one image slot using three-level priority fallback."""
    if future_img is not None:
        b64 = pil_to_b64(future_img)
        if b64:
            return _generated_tile(b64, source_label="Generated")
    if uploaded_img is not None:
        b64 = pil_to_b64(uploaded_img)
        if b64:
            return _generated_tile(b64, source_label="Uploaded")
    return _img_tile(label, icon, mat_hex)


# ─── HTML Board Components ────────────────────────────────────────────────────

def _md_bold_to_html(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def _pale_tint(hex_color: str, mix: float = 0.14,
               base: tuple = (247, 243, 234)) -> str:
    r = int(int(hex_color[1:3], 16) * mix + base[0] * (1 - mix))
    g = int(int(hex_color[3:5], 16) * mix + base[1] * (1 - mix))
    b = int(int(hex_color[5:7], 16) * mix + base[2] * (1 - mix))
    return f"#{min(r,255):02X}{min(g,255):02X}{min(b,255):02X}"


def _img_tile(label: str, icon: str, mat_hex: str, height: str = "100%") -> str:
    pale  = _pale_tint(mat_hex, 0.12)
    light = _pale_tint(mat_hex, 0.22)
    r, g, b = int(mat_hex[1:3], 16), int(mat_hex[3:5], 16), int(mat_hex[5:7], 16)
    icon_col = f"#{int(r*0.55):02X}{int(g*0.55):02X}{int(b*0.55):02X}"
    grid_pat = (
        "repeating-linear-gradient(0deg,transparent,transparent 28px,"
        "rgba(38,50,56,0.04) 28px,rgba(38,50,56,0.04) 29px),"
        "repeating-linear-gradient(90deg,transparent,transparent 28px,"
        "rgba(38,50,56,0.04) 28px,rgba(38,50,56,0.04) 29px)"
    )
    return (
        f'<div style="background:linear-gradient(145deg,{pale},{light});'
        f'border:1px solid #D8D0C3;border-radius:10px;height:{height};'
        f'min-height:128px;display:flex;flex-direction:column;'
        f'align-items:center;justify-content:center;gap:10px;'
        f'position:relative;overflow:hidden;">'
        f'<div style="position:absolute;inset:0;background-image:{grid_pat};'
        f'pointer-events:none;"></div>'
        f'<span style="font-size:28px;position:relative;z-index:1;opacity:0.65;">{icon}</span>'
        f'<span style="font-size:9px;font-weight:700;letter-spacing:2.5px;'
        f'text-transform:uppercase;color:{icon_col};opacity:0.7;'
        f'text-align:center;padding:0 14px;position:relative;z-index:1;">{label}</span>'
        f'</div>'
    )


def _generated_tile(b64: str, height: str = "100%", source_label: str = "Uploaded") -> str:
    return (
        f'<div style="border-radius:10px;overflow:hidden;height:{height};'
        f'min-height:128px;border:1px solid #D8D0C3;position:relative;">'
        f'<img src="data:image/jpeg;base64,{b64}"'
        f' style="width:100%;height:100%;object-fit:cover;display:block;"/>'
        f'<div style="position:absolute;bottom:0;left:0;right:0;padding:6px 10px;'
        f'background:linear-gradient(transparent,rgba(38,50,56,0.45));'
        f'border-radius:0 0 10px 10px;">'
        f'<span style="font-size:8px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:rgba(255,253,247,0.9);">{source_label}</span>'
        f'</div></div>'
    )


def _material_block(name: str) -> str:
    d = MATERIAL_DATA[name]
    return (
        f'<div style="flex:1;min-width:78px;">'
        f'<div style="height:50px;background:linear-gradient(150deg,{d["hex"]},{d["light"]});'
        f'border-radius:7px;margin-bottom:6px;position:relative;border:1px solid rgba(0,0,0,0.06);">'
        f'<span style="position:absolute;bottom:5px;left:8px;font-size:8px;'
        f'font-weight:700;letter-spacing:1.2px;text-transform:uppercase;'
        f'color:rgba(255,255,255,0.82);">{name.upper()}</span>'
        f'</div>'
        f'<div style="font-size:11px;color:#3C3428;font-weight:600;margin-bottom:2px;">{d["ko"]}</div>'
        f'<div style="font-size:10px;color:#6F6A60;">{d["finish"]}</div>'
        f'</div>'
    )


def _chip(label: str, bg: str = "#EEE8DF", fg: str = "#4A4038",
          border: str = "#D8D0C3") -> str:
    return (
        f'<span style="display:inline-block;padding:5px 12px;margin:3px;'
        f'background:{bg};border:1px solid {border};border-radius:20px;'
        f'font-size:11px;font-weight:500;color:{fg};letter-spacing:0.2px;">'
        f'{label}</span>'
    )


def _board_label(text: str) -> str:
    """Section label inside the HTML concept board — readable dark-muted tone."""
    return (
        f'<p style="font-size:9px;letter-spacing:2.5px;text-transform:uppercase;'
        f'color:#7A7268;margin:0 0 12px;font-weight:700;">{text}</p>'
    )


# ─── HTML Board Builder ───────────────────────────────────────────────────────

def build_html_board(
    space, activities, materials, lighting, mood, spatial,
    translated_extra, main_prompt,
    custom_descriptors=None,
    future_main=None, future_material=None, future_atmosphere=None,
    uploaded_main=None, uploaded_material=None, uploaded_atmosphere=None,
    warning="",
):
    custom_descriptors = custom_descriptors or []
    sp = SPACE_TYPES.get(space, {
        "ko": space or "Interior Space",
        "en_char": "contemporary interior architecture",
        "ko_intro": "세심하게 계획된",
        "img_labels": ["Main View", "Detail", "Ambience"],
        "img_icons":  ["🏛️", "✨", "🌿"],
    })
    md = MOOD_DATA.get(mood, {"ko": "차분한", "en_adj": "calm and refined"})

    first_mat = materials[0] if materials else "Wood"
    accent    = MATERIAL_DATA.get(first_mat, MATERIAL_DATA["Wood"])["hex"]
    tile_mats = ((materials or ["Wood", "Concrete", "Stone"]) * 3)[:3]

    hero_tile = resolve_image_slot(
        future_main, uploaded_main,
        sp["img_labels"][0], sp["img_icons"][0],
        MATERIAL_DATA.get(tile_mats[0], MATERIAL_DATA["Wood"])["hex"],
    )
    mid_tile = resolve_image_slot(
        future_material, uploaded_material,
        sp["img_labels"][1], sp["img_icons"][1],
        MATERIAL_DATA.get(tile_mats[1], MATERIAL_DATA["Concrete"])["hex"],
    )
    bot_tile = resolve_image_slot(
        future_atmosphere, uploaded_atmosphere,
        sp["img_labels"][2], sp["img_icons"][2],
        MATERIAL_DATA.get(tile_mats[2], MATERIAL_DATA["Stone"])["hex"],
    )

    mat_blocks = "".join(_material_block(m) for m in (materials or ["Wood"]))

    act_chips = "".join(_chip(a, "#EDE8DF", "#4A3C30") for a in activities) or _chip("—", "#F5F2EE", "#AAA8A4")
    lit_chips = "".join(_chip(l, "#EDE8DF", "#3C3830") for l in lighting)   or _chip("—", "#F5F2EE", "#AAA8A4")
    spa_chips = "".join(_chip(s, "#E6EDE8", "#303C38") for s in spatial)    or _chip("—", "#F5F2EE", "#AAA8A4")

    custom_section = ""
    if custom_descriptors:
        custom_chips = "".join(_chip(d, "#F5EDE6", "#6B3E28", "#D4B8A8") for d in custom_descriptors)
        custom_section = (
            f'<div style="background:#FFFDF7;border-radius:10px;padding:16px;'
            f'margin-bottom:10px;border:1px solid #D8D0C3;border-left:3px solid #C57B57;">'
            f'{_board_label("Custom Concept Elements")}'
            f'<div style="line-height:2;">{custom_chips}</div></div>'
        )

    ko_html   = _md_bold_to_html(
        build_korean(space, activities, materials, lighting, mood, spatial,
                     translated_extra, custom_descriptors)
    )
    tags_str  = build_tags(space, activities, materials, lighting, mood, spatial, custom_descriptors)
    tag_chips = "".join(_chip(t, "#F2EDE8", "#6B5E54", "#D8D0C3") for t in tags_str.split("  "))

    warning_banner = ""
    if warning:
        warning_banner = (
            f'<div style="background:#FDF3EE;border:1px solid #E8C4A8;'
            f'border-radius:8px;padding:12px 16px;margin-bottom:16px;'
            f'font-size:12px;color:#8B4A2A;line-height:1.6;">{warning}</div>'
        )

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
                 color:#263238;font-family:'Georgia','Times New Roman',serif;">
        {sp['ko']}
      </h1>
      <span style="display:inline-block;width:1px;height:22px;background:#D8D0C3;"></span>
      <span style="font-size:14px;color:#6F6A60;font-weight:400;">{mood_label}</span>
    </div>
    <p style="font-size:12px;color:#6F6A60;margin:0;line-height:1.7;">
      {sp['en_char'].replace(',', ' &nbsp;·&nbsp;')}
    </p>
    <div style="width:32px;height:2px;background:{accent};border-radius:1px;margin-top:16px;"></div>
  </div>

  <div style="display:grid;grid-template-columns:1.6fr 1fr;
              grid-template-rows:148px 148px;gap:10px;margin-bottom:20px;">
    <div style="grid-column:1;grid-row:1/3;height:100%;">{hero_tile}</div>
    <div style="grid-column:2;grid-row:1;">{mid_tile}</div>
    <div style="grid-column:2;grid-row:2;">{bot_tile}</div>
  </div>

  <div style="background:#FFFDF7;border-radius:10px;padding:20px;
              margin-bottom:10px;border:1px solid #D8D0C3;">
    {_board_label("Material Palette")}
    <div style="display:flex;gap:12px;flex-wrap:wrap;">{mat_blocks}</div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px;">
    <div style="background:#FFFDF7;border-radius:10px;padding:16px;border:1px solid #D8D0C3;">
      {_board_label("UX Activity")}<div style="line-height:2;">{act_chips}</div>
    </div>
    <div style="background:#FFFDF7;border-radius:10px;padding:16px;border:1px solid #D8D0C3;">
      {_board_label("Lighting")}<div style="line-height:2;">{lit_chips}</div>
    </div>
    <div style="background:#FFFDF7;border-radius:10px;padding:16px;border:1px solid #D8D0C3;">
      {_board_label("Spatial Quality")}<div style="line-height:2;">{spa_chips}</div>
    </div>
  </div>

  {custom_section}

  <div style="background:#FFFDF7;border-radius:10px;padding:20px;
              margin-bottom:10px;border:1px solid #D8D0C3;border-left:3px solid {accent};">
    {_board_label("개념 설명 &nbsp;·&nbsp; Concept Statement")}
    <p style="font-size:14px;color:#3C3830;line-height:1.9;margin:0;">{ko_html}</p>
  </div>

  <div style="background:#FFFDF7;border-radius:10px;padding:16px;
              margin-bottom:10px;border:1px solid #D8D0C3;">
    {_board_label("Tags")}
    <div style="line-height:2.2;">{tag_chips}</div>
  </div>

  <div style="border-radius:10px;padding:16px;border:1px solid #D8D0C3;
              background:rgba(232,216,195,0.18);">
    {_board_label("Main Image Prompt Reference")}
    <p style="font-size:12px;color:#6F6A60;margin:0;line-height:1.8;
              font-style:italic;">&ldquo;{main_prompt}&rdquo;</p>
  </div>

  <div style="text-align:center;margin-top:24px;padding-top:16px;border-top:1px solid #D8D0C3;">
    <p style="font-size:9px;letter-spacing:3.5px;text-transform:uppercase;
              color:#C8C4BC;margin:0;">AI Interior Concept Board Generator</p>
  </div>
</div>
"""


# ══ MAIN GENERATE FUNCTION ════════════════════════════════════════════════════

def generate_concept(
    space, activities, materials, lighting, mood, spatial, extra,
    upload_main, upload_material, upload_atmosphere,
    # [FUTURE] params — not active yet, see FUTURE INTEGRATION HOOK below
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

    # ── [FUTURE INTEGRATION HOOK] ─────────────────────────────────────────────
    # Wire external GPU image generation here when a server is available.
    #
    # if use_external and external_url and external_url.strip():
    #     try:
    #         workflow = _future_load_workflow()
    #         if workflow:
    #             w, h     = parse_image_size(img_size)
    #             seed_val = int(seed) if int(seed) >= 0 else random.randint(0, 2**31 - 1)
    #             neg      = neg_prompt or ""
    #             wf1 = _future_patch_workflow(workflow, main_prompt, neg, w, h, int(steps), float(cfg), seed_val)
    #             future_main = _future_comfyui_generate(external_url.strip(), wf1)
    #             wf2 = _future_patch_workflow(workflow, material_prompt, neg, w, h, int(steps), float(cfg), seed_val + 1)
    #             future_material = _future_comfyui_generate(external_url.strip(), wf2)
    #             wf3 = _future_patch_workflow(workflow, atmosphere_prompt, neg, w, h, int(steps), float(cfg), seed_val + 2)
    #             future_atmosphere = _future_comfyui_generate(external_url.strip(), wf3)
    #     except Exception as e:
    #         warning = f"⚠️ External generation failed: {str(e)[:120]}"
    #
    future_main = future_material = future_atmosphere = None
    # ── End [FUTURE INTEGRATION HOOK] ────────────────────────────────────────

    board = build_html_board(
        space, activities, materials, lighting, mood, spatial,
        translated_extra, main_prompt,
        custom_descriptors=custom_descriptors,
        future_main=future_main,
        future_material=future_material,
        future_atmosphere=future_atmosphere,
        uploaded_main=upload_main,
        uploaded_material=upload_material,
        uploaded_atmosphere=upload_atmosphere,
    )

    n_uploads = sum(1 for x in [upload_main, upload_material, upload_atmosphere] if x is not None)
    upload_note = f" · {n_uploads}장 이미지 사용" if n_uploads else ""
    status_md = f"✓ {space} · {mood}{upload_note} — 컨셉 보드 생성 완료"

    return main_prompt, material_prompt, atmosphere_prompt, tags, ko_stmt, board, status_md


def reset_inputs():
    """Return default values for all input fields."""
    return "Library", [], [], [], "Calm", [], "", None, None, None


# ─── Styling ──────────────────────────────────────────────────────────────────

CSS = """
/* ══ Warm Minimal Studio ════════════════════════════════════════════ */

:root {
    --body-background-fill:                    #F7F3EA;
    --block-background-fill:                   #FFFDF7;
    --block-border-color:                      #D8D0C3;
    --block-border-width:                      1px;
    --block-radius:                            12px;
    --block-shadow:                            0 1px 8px rgba(38,50,56,0.05);
    --block-label-text-color:                  #3C3428;
    --block-label-text-size:                   11px;
    --block-label-text-weight:                 700;
    --block-title-text-color:                  #3C3428;
    --block-title-text-weight:                 700;
    --input-background-fill:                   #FFFDF7;
    --input-border-color:                      #D0C8BA;
    --input-border-color-focus:                #C57B57;
    --input-text-size:                         13px;
    --checkbox-label-background-fill:          #F2ECE3;
    --checkbox-label-background-fill-hover:    #E4EED8;
    --checkbox-label-background-fill-selected: #4E7040;
    --checkbox-label-border-color:             #C8BCAC;
    --checkbox-label-border-color-hover:       #7A9868;
    --checkbox-label-border-color-selected:    #3C5C30;
    --checkbox-label-text-color:               #1E1A14;
    --checkbox-label-text-color-selected:      #FFFFFF;
    --button-primary-background-fill:          #C57B57;
    --button-primary-background-fill-hover:    #A86540;
    --button-primary-text-color:               #FFFDF7;
    --button-primary-border-color:             transparent;
    --button-secondary-background-fill:        #FFFDF7;
    --button-secondary-background-fill-hover:  #F0E8DC;
    --button-secondary-text-color:             #4A4038;
    --button-secondary-border-color:           #D0C8BA;
    --color-accent:                            #C57B57;
    --slider-color:                            #6B8A5E;
}

body, .gradio-container {
    background: #F7F3EA !important;
    font-family: 'Helvetica Neue', Arial, sans-serif !important;
}
.gradio-container { max-width: 1100px !important; margin: 0 auto !important; }
footer { display: none !important; }
.contain, .gap, .panel { background: transparent !important; }

.block, .form {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 8px rgba(38,50,56,0.05) !important;
}

.block .label-wrap > span, label > span, .block label > span, fieldset legend,
.block .label-wrap > label, .block .label-wrap label, .label-wrap label,
.block > label, .form > label, .block label, .wrap label {
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: #3C3428 !important;
}

textarea, input[type="text"], input[type="number"] {
    background: #FFFDF7 !important;
    border: 1px solid #D0C8BA !important;
    color: #1E1A14 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
}
textarea:focus, input[type="text"]:focus, input[type="number"]:focus {
    border-color: #C57B57 !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(197,123,87,0.13) !important;
}
textarea::placeholder, input::placeholder { color: #B8B0A3 !important; font-style: italic !important; }

.wrap-inner, .multiselect, .wrap { background: #FFFDF7 !important; border-color: #D0C8BA !important; color: #1E1A14 !important; }
.token { background: #EDE8DF !important; border: 1px solid #D0C8BA !important; color: #1E1A14 !important; }
.list-items, .options { background: #FFFDF7 !important; border: 1px solid #D0C8BA !important; border-radius: 8px !important; box-shadow: 0 4px 18px rgba(38,50,56,0.10) !important; }
.item, .list-items li { color: #1E1A14 !important; font-size: 13px !important; }
.item:hover, .item.selected, .list-items li:hover { background: #F0EAE0 !important; }

/* Checkbox chips */
.checkbox-group { gap: 6px !important; flex-wrap: wrap !important; padding: 4px 0 6px !important; }

label.checkbox-label, .checkbox-label {
    background: #F2ECE3 !important;
    border: 1.5px solid #C8BCAC !important;
    border-radius: 20px !important;
    padding: 6px 14px !important;
    color: #1E1A14 !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: background 0.12s, border-color 0.12s, color 0.12s !important;
    line-height: 1.5 !important;
    margin: 2px 1px !important;
    white-space: nowrap !important;
    user-select: none !important;
    display: inline-flex !important;
    align-items: center !important;
}
label.checkbox-label span, .checkbox-label span { color: #1E1A14 !important; }
label.checkbox-label:hover, .checkbox-label:hover { background: #E4EED8 !important; border-color: #7A9868 !important; color: #162410 !important; }
label.checkbox-label:hover span, .checkbox-label:hover span { color: #162410 !important; }
label.checkbox-label.selected, .checkbox-label.selected,
label.checkbox-label:has(input[type="checkbox"]:checked),
.checkbox-label:has(input[type="checkbox"]:checked) {
    background: #4E7040 !important; border-color: #3C5C30 !important;
    color: #FFFFFF !important; font-weight: 700 !important;
}
label.checkbox-label.selected span, .checkbox-label.selected span,
label.checkbox-label:has(input[type="checkbox"]:checked) span,
.checkbox-label:has(input[type="checkbox"]:checked) span { color: #FFFFFF !important; }

label.checkbox-label input[type="checkbox"], .checkbox-label input[type="checkbox"] {
    appearance: none !important; -webkit-appearance: none !important;
    width: 0 !important; height: 0 !important;
    margin: 0 !important; padding: 0 !important;
    border: none !important; opacity: 0 !important;
    pointer-events: none !important; position: absolute !important;
}

input[type="range"] { accent-color: #6B8A5E !important; }

button.primary, .btn-primary {
    background: #C57B57 !important;
    background-image: none !important;
    color: #FFFDF7 !important;
    border: none !important;
    border-radius: 9px !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    letter-spacing: 0.4px !important;
    box-shadow: 0 3px 12px rgba(197,123,87,0.30) !important;
    transition: background 0.2s, box-shadow 0.2s !important;
}
button.primary:hover { background: #A86540 !important; box-shadow: 0 5px 18px rgba(197,123,87,0.40) !important; }

button.secondary {
    background: #FFFDF7 !important;
    border: 1.5px solid #D0C8BA !important;
    color: #4A4038 !important;
    border-radius: 9px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
button.secondary:hover { background: #F0E8DC !important; border-color: #B0A898 !important; }

/* Status message */
.status-ok  { color: #4E7040 !important; font-size: 13px !important; font-weight: 600 !important; }
.status-msg .prose p { color: #4E7040 !important; font-weight: 600 !important; margin: 0 !important; }

/* Preset example cards */
.example-card { flex: 1 !important; min-width: 0 !important; }
.example-card > .wrap, .example-card > div { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
.example-card button {
    width: 100% !important;
    background: #FFFDF7 !important;
    border: 1.5px solid #D8D0C3 !important;
    border-radius: 14px !important;
    color: #2A2218 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 20px 16px !important;
    min-height: 80px !important;
    height: auto !important;
    text-align: left !important;
    white-space: normal !important;
    line-height: 1.55 !important;
    box-shadow: 0 1px 6px rgba(38,50,56,0.06) !important;
    transition: all 0.18s ease !important;
    cursor: pointer !important;
}
.example-card button:hover {
    background: #FDF5EE !important; border-color: #C57B57 !important;
    color: #6B2E08 !important; transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(197,123,87,0.18) !important;
}

/* Upload hint text inside concept board tab */
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
<div style="background:linear-gradient(160deg,#FFFDF7 0%,#F7F3EA 100%);
            border:1px solid #D8D0C3;border-radius:14px;
            box-shadow:0 2px 12px rgba(38,50,56,0.05);
            padding:52px 32px 44px;margin-bottom:4px;text-align:center;">

  <p style="font-size:9px;letter-spacing:5px;text-transform:uppercase;
            color:#8A8278;margin:0 0 18px;font-weight:600;">Interior Design Studio</p>

  <h1 style="font-size:36px;font-weight:300;letter-spacing:1.5px;
             color:#263238;margin:0 0 10px;line-height:1.15;
             font-family:'Georgia','Times New Roman',serif;">
    AI Concept Board Generator
  </h1>

  <div style="width:32px;height:2px;background:#C57B57;border-radius:1px;margin:0 auto 22px;"></div>

  <p style="font-size:13px;color:#6F6A60;max-width:520px;margin:0 auto 36px;line-height:1.9;">
    공간 유형과 분위기를 선택하고 한국어 키워드를 입력하세요.<br>
    3가지 이미지 프롬프트와 컨셉 보드가 자동으로 생성됩니다.
  </p>

  <div style="display:flex;align-items:center;justify-content:center;gap:0;flex-wrap:wrap;max-width:760px;margin:0 auto;">
    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:0 10px;">
      <div style="width:36px;height:36px;border-radius:50%;background:#F2ECE3;border:1.5px solid #D0C8BA;display:flex;align-items:center;justify-content:center;font-size:14px;">⌨️</div>
      <span style="font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:#6B6058;font-weight:600;">키워드</span>
    </div>
    <div style="width:24px;height:1px;background:#D0C8BA;margin:0 2px 18px;"></div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:0 10px;">
      <div style="width:36px;height:36px;border-radius:50%;background:#F2ECE3;border:1.5px solid #D0C8BA;display:flex;align-items:center;justify-content:center;font-size:14px;">📝</div>
      <span style="font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:#6B6058;font-weight:600;">3 프롬프트</span>
    </div>
    <div style="width:24px;height:1px;background:#D0C8BA;margin:0 2px 18px;"></div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:0 10px;">
      <div style="width:36px;height:36px;border-radius:50%;background:#F2ECE3;border:1.5px solid #D0C8BA;display:flex;align-items:center;justify-content:center;font-size:14px;">🖼️</div>
      <span style="font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:#6B6058;font-weight:600;">이미지 업로드</span>
    </div>
    <div style="width:24px;height:1px;background:#D0C8BA;margin:0 2px 18px;"></div>
    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:0 10px;">
      <div style="width:36px;height:36px;border-radius:50%;background:#FDF0E8;border:1.5px solid #DDB898;display:flex;align-items:center;justify-content:center;font-size:14px;">🎨</div>
      <span style="font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:#C57B57;font-weight:700;">컨셉 보드</span>
    </div>
  </div>
</div>
"""


def _section_header(title: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;gap:14px;margin:28px 0 16px;">'
        f'<span style="font-size:10px;font-weight:700;letter-spacing:3px;'
        f'text-transform:uppercase;color:#6B6058;white-space:nowrap;">{title}</span>'
        f'<div style="flex:1;height:1px;background:#D8D0C3;border-radius:1px;"></div>'
        f'</div>'
    )


def _col_header(number: str, title: str) -> str:
    return (
        f'<p style="font-size:10px;font-weight:700;letter-spacing:2.5px;'
        f'text-transform:uppercase;color:#3C3428;margin:0 0 16px;'
        f'padding-bottom:10px;border-bottom:1px solid #E4DDD4;">'
        f'<span style="color:#C57B57;margin-right:6px;">{number}</span>{title}'
        f'</p>'
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
    <span style="color:#C57B57;font-weight:600;">Generate Concept ✦</span> 를 클릭하거나<br>
    아래 예시 카드를 선택하세요.
  </p>
</div>
"""

PRESET_EXAMPLES = [
    {
        "label": "📚  Creative Library Lounge",
        "sub":   "Wood · Fabric · Layered · Cozy",
        "data":  (
            "Library",
            ["Reading", "Creative", "Social"],
            ["Wood", "Fabric", "Stone"],
            ["Warm", "Indirect"],
            "Cozy",
            ["Layered", "High Ceiling"],
            "Warm oak shelving, reading alcove nooks, biophilic wall",
        ),
    },
    {
        "label": "🌿  Calm Reading Room",
        "sub":   "Wood · Stone · Natural Light · Calm",
        "data":  (
            "Library",
            ["Reading", "Rest"],
            ["Wood", "Stone"],
            ["Natural Light", "Diffused"],
            "Calm",
            ["Compact", "Enclosed"],
            "차분한 독서 공간, 자연광, 목재 서가",
        ),
    },
    {
        "label": "🔮  Futuristic Gallery Space",
        "sub":   "Glass · Metal · Concrete · Dramatic",
        "data":  (
            "Gallery",
            ["Exhibition", "Creative"],
            ["Glass", "Metal", "Concrete"],
            ["Dramatic", "Accent Lighting"],
            "Futuristic",
            ["Open", "High Ceiling"],
            "sleek surfaces, exhibition lighting, sculptural installation",
        ),
    },
]


# ─── Gradio UI ────────────────────────────────────────────────────────────────

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

    # ── Input section: two-column ─────────────────────────────────────────────
    with gr.Row(equal_height=False):

        with gr.Column(scale=1, min_width=240):
            gr.HTML(_col_header("01 ·", "Project Setup"))
            space_in = gr.Dropdown(choices=SPACE_LIST, value="Library", label="Space Type")
            mood_in  = gr.Dropdown(choices=MOOD_LIST,  value="Calm",    label="Mood")
            extra_in = gr.Textbox(
                label="Custom Concept Keywords",
                placeholder=(
                    "영어 또는 한국어 자유 입력\n"
                    "예: wave-like forms, 물결, 서가, 바이오필릭, biophilic wall"
                ),
                lines=4,
            )
            with gr.Row():
                gen_btn   = gr.Button("Generate Concept  ✦", variant="primary")
                reset_btn = gr.Button("↺ 초기화", variant="secondary", min_width=80)
            status_out = gr.Markdown(value="", elem_classes=["status-msg"])

        with gr.Column(scale=2):
            gr.HTML(_col_header("02 ·", "Design Attributes"))
            activity_in = gr.CheckboxGroup(choices=ACTIVITY_LIST, label="UX / Activity Programme")
            material_in = gr.CheckboxGroup(choices=MATERIAL_LIST, label="Material Palette")
            lighting_in = gr.CheckboxGroup(choices=LIGHTING_LIST, label="Lighting Strategy")
            spatial_in  = gr.CheckboxGroup(choices=SPATIAL_LIST,  label="Volume / Spatial Quality")

    # ── Future settings (collapsed) ───────────────────────────────────────────
    with gr.Accordion("🔌  Future: External Image Generation Settings", open=False):
        gr.Markdown(
            "_GPU 서버(ComfyUI 등)를 연결하면 3개 슬롯에 이미지를 자동 생성합니다. "
            "현재 MVP에서는 비활성 — 아래 Concept Board 탭에서 이미지를 직접 업로드하세요._"
        )
        with gr.Row():
            use_external_in = gr.Checkbox(label="Enable External Generator", value=False, scale=1)
            external_url_in = gr.Textbox(label="Server URL", placeholder="http://192.168.0.15:8188", scale=4)
        neg_prompt_in = gr.Textbox(
            label="Negative Prompt",
            placeholder="blurry, low quality, distorted, oversaturated, people, text",
            lines=2,
        )
        with gr.Row():
            steps_in   = gr.Slider(minimum=1, maximum=100, step=1,   value=20,  label="Steps")
            cfg_in     = gr.Slider(minimum=1, maximum=20,  step=0.5, value=7.0, label="CFG Scale")
            imgsize_in = gr.Dropdown(choices=SIZE_LIST, value="768x768", label="Image Size")
            seed_in    = gr.Number(value=-1, label="Seed  (−1 = random)", precision=0)

    # ── Quick Examples ────────────────────────────────────────────────────────
    gr.HTML(_section_header("Quick Examples — 클릭하면 자동 생성"))
    with gr.Row():
        preset_btns = []
        for preset in PRESET_EXAMPLES:
            btn = gr.Button(
                f"{preset['label']}\n{preset['sub']}",
                elem_classes=["example-card"],
                size="sm",
            )
            preset_btns.append((btn, preset["data"]))

    # ── Results ───────────────────────────────────────────────────────────────
    gr.HTML(_section_header("Results"))
    with gr.Tabs(selected=0) as results_tabs:

        with gr.TabItem("📝  Image Prompts", id=0):
            gr.Markdown("_3개 슬롯별 이미지 생성 프롬프트 — 복사해서 바로 사용하세요._")
            main_prompt_out = gr.Textbox(
                label="Slot 1 — Main Concept Image Prompt",
                placeholder="전체 공간 / 건축 구성 프롬프트",
                lines=4,
            )
            material_prompt_out = gr.Textbox(
                label="Slot 2 — Material / Detail Image Prompt",
                placeholder="소재 클로즈업 텍스처 프롬프트",
                lines=4,
            )
            atmo_prompt_out = gr.Textbox(
                label="Slot 3 — Atmosphere / Experience Image Prompt",
                placeholder="분위기 · 조명 · 경험 프롬프트",
                lines=4,
            )

        with gr.TabItem("🏷️  Tags", id=1):
            tags_out = gr.Textbox(
                label="Hashtags",
                placeholder="디자인 해시태그가 여기 표시됩니다.",
                lines=4,
            )

        with gr.TabItem("🇰🇷  Korean Statement", id=2):
            korean_out = gr.Markdown(
                value="*위에서 옵션을 선택하고 **Generate Concept** 을 클릭하면 한국어 개념 설명이 생성됩니다.*"
            )

        with gr.TabItem("🎨  Concept Board", id=3):
            # Image uploads live here — in context of where they're used
            gr.Markdown(
                "_각 슬롯에 참고 이미지를 업로드하세요 (선택사항). "
                "업로드하지 않으면 소재 플레이스홀더가 사용됩니다._",
                elem_classes=["upload-hint"],
            )
            with gr.Row():
                upload_main_in = gr.Image(
                    label="Slot 1 — Main Concept Image",
                    type="pil",
                    height=180,
                )
                upload_material_in = gr.Image(
                    label="Slot 2 — Material / Detail Image",
                    type="pil",
                    height=180,
                )
                upload_atmosphere_in = gr.Image(
                    label="Slot 3 — Atmosphere / Experience Image",
                    type="pil",
                    height=180,
                )
            board_out = gr.HTML(value=BOARD_PLACEHOLDER)

    # ── Event wiring ──────────────────────────────────────────────────────────

    inputs = [
        space_in, activity_in, material_in, lighting_in,
        mood_in, spatial_in, extra_in,
        upload_main_in, upload_material_in, upload_atmosphere_in,
        use_external_in, external_url_in, neg_prompt_in,
        steps_in, cfg_in, imgsize_in, seed_in,
    ]
    outputs = [
        main_prompt_out, material_prompt_out, atmo_prompt_out,
        tags_out, korean_out, board_out, status_out,
    ]

    # Generate button → run → switch to Concept Board tab
    (gen_btn.click(fn=generate_concept, inputs=inputs, outputs=outputs)
            .then(fn=lambda: gr.update(selected=3), inputs=[], outputs=[results_tabs]))

    # Enter key in keyword field also triggers generation
    (extra_in.submit(fn=generate_concept, inputs=inputs, outputs=outputs)
             .then(fn=lambda: gr.update(selected=3), inputs=[], outputs=[results_tabs]))

    # Reset button — clears all design inputs and uploaded images
    reset_outputs = [
        space_in, activity_in, material_in, lighting_in,
        mood_in, spatial_in, extra_in,
        upload_main_in, upload_material_in, upload_atmosphere_in,
    ]
    reset_btn.click(fn=reset_inputs, inputs=[], outputs=reset_outputs)

    # Preset cards — load values, then auto-generate, then switch to board tab
    preset_outputs = [space_in, activity_in, material_in, lighting_in, mood_in, spatial_in, extra_in]
    for btn, data in preset_btns:
        (btn.click(fn=lambda d=data: d, inputs=[], outputs=preset_outputs)
            .then(fn=generate_concept, inputs=inputs, outputs=outputs)
            .then(fn=lambda: gr.update(selected=3), inputs=[], outputs=[results_tabs]))

FORCE_CSS = """<style>
/* Force checkbox background — overrides Gradio dark-mode stone vars */
label.checkbox-label,
.checkbox-label,
label[class*="checkbox"],
.gradio-container label.checkbox-label {
    background: #EDE8DF !important;
    background-color: #EDE8DF !important;
    color: #2A2420 !important;
    border: 1.5px solid #C8BCAC !important;
}
label.checkbox-label span,
.checkbox-label span,
label[class*="checkbox"] span {
    color: #2A2420 !important;
}
label.checkbox-label:hover,
.checkbox-label:hover {
    background: #E4EED8 !important;
    background-color: #E4EED8 !important;
    border-color: #7A9868 !important;
}
label.checkbox-label.selected,
.checkbox-label.selected,
label.checkbox-label:has(input:checked),
.checkbox-label:has(input:checked) {
    background: #4E7040 !important;
    background-color: #4E7040 !important;
    border-color: #3C5C30 !important;
    color: #FFFFFF !important;
}
label.checkbox-label.selected span,
.checkbox-label.selected span,
label.checkbox-label:has(input:checked) span,
.checkbox-label:has(input:checked) span {
    color: #FFFFFF !important;
}
/* Block/group label text */
.block .label-wrap span,
.block .label-wrap label,
.form span.svelte-bound,
fieldset legend,
span.svelte-text {
    color: #3C3428 !important;
}
</style>"""

if __name__ == "__main__":
    demo.launch(head=FORCE_CSS, server_name="127.0.0.1", server_port=7861)
