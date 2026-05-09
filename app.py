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

KO_DICT = {
    "도서관": "library",
    "독서":   "reading",
    "커뮤니티": "community",
    "물결":   "wave",
    "자연광": "natural light",
    "목재":   "wood",
    "차분한": "calm",
    "개방감": "open space",
    "서가":   "bookshelves",
    "라운지": "lounge",
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
# These functions are scaffolded for future connection to a remote GPU server
# (e.g. ComfyUI on a local desktop). They are NOT called in the current MVP.
#
# To activate: wire _future_generate() into generate_concept() at the
# clearly marked FUTURE INTEGRATION HOOK below.

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

# ── End [FUTURE] External Image Generation ───────────────────────────────────


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
# Generates three distinct image prompts for the concept board:
#
#   Slot 1 — Main Concept Image   : full architectural / spatial view
#   Slot 2 — Material / Detail    : close-up textures, material palette
#   Slot 3 — Atmosphere / Experience: mood, lighting, human scale
#
# Each prompt is self-contained and usable independently with any
# image-generation model (current: placeholder / upload; future: external GPU).
#
# ════════════════════════════════════════════════════════════════════════════

def build_prompts(space, activities, materials, lighting, mood, spatial,
                  translated_extra, custom_descriptors):
    """Return (main_prompt, material_prompt, atmosphere_prompt) as a tuple."""
    sp  = SPACE_TYPES.get(space,  {"en_char": "contemporary interior architecture"})
    md  = MOOD_DATA.get(mood,     {"en_adj":  "calm and refined"})

    mat = ", ".join(m.lower() for m in materials)                         if materials  else "contemporary materials"
    lit = ", ".join(LIGHTING_DATA[l]["desc"] for l in lighting
                    if l in LIGHTING_DATA)                                if lighting   else "balanced, purposeful lighting"
    spt = ", ".join(SPATIAL_DATA[s]["desc"]  for s in spatial
                    if s in SPATIAL_DATA)                                 if spatial    else "thoughtfully composed space"
    act = ", ".join(a.lower() for a in activities)                        if activities else "multipurpose use"

    custom_str = f" Additional elements: {', '.join(custom_descriptors)}." if custom_descriptors else ""
    space_label = (space or "interior space").lower()

    # Slot 1 — Main Concept Image: overall architectural / spatial composition
    main_prompt = (
        f"A {md['en_adj']} {space_label}, {sp['en_char']}. "
        f"Spatial quality: {spt}. "
        f"Primary materials: {mat}. "
        f"Lighting: {lit}. "
        f"Programmed for {act}.{custom_str} "
        f"High-end interior design photography, professional architectural staging, "
        f"editorial portfolio quality."
    )

    # Slot 2 — Material / Detail: close-up texture and material study
    material_prompt = (
        f"Material and texture detail study for a {md['en_adj']} {space_label}. "
        f"Close-up surfaces: {mat}. {sp['en_char']}.{custom_str} "
        f"Illuminated by {lit}. "
        f"Macro interior photography, material palette reference, architectural finish detail, "
        f"soft editorial lighting."
    )

    # Slot 3 — Atmosphere / Experience: mood, light, human-scale perspective
    atmosphere_prompt = (
        f"Atmospheric interior mood study: {md['en_adj']} ambiance in a {space_label}. "
        f"{spt}. Lit by {lit}.{custom_str} "
        f"Designed for {act}. "
        f"Experiential space photography, soft and immersive editorial quality, "
        f"human-scale interior perspective."
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
# Each of the three concept board image slots resolves its content with
# the following priority:
#
#   1. future_img  — image returned by an external generator (not active yet)
#   2. uploaded    — PIL image uploaded by the user through the UI
#   3. placeholder — styled material/icon tile, always available
#
# Activating priority 1 requires wiring _future_comfyui_generate() into
# generate_concept() at the marked FUTURE INTEGRATION HOOK.
#
# ════════════════════════════════════════════════════════════════════════════

def resolve_image_slot(future_img, uploaded_img, label, icon, mat_hex):
    """Return HTML for one image slot using the three-level priority fallback."""
    if future_img is not None:                          # Priority 1 — [FUTURE]
        b64 = pil_to_b64(future_img)
        if b64:
            return _generated_tile(b64, source_label="Generated")
    if uploaded_img is not None:                        # Priority 2 — uploaded
        b64 = pil_to_b64(uploaded_img)
        if b64:
            return _generated_tile(b64, source_label="Uploaded")
    return _img_tile(label, icon, mat_hex)              # Priority 3 — placeholder


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
        f' border:1px solid #D8D0C3; border-radius:10px; height:{height};'
        f' min-height:128px; display:flex; flex-direction:column;'
        f' align-items:center; justify-content:center; gap:10px;'
        f' position:relative; overflow:hidden;">'
        f'<div style="position:absolute;inset:0;background-image:{grid_pat};'
        f'pointer-events:none;"></div>'
        f'<span style="font-size:28px;position:relative;z-index:1;opacity:0.65;">{icon}</span>'
        f'<span style="font-size:9px;font-weight:700;letter-spacing:2.5px;'
        f'text-transform:uppercase;color:{icon_col};opacity:0.6;'
        f'text-align:center;padding:0 14px;position:relative;z-index:1;">{label}</span>'
        f'</div>'
    )


def _generated_tile(b64: str, height: str = "100%", source_label: str = "Uploaded") -> str:
    """Tile for uploaded or externally generated images."""
    return (
        f'<div style="border-radius:10px;overflow:hidden;height:{height};'
        f'min-height:128px;border:1px solid #D8D0C3;position:relative;">'
        f'<img src="data:image/jpeg;base64,{b64}"'
        f' style="width:100%;height:100%;object-fit:cover;display:block;"/>'
        f'<div style="position:absolute;bottom:0;left:0;right:0;padding:6px 10px;'
        f'background:linear-gradient(transparent,rgba(38,50,56,0.45));'
        f'border-radius:0 0 10px 10px;">'
        f'<span style="font-size:8px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:rgba(255,253,247,0.85);">{source_label}</span>'
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
        f'<div style="font-size:11px;color:#263238;font-weight:500;margin-bottom:2px;">{d["ko"]}</div>'
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


# ─── HTML Board Builder ───────────────────────────────────────────────────────

def build_html_board(
    space, activities, materials, lighting, mood, spatial,
    translated_extra, main_prompt,
    custom_descriptors=None,
    # ── Image Source Layer ────────────────────────────────────────────────────
    # Priority per slot: future_* > uploaded_* > placeholder
    # future_* slots: set by [FUTURE INTEGRATION HOOK] in generate_concept()
    future_main=None, future_material=None, future_atmosphere=None,
    # uploaded_* slots: set by user via gr.Image upload components
    uploaded_main=None, uploaded_material=None, uploaded_atmosphere=None,
    # ─────────────────────────────────────────────────────────────────────────
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

    # Resolve all three image slots through the image source priority system
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
        custom_section = f"""
  <div style="background:#FFFDF7;border-radius:10px;padding:16px;
              margin-bottom:10px;border:1px solid #D8D0C3;border-left:3px solid #C57B57;">
    <p style="font-size:9px;letter-spacing:2.5px;text-transform:uppercase;
              color:#B8B0A3;margin:0 0 10px;font-weight:600;">Custom Concept Elements</p>
    <div style="line-height:2;">{custom_chips}</div>
  </div>"""

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
              color:#B8B0A3;margin:0 0 12px;font-weight:500;">
      Interior Concept Board &nbsp;·&nbsp; {space or 'Interior Space'}
    </p>
    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:8px;">
      <h1 style="font-size:28px;font-weight:300;letter-spacing:0.5px;margin:0;
                 color:#263238;font-family:'Georgia','Times New Roman',serif;">
        {sp['ko']}
      </h1>
      <span style="display:inline-block;width:1px;height:22px;background:#D8D0C3;"></span>
      <span style="font-size:14px;color:#6F6A60;font-weight:400;letter-spacing:0.3px;">
        {mood_label}
      </span>
    </div>
    <p style="font-size:12px;color:#6F6A60;margin:0;line-height:1.7;">
      {sp['en_char'].replace(',', ' &nbsp;·&nbsp;')}
    </p>
    <div style="width:32px;height:2px;background:{accent};border-radius:1px;margin-top:16px;"></div>
  </div>

  <!-- Image grid: Slot 1 hero (main concept) left; Slot 2 + 3 stacked right -->
  <div style="display:grid;grid-template-columns:1.6fr 1fr;
              grid-template-rows:148px 148px;gap:10px;margin-bottom:20px;">
    <div style="grid-column:1;grid-row:1/3;height:100%;">{hero_tile}</div>
    <div style="grid-column:2;grid-row:1;">{mid_tile}</div>
    <div style="grid-column:2;grid-row:2;">{bot_tile}</div>
  </div>

  <div style="background:#FFFDF7;border-radius:10px;padding:20px;
              margin-bottom:10px;border:1px solid #D8D0C3;">
    <p style="font-size:9px;letter-spacing:2.5px;text-transform:uppercase;
              color:#B8B0A3;margin:0 0 14px;font-weight:600;">Material Palette</p>
    <div style="display:flex;gap:12px;flex-wrap:wrap;">{mat_blocks}</div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px;">
    <div style="background:#FFFDF7;border-radius:10px;padding:16px;border:1px solid #D8D0C3;">
      <p style="font-size:9px;letter-spacing:2px;text-transform:uppercase;
                color:#B8B0A3;margin:0 0 10px;font-weight:600;">UX Activity</p>
      <div style="line-height:2;">{act_chips}</div>
    </div>
    <div style="background:#FFFDF7;border-radius:10px;padding:16px;border:1px solid #D8D0C3;">
      <p style="font-size:9px;letter-spacing:2px;text-transform:uppercase;
                color:#B8B0A3;margin:0 0 10px;font-weight:600;">Lighting</p>
      <div style="line-height:2;">{lit_chips}</div>
    </div>
    <div style="background:#FFFDF7;border-radius:10px;padding:16px;border:1px solid #D8D0C3;">
      <p style="font-size:9px;letter-spacing:2px;text-transform:uppercase;
                color:#B8B0A3;margin:0 0 10px;font-weight:600;">Spatial Quality</p>
      <div style="line-height:2;">{spa_chips}</div>
    </div>
  </div>

  {custom_section}

  <div style="background:#FFFDF7;border-radius:10px;padding:20px;
              margin-bottom:10px;border:1px solid #D8D0C3;border-left:3px solid {accent};">
    <p style="font-size:9px;letter-spacing:2.5px;text-transform:uppercase;
              color:#B8B0A3;margin:0 0 10px;font-weight:600;">
      개념 설명 &nbsp;·&nbsp; Concept Statement
    </p>
    <p style="font-size:14px;color:#3C3830;line-height:1.9;margin:0;">{ko_html}</p>
  </div>

  <div style="background:#FFFDF7;border-radius:10px;padding:16px;
              margin-bottom:10px;border:1px solid #D8D0C3;">
    <p style="font-size:9px;letter-spacing:2.5px;text-transform:uppercase;
              color:#B8B0A3;margin:0 0 10px;font-weight:600;">Tags</p>
    <div style="line-height:2.2;">{tag_chips}</div>
  </div>

  <div style="border-radius:10px;padding:16px;border:1px solid #D8D0C3;
              background:rgba(232,216,195,0.18);">
    <p style="font-size:9px;letter-spacing:2.5px;text-transform:uppercase;
              color:#B8B0A3;margin:0 0 8px;font-weight:600;">Main Image Prompt Reference</p>
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
    # ── Image Source Layer: current MVP — user uploads ────────────────────────
    upload_main, upload_material, upload_atmosphere,
    # ── [FUTURE INTEGRATION PARAMS] ──────────────────────────────────────────
    # Received from the "Future Image Generation Settings" accordion.
    # Currently not active — see FUTURE INTEGRATION HOOK below.
    use_external, external_url, neg_prompt, steps, cfg, img_size, seed,
    # ─────────────────────────────────────────────────────────────────────────
):
    space      = space or "Library"
    mood       = mood  or "Calm"
    activities = activities or []
    materials  = materials  or []
    lighting   = lighting   or []
    spatial    = spatial    or []
    extra      = extra      or ""

    translated_extra, custom_descriptors = extract_custom_descriptors(extra)

    # ── Prompt Generation Layer ───────────────────────────────────────────────
    main_prompt, material_prompt, atmosphere_prompt = build_prompts(
        space, activities, materials, lighting, mood, spatial,
        translated_extra, custom_descriptors,
    )
    tags    = build_tags(space, activities, materials, lighting, mood, spatial, custom_descriptors)
    ko_stmt = build_korean(space, activities, materials, lighting, mood, spatial,
                           translated_extra, custom_descriptors)

    # ── [FUTURE INTEGRATION HOOK] ─────────────────────────────────────────────
    # Wire external image generation here when a GPU server is available.
    # Each prompt maps to its corresponding concept board slot.
    #
    # Example (not active yet):
    #
    #   if use_external and external_url and external_url.strip():
    #       try:
    #           workflow = _future_load_workflow()
    #           if workflow:
    #               w, h       = parse_image_size(img_size)
    #               seed_val   = int(seed) if int(seed) >= 0 else random.randint(0, 2**31 - 1)
    #               neg        = neg_prompt or ""
    #               # Slot 1 — main concept
    #               wf1        = _future_patch_workflow(workflow, main_prompt, neg, w, h, int(steps), float(cfg), seed_val)
    #               future_main = _future_comfyui_generate(external_url.strip(), wf1)
    #               # Slot 2 — material detail
    #               wf2             = _future_patch_workflow(workflow, material_prompt, neg, w, h, int(steps), float(cfg), seed_val + 1)
    #               future_material = _future_comfyui_generate(external_url.strip(), wf2)
    #               # Slot 3 — atmosphere
    #               wf3               = _future_patch_workflow(workflow, atmosphere_prompt, neg, w, h, int(steps), float(cfg), seed_val + 2)
    #               future_atmosphere = _future_comfyui_generate(external_url.strip(), wf3)
    #       except Exception as e:
    #           warning = f"⚠️ External generation failed: {str(e)[:120]}"
    #
    # For now, all future slots return None → falls back to upload or placeholder.
    future_main       = None   # [FUTURE] will be PILImage from external generator
    future_material   = None   # [FUTURE] will be PILImage from external generator
    future_atmosphere = None   # [FUTURE] will be PILImage from external generator
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

    status_md = "✓ Concept generated."
    return main_prompt, material_prompt, atmosphere_prompt, tags, ko_stmt, board, status_md


# ─── Styling ──────────────────────────────────────────────────────────────────

CSS = """
/* ══ Warm Minimal Studio ════════════════════════════════════════════ */

/* CSS variable overrides — most reliable Gradio theming method */
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

.block .label-wrap > span, label > span, .block label > span, fieldset legend {
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
textarea::placeholder, input::placeholder {
    color: #B8B0A3 !important;
    font-style: italic !important;
}

.wrap-inner, .multiselect, .wrap { background: #FFFDF7 !important; border-color: #D0C8BA !important; color: #1E1A14 !important; }
.token { background: #EDE8DF !important; border: 1px solid #D0C8BA !important; color: #1E1A14 !important; }
.list-items, .options { background: #FFFDF7 !important; border: 1px solid #D0C8BA !important; border-radius: 8px !important; box-shadow: 0 4px 18px rgba(38,50,56,0.10) !important; }
.item, .list-items li { color: #1E1A14 !important; font-size: 13px !important; }
.item:hover, .item.selected, .list-items li:hover { background: #F0EAE0 !important; }

/* Checkbox chips — three-layer for max compatibility */
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
label.checkbox-label:hover, .checkbox-label:hover {
    background: #E4EED8 !important;
    border-color: #7A9868 !important;
    color: #162410 !important;
}
label.checkbox-label.selected, .checkbox-label.selected {
    background: #4E7040 !important;
    border-color: #3C5C30 !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
}
label.checkbox-label:has(input[type="checkbox"]:checked),
.checkbox-label:has(input[type="checkbox"]:checked) {
    background: #4E7040 !important;
    border-color: #3C5C30 !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
}
/* Force text color on the inner span Gradio renders inside each pill */
label.checkbox-label span, .checkbox-label span {
    color: #1E1A14 !important;
}
label.checkbox-label.selected span, .checkbox-label.selected span {
    color: #FFFFFF !important;
}
label.checkbox-label:has(input[type="checkbox"]:checked) span,
.checkbox-label:has(input[type="checkbox"]:checked) span {
    color: #FFFFFF !important;
}

label.checkbox-label input[type="checkbox"], .checkbox-label input[type="checkbox"] {
    appearance: none !important;
    -webkit-appearance: none !important;
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

/* Image upload area */
.upload-area .block { border-style: dashed !important; }

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
    background: #FDF5EE !important;
    border-color: #C57B57 !important;
    color: #6B2E08 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(197,123,87,0.18) !important;
}

.tabs { border: none !important; background: transparent !important; }
.tab-nav { background: transparent !important; border-bottom: 1.5px solid #D0C8BA !important; padding: 0 !important; }
.tab-nav button { background: transparent !important; border: none !important; border-bottom: 3px solid transparent !important; border-radius: 0 !important; color: #7A7268 !important; font-size: 13px !important; font-weight: 500 !important; padding: 13px 24px !important; margin: 0 !important; }
.tab-nav button:hover { color: #1E1A14 !important; }
.tab-nav button.selected { color: #1E1A14 !important; font-weight: 700 !important; border-bottom-color: #C57B57 !important; }
.tabitem { background: transparent !important; border: none !important; padding: 20px 0 0 !important; }

.accordion { border: 1px solid #D0C8BA !important; border-radius: 12px !important; background: #FFFDF7 !important; overflow: hidden !important; }
.accordion > .label-wrap { padding: 14px 18px !important; border-bottom: 1px solid #E8E0D4 !important; }
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
            color:#C0B8B0;margin:0 0 18px;font-weight:600;
            font-family:'Helvetica Neue',Arial,sans-serif;">
    Interior Design Studio
  </p>

  <h1 style="font-size:36px;font-weight:300;letter-spacing:1.5px;
             color:#263238;margin:0 0 10px;line-height:1.15;
             font-family:'Georgia','Times New Roman',serif;">
    AI Concept Board Generator
  </h1>

  <div style="width:32px;height:2px;background:#C57B57;border-radius:1px;
              margin:0 auto 22px;"></div>

  <p style="font-size:13px;color:#6F6A60;max-width:520px;margin:0 auto 36px;
            line-height:1.9;font-family:'Helvetica Neue',Arial,sans-serif;">
    Select your space parameters, upload concept images (optional), then
    generate three image prompts and a full concept board.
  </p>

  <!-- Workflow steps -->
  <div style="display:flex;align-items:center;justify-content:center;
              gap:0;flex-wrap:wrap;max-width:760px;margin:0 auto;">

    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:0 10px;">
      <div style="width:36px;height:36px;border-radius:50%;background:#F2ECE3;
                  border:1.5px solid #D0C8BA;display:flex;align-items:center;
                  justify-content:center;font-size:14px;">⌨️</div>
      <span style="font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
                   color:#A8A098;font-weight:600;">Keywords</span>
    </div>

    <div style="width:24px;height:1px;background:#D0C8BA;margin:0 2px 18px;"></div>

    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:0 10px;">
      <div style="width:36px;height:36px;border-radius:50%;background:#F2ECE3;
                  border:1.5px solid #D0C8BA;display:flex;align-items:center;
                  justify-content:center;font-size:14px;">📝</div>
      <span style="font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
                   color:#A8A098;font-weight:600;">3 Prompts</span>
    </div>

    <div style="width:24px;height:1px;background:#D0C8BA;margin:0 2px 18px;"></div>

    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:0 10px;">
      <div style="width:36px;height:36px;border-radius:50%;background:#F2ECE3;
                  border:1.5px solid #D0C8BA;display:flex;align-items:center;
                  justify-content:center;font-size:14px;">🖼️</div>
      <span style="font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
                   color:#A8A098;font-weight:600;">Images</span>
    </div>

    <div style="width:24px;height:1px;background:#D0C8BA;margin:0 2px 18px;"></div>

    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:0 10px;">
      <div style="width:36px;height:36px;border-radius:50%;background:#F2ECE3;
                  border:1.5px solid #D0C8BA;display:flex;align-items:center;
                  justify-content:center;font-size:14px;">🏷️</div>
      <span style="font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
                   color:#A8A098;font-weight:600;">Tags</span>
    </div>

    <div style="width:24px;height:1px;background:#D0C8BA;margin:0 2px 18px;"></div>

    <div style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:0 10px;">
      <div style="width:36px;height:36px;border-radius:50%;background:#FDF0E8;
                  border:1.5px solid #DDB898;display:flex;align-items:center;
                  justify-content:center;font-size:14px;">🎨</div>
      <span style="font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
                   color:#C57B57;font-weight:700;">Concept Board</span>
    </div>

  </div>
</div>
"""


def _section_header(title: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;gap:14px;margin:28px 0 16px;">'
        f'<span style="font-size:10px;font-weight:700;letter-spacing:3px;'
        f'text-transform:uppercase;color:#6B6058;white-space:nowrap;'
        f'font-family:\'Helvetica Neue\',Arial,sans-serif;">{title}</span>'
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
            margin:0 0 18px;font-weight:600;color:#C0B8B0;">
    Interior Concept Board
  </p>
  <div style="font-size:44px;margin-bottom:20px;opacity:0.45;">🏛️</div>
  <p style="font-size:15px;font-family:'Georgia',serif;font-weight:300;
            color:#9A9288;line-height:2.0;margin:0;">
    Configure your space above and click<br>
    <span style="color:#C57B57;font-weight:600;">Generate Concept ✦</span><br>
    to build your concept board.
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
    ),
    css=CSS,
) as demo:

    # ── Hero header ──────────────────────────────────────────────────────────
    gr.HTML(HEADER_HTML)

    # ── 01 · Design Parameters ───────────────────────────────────────────────
    with gr.Row(equal_height=False):

        with gr.Column(scale=1, min_width=240):
            gr.HTML(_col_header("01 ·", "Project Setup"))
            space_in = gr.Dropdown(choices=SPACE_LIST, value="Library", label="Space Type")
            mood_in  = gr.Dropdown(choices=MOOD_LIST,  value="Calm",    label="Mood")
            extra_in = gr.Textbox(
                label="Custom Concept Keywords",
                placeholder="Free-form — English or Korean\ne.g. wave-like forms, 물결, 서가, biophilic wall",
                lines=4,
            )
            gen_btn    = gr.Button("Generate Concept  ✦", variant="primary", size="lg")
            status_out = gr.Markdown(value="")

        with gr.Column(scale=2):
            gr.HTML(_col_header("02 ·", "Design Attributes"))
            activity_in = gr.CheckboxGroup(choices=ACTIVITY_LIST, label="UX / Activity Programme")
            material_in = gr.CheckboxGroup(choices=MATERIAL_LIST, label="Material Palette")
            lighting_in = gr.CheckboxGroup(choices=LIGHTING_LIST, label="Lighting Strategy")
            spatial_in  = gr.CheckboxGroup(choices=SPATIAL_LIST,  label="Volume / Spatial Quality")

    # ── 03 · Concept Images (upload) ─────────────────────────────────────────
    # Current MVP: users upload their own reference images for each slot.
    # These map directly to the three concept board image positions.
    # Future: these will be auto-populated by the external image generator.
    gr.HTML(_section_header("03 · Concept Images  —  Upload or leave empty for placeholder"))
    with gr.Row(elem_classes=["upload-area"]):
        upload_main_in = gr.Image(
            label="Slot 1 — Main Concept Image",
            type="pil",
            height=200,
        )
        upload_material_in = gr.Image(
            label="Slot 2 — Material / Detail Image",
            type="pil",
            height=200,
        )
        upload_atmosphere_in = gr.Image(
            label="Slot 3 — Atmosphere / Experience Image",
            type="pil",
            height=200,
        )

    # ── [FUTURE] External Image Generation Settings ───────────────────────────
    # This accordion holds the configuration for an external GPU image generator
    # (e.g. ComfyUI on a local desktop). The controls are present but the
    # generate function currently ignores them — see FUTURE INTEGRATION HOOK.
    # To activate: uncomment the hook in generate_concept() and wire use_external_in.
    with gr.Accordion("🔌  Future: External Image Generation Settings", open=False):
        gr.Markdown(
            "_These settings will connect to a remote GPU server (e.g. ComfyUI) "
            "to auto-generate images for all three concept board slots. "
            "Not active in the current MVP — upload images above for now._"
        )
        with gr.Row():
            use_external_in = gr.Checkbox(label="Enable External Generator", value=False, scale=1)
            external_url_in = gr.Textbox(
                label="Server URL",
                placeholder="http://192.168.0.15:8188",
                scale=4,
            )
        neg_prompt_in = gr.Textbox(
            label="Negative Prompt",
            placeholder="blurry, low quality, distorted, oversaturated, people, text",
            lines=2,
        )
        with gr.Row():
            steps_in   = gr.Slider(minimum=1,  maximum=100, step=1,   value=20,  label="Steps")
            cfg_in     = gr.Slider(minimum=1,  maximum=20,  step=0.5, value=7.0, label="CFG Scale")
            imgsize_in = gr.Dropdown(choices=SIZE_LIST, value="768x768",           label="Image Size")
            seed_in    = gr.Number(value=-1, label="Seed  (−1 = random)", precision=0)

    # ── Quick Examples ────────────────────────────────────────────────────────
    gr.HTML(_section_header("Quick Examples"))
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
    with gr.Tabs():

        with gr.TabItem("📝  Image Prompts"):
            gr.Markdown("_Three specialized prompts for each concept board image slot._")
            main_prompt_out = gr.Textbox(
                label="Slot 1 — Main Concept Image Prompt",
                placeholder="Overall architectural / spatial composition prompt.",
                lines=4,
            )
            material_prompt_out = gr.Textbox(
                label="Slot 2 — Material / Detail Image Prompt",
                placeholder="Close-up material and texture study prompt.",
                lines=4,
            )
            atmo_prompt_out = gr.Textbox(
                label="Slot 3 — Atmosphere / Experience Image Prompt",
                placeholder="Mood, lighting, and experiential quality prompt.",
                lines=4,
            )

        with gr.TabItem("🏷️  Tags"):
            tags_out = gr.Textbox(
                label="Hashtags",
                placeholder="Design hashtags will appear here.",
                lines=3,
            )

        with gr.TabItem("🇰🇷  Korean Statement"):
            korean_out = gr.Markdown(
                value="*Select options above and click **Generate Concept** to see the Korean concept statement.*"
            )

        with gr.TabItem("🎨  Concept Board"):
            board_out = gr.HTML(value=BOARD_PLACEHOLDER)

    # ── Wire events ──────────────────────────────────────────────────────────
    preset_outputs = [space_in, activity_in, material_in, lighting_in, mood_in, spatial_in, extra_in]
    for btn, data in preset_btns:
        btn.click(fn=lambda d=data: d, inputs=[], outputs=preset_outputs)

    inputs = [
        space_in, activity_in, material_in, lighting_in,
        mood_in, spatial_in, extra_in,
        # Image source layer — current MVP
        upload_main_in, upload_material_in, upload_atmosphere_in,
        # Future integration params — not active yet
        use_external_in, external_url_in, neg_prompt_in,
        steps_in, cfg_in, imgsize_in, seed_in,
    ]
    outputs = [
        main_prompt_out, material_prompt_out, atmo_prompt_out,
        tags_out, korean_out, board_out, status_out,
    ]

    gen_btn.click(fn=generate_concept, inputs=inputs, outputs=outputs)
    extra_in.submit(fn=generate_concept, inputs=inputs, outputs=outputs)

if __name__ == "__main__":
    demo.launch()
