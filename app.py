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
    "Calm":       {"ko": "차분한",       "en_adj": "serene, tranquil, quietly composed",  "board_bg": "#F0ECE4"},
    "Minimal":    {"ko": "미니멀한",     "en_adj": "restrained, precise, uncluttered",    "board_bg": "#F5F4F0"},
    "Futuristic": {"ko": "미래지향적인", "en_adj": "forward-looking, innovative, sleek",  "board_bg": "#EAEEf4"},
    "Cozy":       {"ko": "아늑한",       "en_adj": "warm, inviting, intimate",            "board_bg": "#F5EDE0"},
    "Elegant":    {"ko": "우아한",       "en_adj": "refined, sophisticated, graceful",    "board_bg": "#EEEAE2"},
    "Dynamic":    {"ko": "역동적인",     "en_adj": "energetic, bold, expressive",         "board_bg": "#EAF0F0"},
    "Immersive":  {"ko": "몰입감 있는",  "en_adj": "atmospheric, enveloping, layered",    "board_bg": "#E8E4E0"},
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

def _luminance(h: str) -> float:
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255

def _text_on(h: str) -> str:
    return "#1C1A16" if _luminance(h) > 0.45 else "#F5F2EC"

def _md_bold_to_html(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

# ─── Output Builders ──────────────────────────────────────────────────────────

def build_english_prompt(space, activities, materials, lighting, mood, spatial, extra):
    sp  = SPACE_TYPES[space]
    md  = MOOD_DATA[mood]
    mat = ", ".join(m.lower() for m in materials)         if materials  else "mixed materials"
    lit = ", ".join(LIGHTING_DATA[l]["desc"] for l in lighting) if lighting  else "balanced lighting"
    spt = ", ".join(SPATIAL_DATA[s]["desc"]  for s in spatial)  if spatial   else "open plan"
    act = ", ".join(a.lower() for a in activities)        if activities else "multipurpose"
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
        + [f"#{a.lower()}"                        for a in activities]
        + [f"#{m.lower()}"                        for m in materials]
        + [f"#{l.replace(' ', '').lower()}"       for l in lighting]
        + [f"#{mood.lower()}design"]
        + [f"#{s.replace(' ', '').lower()}"       for s in spatial]
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

# ─── HTML Concept Board Components ───────────────────────────────────────────

def _img_tile(label: str, icon: str, col: str, light: str, height: str = "100%") -> str:
    text = _text_on(col)
    return (
        f'<div style="background:linear-gradient(145deg,{col},{light}); border-radius:10px;'
        f' height:{height}; min-height:130px; display:flex; flex-direction:column;'
        f' align-items:center; justify-content:center; gap:10px;">'
        f'<span style="font-size:34px;">{icon}</span>'
        f'<span style="font-size:10px; font-weight:700; letter-spacing:1.5px;'
        f' text-transform:uppercase; color:{text}; opacity:0.75;'
        f' text-align:center; padding:0 14px;">{label}</span>'
        f'</div>'
    )


def _material_block(name: str) -> str:
    d    = MATERIAL_DATA[name]
    text = _text_on(d["hex"])
    return (
        f'<div style="flex:1; min-width:76px;">'
        f'<div style="height:52px; background:linear-gradient(150deg,{d["hex"]},{d["light"]});'
        f' border-radius:8px; margin-bottom:6px; position:relative;">'
        f'<span style="position:absolute; bottom:5px; left:8px; font-size:9px;'
        f' font-weight:700; letter-spacing:1px; text-transform:uppercase;'
        f' color:{text}; opacity:0.7;">{name.upper()}</span>'
        f'</div>'
        f'<div style="font-size:11px; color:#5A5650; font-weight:500;">{d["ko"]}</div>'
        f'<div style="font-size:10px; color:#9E9A94; margin-top:2px;">{d["finish"]}</div>'
        f'</div>'
    )


def _chip(label: str, bg: str = "#EDE8DF", fg: str = "#4A4640") -> str:
    return (
        f'<span style="display:inline-block; padding:5px 13px; margin:3px;'
        f' background:{bg}; border-radius:20px; font-size:11px;'
        f' font-weight:500; color:{fg}; letter-spacing:0.2px;">{label}</span>'
    )


def build_html_board(space, activities, materials, lighting, mood, spatial, extra, prompt):
    sp  = SPACE_TYPES[space]
    md  = MOOD_DATA[mood]
    bg  = md["board_bg"]

    first_mat   = materials[0] if materials else "Wood"
    accent      = MATERIAL_DATA[first_mat]["hex"]
    accent_l    = MATERIAL_DATA[first_mat]["light"]

    # Pad material list to at least 3 for the image tiles
    mat_list = (materials or ["Wood", "Concrete", "Stone"])
    tile_mats = (mat_list * 3)[:3]

    hero_tile = _img_tile(
        sp["img_labels"][0], sp["img_icons"][0],
        MATERIAL_DATA[tile_mats[0]]["hex"], MATERIAL_DATA[tile_mats[0]]["light"],
    )
    mid_tile = _img_tile(
        sp["img_labels"][1], sp["img_icons"][1],
        MATERIAL_DATA[tile_mats[1]]["hex"], MATERIAL_DATA[tile_mats[1]]["light"],
    )
    bot_tile = _img_tile(
        sp["img_labels"][2], sp["img_icons"][2],
        MATERIAL_DATA[tile_mats[2]]["hex"], MATERIAL_DATA[tile_mats[2]]["light"],
    )

    mat_blocks = "".join(_material_block(m) for m in (materials or ["Wood"]))

    act_chips = "".join(_chip(a, "#EEE8DF", "#4A4640") for a in activities) or _chip("—", "#F5F2EE", "#AAA")
    lit_chips = "".join(_chip(l, "#EAE4DC", "#4A3C36") for l in lighting)  or _chip("—", "#F5F2EE", "#AAA")
    spa_chips = "".join(_chip(s, "#E4EAE8", "#384A46") for s in spatial)   or _chip("—", "#F5F2EE", "#AAA")

    ko_html  = _md_bold_to_html(build_korean(space, activities, materials, lighting, mood, spatial, extra))

    tags_str  = build_tags(space, activities, materials, lighting, mood, spatial)
    tag_chips = "".join(_chip(t, "#F0EBE3", "#6B5E54") for t in tags_str.split("  "))

    return f"""
<div style="font-family:'Helvetica Neue',Arial,sans-serif; background:{bg};
            padding:40px; border-radius:18px; max-width:900px; margin:0 auto;
            box-sizing:border-box; color:#1C1A16;">

  <!-- ── Header ── -->
  <div style="margin-bottom:32px;">
    <p style="font-size:10px; letter-spacing:3.5px; text-transform:uppercase;
              color:#9E9A94; margin:0 0 10px;">Interior Concept Board &nbsp;·&nbsp; {space}</p>
    <h1 style="font-size:28px; font-weight:700; letter-spacing:-0.5px;
               margin:0 0 6px; color:#1C1A16;">
      {sp['ko']} <span style="color:{accent};">·</span> {mood}
    </h1>
    <p style="font-size:14px; color:#6B6860; margin:0; line-height:1.6;">
      {sp['en_char'].replace(',', ' &nbsp;·&nbsp;')}
    </p>
    <div style="width:44px; height:3px; background:{accent};
                border-radius:2px; margin-top:16px;"></div>
  </div>

  <!-- ── Image Grid: hero left + 2 stacked right ── -->
  <div style="display:grid; grid-template-columns:1.6fr 1fr;
              grid-template-rows:1fr 1fr; gap:12px; margin-bottom:26px;
              min-height:300px;">
    <div style="grid-column:1; grid-row:1/3;">{hero_tile}</div>
    <div style="grid-column:2; grid-row:1;">{mid_tile}</div>
    <div style="grid-column:2; grid-row:2;">{bot_tile}</div>
  </div>

  <!-- ── Material Palette ── -->
  <div style="background:#FFFFFF; border-radius:12px; padding:22px;
              margin-bottom:14px; border:1px solid #E8E2D8;">
    <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
              color:#9E9A94; margin:0 0 16px;">Material Palette</p>
    <div style="display:flex; gap:14px; flex-wrap:wrap;">{mat_blocks}</div>
  </div>

  <!-- ── Design Specs ── -->
  <div style="display:grid; grid-template-columns:1fr 1fr 1fr;
              gap:12px; margin-bottom:14px;">

    <div style="background:#FFFFFF; border-radius:12px; padding:18px;
                border:1px solid #E8E2D8;">
      <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                color:#9E9A94; margin:0 0 10px;">UX Activity</p>
      <div>{act_chips}</div>
    </div>

    <div style="background:#FFFFFF; border-radius:12px; padding:18px;
                border:1px solid #E8E2D8;">
      <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                color:#9E9A94; margin:0 0 10px;">Lighting</p>
      <div>{lit_chips}</div>
    </div>

    <div style="background:#FFFFFF; border-radius:12px; padding:18px;
                border:1px solid #E8E2D8;">
      <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                color:#9E9A94; margin:0 0 10px;">Spatial Quality</p>
      <div>{spa_chips}</div>
    </div>
  </div>

  <!-- ── Korean Concept Statement ── -->
  <div style="background:#FFFFFF; border-radius:12px; padding:22px;
              margin-bottom:14px; border:1px solid #E8E2D8;
              border-left:4px solid {accent};">
    <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
              color:#9E9A94; margin:0 0 10px;">개념 설명 · Concept Statement</p>
    <p style="font-size:14px; color:#3C3830; line-height:1.9; margin:0;">
      {ko_html}
    </p>
  </div>

  <!-- ── Tags ── -->
  <div style="background:#FFFFFF; border-radius:12px; padding:18px;
              margin-bottom:14px; border:1px solid #E8E2D8;">
    <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
              color:#9E9A94; margin:0 0 10px;">Tags</p>
    <div>{tag_chips}</div>
  </div>

  <!-- ── Prompt Reference ── -->
  <div style="background:rgba(0,0,0,0.03); border-radius:12px; padding:18px;
              border:1px solid #E8E2D8;">
    <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
              color:#9E9A94; margin:0 0 8px;">Image Prompt Reference</p>
    <p style="font-size:12px; color:#6B6860; margin:0; line-height:1.8;
              font-style:italic;">&ldquo;{prompt}&rdquo;</p>
  </div>

  <!-- ── Footer ── -->
  <div style="text-align:center; margin-top:28px; padding-top:18px;
              border-top:1px solid #E0DCD4;">
    <p style="font-size:9px; letter-spacing:3px; text-transform:uppercase;
              color:#B8B4AE; margin:0;">AI Interior Concept Board Generator</p>
  </div>

</div>
"""

# ─── Main Orchestrator ────────────────────────────────────────────────────────

def generate_concept(space, activities, materials, lighting, mood, spatial, extra):
    space  = space or "Library"
    mood   = mood  or "Calm"
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

# ─── Gradio UI ────────────────────────────────────────────────────────────────

SPACE_LIST    = list(SPACE_TYPES.keys())
ACTIVITY_LIST = list(ACTIVITY_DATA.keys())
MATERIAL_LIST = list(MATERIAL_DATA.keys())
LIGHTING_LIST = list(LIGHTING_DATA.keys())
MOOD_LIST     = list(MOOD_DATA.keys())
SPATIAL_LIST  = list(SPATIAL_DATA.keys())

CSS = """
.gradio-container { max-width: 1080px !important; margin: 0 auto; }
footer { display: none !important; }
"""

with gr.Blocks(
    title="AI Interior Concept Board",
    theme=gr.themes.Soft(primary_hue="stone", neutral_hue="stone"),
    css=CSS,
) as demo:

    gr.Markdown(
        """
        # 🏛️ AI Interior Concept Board Generator
        Configure your space below. Combine multiple selections to build a layered design concept.
        """
    )

    with gr.Row(equal_height=False):

        # ── Left column: single-select + free text ──
        with gr.Column(scale=1, min_width=220):
            space_in   = gr.Dropdown(choices=SPACE_LIST, value="Library",
                                     label="Space Type")
            mood_in    = gr.Dropdown(choices=MOOD_LIST,  value="Calm",
                                     label="Mood")
            extra_in   = gr.Textbox(
                label="Additional Concept Text",
                placeholder="e.g. biophilic wall, exposed structure, terrazzo floors…",
                lines=4,
            )
            gen_btn    = gr.Button("Generate Concept ✦", variant="primary", size="lg")

        # ── Right column: multi-select checkboxes ──
        with gr.Column(scale=2):
            activity_in = gr.CheckboxGroup(choices=ACTIVITY_LIST,
                                           label="UX / Activity")
            material_in = gr.CheckboxGroup(choices=MATERIAL_LIST,
                                           label="Material")
            lighting_in = gr.CheckboxGroup(choices=LIGHTING_LIST,
                                           label="Lighting")
            spatial_in  = gr.CheckboxGroup(choices=SPATIAL_LIST,
                                           label="Volume / Spatial Quality")

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
             "Mural art, adaptable modular furniture"],
        ],
        inputs=[space_in, activity_in, material_in, lighting_in,
                mood_in, spatial_in, extra_in],
        label="Quick Examples",
    )

    with gr.Tabs():
        with gr.TabItem("📝 English Prompt"):
            prompt_out = gr.Textbox(
                label="Image-generation prompt  (Midjourney · DALL·E · Stable Diffusion)",
                lines=5, show_copy_button=True,
            )
        with gr.TabItem("🏷️ Tags"):
            tags_out = gr.Textbox(
                label="Hashtags", lines=3, show_copy_button=True,
            )
        with gr.TabItem("🇰🇷 Korean Concept Statement"):
            korean_out = gr.Markdown()
        with gr.TabItem("🎨 Concept Board"):
            board_out = gr.HTML()

    inputs  = [space_in, activity_in, material_in, lighting_in,
               mood_in, spatial_in, extra_in]
    outputs = [prompt_out, tags_out, korean_out, board_out]

    gen_btn.click(fn=generate_concept, inputs=inputs, outputs=outputs)
    # Also trigger on Enter inside the free-text box
    extra_in.submit(fn=generate_concept, inputs=inputs, outputs=outputs)

if __name__ == "__main__":
    demo.launch()
