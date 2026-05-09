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

# ─── Part A: Free-form Keyword Processing ────────────────────────────────────

def translate_korean(text: str) -> str:
    """Replace Korean terms using the mini-dictionary."""
    for ko, en in KO_DICT.items():
        text = text.replace(ko, en)
    return text


def extract_custom_descriptors(extra: str) -> tuple:
    """
    Translate Korean, then parse custom concept terms.
    Returns (translated_text, list_of_descriptors).
    """
    if not extra or not extra.strip():
        return "", []

    translated = translate_korean(extra.strip())

    # Split on commas, semicolons, or newlines; drop empties
    parts = re.split(r"[,;\n]+", translated)
    descriptors = [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]
    return translated, descriptors


# ─── Part B: ComfyUI Integration ─────────────────────────────────────────────

WORKFLOW_PATH = Path("comfyui_workflow.json")


def load_workflow():
    """Load ComfyUI workflow JSON from disk. Returns dict or None."""
    if WORKFLOW_PATH.exists():
        try:
            with open(WORKFLOW_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def patch_workflow(workflow, pos_prompt, neg_prompt, width, height, steps, cfg, seed):
    """
    Deep-copy workflow and inject generation parameters into matching nodes.
    Never touches checkpoint/model names.
    """
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
            # Discover connected node IDs
            if isinstance(inp.get("positive"),     list): pos_id    = str(inp["positive"][0])
            if isinstance(inp.get("negative"),     list): neg_id    = str(inp["negative"][0])
            if isinstance(inp.get("latent_image"), list): latent_id = str(inp["latent_image"][0])

    # Positive prompt
    if pos_id and pos_id in wf:
        n = wf[pos_id]
        if n.get("class_type") == "CLIPTextEncode" and "text" in n.get("inputs", {}):
            n["inputs"]["text"] = pos_prompt

    # Negative prompt
    if neg_id and neg_id in wf:
        n = wf[neg_id]
        if n.get("class_type") == "CLIPTextEncode" and "text" in n.get("inputs", {}):
            n["inputs"]["text"] = neg_prompt

    # Latent image dimensions
    if latent_id and latent_id in wf:
        n   = wf[latent_id]
        inp = n.get("inputs", {})
        if n.get("class_type") in ("EmptyLatentImage", "EmptySD3LatentImage",
                                   "EmptyHunyuanLatentVideo", "EmptyMochiLatentVideo"):
            if "width"  in inp: inp["width"]  = int(width)
            if "height" in inp: inp["height"] = int(height)

    return wf


def comfyui_generate(server_url: str, workflow: dict, timeout: int = 300):
    """
    Submit workflow to ComfyUI REST API, poll until done, return PIL Image.
    Raises on network error, API error, or timeout.
    """
    if not HAS_REQUESTS:
        raise RuntimeError("'requests' not installed — run: pip install requests")
    if not HAS_PIL:
        raise RuntimeError("'Pillow' not installed — run: pip install Pillow")

    url        = server_url.rstrip("/")
    client_id  = str(uuid.uuid4())

    # Submit prompt
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

    # Poll /history until output appears
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

        # Check for server-side errors
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            msgs = status.get("messages", [])
            raise RuntimeError(f"ComfyUI execution error: {msgs}")

        # Retrieve first available image
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


def pil_to_b64(img) -> str:
    """Encode a PIL image as a JPEG base64 string."""
    if not (HAS_PIL and isinstance(img, PILImage.Image)):
        return ""
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def parse_image_size(size_str: str) -> tuple:
    w, h = size_str.strip().split("x")
    return int(w), int(h)


# ─── Output Builders ──────────────────────────────────────────────────────────

def build_english_prompt(space, activities, materials, lighting, mood, spatial,
                         translated_extra, custom_descriptors):
    sp  = SPACE_TYPES.get(space,  {"en_char": "contemporary interior architecture"})
    md  = MOOD_DATA.get(mood,     {"en_adj":  "calm and refined"})
    mat = ", ".join(m.lower() for m in materials)                         if materials  else "contemporary materials"
    lit = ", ".join(LIGHTING_DATA[l]["desc"] for l in lighting
                    if l in LIGHTING_DATA)                                if lighting   else "balanced, purposeful lighting"
    spt = ", ".join(SPATIAL_DATA[s]["desc"]  for s in spatial
                    if s in SPATIAL_DATA)                                 if spatial    else "thoughtfully composed space"
    act = ", ".join(a.lower() for a in activities)                        if activities else "multipurpose use"

    custom_str = (f" Additional concept elements: {', '.join(custom_descriptors)}."
                  if custom_descriptors else "")

    space_label = space.lower() if space else "interior space"
    return (
        f"A {md['en_adj']} {space_label}, {sp['en_char']}. "
        f"Spatial quality: {spt}. "
        f"Primary materials: {mat}. "
        f"Lighting: {lit}. "
        f"Programmed for {act}.{custom_str} "
        f"High-end interior design photography, professional architectural staging, "
        f"editorial portfolio quality."
    )


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
    # Custom descriptor tags — strip non-alphanumeric chars
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

    sp_ko    = sp["ko"]    if sp else (space or "인테리어 공간")
    sp_intro = sp["ko_intro"] if sp else "섬세하게 계획된"

    mat_ko = " · ".join(MATERIAL_DATA[m]["ko"]   for m in materials  if m in MATERIAL_DATA) \
             if materials  else "현대적 소재"
    act_ko = " · ".join(ACTIVITY_DATA[a]["ko"]   for a in activities if a in ACTIVITY_DATA) \
             if activities else "다목적"
    spt_ko = " · ".join(SPATIAL_DATA[s]["ko"]    for s in spatial    if s in SPATIAL_DATA) \
             if spatial    else "개방형"
    lit_ko = " · ".join(LIGHTING_DATA[l]["ko"]   for l in lighting   if l in LIGHTING_DATA) \
             if lighting   else "균형 조명"

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
    r = int(mat_hex[1:3], 16)
    g = int(mat_hex[3:5], 16)
    b = int(mat_hex[5:7], 16)
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
        f'<span style="font-size:28px; position:relative; z-index:1; opacity:0.65;">{icon}</span>'
        f'<span style="font-size:9px; font-weight:700; letter-spacing:2.5px;'
        f' text-transform:uppercase; color:{icon_col}; opacity:0.6;'
        f' text-align:center; padding:0 14px; position:relative; z-index:1;">{label}</span>'
        f'</div>'
    )


def _generated_tile(b64: str, height: str = "100%") -> str:
    """Hero tile showing the ComfyUI-generated image."""
    return (
        f'<div style="border-radius:10px; overflow:hidden; height:{height};'
        f' min-height:296px; border:1px solid #D8D0C3; position:relative;">'
        f'<img src="data:image/jpeg;base64,{b64}"'
        f' style="width:100%; height:100%; object-fit:cover; display:block;" />'
        f'<div style="position:absolute; bottom:0; left:0; right:0;'
        f' padding:8px 12px;'
        f' background:linear-gradient(transparent, rgba(38,50,56,0.45));'
        f' border-radius:0 0 10px 10px;">'
        f'<span style="font-size:9px; font-weight:700; letter-spacing:2px;'
        f' text-transform:uppercase; color:rgba(255,253,247,0.85);">Generated · ComfyUI</span>'
        f'</div>'
        f'</div>'
    )


def _material_block(name: str) -> str:
    d = MATERIAL_DATA[name]
    return (
        f'<div style="flex:1; min-width:78px;">'
        f'<div style="height:50px; background:linear-gradient(150deg,{d["hex"]},{d["light"]});'
        f' border-radius:7px; margin-bottom:6px; position:relative;'
        f' border:1px solid rgba(0,0,0,0.06);">'
        f'<span style="position:absolute; bottom:5px; left:8px; font-size:8px;'
        f' font-weight:700; letter-spacing:1.2px; text-transform:uppercase;'
        f' color:rgba(255,255,255,0.82);">{name.upper()}</span>'
        f'</div>'
        f'<div style="font-size:11px; color:#263238; font-weight:500; margin-bottom:2px;">{d["ko"]}</div>'
        f'<div style="font-size:10px; color:#6F6A60;">{d["finish"]}</div>'
        f'</div>'
    )


def _chip(label: str, bg: str = "#EEE8DF", fg: str = "#4A4038",
          border: str = "#D8D0C3") -> str:
    return (
        f'<span style="display:inline-block; padding:5px 12px; margin:3px;'
        f' background:{bg}; border:1px solid {border}; border-radius:20px;'
        f' font-size:11px; font-weight:500; color:{fg}; letter-spacing:0.2px;">'
        f'{label}</span>'
    )


def build_html_board(space, activities, materials, lighting, mood, spatial,
                     translated_extra, prompt,
                     custom_descriptors=None, generated_img=None, warning=""):
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

    # Hero tile: real image if available, else placeholder
    if generated_img is not None:
        b64       = pil_to_b64(generated_img)
        hero_tile = _generated_tile(b64)
    else:
        hero_tile = _img_tile(
            sp["img_labels"][0], sp["img_icons"][0],
            MATERIAL_DATA.get(tile_mats[0], MATERIAL_DATA["Wood"])["hex"]
        )

    mid_tile = _img_tile(
        sp["img_labels"][1], sp["img_icons"][1],
        MATERIAL_DATA.get(tile_mats[1], MATERIAL_DATA["Concrete"])["hex"]
    )
    bot_tile = _img_tile(
        sp["img_labels"][2], sp["img_icons"][2],
        MATERIAL_DATA.get(tile_mats[2], MATERIAL_DATA["Stone"])["hex"]
    )

    mat_blocks = "".join(_material_block(m) for m in (materials or ["Wood"]))

    act_chips = ("".join(_chip(a, "#EDE8DF", "#4A3C30") for a in activities)
                 or _chip("—", "#F5F2EE", "#AAA8A4"))
    lit_chips = ("".join(_chip(l, "#EDE8DF", "#3C3830") for l in lighting)
                 or _chip("—", "#F5F2EE", "#AAA8A4"))
    spa_chips = ("".join(_chip(s, "#E6EDE8", "#303C38") for s in spatial)
                 or _chip("—", "#F5F2EE", "#AAA8A4"))

    # Custom descriptor chips (terracotta tint)
    custom_section = ""
    if custom_descriptors:
        custom_chips = "".join(_chip(d, "#F5EDE6", "#6B3E28", "#D4B8A8")
                               for d in custom_descriptors)
        custom_section = f"""
  <div style="background:#FFFDF7; border-radius:10px; padding:16px;
              margin-bottom:10px; border:1px solid #D8D0C3;
              border-left:3px solid #C57B57;">
    <p style="font-size:9px; letter-spacing:2.5px; text-transform:uppercase;
              color:#B8B0A3; margin:0 0 10px; font-weight:600;">
      Custom Concept Elements
    </p>
    <div style="line-height:2;">{custom_chips}</div>
  </div>"""

    ko_html   = _md_bold_to_html(
        build_korean(space, activities, materials, lighting, mood, spatial,
                     translated_extra, custom_descriptors)
    )
    tags_str  = build_tags(space, activities, materials, lighting, mood, spatial, custom_descriptors)
    tag_chips = "".join(_chip(t, "#F2EDE8", "#6B5E54", "#D8D0C3")
                        for t in tags_str.split("  "))

    warning_banner = ""
    if warning:
        warning_banner = (
            f'<div style="background:#FDF3EE; border:1px solid #E8C4A8;'
            f' border-radius:8px; padding:12px 16px; margin-bottom:16px;'
            f' font-size:12px; color:#8B4A2A; line-height:1.6;">'
            f'{warning}</div>'
        )

    space_label = sp["ko"]
    mood_label  = f"{mood} · {md['en_adj'].split(',')[0].strip().title()}"

    return f"""
<div style="font-family:'Helvetica Neue',Arial,sans-serif; background:#F7F3EA;
            padding:40px; border-radius:14px; max-width:900px; margin:0 auto;
            box-sizing:border-box; color:#263238;
            border:1px solid #D8D0C3;
            box-shadow:0 2px 20px rgba(38,50,56,0.06);">

  {warning_banner}

  <!-- Header -->
  <div style="margin-bottom:30px; padding-bottom:22px; border-bottom:1px solid #D8D0C3;">
    <p style="font-size:9px; letter-spacing:4px; text-transform:uppercase;
              color:#B8B0A3; margin:0 0 12px; font-weight:500;">
      Interior Concept Board &nbsp;·&nbsp; {space or 'Interior Space'}
    </p>
    <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:8px;">
      <h1 style="font-size:28px; font-weight:300; letter-spacing:0.5px; margin:0;
                 color:#263238; font-family:'Georgia','Times New Roman',serif;">
        {space_label}
      </h1>
      <span style="display:inline-block; width:1px; height:22px; background:#D8D0C3;"></span>
      <span style="font-size:14px; color:#6F6A60; font-weight:400; letter-spacing:0.3px;">
        {mood_label}
      </span>
    </div>
    <p style="font-size:12px; color:#6F6A60; margin:0; line-height:1.7;">
      {sp['en_char'].replace(',', ' &nbsp;·&nbsp;')}
    </p>
    <div style="width:32px; height:2px; background:{accent}; border-radius:1px; margin-top:16px;"></div>
  </div>

  <!-- Image Grid: hero left + 2 stacked right -->
  <div style="display:grid; grid-template-columns:1.6fr 1fr;
              grid-template-rows:148px 148px; gap:10px; margin-bottom:20px;">
    <div style="grid-column:1; grid-row:1/3; height:100%;">{hero_tile}</div>
    <div style="grid-column:2; grid-row:1;">{mid_tile}</div>
    <div style="grid-column:2; grid-row:2;">{bot_tile}</div>
  </div>

  <!-- Material Palette -->
  <div style="background:#FFFDF7; border-radius:10px; padding:20px;
              margin-bottom:10px; border:1px solid #D8D0C3;">
    <p style="font-size:9px; letter-spacing:2.5px; text-transform:uppercase;
              color:#B8B0A3; margin:0 0 14px; font-weight:600;">Material Palette</p>
    <div style="display:flex; gap:12px; flex-wrap:wrap;">{mat_blocks}</div>
  </div>

  <!-- Design Specs -->
  <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:10px;">
    <div style="background:#FFFDF7; border-radius:10px; padding:16px; border:1px solid #D8D0C3;">
      <p style="font-size:9px; letter-spacing:2px; text-transform:uppercase;
                color:#B8B0A3; margin:0 0 10px; font-weight:600;">UX Activity</p>
      <div style="line-height:2;">{act_chips}</div>
    </div>
    <div style="background:#FFFDF7; border-radius:10px; padding:16px; border:1px solid #D8D0C3;">
      <p style="font-size:9px; letter-spacing:2px; text-transform:uppercase;
                color:#B8B0A3; margin:0 0 10px; font-weight:600;">Lighting</p>
      <div style="line-height:2;">{lit_chips}</div>
    </div>
    <div style="background:#FFFDF7; border-radius:10px; padding:16px; border:1px solid #D8D0C3;">
      <p style="font-size:9px; letter-spacing:2px; text-transform:uppercase;
                color:#B8B0A3; margin:0 0 10px; font-weight:600;">Spatial Quality</p>
      <div style="line-height:2;">{spa_chips}</div>
    </div>
  </div>

  {custom_section}

  <!-- Korean Concept Statement -->
  <div style="background:#FFFDF7; border-radius:10px; padding:20px;
              margin-bottom:10px; border:1px solid #D8D0C3;
              border-left:3px solid {accent};">
    <p style="font-size:9px; letter-spacing:2.5px; text-transform:uppercase;
              color:#B8B0A3; margin:0 0 10px; font-weight:600;">
      개념 설명 &nbsp;·&nbsp; Concept Statement
    </p>
    <p style="font-size:14px; color:#3C3830; line-height:1.9; margin:0;">{ko_html}</p>
  </div>

  <!-- Tags -->
  <div style="background:#FFFDF7; border-radius:10px; padding:16px;
              margin-bottom:10px; border:1px solid #D8D0C3;">
    <p style="font-size:9px; letter-spacing:2.5px; text-transform:uppercase;
              color:#B8B0A3; margin:0 0 10px; font-weight:600;">Tags</p>
    <div style="line-height:2.2;">{tag_chips}</div>
  </div>

  <!-- Prompt Reference -->
  <div style="border-radius:10px; padding:16px; border:1px solid #D8D0C3;
              background:rgba(232,216,195,0.18);">
    <p style="font-size:9px; letter-spacing:2.5px; text-transform:uppercase;
              color:#B8B0A3; margin:0 0 8px; font-weight:600;">Image Prompt Reference</p>
    <p style="font-size:12px; color:#6F6A60; margin:0; line-height:1.8;
              font-style:italic;">&ldquo;{prompt}&rdquo;</p>
  </div>

  <!-- Footer -->
  <div style="text-align:center; margin-top:24px; padding-top:16px;
              border-top:1px solid #D8D0C3;">
    <p style="font-size:9px; letter-spacing:3.5px; text-transform:uppercase;
              color:#C8C4BC; margin:0;">AI Interior Concept Board Generator</p>
  </div>

</div>
"""

# ─── Main Generate Function ───────────────────────────────────────────────────

def generate_concept(
    space, activities, materials, lighting, mood, spatial, extra,
    use_comfyui, comfyui_url, neg_prompt, steps, cfg, img_size, seed,
):
    # Defaults
    space      = space or "Library"
    mood       = mood  or "Calm"
    activities = activities or []
    materials  = materials  or []
    lighting   = lighting   or []
    spatial    = spatial    or []
    extra      = extra      or ""

    # Part A: translate Korean + collect custom descriptors
    translated_extra, custom_descriptors = extract_custom_descriptors(extra)

    # Build text outputs
    prompt  = build_english_prompt(space, activities, materials, lighting, mood, spatial,
                                   translated_extra, custom_descriptors)
    tags    = build_tags(space, activities, materials, lighting, mood, spatial, custom_descriptors)
    ko_stmt = build_korean(space, activities, materials, lighting, mood, spatial,
                           translated_extra, custom_descriptors)

    # Part B: optional ComfyUI generation
    generated_img = None
    warning       = ""

    if use_comfyui:
        if not comfyui_url or not comfyui_url.strip():
            warning = "⚠️ ComfyUI URL is empty. Add the server URL and try again."
        elif not HAS_REQUESTS:
            warning = "⚠️ `requests` is not installed. Run: pip install requests"
        elif not HAS_PIL:
            warning = "⚠️ `Pillow` is not installed. Run: pip install Pillow"
        else:
            try:
                workflow = load_workflow()
                if workflow is None:
                    warning = (
                        "⚠️ comfyui_workflow.json not found next to app.py. "
                        "Export a workflow in API format from ComfyUI and save it there."
                    )
                else:
                    actual_seed = (int(seed) if int(seed) >= 0
                                   else random.randint(0, 2**31 - 1))
                    w, h = parse_image_size(img_size)
                    wf   = patch_workflow(
                        workflow, prompt, neg_prompt or "",
                        w, h, int(steps), float(cfg), actual_seed,
                    )
                    generated_img = comfyui_generate(comfyui_url.strip(), wf)
            except TimeoutError as e:
                warning = f"⚠️ {e}. Using placeholder images."
            except Exception as e:
                warning = f"⚠️ ComfyUI generation failed: {str(e)[:140]}. Using placeholder images."

    board = build_html_board(
        space, activities, materials, lighting, mood, spatial,
        translated_extra, prompt,
        custom_descriptors=custom_descriptors,
        generated_img=generated_img,
        warning=warning,
    )

    # Return image update: visible only when an image was generated
    if generated_img is not None:
        img_update = gr.update(visible=True, value=generated_img)
        status_md  = "✓ Concept generated with ComfyUI image."
    else:
        img_update = gr.update(visible=False, value=None)
        status_md  = warning if warning else "✓ Concept generated."

    return prompt, tags, ko_stmt, board, img_update, status_md

# ─── Styling ──────────────────────────────────────────────────────────────────

CSS = """
/* ── Warm Minimal Studio Theme ────────────────────────────────────── */

body, .gradio-container {
    background: #F7F3EA !important;
    font-family: 'Helvetica Neue', Arial, sans-serif !important;
}
.gradio-container {
    max-width: 1080px !important;
    margin: 0 auto !important;
}
footer { display: none !important; }

.contain, .gap, .panel { background: transparent !important; }

/* Blocks / cards */
.block, .form {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 6px rgba(38,50,56,0.04) !important;
}

/* Labels */
.block .label-wrap > span, label > span {
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: #B8B0A3 !important;
}

/* Text inputs */
textarea, input[type="text"], input[type="number"] {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    color: #263238 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
textarea:focus, input[type="text"]:focus, input[type="number"]:focus {
    border-color: #C57B57 !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(197,123,87,0.12) !important;
}
textarea::placeholder, input::placeholder {
    color: #C8C4BC !important;
    font-style: italic !important;
}

/* Dropdown */
.wrap-inner, .multiselect, .wrap {
    background: #FFFDF7 !important;
    border-color: #D8D0C3 !important;
    color: #263238 !important;
}
.token {
    background: #EDE8DF !important;
    border: 1px solid #D8D0C3 !important;
    color: #263238 !important;
}
.list-items, .options {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 16px rgba(38,50,56,0.08) !important;
}
.item, .list-items li {
    color: #263238 !important;
    font-size: 13px !important;
}
.item:hover, .item.selected, .list-items li:hover {
    background: #F2EDE0 !important;
}

/* Checkbox pill chips */
.checkbox-group { gap: 6px !important; flex-wrap: wrap !important; }
.checkbox-label {
    background: #F0EBE2 !important;
    border: 1px solid #D8D0C3 !important;
    border-radius: 20px !important;
    padding: 6px 15px !important;
    color: #4A4038 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: background 0.15s, border-color 0.15s, color 0.15s !important;
    margin: 2px !important;
}
.checkbox-label:hover {
    border-color: #8A9A7B !important;
    background: #E4EDE8 !important;
}
.checkbox-label.selected {
    background: #8A9A7B !important;
    border-color: #8A9A7B !important;
    color: #FFFDF7 !important;
    box-shadow: 0 1px 4px rgba(138,154,123,0.3) !important;
}
.checkbox-label input[type="checkbox"] {
    -webkit-appearance: none !important;
    appearance: none !important;
    width: 0 !important; height: 0 !important;
    margin: 0 !important; padding: 0 !important;
    position: absolute !important; opacity: 0 !important;
}

/* Slider */
input[type="range"] { accent-color: #8A9A7B !important; }

/* Primary button — terracotta */
button.primary, .btn-primary {
    background: #C57B57 !important;
    background-image: none !important;
    color: #FFFDF7 !important;
    border: none !important;
    border-radius: 9px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    box-shadow: 0 2px 10px rgba(197,123,87,0.28) !important;
    transition: background 0.2s !important;
}
button.primary:hover { background: #AD6B47 !important; }

/* Secondary button */
button.secondary {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    color: #6F6A60 !important;
    border-radius: 9px !important;
    font-size: 12px !important;
}
button.secondary:hover {
    background: #F2EDE0 !important;
    border-color: #B8B0A3 !important;
}

/* Tabs */
.tabs { border: none !important; background: transparent !important; }
.tab-nav {
    background: transparent !important;
    border-bottom: 1px solid #D8D0C3 !important;
    padding: 0 !important;
}
.tab-nav button {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    color: #6F6A60 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.4px !important;
    padding: 12px 22px !important;
    margin: 0 !important;
    transition: color 0.15s, border-color 0.15s !important;
}
.tab-nav button:hover { color: #263238 !important; }
.tab-nav button.selected {
    color: #263238 !important;
    font-weight: 600 !important;
    border-bottom-color: #C57B57 !important;
}
.tabitem { background: transparent !important; border: none !important; padding: 18px 0 0 !important; }

/* Accordion */
.accordion { border: 1px solid #D8D0C3 !important; border-radius: 10px !important; background: #FFFDF7 !important; }
.accordion > .label-wrap { border-bottom: 1px solid #D8D0C3 !important; }

/* Examples */
.examples > .label-wrap > span {
    font-size: 10px !important; color: #B8B0A3 !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
}
.examples table { background: transparent !important; border-collapse: separate !important; border-spacing: 0 4px !important; }
.examples thead { display: none !important; }
.examples tbody tr {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    border-radius: 8px !important;
    cursor: pointer !important;
}
.examples tbody tr:hover { background: #F2EDE0 !important; }
.examples td {
    color: #6F6A60 !important;
    font-size: 12px !important;
    border: none !important;
    padding: 8px 14px !important;
    max-width: 160px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

/* Markdown */
.prose, .md { color: #263238 !important; }
.prose h1,.prose h2,.prose h3 { color: #263238 !important; }
.prose strong { color: #263238 !important; }
.prose p { color: #3C3830 !important; line-height: 1.85 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F7F3EA; }
::-webkit-scrollbar-thumb { background: #D8D0C3; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #B8B0A3; }
"""

HEADER_HTML = """
<div style="text-align:center; padding:52px 24px 44px;
            background:linear-gradient(180deg,#FFFDF7 0%,#F7F3EA 100%);
            border-radius:12px; border:1px solid #D8D0C3;
            box-shadow:0 1px 6px rgba(38,50,56,0.04); margin-bottom:0;">
  <p style="font-size:9px; letter-spacing:5px; text-transform:uppercase;
            color:#C8C4BC; margin:0 0 20px; font-weight:500;">
    Interior Design Studio
  </p>
  <h1 style="font-size:38px; font-weight:300; letter-spacing:2px;
             color:#263238; margin:0 0 18px; line-height:1.15;
             font-family:'Georgia','Times New Roman',serif;">
    Concept Board Generator
  </h1>
  <div style="width:28px; height:1.5px; background:#C57B57; margin:0 auto 20px; border-radius:1px;"></div>
  <p style="font-size:13px; color:#6F6A60; max-width:500px; margin:0 auto;
            line-height:1.85;">
    Select space type, activities, and materials — or type any custom concept words
    (English or Korean) in the text field below.
  </p>
</div>
"""

SECTION_LEFT  = '<p style="font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#B8B0A3;margin:0 0 6px;font-weight:600;">Space &amp; Mood</p>'
SECTION_RIGHT = '<p style="font-size:9px;letter-spacing:3px;text-transform:uppercase;color:#B8B0A3;margin:0 0 6px;font-weight:600;">Programme &amp; Materials</p>'

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

    gr.HTML(HEADER_HTML)

    # ── Main inputs ──────────────────────────────────────────────────────────
    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=230):
            gr.HTML(SECTION_LEFT)
            space_in = gr.Dropdown(choices=SPACE_LIST, value="Library",
                                   label="Space Type")
            mood_in  = gr.Dropdown(choices=MOOD_LIST,  value="Calm",
                                   label="Mood")
            extra_in = gr.Textbox(
                label="Additional Concept Text",
                placeholder=(
                    "Free-form keywords — English or Korean\n"
                    "e.g. wave-like forms, 물결, 서가, biophilic wall"
                ),
                lines=4,
            )
            gen_btn  = gr.Button("Generate Concept  ✦", variant="primary", size="lg")
            status_out = gr.Markdown(value="", visible=True)

        with gr.Column(scale=2):
            gr.HTML(SECTION_RIGHT)
            activity_in = gr.CheckboxGroup(choices=ACTIVITY_LIST, label="UX / Activity")
            material_in = gr.CheckboxGroup(choices=MATERIAL_LIST, label="Material")
            lighting_in = gr.CheckboxGroup(choices=LIGHTING_LIST, label="Lighting")
            spatial_in  = gr.CheckboxGroup(choices=SPATIAL_LIST,  label="Volume / Spatial Quality")

    # ── ComfyUI accordion ────────────────────────────────────────────────────
    with gr.Accordion("🖼️  ComfyUI Image Generation  (Optional)", open=False):
        gr.Markdown(
            "_Requires `comfyui_workflow.json` (API format) in the same folder as app.py. "
            "The app patches your workflow's positive/negative prompts, size, steps, CFG, "
            "and seed — checkpoint names are never changed._",
        )
        with gr.Row():
            use_comfyui_in = gr.Checkbox(
                label="Enable ComfyUI generation", value=False, scale=1
            )
            comfyui_url_in = gr.Textbox(
                label="ComfyUI Server URL",
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

    # ── Examples ─────────────────────────────────────────────────────────────
    gr.Examples(
        examples=[
            ["Library",
             ["Reading", "Learning"],
             ["Wood", "Concrete"],
             ["Natural Light", "Indirect"],
             "Calm",
             ["High Ceiling", "Layered"],
             "Warm oak shelving, terrazzo floors, reading nooks"],
            ["Gallery",
             ["Exhibition", "Social"],
             ["Glass", "Concrete"],
             ["Dramatic", "Accent Lighting"],
             "Minimal",
             ["Open", "High Ceiling"],
             ""],
            ["Cafe",
             ["Social", "Creative", "Rest"],
             ["Wood", "Fabric", "Brick"],
             ["Warm", "Indirect"],
             "Cozy",
             ["Layered", "Flowing"],
             "물결 형태 천장, 수제 도자기 타일"],
            ["Office",
             ["Collaboration", "Learning"],
             ["Metal", "Glass"],
             ["Natural Light", "Diffused"],
             "Futuristic",
             ["Flexible", "Open"],
             "자연광 생태 벽, 높이조절 책상, 모듈형 파티션"],
            ["Community Space",
             ["Social", "Exhibition", "Collaboration"],
             ["Concrete", "Wood"],
             ["Natural Light", "Accent Lighting"],
             "Dynamic",
             ["Flowing", "High Ceiling"],
             "서가 벽면, 커뮤니티 이벤트 존, 모듈형 가구"],
        ],
        inputs=[space_in, activity_in, material_in, lighting_in,
                mood_in, spatial_in, extra_in],
        label="Quick Examples",
    )

    # ── Output tabs ──────────────────────────────────────────────────────────
    with gr.Tabs():
        with gr.TabItem("  📝  English Prompt  "):
            prompt_out = gr.Textbox(label="Image-generation prompt", lines=5)
        with gr.TabItem("  🏷️  Tags  "):
            tags_out = gr.Textbox(label="Hashtags", lines=3)
        with gr.TabItem("  🇰🇷  Korean Statement  "):
            korean_out = gr.Markdown()
        with gr.TabItem("  🎨  Concept Board  "):
            image_out = gr.Image(
                label="Generated Image  (ComfyUI)",
                type="pil",
                visible=False,
                height=380,
            )
            board_out = gr.HTML()

    # ── Wire events ──────────────────────────────────────────────────────────
    inputs  = [space_in, activity_in, material_in, lighting_in,
               mood_in, spatial_in, extra_in,
               use_comfyui_in, comfyui_url_in, neg_prompt_in,
               steps_in, cfg_in, imgsize_in, seed_in]
    outputs = [prompt_out, tags_out, korean_out, board_out, image_out, status_out]

    gen_btn.click(fn=generate_concept, inputs=inputs, outputs=outputs)
    extra_in.submit(fn=generate_concept, inputs=inputs, outputs=outputs)

if __name__ == "__main__":
    demo.launch()
