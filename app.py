import gradio as gr
import re

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

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _md_bold_to_html(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

# ─── Output Builders ──────────────────────────────────────────────────────────

def build_english_prompt(space, activities, materials, lighting, mood, spatial, extra):
    sp  = SPACE_TYPES[space]
    md  = MOOD_DATA[mood]
    mat = ", ".join(m.lower() for m in materials)                  if materials  else "mixed materials"
    lit = ", ".join(LIGHTING_DATA[l]["desc"] for l in lighting)    if lighting   else "balanced lighting"
    spt = ", ".join(SPATIAL_DATA[s]["desc"]  for s in spatial)     if spatial    else "open plan"
    act = ", ".join(a.lower() for a in activities)                 if activities else "multipurpose"
    ext = f" {extra.strip()}" if extra and extra.strip() else ""
    return (
        f"A {md['en_adj']} {space.lower()}, {sp['en_char']}. "
        f"Spatial quality: {spt}. "
        f"Primary materials: {mat}. "
        f"Lighting: {lit}. "
        f"Programmed for {act}.{ext} "
        f"High-end interior design photography, professional architectural staging, "
        f"editorial portfolio quality."
    )


def build_tags(space, activities, materials, lighting, mood, spatial):
    parts = (
        [f"#{space.replace(' ', '')}"]
        + [f"#{a.lower()}"                   for a in activities]
        + [f"#{m.lower()}"                   for m in materials]
        + [f"#{l.replace(' ', '').lower()}"  for l in lighting]
        + [f"#{mood.lower()}design"]
        + [f"#{s.replace(' ', '').lower()}"  for s in spatial]
        + ["#interiordesign", "#conceptboard", "#spacedesign", "#designinspiration"]
    )
    return "  ".join(parts)


def build_korean(space, activities, materials, lighting, mood, spatial, extra):
    sp     = SPACE_TYPES[space]
    md     = MOOD_DATA[mood]
    mat_ko = " · ".join(MATERIAL_DATA[m]["ko"]  for m in materials)  if materials  else "복합 소재"
    act_ko = " · ".join(ACTIVITY_DATA[a]["ko"]  for a in activities) if activities else "다목적"
    spt_ko = " · ".join(SPATIAL_DATA[s]["ko"]   for s in spatial)    if spatial    else "개방형"
    lit_ko = " · ".join(LIGHTING_DATA[l]["ko"]  for l in lighting)   if lighting   else "균형 조명"
    ext    = f" {extra.strip()}" if extra and extra.strip() else ""
    return (
        f"{sp['ko_intro']} **{sp['ko']}**은 **{md['ko']}** 분위기를 중심으로 "
        f"{mat_ko} 소재와 {lit_ko}을 통해 공간의 정체성을 형성합니다. "
        f"{spt_ko} 공간 구성 속에서 {act_ko} 활동을 지원하며, "
        f"사용자에게 목적과 감성이 공존하는 경험을 제공합니다.{ext}"
    )

# ─── HTML Board Components ────────────────────────────────────────────────────

def _pale_tint(hex_color: str, mix: float = 0.14, base=(247, 243, 234)) -> str:
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


def _material_block(name: str) -> str:
    d = MATERIAL_DATA[name]
    return (
        f'<div style="flex:1; min-width:78px;">'
        f'<div style="height:50px; background:linear-gradient(150deg,{d["hex"]},{d["light"]});'
        f' border-radius:7px; margin-bottom:6px; position:relative; border:1px solid rgba(0,0,0,0.06);">'
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


def build_html_board(space, activities, materials, lighting, mood, spatial, extra, prompt):
    sp = SPACE_TYPES[space]
    md = MOOD_DATA[mood]

    first_mat = materials[0] if materials else "Wood"
    accent    = MATERIAL_DATA[first_mat]["hex"]

    tile_mats = ((materials or ["Wood", "Concrete", "Stone"]) * 3)[:3]

    hero_tile = _img_tile(sp["img_labels"][0], sp["img_icons"][0],
                          MATERIAL_DATA[tile_mats[0]]["hex"])
    mid_tile  = _img_tile(sp["img_labels"][1], sp["img_icons"][1],
                          MATERIAL_DATA[tile_mats[1]]["hex"])
    bot_tile  = _img_tile(sp["img_labels"][2], sp["img_icons"][2],
                          MATERIAL_DATA[tile_mats[2]]["hex"])

    mat_blocks = "".join(_material_block(m) for m in (materials or ["Wood"]))

    act_chips = "".join(_chip(a, "#EDE8DF", "#4A3C30") for a in activities) \
                or _chip("—", "#F5F2EE", "#AAA8A4")
    lit_chips = "".join(_chip(l, "#EDE8DF", "#3C3830") for l in lighting) \
                or _chip("—", "#F5F2EE", "#AAA8A4")
    spa_chips = "".join(_chip(s, "#E6EDE8", "#303C38") for s in spatial) \
                or _chip("—", "#F5F2EE", "#AAA8A4")

    ko_html   = _md_bold_to_html(
        build_korean(space, activities, materials, lighting, mood, spatial, extra)
    )
    tags_str  = build_tags(space, activities, materials, lighting, mood, spatial)
    tag_chips = "".join(_chip(t, "#F2EDE8", "#6B5E54", "#D8D0C3")
                        for t in tags_str.split("  "))

    return f"""
<div style="font-family:'Helvetica Neue',Arial,sans-serif; background:#F7F3EA;
            padding:40px; border-radius:14px; max-width:900px; margin:0 auto;
            box-sizing:border-box; color:#263238;
            border:1px solid #D8D0C3;
            box-shadow:0 2px 20px rgba(38,50,56,0.06);">

  <!-- Header -->
  <div style="margin-bottom:30px; padding-bottom:22px; border-bottom:1px solid #D8D0C3;">
    <p style="font-size:9px; letter-spacing:4px; text-transform:uppercase;
              color:#B8B0A3; margin:0 0 12px; font-weight:500;
              font-family:'Helvetica Neue',sans-serif;">
      Interior Concept Board &nbsp;·&nbsp; {space}
    </p>
    <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:8px;">
      <h1 style="font-size:28px; font-weight:300; letter-spacing:0.5px; margin:0;
                 color:#263238; font-family:'Georgia','Times New Roman',serif;">
        {sp['ko']}
      </h1>
      <span style="display:inline-block; width:1px; height:22px; background:#D8D0C3;"></span>
      <span style="font-size:14px; color:#6F6A60; font-weight:400; letter-spacing:0.3px;">
        {mood} &nbsp;·&nbsp; {md['en_adj'].split(',')[0].strip().title()}
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

  <!-- Design Specs (3 cards) -->
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

# ─── Main ────────────────────────────────────────────────────────────────────

def generate_concept(space, activities, materials, lighting, mood, spatial, extra):
    space      = space or "Library"
    mood       = mood  or "Calm"
    activities = activities or []
    materials  = materials  or []
    lighting   = lighting   or []
    spatial    = spatial    or []
    extra      = extra      or ""

    prompt  = build_english_prompt(space, activities, materials, lighting, mood, spatial, extra)
    tags    = build_tags(space, activities, materials, lighting, mood, spatial)
    ko_stmt = build_korean(space, activities, materials, lighting, mood, spatial, extra)
    board   = build_html_board(space, activities, materials, lighting, mood, spatial, extra, prompt)
    return prompt, tags, ko_stmt, board

# ─── Styling ──────────────────────────────────────────────────────────────────

CSS = """
/* ── Warm Minimal Studio Theme ────────────────────────────────────── */

/* Page & container */
body, .gradio-container {
    background: #F7F3EA !important;
    font-family: 'Helvetica Neue', Arial, sans-serif !important;
}
.gradio-container {
    max-width: 1080px !important;
    margin: 0 auto !important;
}
footer { display: none !important; }

/* Remove dark fills from wrapper panels */
.contain, .gap, .panel {
    background: transparent !important;
}

/* ── Blocks / cards ── */
.block, .form {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 6px rgba(38,50,56,0.04) !important;
}

/* ── Labels ── */
.block .label-wrap > span,
label > span,
.svelte-1gfkn6j {
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: #B8B0A3 !important;
}

/* ── Text inputs / textareas ── */
textarea, input[type="text"] {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    color: #263238 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: #C57B57 !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(197,123,87,0.12) !important;
}
textarea::placeholder, input::placeholder {
    color: #C8C4BC !important;
    font-style: italic !important;
}

/* ── Dropdown (Gradio uses custom select) ── */
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
    padding: 8px 14px !important;
}
.item:hover, .item.selected, .list-items li:hover {
    background: #F2EDE0 !important;
    color: #263238 !important;
}

/* ── Checkbox groups — pill chip style ── */
.checkbox-group {
    gap: 6px !important;
    flex-wrap: wrap !important;
    padding: 2px 0 !important;
}
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
    line-height: 1.4 !important;
    margin: 2px !important;
}
.checkbox-label:hover {
    border-color: #8A9A7B !important;
    background: #E4EDE8 !important;
    color: #2E3E2E !important;
}
.checkbox-label.selected {
    background: #8A9A7B !important;
    border-color: #8A9A7B !important;
    color: #FFFDF7 !important;
    box-shadow: 0 1px 4px rgba(138,154,123,0.3) !important;
}
/* Visually hide the checkbox square while keeping click */
.checkbox-label input[type="checkbox"] {
    -webkit-appearance: none !important;
    appearance: none !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    position: absolute !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* ── Primary button — warm terracotta ── */
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
    transition: background 0.2s, box-shadow 0.2s !important;
}
button.primary:hover, .btn-primary:hover {
    background: #AD6B47 !important;
    box-shadow: 0 3px 14px rgba(197,123,87,0.35) !important;
}

/* ── Secondary / outline buttons ── */
button.secondary, .btn-secondary {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    color: #6F6A60 !important;
    border-radius: 9px !important;
    font-size: 12px !important;
    transition: background 0.15s, border-color 0.15s !important;
}
button.secondary:hover {
    background: #F2EDE0 !important;
    border-color: #B8B0A3 !important;
}

/* ── Tabs ── */
.tabs { border: none !important; background: transparent !important; }
.tab-nav {
    background: transparent !important;
    border-bottom: 1px solid #D8D0C3 !important;
    padding: 0 !important;
    gap: 0 !important;
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
.tabitem {
    background: transparent !important;
    border: none !important;
    padding: 18px 0 0 !important;
}

/* ── Examples table ── */
.examples > .label-wrap > span {
    font-size: 10px !important;
    color: #B8B0A3 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}
.examples table {
    background: transparent !important;
    border-collapse: separate !important;
    border-spacing: 0 4px !important;
}
.examples thead { display: none !important; }
.examples tbody tr {
    background: #FFFDF7 !important;
    border: 1px solid #D8D0C3 !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: background 0.15s !important;
}
.examples tbody tr:hover { background: #F2EDE0 !important; }
.examples td {
    color: #6F6A60 !important;
    font-size: 12px !important;
    border: none !important;
    padding: 8px 14px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 160px !important;
}

/* ── Markdown output ── */
.prose, .md { color: #263238 !important; }
.prose h1,.prose h2,.prose h3 { color: #263238 !important; font-weight: 500 !important; }
.prose strong { color: #263238 !important; }
.prose p { color: #3C3830 !important; line-height: 1.85 !important; }

/* ── Scrollbar (subtle) ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F7F3EA; }
::-webkit-scrollbar-thumb { background: #D8D0C3; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #B8B0A3; }
"""

HEADER_HTML = """
<div style="text-align:center; padding:52px 24px 44px;
            background:linear-gradient(180deg,#FFFDF7 0%,#F7F3EA 100%);
            border-radius:12px; border:1px solid #D8D0C3;
            margin-bottom:0;
            box-shadow:0 1px 6px rgba(38,50,56,0.04);">
  <p style="font-size:9px; letter-spacing:5px; text-transform:uppercase;
            color:#C8C4BC; margin:0 0 20px;
            font-family:'Helvetica Neue',Arial,sans-serif; font-weight:500;">
    Interior Design Studio
  </p>
  <h1 style="font-size:38px; font-weight:300; letter-spacing:2px;
             color:#263238; margin:0 0 18px; line-height:1.15;
             font-family:'Georgia','Times New Roman',serif;">
    Concept Board Generator
  </h1>
  <div style="width:28px; height:1.5px; background:#C57B57; margin:0 auto 20px;
              border-radius:1px;"></div>
  <p style="font-size:13px; color:#6F6A60; max-width:460px; margin:0 auto;
            line-height:1.85; font-family:'Helvetica Neue',Arial,sans-serif;">
    Select space type, activities, materials, and mood below to generate
    a complete design concept ready for presentation.
  </p>
</div>
"""

SECTION_LABEL_LEFT = """
<p style="font-size:9px; letter-spacing:3px; text-transform:uppercase;
          color:#B8B0A3; margin:0 0 6px; font-weight:600;
          font-family:'Helvetica Neue',Arial,sans-serif;">
  Space &amp; Mood
</p>
"""

SECTION_LABEL_RIGHT = """
<p style="font-size:9px; letter-spacing:3px; text-transform:uppercase;
          color:#B8B0A3; margin:0 0 6px; font-weight:600;
          font-family:'Helvetica Neue',Arial,sans-serif;">
  Programme &amp; Materials
</p>
"""

# ─── Gradio UI ────────────────────────────────────────────────────────────────

SPACE_LIST    = list(SPACE_TYPES.keys())
ACTIVITY_LIST = list(ACTIVITY_DATA.keys())
MATERIAL_LIST = list(MATERIAL_DATA.keys())
LIGHTING_LIST = list(LIGHTING_DATA.keys())
MOOD_LIST     = list(MOOD_DATA.keys())
SPATIAL_LIST  = list(SPATIAL_DATA.keys())

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

    with gr.Row(equal_height=False):

        # ── Left column: Space, Mood, free text, button ──────────────────
        with gr.Column(scale=1, min_width=230):
            gr.HTML(SECTION_LABEL_LEFT)
            space_in = gr.Dropdown(
                choices=SPACE_LIST, value="Library",
                label="Space Type",
            )
            mood_in = gr.Dropdown(
                choices=MOOD_LIST, value="Calm",
                label="Mood",
            )
            extra_in = gr.Textbox(
                label="Additional Concept Text",
                placeholder="e.g. biophilic wall, exposed structure, terrazzo…",
                lines=4,
            )
            gen_btn = gr.Button("Generate Concept  ✦", variant="primary", size="lg")

        # ── Right column: all CheckboxGroups ─────────────────────────────
        with gr.Column(scale=2):
            gr.HTML(SECTION_LABEL_RIGHT)
            activity_in = gr.CheckboxGroup(
                choices=ACTIVITY_LIST, label="UX / Activity",
            )
            material_in = gr.CheckboxGroup(
                choices=MATERIAL_LIST, label="Material",
            )
            lighting_in = gr.CheckboxGroup(
                choices=LIGHTING_LIST, label="Lighting",
            )
            spatial_in = gr.CheckboxGroup(
                choices=SPATIAL_LIST, label="Volume / Spatial Quality",
            )

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
             "Exposed ceiling joists, handmade ceramic tiles"],
            ["Office",
             ["Collaboration", "Learning"],
             ["Metal", "Glass"],
             ["Natural Light", "Diffused"],
             "Futuristic",
             ["Flexible", "Open"],
             "Biophilic green wall, sit-stand desks"],
            ["Community Space",
             ["Social", "Exhibition", "Collaboration"],
             ["Concrete", "Wood"],
             ["Natural Light", "Accent Lighting"],
             "Dynamic",
             ["Flowing", "High Ceiling"],
             "Mural art, modular furniture system"],
        ],
        inputs=[space_in, activity_in, material_in, lighting_in,
                mood_in, spatial_in, extra_in],
        label="Quick Examples",
    )

    with gr.Tabs():
        with gr.TabItem("  📝  English Prompt  "):
            prompt_out = gr.Textbox(
                label="Image-generation prompt",
                lines=5,
            )
        with gr.TabItem("  🏷️  Tags  "):
            tags_out = gr.Textbox(
                label="Hashtags",
                lines=3,
            )
        with gr.TabItem("  🇰🇷  Korean Statement  "):
            korean_out = gr.Markdown()
        with gr.TabItem("  🎨  Concept Board  "):
            board_out = gr.HTML()

    inputs  = [space_in, activity_in, material_in, lighting_in,
               mood_in, spatial_in, extra_in]
    outputs = [prompt_out, tags_out, korean_out, board_out]

    gen_btn.click(fn=generate_concept, inputs=inputs, outputs=outputs)
    extra_in.submit(fn=generate_concept, inputs=inputs, outputs=outputs)

if __name__ == "__main__":
    demo.launch()
