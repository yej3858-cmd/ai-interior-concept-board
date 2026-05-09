import gradio as gr
import random

# ─── Style Knowledge Base ─────────────────────────────────────────────────────

STYLES = {
    "modern": {
        "adjectives": ["sleek", "clean-lined", "geometric", "minimalist"],
        "materials": ["polished concrete", "tempered glass", "brushed steel", "lacquered wood"],
        "colors_hex": ["#F2F2F0", "#1A1A1A", "#C8B99A", "#8C7B6B", "#E8E4DF"],
        "color_names": ["Off White", "Charcoal", "Sand", "Mocha", "Linen"],
        "lighting": "recessed LED strips, slim floor lamps with metal shades",
        "ko_style": "모던",
        "ko_desc": "직선과 기하학적 형태를 강조한 세련되고 깔끔한 스타일",
    },
    "scandinavian": {
        "adjectives": ["hygge", "cozy", "functional", "natural", "serene"],
        "materials": ["light oak", "white-painted wood", "wool textiles", "ceramic", "rattan"],
        "colors_hex": ["#FFFFFF", "#E8E2D9", "#C4D4C8", "#9EB5A3", "#4A5E52"],
        "color_names": ["Pure White", "Warm Ivory", "Sage Mist", "Forest Sage", "Deep Pine"],
        "lighting": "diffused pendant lights, candlelight, soft natural light",
        "ko_style": "스칸디나비안",
        "ko_desc": "자연 소재와 따뜻한 색감으로 아늑함과 기능성을 동시에 추구하는 북유럽 스타일",
    },
    "industrial": {
        "adjectives": ["raw", "urban", "edgy", "exposed", "vintage"],
        "materials": ["exposed brick", "raw steel", "reclaimed wood", "concrete", "leather"],
        "colors_hex": ["#3C3C3C", "#6B5B4E", "#A89070", "#C4B8A8", "#F0EDE8"],
        "color_names": ["Iron", "Rust Brown", "Aged Bronze", "Stone", "Chalk"],
        "lighting": "Edison bulb pendants, pipe-style wall fixtures, cage sconces",
        "ko_style": "인더스트리얼",
        "ko_desc": "날것의 소재와 도시적인 감성이 어우러진 거친 매력의 스타일",
    },
    "bohemian": {
        "adjectives": ["eclectic", "layered", "artistic", "free-spirited", "colorful"],
        "materials": ["macramé", "woven textiles", "terracotta", "rattan", "vintage fabric"],
        "colors_hex": ["#C17B3E", "#8B4513", "#D4956A", "#6B8E6E", "#9370DB"],
        "color_names": ["Burnt Sienna", "Saddle Brown", "Terracotta", "Sage", "Lavender"],
        "lighting": "fairy lights, Moroccan lanterns, pillar candles",
        "ko_style": "보헤미안",
        "ko_desc": "다양한 문화와 예술적 감각이 자유롭게 어우러진 에클렉틱한 스타일",
    },
    "japanese": {
        "adjectives": ["wabi-sabi", "zen", "serene", "natural", "timeless"],
        "materials": ["bamboo", "shoji paper", "tatami", "natural stone", "hand-thrown ceramics"],
        "colors_hex": ["#F5F0E8", "#8B7355", "#5C7A5C", "#2F4F2F", "#C8B89A"],
        "color_names": ["Washi White", "Teak", "Bamboo Green", "Pine", "Rice Paper"],
        "lighting": "washi paper lanterns, indirect cove lighting, filtered natural light",
        "ko_style": "재패니즈 젠",
        "ko_desc": "자연과의 조화 속에서 고요함과 단순미를 추구하는 일본식 선(禪) 스타일",
    },
    "luxury": {
        "adjectives": ["opulent", "sophisticated", "refined", "grand", "timeless"],
        "materials": ["Calacatta marble", "velvet", "antique brass", "mirrored surfaces", "silk"],
        "colors_hex": ["#1C1C1C", "#B8960C", "#F5ECD7", "#8B7355", "#E8D5B5"],
        "color_names": ["Ebony", "Antique Gold", "Champagne", "Bronze", "Cream"],
        "lighting": "crystal chandeliers, brass wall sconces, curated accent lighting",
        "ko_style": "럭셔리",
        "ko_desc": "고급 소재와 정교한 디테일로 완성하는 품격 있는 럭셔리 스타일",
    },
    "coastal": {
        "adjectives": ["breezy", "relaxed", "nautical", "sun-drenched", "casual"],
        "materials": ["whitewashed wood", "linen", "jute", "sea glass", "driftwood"],
        "colors_hex": ["#FFFFFF", "#87CEEB", "#4682B4", "#F5DEB3", "#708090"],
        "color_names": ["White Sand", "Sky Blue", "Ocean Blue", "Wheat", "Sea Fog"],
        "lighting": "abundant natural light, rattan pendants, weathered lanterns",
        "ko_style": "코스탈",
        "ko_desc": "바다의 시원함과 자연스러운 여유로움이 느껴지는 해변 감성 스타일",
    },
    "rustic": {
        "adjectives": ["warm", "earthy", "textured", "handcrafted", "inviting"],
        "materials": ["reclaimed wood", "fieldstone", "wrought iron", "chunky wool", "aged leather"],
        "colors_hex": ["#8B4513", "#A0785A", "#C4A882", "#E8D5B0", "#6B8E23"],
        "color_names": ["Chestnut", "Caramel", "Burlap", "Parchment", "Olive"],
        "lighting": "Edison filament bulbs, antler chandeliers, firelight",
        "ko_style": "러스틱",
        "ko_desc": "자연 소재의 질감과 따뜻한 색조로 포근하고 정겨운 감성을 자아내는 스타일",
    },
}

ROOMS = {
    "bedroom": {
        "ko": "침실",
        "desc": "A restful sanctuary layered with soft textiles and calming illumination",
        "icons": ["🛏️", "🕯️", "🪞"],
    },
    "living room": {
        "ko": "거실",
        "desc": "An inviting gathering space anchored by comfortable seating and curated objects",
        "icons": ["🛋️", "🪴", "📚"],
    },
    "kitchen": {
        "ko": "주방",
        "desc": "A functional culinary space balancing form and everyday practicality",
        "icons": ["🍳", "🌿", "☕"],
    },
    "bathroom": {
        "ko": "욕실",
        "desc": "A spa-inspired retreat elevated by premium finishes and serene details",
        "icons": ["🛁", "🪴", "🕯️"],
    },
    "office": {
        "ko": "홈 오피스",
        "desc": "A focused workspace designed to inspire productivity and creative thought",
        "icons": ["🖥️", "📐", "🌱"],
    },
    "dining room": {
        "ko": "다이닝룸",
        "desc": "An elegant entertaining space set for memorable shared meals",
        "icons": ["🕯️", "🍽️", "🌸"],
    },
}

MOODS = {
    "calm":       {"en": "serene and calming",      "ko": "고요하고 평온한"},
    "energetic":  {"en": "vibrant and energizing",  "ko": "활기차고 생동감 있는"},
    "romantic":   {"en": "warm and romantic",        "ko": "따뜻하고 로맨틱한"},
    "productive": {"en": "focused and productive",   "ko": "집중력을 높이는"},
    "cozy":       {"en": "cozy and intimate",        "ko": "아늑하고 포근한"},
    "fresh":      {"en": "fresh and airy",           "ko": "신선하고 시원한"},
    "elegant":    {"en": "refined and elegant",      "ko": "우아하고 세련된"},
    "playful":    {"en": "playful and expressive",   "ko": "개성 넘치고 표현적인"},
}

STYLE_ALIASES = {
    "minimalist": "modern", "minimal": "modern",
    "nordic": "scandinavian", "scandi": "scandinavian", "hygge": "scandinavian",
    "zen": "japanese", "japandi": "japanese", "wabi": "japanese",
    "boho": "bohemian", "eclectic": "bohemian",
    "glam": "luxury", "opulent": "luxury",
    "beach": "coastal", "nautical": "coastal",
    "farmhouse": "rustic", "cottage": "rustic",
    "urban": "industrial", "loft": "industrial",
}

ROOM_ALIASES = {
    "bed": "bedroom", "sleep": "bedroom",
    "living": "living room", "lounge": "living room", "sitting": "living room",
    "bath": "bathroom", "toilet": "bathroom",
    "work": "office", "study": "office", "workspace": "office",
    "dining": "dining room", "dinner": "dining room",
    "cook": "kitchen",
}

# ─── Keyword Detection ────────────────────────────────────────────────────────

def detect_keywords(keywords: str):
    kw = keywords.lower()
    words = kw.split()

    detected_style = "modern"
    for word in words:
        if word in STYLE_ALIASES:
            detected_style = STYLE_ALIASES[word]
            break
        if word in STYLES:
            detected_style = word
            break

    detected_room = "living room"
    for word in words:
        if word in ROOM_ALIASES:
            detected_room = ROOM_ALIASES[word]
            break
        for room in ROOMS:
            if room in kw:
                detected_room = room
                break

    detected_mood = "calm"
    for word in words:
        if word in MOODS:
            detected_mood = word
            break

    stop = set(list(STYLES) + list(STYLE_ALIASES) + list(ROOMS) + list(ROOM_ALIASES)
               + list(MOODS) + ["room", "the", "and", "with", "for", "in", "a", "an"])
    extra = [w for w in words if w not in stop and len(w) > 3][:3]

    return detected_style, detected_room, detected_mood, extra

# ─── Output Generators ───────────────────────────────────────────────────────

def generate_english_prompt(style_data, style_name, room, mood_data, extra_terms):
    adj = random.sample(style_data["adjectives"], min(3, len(style_data["adjectives"])))
    mats = random.sample(style_data["materials"], min(3, len(style_data["materials"])))
    extra_str = f", {', '.join(extra_terms)}" if extra_terms else ""
    return (
        f"A {mood_data['en']} {style_name} {room}, showcasing {', '.join(adj)} design "
        f"with {', '.join(mats)}{extra_str}. {style_data['lighting'].capitalize()}. "
        f"Interior design photography, professionally staged, editorial quality, "
        f"high-end {room.replace(' ', '_')} design concept."
    )


def generate_tags(style_name, room, mood, extra_terms):
    room_tag = room.replace(" ", "")
    style_tag = style_name.replace(" ", "")
    tags = [
        f"#{style_tag}", f"#{room_tag}", f"#interiordesign", f"#homedecor",
        f"#conceptboard", f"#moodboard", f"#designinspiration",
        f"#{mood}vibes", f"#interiors", f"#homedesign",
    ]
    tags += [f"#{t}" for t in extra_terms]
    return "  ".join(tags)


def generate_korean_statement(style_data, room_data, mood_data, extra_terms):
    extra_ko = f" '{', '.join(extra_terms)}' 요소를 가미하여" if extra_terms else ""
    return (
        f"### {style_data['ko_style']} {room_data['ko']} 콘셉트\n\n"
        f"{style_data['ko_desc']}.\n\n"
        f"이 공간은 **{mood_data['ko']}** 분위기를 핵심 키워드로{extra_ko}, "
        f"소재와 컬러 팔레트가 섬세하게 큐레이션된 {room_data['ko']} 디자인을 제안합니다. "
        f"일상의 공간에 디자인의 가치를 더해 매일을 특별하게 만드는 "
        f"인테리어 경험을 목표로 합니다.\n\n"
        f"**핵심 가치:** 기능성 &nbsp;·&nbsp; 심미성 &nbsp;·&nbsp; 지속가능성"
    )

# ─── HTML Concept Board ───────────────────────────────────────────────────────

def _luminance(hex_color: str) -> float:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _text_on(hex_color: str) -> str:
    return "#1A1A1A" if _luminance(hex_color) > 0.45 else "#F5F2EE"


def _lighten(hex_color: str, amount: int = 30) -> str:
    r = min(255, int(hex_color[1:3], 16) + amount)
    g = min(255, int(hex_color[3:5], 16) + amount)
    b = min(255, int(hex_color[5:7], 16) + amount)
    return f"#{r:02X}{g:02X}{b:02X}"


def _placeholder_tile(label: str, icon: str, color: str, height: str = "180px") -> str:
    lighter = _lighten(color, 35)
    text = _text_on(color)
    return (
        f'<div style="height:{height}; background:linear-gradient(135deg,{color},{lighter}); '
        f'border-radius:10px; display:flex; flex-direction:column; align-items:center; '
        f'justify-content:center; gap:8px;">'
        f'<span style="font-size:32px;">{icon}</span>'
        f'<span style="font-size:12px; font-weight:600; color:{text}; opacity:0.85; '
        f'text-align:center; padding:0 12px;">{label}</span>'
        f'</div>'
    )


def _swatch(hex_color: str, name: str) -> str:
    text = _text_on(hex_color)
    return (
        f'<div style="display:flex; flex-direction:column; align-items:center; gap:5px;">'
        f'<div style="width:64px; height:64px; border-radius:50%; background:{hex_color}; '
        f'border:2px solid rgba(0,0,0,0.08); box-shadow:0 2px 8px rgba(0,0,0,0.12);"></div>'
        f'<span style="font-size:11px; font-weight:500; color:#555; text-align:center;">{name}</span>'
        f'<span style="font-size:10px; color:#999; font-family:monospace;">{hex_color}</span>'
        f'</div>'
    )


def generate_concept_board_html(style_name, style_data, room, room_data, mood_data, extra_terms, prompt):
    colors = style_data["colors_hex"]
    bg      = colors[0]
    accent  = colors[3] if len(colors) > 3 else colors[-1]
    text_m  = _text_on(bg)
    text_s  = "#666" if _luminance(bg) > 0.45 else "#BBB"
    panel   = "rgba(255,255,255,0.28)" if _luminance(bg) > 0.45 else "rgba(0,0,0,0.18)"

    icons = room_data["icons"]
    tiles = [
        _placeholder_tile(f"{style_name.title()} {room.title()}", icons[0],
                          colors[1] if len(colors) > 1 else colors[0]),
        _placeholder_tile("Materials & Textures", icons[1] if len(icons) > 1 else "🪵",
                          colors[2] if len(colors) > 2 else colors[0]),
        _placeholder_tile("Lighting Concept", icons[2] if len(icons) > 2 else "💡",
                          colors[3] if len(colors) > 3 else colors[0]),
        _placeholder_tile("Detail & Finish", "✨",
                          colors[4] if len(colors) > 4 else colors[0]),
    ]

    swatches_html = "".join(_swatch(h, n)
                            for h, n in zip(style_data["colors_hex"], style_data["color_names"]))

    material_tags = "".join(
        f'<span style="display:inline-block; padding:5px 13px; margin:4px; '
        f'background:rgba(0,0,0,0.07); border-radius:20px; font-size:12px; color:{text_s};">'
        f'{m}</span>'
        for m in style_data["materials"]
    )

    return f"""
<div style="font-family:'Helvetica Neue',Arial,sans-serif; background:{bg};
            padding:32px; border-radius:16px; color:{text_m}; max-width:860px; margin:0 auto;">

  <!-- Header -->
  <div style="text-align:center; margin-bottom:28px; padding-bottom:22px;
              border-bottom:1px solid rgba(0,0,0,0.1);">
    <p style="font-size:10px; letter-spacing:3px; text-transform:uppercase;
              color:{text_s}; margin:0 0 6px;">Interior Concept Board</p>
    <h1 style="font-size:30px; font-weight:700; margin:0 0 6px; color:{text_m};">
      {style_data['ko_style']} {room_data['ko']}
    </h1>
    <h2 style="font-size:16px; font-weight:400; color:{text_s}; margin:0 0 10px;">
      {style_name.title()} {room.title()} &nbsp;·&nbsp; {mood_data['en'].title()}
    </h2>
    <p style="font-size:12px; color:{text_s}; max-width:560px; margin:0 auto; line-height:1.65;">
      {room_data['desc']}
    </p>
  </div>

  <!-- 2×2 Image Grid -->
  <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:22px;">
    {tiles[0]}{tiles[1]}{tiles[2]}{tiles[3]}
  </div>

  <!-- Color Palette -->
  <div style="background:{panel}; border-radius:12px; padding:20px; margin-bottom:16px;">
    <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
              color:{text_s}; margin:0 0 14px;">Color Palette</p>
    <div style="display:flex; gap:18px; flex-wrap:wrap; justify-content:center;">
      {swatches_html}
    </div>
  </div>

  <!-- Materials -->
  <div style="background:{panel}; border-radius:12px; padding:20px; margin-bottom:16px;">
    <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
              color:{text_s}; margin:0 0 10px;">Materials & Finishes</p>
    <div>{material_tags}</div>
  </div>

  <!-- Lighting -->
  <div style="background:{panel}; border-radius:12px; padding:20px; margin-bottom:16px;">
    <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
              color:{text_s}; margin:0 0 8px;">Lighting & Atmosphere</p>
    <p style="font-size:13px; color:{text_s}; margin:0; line-height:1.65;">
      {style_data['lighting'].capitalize()}
    </p>
  </div>

  <!-- Prompt Preview -->
  <div style="background:rgba(0,0,0,0.06); border-radius:12px; padding:20px;
              border-left:4px solid {accent};">
    <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
              color:{text_s}; margin:0 0 8px;">Design Prompt</p>
    <p style="font-size:12px; color:{text_s}; margin:0; line-height:1.75; font-style:italic;">
      &ldquo;{prompt}&rdquo;
    </p>
  </div>

  <!-- Footer -->
  <div style="text-align:center; margin-top:22px; padding-top:16px;
              border-top:1px solid rgba(0,0,0,0.08);">
    <p style="font-size:10px; color:{text_s}; letter-spacing:2px;
              text-transform:uppercase; margin:0;">
      AI Interior Concept Board Generator
    </p>
  </div>

</div>
"""

# ─── Main Function ────────────────────────────────────────────────────────────

def generate_concept(keywords: str):
    if not keywords.strip():
        empty = "<p style='color:#888; font-family:sans-serif;'>Enter keywords above and click <strong>Generate</strong>.</p>"
        return "", "", "", empty

    style_name, room, mood, extra = detect_keywords(keywords)
    style_data = STYLES[style_name]
    room_data  = ROOMS[room]
    mood_data  = MOODS[mood]

    en_prompt = generate_english_prompt(style_data, style_name, room, mood_data, extra)
    tags      = generate_tags(style_name, room, mood, extra)
    ko_stmt   = generate_korean_statement(style_data, room_data, mood_data, extra)
    board     = generate_concept_board_html(style_name, style_data, room, room_data, mood_data, extra, en_prompt)

    return en_prompt, tags, ko_stmt, board

# ─── Gradio UI ────────────────────────────────────────────────────────────────

EXAMPLES = [
    ["modern minimalist living room calm"],
    ["scandinavian bedroom cozy"],
    ["industrial office productive"],
    ["bohemian colorful bedroom romantic"],
    ["japanese zen bathroom fresh"],
    ["luxury dining room elegant"],
    ["coastal kitchen fresh breezy"],
    ["rustic bedroom cozy warm"],
]

CSS = """
.gradio-container { max-width: 980px !important; margin: 0 auto; }
footer { display: none !important; }
"""

with gr.Blocks(
    title="AI Interior Concept Board",
    theme=gr.themes.Soft(primary_hue="stone", neutral_hue="stone"),
    css=CSS,
) as demo:
    gr.Markdown(
        """
        # 🏠 AI Interior Concept Board Generator
        Describe your space with **style · room · mood** keywords and receive a full design concept instantly — no AI image API required.

        **Styles:** modern · scandinavian · industrial · bohemian · japanese · luxury · coastal · rustic
        **Rooms:** bedroom · living room · kitchen · bathroom · office · dining room
        **Moods:** calm · cozy · elegant · fresh · romantic · energetic · productive · playful
        """
    )

    with gr.Row(equal_height=True):
        keyword_input = gr.Textbox(
            label="Design Keywords",
            placeholder="e.g.  scandinavian bedroom cozy natural",
            lines=2,
            scale=5,
        )
        generate_btn = gr.Button("Generate Concept ✦", variant="primary", scale=1, min_width=160)

    gr.Examples(examples=EXAMPLES, inputs=keyword_input, label="Quick Examples")

    with gr.Tabs():
        with gr.TabItem("📝 English Prompt"):
            prompt_out = gr.Textbox(
                label="Image-generation prompt (copy into Midjourney, DALL·E, Stable Diffusion…)",
                lines=5,
                show_copy_button=True,
            )
        with gr.TabItem("🏷️ Tags"):
            tags_out = gr.Textbox(
                label="Hashtags for social media / project tagging",
                lines=3,
                show_copy_button=True,
            )
        with gr.TabItem("🇰🇷 Korean Concept Statement"):
            korean_out = gr.Markdown(label="Korean Concept Statement")
        with gr.TabItem("🎨 Concept Board"):
            board_out = gr.HTML(label="Visual Concept Board")

    generate_btn.click(
        fn=generate_concept,
        inputs=keyword_input,
        outputs=[prompt_out, tags_out, korean_out, board_out],
    )
    keyword_input.submit(
        fn=generate_concept,
        inputs=keyword_input,
        outputs=[prompt_out, tags_out, korean_out, board_out],
    )

if __name__ == "__main__":
    demo.launch()
