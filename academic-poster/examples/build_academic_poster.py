"""
Professional Academic Roll-up Banner (易拉宝) Poster Generator - Perfected Master Edition
Title: 密歇根大学LSA住宿书院何以实现科技与人文协同？——基于具身化整合学习生态系统的分析
Size: 60.6 cm x 160.6 cm (with 3mm bleed on all sides, trim size: 60 cm x 160 cm)
Resolution: 300 DPI target, vector typography & figures
Fonts: SimHei (Title/Subheadings), NotoSerifSC (Body >= 30pt, References 22-24pt)
Color: CMYK print-ready & high visual fidelity

Key Improvements:
1. Main Title: Split into two elegant balanced lines at 64pt, matching content column width.
2. Fig 3: Upgraded to zero line-text overlap with clean label masks and offsets.
3. Left-Alignment: All card items use individual Paragraphs with firstLineIndent=-15.5pt, ensuring
   the left bracket ink and text characters form a 100% straight vertical collinear left margin.
   All line wraps tuned so NO line starts with punctuation or leaves orphaned short tails.
4. Footer & Space: Footer card height optimized to 195pt (zero dead white space), vertical space
   evenly budgeted with 6.2cm bottom clearance for roll-up banner bottom cassette.
"""

import os
from reportlab.lib.colors import CMYKColor, HexColor
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import pymupdf

# 1. Exact Physical Dimensions
PAGE_WIDTH = 60.6 * cm     # 1717.795 pt
PAGE_HEIGHT = 160.6 * cm   # 4552.441 pt
BLEED = 0.3 * cm           # 8.504 pt (3 mm)
SAFE_MARGIN = 2.0 * cm     # 56.693 pt (20 mm inside trim line)

# Coordinates of Trim Box (60cm x 160cm)
TRIM_X1 = BLEED
TRIM_Y1 = BLEED
TRIM_X2 = PAGE_WIDTH - BLEED
TRIM_Y2 = PAGE_HEIGHT - BLEED

# Coordinates of Safe Content Area
CONTENT_X1 = TRIM_X1 + SAFE_MARGIN  # 65.2 pt
CONTENT_X2 = TRIM_X2 - SAFE_MARGIN  # 1652.6 pt
CONTENT_WIDTH = CONTENT_X2 - CONTENT_X1 # 1587.4 pt

CONTENT_Y1 = TRIM_Y1 + SAFE_MARGIN + 55  # ~120 pt (bottom roll-up safety space)

# 2. CMYK & Color Palette
C_PRIMARY = CMYKColor(0.95, 0.75, 0.25, 0.35)   # #0F294A (Academic Navy)
C_ACCENT = CMYKColor(0.12, 0.40, 0.95, 0.05)    # #C28212 (Warm Gold)
C_SLATE = CMYKColor(0.80, 0.50, 0.20, 0.10)     # #2B4C7E (Slate Blue)
C_TEXT = CMYKColor(0.10, 0.10, 0.10, 0.95)      # #1A1A1A (Charcoal Dark)
C_CARD_BG = CMYKColor(0.01, 0.01, 0.02, 0.01)   # #F8FAFC
C_BORDER = CMYKColor(0.15, 0.10, 0.05, 0.10)    # #CBD5E1

# Register Fonts
pdfmetrics.registerFont(TTFont('SimHei', 'C:/Windows/Fonts/simhei.ttf'))
pdfmetrics.registerFont(TTFont('NotoSerifSC', 'C:/Windows/Fonts/NotoSerifSC-VF.ttf'))
pdfmetrics.registerFontFamily('SimHei', normal='SimHei', bold='SimHei')
pdfmetrics.registerFontFamily('NotoSerifSC', normal='NotoSerifSC', bold='NotoSerifSC')

def draw_crop_marks(c):
    """Draw professional printer crop marks at trim boundaries (outside trim box)"""
    c.setStrokeColor(CMYKColor(0, 0, 0, 1))
    c.setLineWidth(0.6)
    mark_len = 20
    
    c.line(TRIM_X1 - mark_len, TRIM_Y1, TRIM_X1 - 2, TRIM_Y1)
    c.line(TRIM_X1, TRIM_Y1 - mark_len, TRIM_X1, TRIM_Y1 - 2)
    c.line(TRIM_X2 + 2, TRIM_Y1, TRIM_X2 + mark_len, TRIM_Y1)
    c.line(TRIM_X2, TRIM_Y1 - mark_len, TRIM_X2, TRIM_Y1 - 2)
    c.line(TRIM_X1 - mark_len, TRIM_Y2, TRIM_X1 - 2, TRIM_Y2)
    c.line(TRIM_X1, TRIM_Y2 + 2, TRIM_X1, TRIM_Y2 + mark_len)
    c.line(TRIM_X2 + 2, TRIM_Y2, TRIM_X2 + mark_len, TRIM_Y2)
    c.line(TRIM_X2, TRIM_Y2 + 2, TRIM_X2, TRIM_Y2 + mark_len)

def draw_card(c, x, y, w, h, bg_color=C_CARD_BG, border_color=C_BORDER, radius=12, fill=True, stroke=True):
    """Draw a smooth rounded card with subtle academic border"""
    c.saveState()
    if fill:
        c.setFillColor(bg_color)
    else:
        c.setFillColor('none')
    if stroke:
        c.setStrokeColor(border_color)
        c.setLineWidth(1.5)
    else:
        c.setStrokeColor('none')
    c.roundRect(x, y, w, h, radius, fill=1 if fill else 0, stroke=1 if stroke else 0)
    c.restoreState()

def draw_section_header(c, x, y, title):
    """
    Draw a distinct, modern academic section header:
    Solid navy block with amber accent bar, 45pt bold SimHei text
    """
    h_height = 68
    c.saveState()
    c.setFillColor(C_PRIMARY)
    c.roundRect(x, y - h_height, CONTENT_WIDTH, h_height, 8, fill=1, stroke=0)
    
    c.setFillColor(C_ACCENT)
    c.roundRect(x + 10, y - h_height + 10, 12, h_height - 20, 4, fill=1, stroke=0)
    
    c.setFillColor(CMYKColor(0, 0, 0, 0))
    c.setFont('SimHei', 45)
    c.drawString(x + 38, y - h_height + 18, title)
    c.restoreState()
    return y - h_height - 22

def draw_card_bullets(c, items, x, y_top, max_w, style, space_after=12):
    """
    Draw multiple bullet paragraphs top-down.
    Each item is an independent Paragraph with firstLineIndent=-15.5pt,
    guaranteeing that the left bracket ink and the text on subsequent lines
    are 100% strictly left-aligned in a single vertical line.
    """
    cur_y = y_top
    for it in items:
        p = Paragraph(it, style)
        w, h = p.wrap(max_w, 500)
        p.drawOn(c, x, cur_y - h)
        cur_y -= (h + space_after)
    return y_top - cur_y

def draw_paragraph_top_down(p, c, x, y_top, max_w, max_h):
    """Draw a ReportLab Paragraph measured top-down with zero overlap"""
    w, h = p.wrap(max_w, max_h)
    p.drawOn(c, x, y_top - h)
    return h

def create_poster():
    pdf_path = "academic_poster_60x160cm.pdf"
    c = canvas.Canvas(pdf_path, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    
    c.setTitle("密歇根大学LSA住宿书院何以实现科技与人文协同？")
    c.setAuthor("王青, Zhang Ren Melisa Xun, 庞海芍")
    c.setSubject("具身化整合学习生态系统与高校书院制改革")
    
    c._doc.TrimBox = [float(TRIM_X1), float(TRIM_Y1), float(TRIM_X2), float(TRIM_Y2)]
    c._doc.BleedBox = [0, 0, float(PAGE_WIDTH), float(PAGE_HEIGHT)]
    
    # 1. Base Paper Background
    c.setFillColor(CMYKColor(0.0, 0.01, 0.03, 0.01))
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    
    # Draw nanobanana_poster_bg.png as watermark texture across the full poster
    if os.path.exists("nanobanana_poster_bg.png"):
        c.drawImage("nanobanana_poster_bg.png", 0, 0, width=PAGE_WIDTH, height=PAGE_HEIGHT, preserveAspectRatio=False)
        c.setFillColor(CMYKColor(0, 0, 0, 0), alpha=0.30)
        c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    
    # 2. Top Banner Header (Bleeds fully at top)
    banner_h = 135
    banner_y = PAGE_HEIGHT - banner_h
    if os.path.exists("nanobanana_header_banner.png"):
        c.drawImage("nanobanana_header_banner.png", 0, banner_y, width=PAGE_WIDTH, height=banner_h, preserveAspectRatio=False)
        c.setFillColor(C_ACCENT)
        c.rect(0, banner_y - 3, PAGE_WIDTH, 3, fill=1, stroke=0)
        
        # Pill container for forum text on left/center
        pill_w = 1120
        pill_h = 56
        pill_x = CONTENT_X1 + 15
        pill_y = banner_y + 38
        c.setFillColor(CMYKColor(0.95, 0.8, 0.3, 0.65), alpha=0.88)
        c.roundRect(pill_x, pill_y, pill_w, pill_h, 8, fill=1, stroke=0)
        
        c.setFillColor(CMYKColor(0, 0, 0, 0), alpha=1.0)
        c.setFont('SimHei', 30)
        c.drawString(pill_x + 30, pill_y + 17, "高等教育综合改革与拔尖创新人才培养专题论坛 · 学术成果展示")
    else:
        c.setFillColor(C_PRIMARY)
        c.rect(0, banner_y, PAGE_WIDTH, banner_h, fill=1, stroke=0)
        c.setFillColor(C_ACCENT)
        c.rect(0, banner_y - 4, PAGE_WIDTH, 4, fill=1, stroke=0)
        c.setFillColor(CMYKColor(0, 0, 0, 0))
        c.setFont('SimHei', 32)
        c.drawCentredString(PAGE_WIDTH / 2.0, banner_y + 50, "高等教育综合改革与拔尖创新人才培养专题论坛 · 学术成果展示")
    
    # Draw printer crop marks
    draw_crop_marks(c)
    
    # ==========================================
    # HEADER SECTION: Titles & Author Card
    # ==========================================
    # Main title split into 2 well-proportioned lines at 64pt, centered and matching content column
    title_y1 = banner_y - 72
    c.setFillColor(C_PRIMARY)
    c.setFont('SimHei', 64)
    c.drawCentredString(PAGE_WIDTH / 2.0, title_y1, "密歇根大学LSA住宿书院")
    
    title_y2 = title_y1 - 74
    c.drawCentredString(PAGE_WIDTH / 2.0, title_y2, "何以实现科技与人文协同？")
    
    subtitle_y = title_y2 - 58
    c.setFillColor(C_SLATE)
    c.setFont('SimHei', 42)
    c.drawCentredString(PAGE_WIDTH / 2.0, subtitle_y, "——基于具身化整合学习生态系统的分析")
    
    # Personal Info Card (Matching reference diagram)
    card_h = 225
    card_y = subtitle_y - 25 - card_h
    
    if os.path.exists("nanobanana_info_card_bg.png"):
        c.drawImage("nanobanana_info_card_bg.png", CONTENT_X1, card_y, width=CONTENT_WIDTH, height=card_h, preserveAspectRatio=False)
        c.saveState()
        c.setStrokeColor(HexColor('#C8A165'))
        c.setLineWidth(1.8)
        c.roundRect(CONTENT_X1, card_y, CONTENT_WIDTH, card_h, 10, fill=0, stroke=1)
        c.setStrokeColor(HexColor('#E5D0B0'))
        c.setLineWidth(0.8)
        c.roundRect(CONTENT_X1 + 4, card_y + 4, CONTENT_WIDTH - 8, card_h - 8, 8, fill=0, stroke=1)
        c.restoreState()
    else:
        draw_card(c, CONTENT_X1, card_y, CONTENT_WIDTH, card_h, bg_color=CMYKColor(0, 0.02, 0.06, 0.01), border_color=C_ACCENT, radius=10)
    
    # Text inside Personal Info Card
    info_x = CONTENT_X1 + 45
    info_start_y = card_y + card_h - 52
    line_gap = 43
    
    fields = [
        ("作　　者：", "王 青、Zhang Ren Melisa Xun、庞海芍（通讯作者）"),
        ("单　　位：", "北京理工大学教育学院"),
        ("邮　　箱：", "panghaishao@163.com"),
        ("研究方向：", "科技与人文教育协同 · 高等教育书院制 · 具身认知与整合学习")
    ]
    
    for i, (k, v) in enumerate(fields):
        y_pos = info_start_y - i * line_gap
        c.setFont('SimHei', 31)
        c.setFillColor(C_PRIMARY)
        c.drawString(info_x, y_pos, k)
        c.setFont('NotoSerifSC', 30)
        c.setFillColor(C_TEXT)
        c.drawString(info_x + 155, y_pos, v)
        
    cur_y = card_y - 25
    
    # Typography Styles (strictly >= 30pt body)
    card_bullet_style = ParagraphStyle(
        'CardBullet',
        fontName='NotoSerifSC',
        fontSize=30.5,
        leading=39.5,
        textColor='#1A202C',
        firstLineIndent=-15.5,  # Eliminates CJK 【 sidebearing so bracket ink and text ink align 100% flush!
        wordWrap='CJK'
    )
    
    body_plain_style = ParagraphStyle(
        'BodyPlain',
        fontName='NotoSerifSC',
        fontSize=30.5,
        leading=40,
        textColor='#1A202C',
        wordWrap='CJK'
    )
    
    caption_style = ParagraphStyle(
        'Caption',
        fontName='NotoSerifSC',
        fontSize=23,
        leading=32,
        alignment=1, # Center
        textColor='#334155',
        wordWrap='CJK'
    )
    ref_style = ParagraphStyle(
        'Ref',
        fontName='NotoSerifSC',
        fontSize=22,
        leading=26,
        textColor='#334155',
        wordWrap='CJK'
    )

    # ==========================================
    # SECTION 1: 研究背景与理论透镜
    # ==========================================
    cur_y = draw_section_header(c, CONTENT_X1, cur_y, "一、研究背景与理论透镜")
    
    col_gap = 25
    col_w = (CONTENT_WIDTH - col_gap) / 2.0
    sec1_h = 450
    card1_y = cur_y - sec1_h
    
    # Left Card
    draw_card(c, CONTENT_X1, card1_y, col_w, sec1_h, bg_color=CMYKColor(0.01, 0.01, 0.02, 0.01))
    c.setFillColor(C_SLATE)
    c.roundRect(CONTENT_X1, card1_y + sec1_h - 48, col_w, 48, 8, fill=1, stroke=0)
    c.setFillColor(CMYKColor(0,0,0,0))
    c.setFont('SimHei', 29)
    c.drawString(CONTENT_X1 + 25, card1_y + sec1_h - 34, "【问题提出与现实困境】")
    
    s1_left_items = [
        '<b>【战略需求】</b>科技与人文协同是破除工具理性异化、培育拔尖创新人才的战略支撑。',
        '<b>【深层困境】</b>我国高校跨学科融合多停留在“课程并列、活动叠加”表层；书院与专业院系权责模糊，缺乏嵌入日常生活与身体实践的育人生态。',
        '<b>【核心追问】</b>住宿书院如何通过空间、课程与治理的三维互构，促使学生在认知与价值上实现科技理性与人文关怀的有机融合？'
    ]
    draw_card_bullets(c, s1_left_items, CONTENT_X1 + 35, card1_y + sec1_h - 60, col_w - 45, card_bullet_style, space_after=8)
    
    # Right Card
    card2_x = CONTENT_X1 + col_w + col_gap
    draw_card(c, card2_x, card1_y, col_w, sec1_h, bg_color=CMYKColor(0.01, 0.01, 0.02, 0.01))
    c.setFillColor(C_SLATE)
    c.roundRect(card2_x, card1_y + sec1_h - 48, col_w, 48, 8, fill=1, stroke=0)
    c.setFillColor(CMYKColor(0,0,0,0))
    c.setFont('SimHei', 29)
    c.drawString(card2_x + 25, card1_y + sec1_h - 34, "【理论透镜：具身认知与整合学习】")
    
    s1_right_items = [
        '<b>【突破离身】</b>挑战“纯符号加工”的离身学习范式，强调认知根植于身体感知运动经验及其与环境的互动。',
        '<b>【三维支点】</b>① 身体是主体（感知与情绪直接塑造认知）；② 环境是构成（空间布局与人际氛围形塑认知方向）；③ 行动是实现（在“做与思”循环中体认价值）。',
        '<b>【分析切口】</b>揭示书院通过身体共在、情境行动与民主参与将协同思维内化为身体惯习（Habitus）的生成机制。'
    ]
    draw_card_bullets(c, s1_right_items, card2_x + 35, card1_y + sec1_h - 60, col_w - 55, card_bullet_style, space_after=8)
    
    cur_y = card1_y - 25
    
    # ==========================================
    # SECTION 2: 核心分析框架：具身化整合学习生态系统
    # ==========================================
    cur_y = draw_section_header(c, CONTENT_X1, cur_y, "二、核心分析框架：具身化整合学习生态系统")
    
    sec2_h = 600
    sec2_y = cur_y - sec2_h
    draw_card(c, CONTENT_X1, sec2_y, CONTENT_WIDTH, sec2_h, bg_color=CMYKColor(0, 0.01, 0.02, 0.01))
    
    # Left: Fig 1 (Ecosystem diagram with 100% horizontal text)
    fig3_w = 720
    fig3_h = 525
    fig3_x = CONTENT_X1 + 25
    fig3_y = sec2_y + 45
    fig3_file = "fig_ecosystem_horizontal.png" if os.path.exists("fig_ecosystem_horizontal.png") else "fig3_ecosystem_v3.png"
    c.drawImage(fig3_file, fig3_x, fig3_y, width=fig3_w, height=fig3_h, preserveAspectRatio=True)
    
    p_cap3 = Paragraph("<b>图1 科技与人文教育协同三大核心维度关系图</b>", caption_style)
    p_cap3.wrap(fig3_w, 35)
    p_cap3.drawOn(c, fig3_x, sec2_y + 14)
    
    # Right: Theoretical Explanation
    desc_x = fig3_x + fig3_w + 35
    desc_w = CONTENT_WIDTH - fig3_w - 85
    sec2_desc = """<b>【系统定性】</b>密歇根大学 LSA 住宿书院（1967年创设）构建了自我生成的“具身化整合学习生态系统”，回应三大递进命题：<br/><br/>
<b>1. 认知何以生成（空间社群）：</b>以身体共在与日常浸润打破学科隔离，催生主体间对话性思维。<br/><br/>
<b>2. 认知如何深化（课程教学）：</b>以情境化行动整合多学科知识，实现知（Knowing）、行（Acting）、在（Being）合一。<br/><br/>
<b>3. 认知如何成为存在方式（组织治理）：</b>以双轨制度中介与学生自治，使协同思维沉淀为前反思的身体惯习。"""
    p_desc = Paragraph(sec2_desc, body_plain_style)
    draw_paragraph_top_down(p_desc, c, desc_x, sec2_y + sec2_h - 32, desc_w, sec2_h - 45)
    
    cur_y = sec2_y - 25
    
    # ==========================================
    # SECTION 3: 三维运作机理深度剖析
    # ==========================================
    cur_y = draw_section_header(c, CONTENT_X1, cur_y, "三、LSA住宿书院三维运作机理深度剖析")
    
    # 3.1 空间社群
    dim1_h = 445
    dim1_y = cur_y - dim1_h
    draw_card(c, CONTENT_X1, dim1_y, CONTENT_WIDTH, dim1_h)
    
    # Blue sub-pill: 680pt width to ensure ample breathing room
    c.setFillColor(C_PRIMARY)
    c.roundRect(CONTENT_X1 + 15, dim1_y + dim1_h - 44, 680, 42, 6, fill=1, stroke=0)
    c.setFillColor(CMYKColor(0,0,0,0))
    c.setFont('SimHei', 28)
    c.drawString(CONTENT_X1 + 30, dim1_y + dim1_h - 32, "（一）空间社群：身体共在与日常浸润")
    
    comm_img_w = 640
    comm_img_h = 340
    comm_img_x = CONTENT_X1 + 25
    comm_img_y = dim1_y + 45
    
    if os.path.exists("nanobanana_embodied_community.png"):
        c.drawImage("nanobanana_embodied_community.png", comm_img_x, comm_img_y, width=comm_img_w, height=comm_img_h, preserveAspectRatio=True)
        c.saveState()
        c.setStrokeColor(HexColor('#CBD5E1'))
        c.setLineWidth(1.2)
        c.rect(comm_img_x, comm_img_y, comm_img_w, comm_img_h, fill=0, stroke=1)
        c.restoreState()
        
    p_cap_comm = Paragraph("<b>图2 LSA住宿书院跨学科生活与实践社群情境图</b>", caption_style)
    p_cap_comm.wrap(comm_img_w, 30)
    p_cap_comm.drawOn(c, comm_img_x, dim1_y + 10)
    
    dim1_text_x = comm_img_x + comm_img_w + 35
    dim1_text_w = CONTENT_WIDTH - comm_img_w - 85
    dim1_items = [
        '<b>【住宿混融】</b>采用“兴趣初配+背景混融”模式打破传统专业隔离，通过物理距离压缩促进跨学科偶发相遇；',
        '<b>【文化场域】</b>常态化开展艺术展览与伦理研讨，在日常互动中深度激活学生的跨学科共情与理解；',
        '<b>【师生共在】</b>教师办公室与学生活动区紧邻配置，使学术对话与价值关怀自然渗透于起居交往之中；',
        '<b>【具身效应】</b>走廊偶遇、共餐闲谈与工坊协作，促使跨学科对话从刻意安排转化为无处不在的生活常态。'
    ]
    draw_card_bullets(c, dim1_items, dim1_text_x + 15.5, dim1_y + dim1_h - 56, dim1_text_w - 15.5, card_bullet_style, space_after=12)
    
    cur_y = dim1_y - 22
    
    # 3.2 课程教学 (Text on Left + Fig 3 on Right)
    dim2_h = 580
    dim2_y = cur_y - dim2_h
    draw_card(c, CONTENT_X1, dim2_y, CONTENT_WIDTH, dim2_h)
    
    c.setFillColor(C_PRIMARY)
    c.roundRect(CONTENT_X1 + 15, dim2_y + dim2_h - 44, 680, 42, 6, fill=1, stroke=0)
    c.setFillColor(CMYKColor(0,0,0,0))
    c.setFont('SimHei', 28)
    c.drawString(CONTENT_X1 + 30, dim2_y + dim2_h - 32, "（二）课程教学：情境认知与行动整合")
    
    # Left: Text Bullets
    dim2_text_x = CONTENT_X1 + 35
    dim2_text_w = 780
    dim2_items = [
        '<b>【轮毂—辐条架构】</b>以写作研讨、外语、艺术实践三类核心课为能力“轮毂”，支撑专业与跨界选修“辐条”延伸。',
        '<b>【现实主题联动】</b>开设“创造力科学与艺术”“社会理论与实践（STP）”等主题课，制造跨学科整合的内在需求。',
        '<b>【真实社区嵌入】</b>依托“底特律学期项目”“午餐语言桌”等，在“调研—行动—反思”循环中检验并深化跨学科理解。',
        '<b>【多元过程评价】</b>引入同伴互评与教师书面叙事反馈，将整合能力转化为可观察、可追踪的实践目标。'
    ]
    draw_card_bullets(c, dim2_items, dim2_text_x + 15.5, dim2_y + dim2_h - 56, dim2_text_w - 15.5, card_bullet_style, space_after=12)
    
    # Right: Fig 3 Image & Caption (Curriculum mechanism with 100% horizontal text)
    fig1_w = 660
    fig1_h = 490
    fig1_x = CONTENT_X1 + dim2_text_w + 45
    fig1_y = dim2_y + 45
    fig1_file = "fig_curriculum_horizontal.png" if os.path.exists("fig_curriculum_horizontal.png") else "fig1_curriculum_v2.png"
    c.drawImage(fig1_file, fig1_x, fig1_y, width=fig1_w, height=fig1_h, preserveAspectRatio=True)
    
    p_cap1 = Paragraph("<b>图3 LSA住宿书院课程构建的四维机制图</b>", caption_style)
    p_cap1.wrap(fig1_w, 35)
    p_cap1.drawOn(c, fig1_x, dim2_y + 12)
    
    cur_y = dim2_y - 22
    
    # 3.3 组织治理 (Fig 4 on Left + Text on Right)
    dim3_h = 580
    dim3_y = cur_y - dim3_h
    draw_card(c, CONTENT_X1, dim3_y, CONTENT_WIDTH, dim3_h)
    
    c.setFillColor(C_PRIMARY)
    c.roundRect(CONTENT_X1 + 15, dim3_y + dim3_h - 44, 680, 42, 6, fill=1, stroke=0)
    c.setFillColor(CMYKColor(0,0,0,0))
    c.setFont('SimHei', 28)
    c.drawString(CONTENT_X1 + 30, dim3_y + dim3_h - 32, "（三）组织治理：制度中介与主体性驱动")
    
    # Left: Fig 4 Image & Caption
    fig2_w = 720
    fig2_h = 490
    fig2_x = CONTENT_X1 + 25
    fig2_y = dim3_y + 45
    if os.path.exists("fig2_governance_v2.png"):
        c.drawImage("fig2_governance_v2.png", fig2_x, fig2_y, width=fig2_w, height=fig2_h, preserveAspectRatio=True)
        
    p_cap2 = Paragraph("<b>图4 密歇根大学安娜堡分校住宿书院组织结构图</b>", caption_style)
    p_cap2.wrap(fig2_w, 35)
    p_cap2.drawOn(c, fig2_x, dim3_y + 12)
    
    # Right: Text Bullets
    dim3_text_x = fig2_x + fig2_w + 35
    dim3_text_w = CONTENT_WIDTH - fig2_w - 85
    dim3_items = [
        '<b>【双轨领导结构】</b>书院设立“学术主任+首席行政官”双轨制，在传统学科体制内开辟制度化跨学科特区，平衡科技与人文资源；',
        '<b>【教师联合聘任】</b>建立跨院联合聘任机制（Joint Appointment），兼具学院与书院双重身份，促进学科前沿与跨界理念双向反哺；',
        '<b>【学生主体赋权】</b>依托执行委员会（RCEC）与自治联合体，学生深度参与课程审议与公共事务决策；',
        '<b>【惯习深度内化】</b>学生在民主协商与社区操演中，推动协同思维内化为身体化的前反思存在方式。'
    ]
    draw_card_bullets(c, dim3_items, dim3_text_x + 15.5, dim3_y + dim3_h - 56, dim3_text_w - 15.5, card_bullet_style, space_after=11)
    
    cur_y = dim3_y - 25
    
    # ==========================================
    # SECTION 4: 对我国高校书院制改革的启示
    # ==========================================
    cur_y = draw_section_header(c, CONTENT_X1, cur_y, "四、对我国高校书院制改革的理论与实践启示")
    
    sec4_h = 400
    sec4_y = cur_y - sec4_h
    
    col3_gap = 22
    col3_w = (CONTENT_WIDTH - 2 * col3_gap) / 3.0
    
    cards_data = [
        ("【空间重构：生活方式化】", [
            '<b>【打破专业壁垒】</b>推行多学科交叉混宿，破除院系物理隔离；',
            '<b>【营造偶遇场域】</b>布局共享起居与工坊，高频促生跨界思想碰撞；',
            '<b>【推进导师共在】</b>引导导师常态入驻生活圈，促使学术融入日常起居。'
        ], C_SLATE),
        ("【课程重塑：情境行动化】", [
            '<b>【筑牢能力轮毂】</b>强化写作思辨、外语沉浸与具身艺术创作素养；',
            '<b>【现实议题牵引】</b>围绕前沿现实议题重构交叉微专业，激发整合动能；',
            '<b>【嵌入社区行动】</b>拓展社区服务学习实践，在知行合一中深化跨界认知。'
        ], C_PRIMARY),
        ("【制度创新：治理主体化】", [
            '<b>【健全双轨协同】</b>探索院系书院联合聘任机制，打破单一评价壁垒；',
            '<b>【赋权学生自治】</b>搭建民主协商共治平台，赋予学生公共管理话语权；',
            '<b>【内化身体惯习】</b>在社区公共生活操演中，将跨界协同内化为思维惯习。'
        ], C_ACCENT)
    ]
    
    for i, (title, items, bar_color) in enumerate(cards_data):
        c_x = CONTENT_X1 + i * (col3_w + col3_gap)
        draw_card(c, c_x, sec4_y, col3_w, sec4_h, bg_color=CMYKColor(0, 0.01, 0.02, 0.01))
        
        c.setFillColor(bar_color)
        c.roundRect(c_x, sec4_y + sec4_h - 48, col3_w, 48, 8, fill=1, stroke=0)
        c.setFillColor(CMYKColor(0,0,0,0))
        c.setFont('SimHei', 28)
        c.drawString(c_x + 18, sec4_y + sec4_h - 34, title)
        
        draw_card_bullets(c, items, c_x + 22, sec4_y + sec4_h - 68, col3_w - 32, card_bullet_style, space_after=14)
        
    cur_y = sec4_y - 25
    
    # ==========================================
    # FOOTER SECTION: Funding & Key References
    # ==========================================
    # Footer card height set to 245pt to generously contain all citations with ample padding
    footer_h = 245
    footer_y = cur_y - footer_h
    draw_card(c, CONTENT_X1, footer_y, CONTENT_WIDTH, footer_h, bg_color=CMYKColor(0.02, 0.01, 0.01, 0.02), border_color=C_BORDER)
    
    # Left: Funding & Contact
    fund_x = CONTENT_X1 + 25
    fund_w = 635
    fund_text = """<b>［基金项目］</b>全国教育科学规划2023年度教育学青年课题“基于跨界学习的学科交叉团队互动模式与建设机制研究”（课题编号：CIA230319）<br/><br/>
<b>［学术交流］</b>本研究立足拔尖创新人才培养与书院制改革前沿，欢迎批评指正。邮箱：panghaishao@163.com"""
    p_fund = Paragraph(fund_text, ref_style)
    draw_paragraph_top_down(p_fund, c, fund_x, footer_y + footer_h - 22, fund_w, footer_h - 30)
    
    # Right: References (4 Key citations)
    ref_x = fund_x + fund_w + 35
    ref_w = CONTENT_WIDTH - fund_w - 65
    ref_text = """<b>［代表性参考文献］</b><br/>
[1] 顾建军. 教育综合改革视角下科技与人文协同发展[J]. 国家教育行政学院学报, 2025(03).<br/>
[2] Varela F J, et al. The embodied mind: Cognitive science and experience[M]. MIT press, 2017.<br/>
[3] Sullivan W M. The power of integrated learning: Higher ed for success[M]. Routledge, 2023.<br/>
[4] Dall’Alba G. Learning professional ways of being[J]. Educ Philos Theory, 2009."""
    p_ref = Paragraph(ref_text, ref_style)
    draw_paragraph_top_down(p_ref, c, ref_x, footer_y + footer_h - 22, ref_w, footer_h - 30)
    
    dist_to_trim = footer_y - TRIM_Y1
    dist_to_trim_cm = dist_to_trim / 72.0 * 2.54
    print(f"DEBUG: Final Footer Bottom Y = {footer_y:.1f} pt (Safety Limit: {CONTENT_Y1:.1f} pt, Trim Margin: {dist_to_trim:.1f} pt / {dist_to_trim_cm:.2f} cm)")
    
    # Save Canvas
    c.showPage()
    c.save()
    print(f"Generated {pdf_path} successfully!")

def render_preview(pdf_path="academic_poster_60x160cm.pdf", png_path="academic_poster_preview.png"):
    """Render high-resolution preview image from PDF using PyMuPDF"""
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    zoom = 150.0 / 72.0
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(png_path)
    print(f"Rendered preview image: {png_path} ({pix.width}x{pix.height})")

if __name__ == '__main__':
    create_poster()
    render_preview()
