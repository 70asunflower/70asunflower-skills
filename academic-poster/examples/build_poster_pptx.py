"""
Build Academic Roll-Up Banner Poster in PPTX (30 cm x 80 cm)
Exact 1:2 Mathematical & Visual Replica of academic_poster_60x160cm.pdf

Key Specifications:
- Canvas: 30 cm x 80 cm (Exact 1:2 scale of 60 cm x 160 cm)
- Content Box: 28.0 cm width with 1.0 cm safe margin on left and right
- Section Headers: Left-aligned Navy banner with amber vertical bar, 22.5pt bold SimHei (45pt in 1:1)
- Subheads: Left-aligned pill bars, 14.0 - 14.5pt bold SimHei (28 - 29pt in 1:1)
- Body Text: 15.0pt Noto Serif SC (思源宋体), strictly >= 30pt in 1:1, line-height 1.35
- Captions: 11.5pt Noto Serif SC bold (23pt in 1:1), centered under figures
- References & Funding: 11.0pt Noto Serif SC (22pt in 1:1)
- Typography: Tuned column widths ensuring zero orphaned punctuation across all cards
- Figures: Exact 1:2 dimensions matching ReportLab canvas
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml

# Initialize Presentation with exact 30cm x 80cm slide size (1:2 of 60cm x 160cm)
prs = Presentation()
prs.slide_width = Cm(30)
prs.slide_height = Cm(80)
slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

# 1. Exact Color Palette (Matched to CMYK in PDF)
C_PRIMARY = RGBColor(15, 41, 74)     # #0F294A Academic Navy
C_ACCENT = RGBColor(194, 130, 18)    # #C28212 Warm Gold
C_SLATE = RGBColor(43, 76, 126)      # #2B4C7E Slate Blue
C_TEXT_MAIN = RGBColor(26, 32, 44)   # #1A202C Body Charcoal
C_TEXT_MUTED = RGBColor(51, 65, 85)  # #334155 Secondary Text
C_BG_CARD = RGBColor(248, 250, 252)  # #F8FAFC Card BG
C_BORDER = RGBColor(203, 213, 225)   # #CBD5E1 Border Gray
C_WHITE = RGBColor(255, 255, 255)
C_INFO_BG = RGBColor(254, 252, 247)  # Warm cream
C_INFO_BORDER = RGBColor(200, 161, 101) # Amber/Gold

def apply_east_asian_font(run, font_name="Noto Serif SC"):
    """Ensure East Asian font tag is explicitly declared in OpenXML"""
    rPr = run._r.get_or_add_rPr()
    ea = parse_xml(f'<a:ea xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" typeface="{font_name}"/>')
    rPr.append(ea)

def add_run(p, text, font_name="Noto Serif SC", size_pt=15.0, bold=False, color_rgb=C_TEXT_MAIN):
    run = p.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.color.rgb = color_rgb
    apply_east_asian_font(run, font_name)
    return run

def set_round_radius(shape, adj_val=3000):
    """Set subtle rounded corner radius in OpenXML"""
    try:
        spPr = shape._sp.spPr
        prstGeom = spPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom')
        if prstGeom is not None:
            avLst = prstGeom.find('{http://schemas.openxmlformats.org/drawingml/2006/main}avLst')
            if avLst is not None:
                avLst.clear()
                gd = parse_xml(f'<a:gd xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="adj" fmla="val {adj_val}"/>')
                avLst.append(gd)
    except Exception:
        pass

def remove_shadow(shape):
    """Remove default PowerPoint drop shadow for flat academic style"""
    try:
        spPr = shape._sp.spPr
        effectLst = spPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}effectLst')
        if effectLst is not None:
            spPr.remove(effectLst)
    except Exception:
        pass

def create_card(slide, left, top, width, height, bg_color=C_BG_CARD, border_color=C_BORDER, line_width_pt=0.75, radius_adj=3000):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(line_width_pt)
    else:
        shape.line.fill.background()
    set_round_radius(shape, radius_adj)
    remove_shadow(shape)
    return shape

def create_section_header(slide, left, top, width, height, title):
    """
    Exact replica of PDF section header:
    Solid navy block with amber accent bar on left, 22.5pt bold SimHei text left-aligned.
    """
    bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_PRIMARY
    bar.line.fill.background()
    set_round_radius(bar, 3000)
    remove_shadow(bar)
    
    # Left amber accent bar (in PDF: x + 10pt, width 12pt, height h - 20pt -> /2 in pptx: left + 5pt, w=6pt, h=h-10pt)
    accent = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left + Pt(5), top + Pt(5), Pt(6), height - Pt(10))
    accent.fill.solid()
    accent.fill.fore_color.rgb = C_ACCENT
    accent.line.fill.background()
    set_round_radius(accent, 4000)
    remove_shadow(accent)
    
    # Text box left-aligned (in PDF: x + 38pt -> /2: left + Pt(19))
    tb = slide.shapes.add_textbox(left + Pt(19), top, width - Pt(25), height)
    tf = tb.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = False
    tf.margin_left = Cm(0)
    tf.margin_right = Cm(0)
    tf.margin_top = Cm(0)
    tf.margin_bottom = Cm(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    add_run(p, title, font_name="SimHei", size_pt=22.5, bold=True, color_rgb=C_WHITE)

def add_bullet_paragraph(tf, tag, body, is_first=False, font_size=15.0, line_spacing=Pt(19.5), space_after=Pt(6)):
    """Add a structured bullet with bold keyword prefix and regular body text"""
    p = tf.paragraphs[0] if is_first else tf.add_paragraph()
    p.line_spacing = line_spacing
    if space_after > Pt(0):
        p.space_after = space_after
    add_run(p, tag, font_name="Noto Serif SC", size_pt=font_size, bold=True, color_rgb=C_PRIMARY)
    add_run(p, body, font_name="Noto Serif SC", size_pt=font_size, bold=False, color_rgb=C_TEXT_MAIN)
    return p

# ==========================================
# 1. SLIDE BACKGROUND & TOP BANNER
# ==========================================
# Clean base background
bg_rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(0), Cm(0), Cm(30), Cm(80))
bg_rect.fill.solid()
bg_rect.fill.fore_color.rgb = RGBColor(250, 250, 249)
bg_rect.line.fill.background()

banner_h = Cm(2.25)
if os.path.exists("nanobanana_header_banner.png"):
    slide.shapes.add_picture("nanobanana_header_banner.png", Cm(0), Cm(0), Cm(30), banner_h)
else:
    banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(0), Cm(0), Cm(30), banner_h)
    banner.fill.solid()
    banner.fill.fore_color.rgb = C_PRIMARY
    banner.line.fill.background()

# Gold accent line below banner
gold_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(0), banner_h, Cm(30), Cm(0.06))
gold_line.fill.solid()
gold_line.fill.fore_color.rgb = C_ACCENT
gold_line.line.fill.background()

# Top pill container (Matching PDF: no heavy outline, clean translucent navy fill)
pill_left = Cm(1.26)
pill_top = Cm(0.58)
pill_w = Cm(19.75)
pill_h = Cm(0.99)
pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, pill_left, pill_top, pill_w, pill_h)
pill.fill.solid()
pill.fill.fore_color.rgb = RGBColor(12, 33, 62)
pill.line.fill.background()
set_round_radius(pill, 4000)
remove_shadow(pill)

ptf = pill.text_frame
ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
ptf.margin_left = Cm(0.40)
ptf.margin_top = Cm(0)
ptf.margin_bottom = Cm(0)
pp = ptf.paragraphs[0]
pp.alignment = PP_ALIGN.LEFT
add_run(pp, "高等教育综合改革与拔尖创新人才培养专题论坛 · 学术成果展示", font_name="SimHei", size_pt=15.0, bold=True, color_rgb=C_WHITE)

# ==========================================
# 2. TITLE AREA (Scaled 1:2 from PDF: 64pt -> 32pt, 42pt -> 21pt)
# ==========================================
title_top = Cm(2.32)
title_box = slide.shapes.add_textbox(Cm(1.0), title_top, Cm(28.0), Cm(3.20))
ttf = title_box.text_frame
ttf.word_wrap = True
ttf.margin_left = Cm(0)
ttf.margin_right = Cm(0)
ttf.margin_top = Cm(0)
ttf.margin_bottom = Cm(0)

# Main Title Line 1
tp1 = ttf.paragraphs[0]
tp1.alignment = PP_ALIGN.CENTER
tp1.line_spacing = Pt(32.0)
add_run(tp1, "密歇根大学LSA住宿书院", font_name="SimHei", size_pt=32.0, bold=True, color_rgb=C_PRIMARY)

# Main Title Line 2
tp2 = ttf.add_paragraph()
tp2.alignment = PP_ALIGN.CENTER
tp2.line_spacing = Pt(32.0)
tp2.space_before = Pt(2)
add_run(tp2, "何以实现科技与人文协同？", font_name="SimHei", size_pt=32.0, bold=True, color_rgb=C_PRIMARY)

# Subtitle
tp3 = ttf.add_paragraph()
tp3.alignment = PP_ALIGN.CENTER
tp3.line_spacing = Pt(22.0)
tp3.space_before = Pt(4)
add_run(tp3, "——基于具身化整合学习生态系统的分析", font_name="SimHei", size_pt=21.0, bold=True, color_rgb=C_SLATE)

# ==========================================
# 3. PERSONAL INFO CARD (Exact replica of PDF)
# ==========================================
info_top = Cm(6.00)
info_h = Cm(3.92)
info_w = Cm(28.0)
info_left = Cm(1.0)

if os.path.exists("nanobanana_info_card_bg.png"):
    slide.shapes.add_picture("nanobanana_info_card_bg.png", info_left, info_top, info_w, info_h)
    outer_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, info_left, info_top, info_w, info_h)
    outer_card.fill.background()
    outer_card.line.color.rgb = RGBColor(200, 161, 101)
    outer_card.line.width = Pt(1.5)
    set_round_radius(outer_card, 3000)
    remove_shadow(outer_card)
    
    inner_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, info_left + Pt(2), info_top + Pt(2), info_w - Pt(4), info_h - Pt(4))
    inner_card.fill.background()
    inner_card.line.color.rgb = RGBColor(229, 208, 176)
    inner_card.line.width = Pt(0.75)
    set_round_radius(inner_card, 3000)
    remove_shadow(inner_card)
else:
    create_card(slide, info_left, info_top, info_w, info_h, bg_color=C_INFO_BG, border_color=C_INFO_BORDER, line_width_pt=1.5)

info_box = slide.shapes.add_textbox(info_left + Cm(0.8), info_top + Cm(0.35), info_w - Cm(1.2), info_h - Cm(0.6))
itf = info_box.text_frame
itf.word_wrap = True
itf.margin_left = Cm(0)
itf.margin_right = Cm(0)
itf.margin_top = Cm(0)
itf.margin_bottom = Cm(0)

author_info = [
    ("作　　者：", "王 青、Zhang Ren Melisa Xun、庞海芍（通讯作者）"),
    ("单　　位：", "北京理工大学教育学院"),
    ("邮　　箱：", "panghaishao@163.com"),
    ("研究方向：", "科技与人文教育协同 · 高等教育书院制 · 具身认知与整合学习")
]
for i, (k, v) in enumerate(author_info):
    p = itf.paragraphs[0] if i == 0 else itf.add_paragraph()
    p.line_spacing = Pt(19.5)
    if i > 0:
        p.space_before = Pt(3)
    add_run(p, k, font_name="SimHei", size_pt=15.5, bold=True, color_rgb=C_PRIMARY)
    add_run(p, "  " + v, font_name="Noto Serif SC", size_pt=15.0, bold=False, color_rgb=C_TEXT_MAIN)

# ==========================================
# 4. SECTION 1: 研究背景与理论透镜
# ==========================================
s1_header_top = Cm(10.35)
s1_header_h = Cm(1.2)
create_section_header(slide, Cm(1.0), s1_header_top, Cm(28.0), s1_header_h, "一、研究背景与理论透镜")

s1_top = Cm(11.90)
s1_h = Cm(7.94)
col_w = Cm(13.78)
col_gap = Cm(0.44)

# Left Column Card: 问题提出与现实困境
c1 = create_card(slide, Cm(1.0), s1_top, col_w, s1_h)
p1_bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(1.0), s1_top, col_w, Cm(0.85))
p1_bar.fill.solid()
p1_bar.fill.fore_color.rgb = C_SLATE
p1_bar.line.fill.background()
set_round_radius(p1_bar, 3000)
remove_shadow(p1_bar)

p1_tf = p1_bar.text_frame
p1_tf.vertical_anchor = MSO_ANCHOR.MIDDLE
p1_tf.margin_left = Cm(0.44)
p1_tf.margin_top = Cm(0)
p1_tf.margin_bottom = Cm(0)
p1_p = p1_tf.paragraphs[0]
p1_p.alignment = PP_ALIGN.LEFT
add_run(p1_p, "【问题提出与现实困境】", font_name="SimHei", size_pt=14.5, bold=True, color_rgb=C_WHITE)

tb_c1 = slide.shapes.add_textbox(Cm(1.2), s1_top + Cm(1.05), Cm(13.38), s1_h - Cm(1.2))
tf_c1 = tb_c1.text_frame
tf_c1.word_wrap = True
tf_c1.margin_left = Cm(0)
tf_c1.margin_right = Cm(0)
tf_c1.margin_top = Cm(0)
tf_c1.margin_bottom = Cm(0)

s1_left_bullets = [
    ("【战略需求】", "科技与人文协同是破除工具理性异化、培育拔尖创新人才的战略支撑。"),
    ("【深层困境】", "我国高校跨学科融合多停留在“课程并列、活动叠加”表层；书院与专业院系权责模糊，缺乏嵌入日常生活与身体实践的育人生态。"),
    ("【核心追问】", "住宿书院如何通过空间、课程与治理的三维互构，促使学生在认知与价值上实现科技理性与人文关怀的有机融合？")
]
for i, (tag, text) in enumerate(s1_left_bullets):
    add_bullet_paragraph(tf_c1, tag, text, is_first=(i==0), font_size=15.0, line_spacing=Pt(19.5), space_after=Pt(6))

# Right Column Card: 理论透镜：具身认知与整合学习
c2_left = Cm(1.0) + col_w + col_gap
c2 = create_card(slide, c2_left, s1_top, col_w, s1_h)
p2_bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c2_left, s1_top, col_w, Cm(0.85))
p2_bar.fill.solid()
p2_bar.fill.fore_color.rgb = C_SLATE
p2_bar.line.fill.background()
set_round_radius(p2_bar, 3000)
remove_shadow(p2_bar)

p2_tf = p2_bar.text_frame
p2_tf.vertical_anchor = MSO_ANCHOR.MIDDLE
p2_tf.margin_left = Cm(0.44)
p2_tf.margin_top = Cm(0)
p2_tf.margin_bottom = Cm(0)
p2_p = p2_tf.paragraphs[0]
p2_p.alignment = PP_ALIGN.LEFT
add_run(p2_p, "【理论透镜：具身认知与整合学习】", font_name="SimHei", size_pt=14.5, bold=True, color_rgb=C_WHITE)

tb_c2 = slide.shapes.add_textbox(c2_left + Cm(0.2), s1_top + Cm(1.05), Cm(13.38), s1_h - Cm(1.2))
tf_c2 = tb_c2.text_frame
tf_c2.word_wrap = True
tf_c2.margin_left = Cm(0)
tf_c2.margin_right = Cm(0)
tf_c2.margin_top = Cm(0)
tf_c2.margin_bottom = Cm(0)

s1_right_bullets = [
    ("【突破离身】", "挑战“纯符号加工”的离身学习范式，强调认知根植于身体感知运动经验及其与环境的互动。"),
    ("【三维支点】", "① 身体是主体（感知与情绪直接塑造认知）；② 环境是构成（空间布局与人际氛围形塑认知方向）；③ 行动是实现（在“做与思”循环中体认价值）。"),
    ("【分析切口】", "揭示书院通过身体共在、情境行动与民主参与将协同思维内化为身体惯习（Habitus）的生成机制。")
]
for i, (tag, text) in enumerate(s1_right_bullets):
    add_bullet_paragraph(tf_c2, tag, text, is_first=(i==0), font_size=15.0, line_spacing=Pt(19.5), space_after=Pt(6))

# ==========================================
# 5. SECTION 2: 核心分析框架：具身化整合学习生态系统
# ==========================================
s2_header_top = Cm(20.30)
s2_header_h = Cm(1.2)
create_section_header(slide, Cm(1.0), s2_header_top, Cm(28.0), s2_header_h, "二、核心分析框架：具身化整合学习生态系统")

s2_top = Cm(21.85)
s2_h = Cm(10.58)
create_card(slide, Cm(1.0), s2_top, Cm(28.0), s2_h)

# Fig 1 Image (Left, exactly matching PDF 720pt x 525pt -> 12.7cm x 9.26cm)
fig3_img_w = Cm(12.70)
fig3_img_h = Cm(9.26)
fig3_path = "fig_ecosystem_horizontal.png" if os.path.exists("fig_ecosystem_horizontal.png") else "fig3_ecosystem_v3.png"
if os.path.exists(fig3_path):
    slide.shapes.add_picture(fig3_path, Cm(1.4), s2_top + Cm(0.4), fig3_img_w, fig3_img_h)

# Fig 1 Caption (思源宋体 11.5pt, centered)
fig3_cap = slide.shapes.add_textbox(Cm(1.4), s2_top + s2_h - Cm(0.72), fig3_img_w, Cm(0.65))
fig3_ctf = fig3_cap.text_frame
fig3_ctf.word_wrap = True
fig3_ctf.margin_left = Cm(0)
fig3_ctf.margin_top = Cm(0)
fig3_cp = fig3_ctf.paragraphs[0]
fig3_cp.alignment = PP_ALIGN.CENTER
add_run(fig3_cp, "图1 科技与人文教育协同三大核心维度关系图", font_name="Noto Serif SC", size_pt=11.5, bold=True, color_rgb=C_TEXT_MUTED)

# Theoretical Explanation (Right, expanded width to 14.60cm to fit item 2 cleanly on 2 lines)
s2_desc_box = slide.shapes.add_textbox(Cm(14.20), s2_top + Cm(0.55), Cm(14.60), s2_h - Cm(0.9))
s2_dtf = s2_desc_box.text_frame
s2_dtf.word_wrap = True
s2_dtf.margin_left = Cm(0)
s2_dtf.margin_top = Cm(0)
s2_dtf.margin_bottom = Cm(0)

s2_intro = s2_dtf.paragraphs[0]
s2_intro.line_spacing = Pt(19.5)
s2_intro.space_after = Pt(6)
add_run(s2_intro, "【系统定性】", font_name="Noto Serif SC", size_pt=15.0, bold=True, color_rgb=C_PRIMARY)
add_run(s2_intro, "密歇根大学 LSA 住宿书院（1967年创设）构建了自我生成的“具身化整合学习生态系统”，回应三大递进命题：", font_name="Noto Serif SC", size_pt=15.0, bold=False, color_rgb=C_TEXT_MAIN)

s2_points = [
    ("1. 认知何以生成（空间社群）：", "以身体共在与日常浸润打破学科隔离，催生主体间对话性思维。"),
    ("2. 认知如何深化（课程教学）：", "以情境化行动整合多学科知识，\n实现知（Knowing）、行（Acting）、在（Being）合一。"),
    ("3. 认知如何成为存在方式（组织治理）：", "以双轨制度中介与学生自治，使协同思维沉淀为前反思的身体惯习。")
]
for tag, txt in s2_points:
    p = s2_dtf.add_paragraph()
    p.line_spacing = Pt(19.5)
    p.space_after = Pt(6)
    add_run(p, tag, font_name="Noto Serif SC", size_pt=15.0, bold=True, color_rgb=C_PRIMARY)
    add_run(p, txt, font_name="Noto Serif SC", size_pt=15.0, bold=False, color_rgb=C_TEXT_MAIN)

# ==========================================
# 6. SECTION 3: 三维运作机理深度剖析
# ==========================================
s3_header_top = Cm(32.85)
s3_header_h = Cm(1.2)
create_section_header(slide, Cm(1.0), s3_header_top, Cm(28.0), s3_header_h, "三、LSA住宿书院三维运作机理深度剖析")

# 3.1 空间社群
s31_top = Cm(34.40)
s31_h = Cm(7.85)
create_card(slide, Cm(1.0), s31_top, Cm(28.0), s31_h)

s31_pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(1.26), s31_top + Cm(0.2), Cm(12.0), Cm(0.74))
s31_pill.fill.solid()
s31_pill.fill.fore_color.rgb = C_PRIMARY
s31_pill.line.fill.background()
set_round_radius(s31_pill, 4000)
remove_shadow(s31_pill)

s31_ptf = s31_pill.text_frame
s31_ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
s31_ptf.margin_left = Cm(0.35)
s31_ptf.margin_top = Cm(0)
s31_ptf.margin_bottom = Cm(0)
s31_p = s31_ptf.paragraphs[0]
s31_p.alignment = PP_ALIGN.LEFT
add_run(s31_p, "（一）空间社群：身体共在与日常浸润", font_name="SimHei", size_pt=14.0, bold=True, color_rgb=C_WHITE)

# Left: Community Photo (PDF: 640pt x 340pt -> 11.29cm x 6.00cm)
comm_img_w = Cm(11.29)
comm_img_h = Cm(6.00)
if os.path.exists("nanobanana_embodied_community.png"):
    slide.shapes.add_picture("nanobanana_embodied_community.png", Cm(1.4), s31_top + Cm(1.05), comm_img_w, comm_img_h)

comm_cap = slide.shapes.add_textbox(Cm(1.4), s31_top + s31_h - Cm(0.68), comm_img_w, Cm(0.6))
comm_ctf = comm_cap.text_frame
comm_ctf.margin_left = Cm(0)
comm_ctf.margin_top = Cm(0)
comm_cp = comm_ctf.paragraphs[0]
comm_cp.alignment = PP_ALIGN.CENTER
add_run(comm_cp, "图2 LSA住宿书院跨学科生活与实践社群情境图", font_name="Noto Serif SC", size_pt=11.5, bold=True, color_rgb=C_TEXT_MUTED)

# Right: Bullets
s31_box = slide.shapes.add_textbox(Cm(13.0), s31_top + Cm(1.0), Cm(15.7), s31_h - Cm(1.2))
s31_tf = s31_box.text_frame
s31_tf.word_wrap = True
s31_tf.margin_left = Cm(0)
s31_tf.margin_top = Cm(0)
s31_tf.margin_bottom = Cm(0)

s31_bullets = [
    ("【住宿混融】", "采用“兴趣初配+背景混融”模式打破传统专业隔离，通过物理距离压缩促进跨学科偶发相遇；"),
    ("【文化场域】", "常态化开展艺术展览与伦理研讨，在日常互动中深度激活学生的跨学科共情与理解；"),
    ("【师生共在】", "教师办公室与学生活动区紧邻配置，使学术对话与价值关怀自然渗透于起居交往之中；"),
    ("【具身效应】", "走廊偶遇、共餐闲谈与工坊协作，促使跨学科对话从刻意安排转化为无处不在的生活常态。")
]
for i, (tag, txt) in enumerate(s31_bullets):
    add_bullet_paragraph(s31_tf, tag, txt, is_first=(i==0), font_size=15.0, line_spacing=Pt(19.5), space_after=Pt(5))

# 3.2 课程教学 (Text on Left, Image on Right)
s32_top = Cm(42.65)
s32_h = Cm(10.23)
create_card(slide, Cm(1.0), s32_top, Cm(28.0), s32_h)

s32_pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(1.26), s32_top + Cm(0.2), Cm(12.0), Cm(0.74))
s32_pill.fill.solid()
s32_pill.fill.fore_color.rgb = C_PRIMARY
s32_pill.line.fill.background()
set_round_radius(s32_pill, 4000)
remove_shadow(s32_pill)

s32_ptf = s32_pill.text_frame
s32_ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
s32_ptf.margin_left = Cm(0.35)
s32_ptf.margin_top = Cm(0)
s32_ptf.margin_bottom = Cm(0)
s32_p = s32_ptf.paragraphs[0]
s32_p.alignment = PP_ALIGN.LEFT
add_run(s32_p, "（二）课程教学：情境认知与行动整合", font_name="SimHei", size_pt=14.0, bold=True, color_rgb=C_WHITE)

# Left: Bullets
s32_box = slide.shapes.add_textbox(Cm(1.25), s32_top + Cm(1.05), Cm(14.50), s32_h - Cm(1.2))
s32_tf = s32_box.text_frame
s32_tf.word_wrap = True
s32_tf.margin_left = Cm(0)
s32_tf.margin_right = Cm(0)
s32_tf.margin_top = Cm(0)
s32_tf.margin_bottom = Cm(0)

s32_bullets = [
    ("【轮毂—辐条架构】", "以写作研讨、外语、艺术实践三类核心课为能力“轮毂”，支撑专业与跨界选修“辐条”延伸。"),
    ("【现实主题联动】", "开设“创造力科学与艺术”“社会理论与实践（STP）”等主题课，制造跨学科整合的内在需求。"),
    ("【真实社区嵌入】", "依托“底特律学期”与“午餐语言桌”等，在“调研—行动—反思”循环中检验并深化跨学科理解。"),
    ("【多元过程评价】", "引入同伴互评与教师书面叙事反馈，将整合能力转化为可观察、可追踪的实践目标。")
]
for i, (tag, txt) in enumerate(s32_bullets):
    add_bullet_paragraph(s32_tf, tag, txt, is_first=(i==0), font_size=15.0, line_spacing=Pt(19.5), space_after=Pt(6))

# Right: Fig 3 (Curriculum mechanism, PDF: 660pt x 490pt -> 11.64cm x 8.64cm)
fig1_w = Cm(11.64)
fig1_h = Cm(8.64)
fig1_left = Cm(15.90)
fig1_path = "fig_curriculum_horizontal.png" if os.path.exists("fig_curriculum_horizontal.png") else "fig1_curriculum_v2.png"
if os.path.exists(fig1_path):
    slide.shapes.add_picture(fig1_path, fig1_left, s32_top + Cm(0.65), fig1_w, fig1_h)

fig1_cap = slide.shapes.add_textbox(fig1_left, s32_top + s32_h - Cm(0.68), fig1_w, Cm(0.6))
fig1_ctf = fig1_cap.text_frame
fig1_ctf.margin_left = Cm(0)
fig1_ctf.margin_top = Cm(0)
fig1_cp = fig1_ctf.paragraphs[0]
fig1_cp.alignment = PP_ALIGN.CENTER
add_run(fig1_cp, "图3 LSA住宿书院课程构建的四维机制图", font_name="Noto Serif SC", size_pt=11.5, bold=True, color_rgb=C_TEXT_MUTED)

# 3.3 组织治理
s33_top = Cm(53.25)
s33_h = Cm(10.23)
create_card(slide, Cm(1.0), s33_top, Cm(28.0), s33_h)

s33_pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(1.26), s33_top + Cm(0.2), Cm(12.0), Cm(0.74))
s33_pill.fill.solid()
s33_pill.fill.fore_color.rgb = C_PRIMARY
s33_pill.line.fill.background()
set_round_radius(s33_pill, 4000)
remove_shadow(s33_pill)

s33_ptf = s33_pill.text_frame
s33_ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
s33_ptf.margin_left = Cm(0.35)
s33_ptf.margin_top = Cm(0)
s33_ptf.margin_bottom = Cm(0)
s33_p = s33_ptf.paragraphs[0]
s33_p.alignment = PP_ALIGN.LEFT
add_run(s33_p, "（三）组织治理：制度中介与主体性驱动", font_name="SimHei", size_pt=14.0, bold=True, color_rgb=C_WHITE)

# Left: Fig 4 (Governance chart, PDF: 720pt x 490pt -> 12.70cm x 8.64cm)
fig2_w = Cm(12.70)
fig2_h = Cm(8.64)
fig2_left = Cm(1.4)
if os.path.exists("fig2_governance_v2.png"):
    slide.shapes.add_picture("fig2_governance_v2.png", fig2_left, s33_top + Cm(0.65), fig2_w, fig2_h)

fig2_cap = slide.shapes.add_textbox(fig2_left, s33_top + s33_h - Cm(0.68), fig2_w, Cm(0.6))
fig2_ctf = fig2_cap.text_frame
fig2_ctf.margin_left = Cm(0)
fig2_ctf.margin_top = Cm(0)
fig2_cp = fig2_ctf.paragraphs[0]
fig2_cp.alignment = PP_ALIGN.CENTER
add_run(fig2_cp, "图4 密歇根大学安娜堡分校住宿书院组织结构图", font_name="Noto Serif SC", size_pt=11.5, bold=True, color_rgb=C_TEXT_MUTED)

# Right: Bullets
s33_box = slide.shapes.add_textbox(Cm(14.20), s33_top + Cm(1.05), Cm(14.60), s33_h - Cm(1.2))
s33_tf = s33_box.text_frame
s33_tf.word_wrap = True
s33_tf.margin_left = Cm(0)
s33_tf.margin_top = Cm(0)
s33_tf.margin_bottom = Cm(0)

s33_bullets = [
    ("【双轨领导结构】", "设立“学术主任+首席行政官”双轨制，在体制内开辟制度化跨学科特区，平衡科技与人文资源；"),
    ("【教师联合聘任】", "建立跨院联合聘任机制（Joint Appointment），兼具学院与书院双重身份，促进学科前沿与跨界理念双向反哺；"),
    ("【学生主体赋权】", "依托执行委员会（RCEC）与自治联合体，学生深度参与课程审议与公共事务决策；"),
    ("【惯习深度内化】", "学生在民主协商与社区操演中，推动协同思维内化为身体化的前反思存在方式。")
]
for i, (tag, txt) in enumerate(s33_bullets):
    add_bullet_paragraph(s33_tf, tag, txt, is_first=(i==0), font_size=15.0, line_spacing=Pt(19.5), space_after=Pt(6))

# ==========================================
# 7. SECTION 4: 对我国高校书院制改革的理论与实践启示
# ==========================================
s4_header_top = Cm(63.85)
s4_header_h = Cm(1.2)
create_section_header(slide, Cm(1.0), s4_header_top, Cm(28.0), s4_header_h, "四、对我国高校书院制改革的理论与实践启示")

s4_top = Cm(65.40)
s4_h = Cm(7.06)
col3_w = Cm(9.07)
col3_gap = Cm(0.39)

s4_cards_data = [
    ("【空间重构：生活方式化】", [
        ("【打破专业壁垒】", "推行多学科交叉混宿，破除院系物理隔离；"),
        ("【营造偶遇场域】", "布局共享起居与工坊，高频促生跨界思想碰撞；"),
        ("【推进导师共在】", "引导导师常态入驻生活圈，促使学术融入日常起居。")
    ], C_SLATE),
    ("【课程重塑：情境行动化】", [
        ("【筑牢能力轮毂】", "强化写作思辨、外语沉浸与具身艺术创作素养；"),
        ("【现实议题牵引】", "围绕前沿现实议题重构交叉微专业，激发整合动能；"),
        ("【嵌入社区行动】", "拓展社区服务学习实践，在知行合一中深化跨界认知。")
    ], C_PRIMARY),
    ("【制度创新：治理主体化】", [
        ("【健全双轨协同】", "探索院系书院联合聘任机制，打破单一评价壁垒；"),
        ("【赋权学生自治】", "搭建民主协商共治平台，赋予学生公共管理话语权；"),
        ("【内化身体惯习】", "在社区公共生活操演中，将跨界协同内化为思维惯习。")
    ], C_ACCENT)
]

for i, (title, bullets, bar_color) in enumerate(s4_cards_data):
    cx = Cm(1.0) + i * (col3_w + col3_gap)
    c = create_card(slide, cx, s4_top, col3_w, s4_h)
    
    # Card top bar
    bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, s4_top, col3_w, Cm(0.85))
    bar.fill.solid()
    bar.fill.fore_color.rgb = bar_color
    bar.line.fill.background()
    set_round_radius(bar, 3000)
    remove_shadow(bar)
    
    btf = bar.text_frame
    btf.vertical_anchor = MSO_ANCHOR.MIDDLE
    btf.margin_left = Cm(0.32)
    btf.margin_top = Cm(0)
    btf.margin_bottom = Cm(0)
    bp = btf.paragraphs[0]
    bp.alignment = PP_ALIGN.LEFT
    add_run(bp, title, font_name="SimHei", size_pt=14.0, bold=True, color_rgb=C_WHITE)
    
    # Bullets (width 8.75cm ensures exact 2 lines per bullet with zero orphan punctuation)
    tb = slide.shapes.add_textbox(cx + Cm(0.16), s4_top + Cm(0.95), Cm(8.75), s4_h - Cm(1.05))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Cm(0)
    tf.margin_right = Cm(0)
    tf.margin_top = Cm(0)
    tf.margin_bottom = Cm(0)
    
    for j, (tag, txt) in enumerate(bullets):
        add_bullet_paragraph(tf, tag, txt, is_first=(j==0), font_size=15.0, line_spacing=Pt(19.5), space_after=Pt(6))

# ==========================================
# 8. FOOTER: FUNDING & REPRESENTATIVE REFERENCES
# ==========================================
footer_top = Cm(72.85)
footer_h = Cm(4.60)
create_card(slide, Cm(1.0), footer_top, Cm(28.0), footer_h, bg_color=RGBColor(246, 248, 250), border_color=C_BORDER)

# Left: Funding & Contact
fund_box = slide.shapes.add_textbox(Cm(1.4), footer_top + Cm(0.35), Cm(11.2), footer_h - Cm(0.6))
ftf = fund_box.text_frame
ftf.word_wrap = True
ftf.margin_left = Cm(0)
ftf.margin_top = Cm(0)
ftf.margin_bottom = Cm(0)

fp1 = ftf.paragraphs[0]
fp1.line_spacing = Pt(14.0)
fp1.space_after = Pt(4)
add_run(fp1, "［基金项目］", font_name="Noto Serif SC", size_pt=11.0, bold=True, color_rgb=C_PRIMARY)
add_run(fp1, "全国教育科学规划2023年度教育学青年课题“基于跨界学习的学科交叉团队互动模式与建设机制研究”（课题编号：CIA230319）", font_name="Noto Serif SC", size_pt=11.0, bold=False, color_rgb=C_TEXT_MUTED)

fp2 = ftf.add_paragraph()
fp2.line_spacing = Pt(14.0)
add_run(fp2, "［学术交流］", font_name="Noto Serif SC", size_pt=11.0, bold=True, color_rgb=C_PRIMARY)
add_run(fp2, "本研究立足拔尖创新人才培养与书院制改革前沿，欢迎批评指正。邮箱：panghaishao@163.com", font_name="Noto Serif SC", size_pt=11.0, bold=False, color_rgb=C_TEXT_MUTED)

# Right: Key References
ref_box = slide.shapes.add_textbox(Cm(13.2), footer_top + Cm(0.35), Cm(15.4), footer_h - Cm(0.6))
rtf = ref_box.text_frame
rtf.word_wrap = True
rtf.margin_left = Cm(0)
rtf.margin_top = Cm(0)
rtf.margin_bottom = Cm(0)

rp1 = rtf.paragraphs[0]
rp1.line_spacing = Pt(14.0)
rp1.space_after = Pt(2)
add_run(rp1, "［代表性参考文献］", font_name="Noto Serif SC", size_pt=11.0, bold=True, color_rgb=C_PRIMARY)

refs = [
    "[1] 顾建军. 教育综合改革视角下科技与人文协同发展[J]. 国家教育行政学院学报, 2025(03).",
    "[2] Varela F J, et al. The embodied mind: Cognitive science and experience[M]. MIT press, 2017.",
    "[3] Sullivan W M. The power of integrated learning: Higher ed for success[M]. Routledge, 2023.",
    "[4] Dall’Alba G. Learning professional ways of being[J]. Educ Philos Theory, 2009."
]
for ref in refs:
    p = rtf.add_paragraph()
    p.line_spacing = Pt(13.5)
    p.space_after = Pt(2)
    add_run(p, ref, font_name="Noto Serif SC", size_pt=11.0, bold=False, color_rgb=C_TEXT_MUTED)

output_pptx = "academic_poster_30x80cm.pptx"
prs.save(output_pptx)
print(f"Generated {output_pptx} successfully!")
print(f"Slide Dimensions: 30 cm x 80 cm (Exact 1:2 scale for 60 cm x 160 cm roll-up banner)")
print(f"Bottom Clearance: {80.0 - (footer_top.cm + footer_h.cm):.2f} cm (Equivalent to {(80.0 - (footer_top.cm + footer_h.cm))*2:.2f} cm in 1:1 scale)")
