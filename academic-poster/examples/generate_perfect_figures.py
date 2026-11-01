"""
Publication-Quality Figures Generator for LSA Residential College Academic Poster
Strictly Aligns with Original Paper Diagrams & User Feedback:
1. Fig 1 (Ecosystem):
   - 3 outer nodes are elegant ellipses ('空间社群', '组织治理', '课程教学')
   - Center circle is highlighted amber gold ('科技与人文协同')
   - Dashed lines connect nodes continuously
   - Labels '共在性凝聚', '场域性保障', '具身情境', '意义构建', '认知内化保障', '认知深化路径' are strictly PARALLEL to the lines
   - Zero overlap, ample breathing room
2. Fig 3 (Curriculum):
   - Center equilateral triangle '整合学习'
   - 3 circles: '整合思维', '公民责任', '知识迁移'
   - Connecting arrows with PARALLEL text: '思维方式', '跨界整合', '行动载体'
   - 4 outer rectangular boxes: '课程结构重构', '内容联动', '实践嵌入', '评估革新'
   - 4 corner knowledge flow arrows: '知识整合', '知识运用', '制度保障', '闭环驱动'
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Ellipse, Circle, FancyBboxPatch, Polygon, FancyArrowPatch
import numpy as np

# Font settings
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Colors aligned with academic poster theme
NAVY = '#1B365D'
DARK_BLUE = '#0F294A'
SLATE = '#2B6CB0'
AMBER = '#D97706'
AMBER_BG = '#FFFBEB'
AMBER_TEXT = '#92400E'
LIGHT_BLUE_BG = '#F0F7FF'
CARD_BG = '#FFFFFF'
CHARCOAL = '#1E293B'
GRAY_LINE = '#475569'
DASH_LINE = '#64748B'

def draw_ecosystem_figure(output_path="fig_ecosystem_horizontal.png"):
    """
    Figure 1: 科技与人文教育协同三大核心维度关系图
    """
    fig, ax = plt.subplots(figsize=(9, 9), dpi=300)
    fig.patch.set_facecolor(CARD_BG)
    ax.set_facecolor(CARD_BG)
    ax.set_aspect('equal')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Center coordinates of the 4 nodes
    P_top = np.array([50.0, 86.0])
    P_bl = np.array([17.0, 15.0])
    P_br = np.array([83.0, 15.0])
    P_c = np.array([50.0, 46.0])

    ew, eh = 29.0, 14.2  # Ellipse width and height
    cr = 8.8             # Center circle radius

    # 1. Dashed lines to center (zorder=2)
    # Top -> Center: 认知生成基础
    y_top_dash_start = P_top[1] - eh/2 - 0.5   # 78.4
    y_txt_top = 67.5
    y_center_dash_end = P_c[1] + cr + 0.5      # 55.3
    
    ax.plot([50.0, 50.0], [y_top_dash_start, y_txt_top + 2.8],
            color=DASH_LINE, linestyle='--', linewidth=2.0, zorder=2)
    ax.plot([50.0, 50.0], [y_txt_top - 2.8, y_center_dash_end],
            color=DASH_LINE, linestyle='--', linewidth=2.0, zorder=2)
    ax.text(50.0, y_txt_top, '认知生成基础', fontsize=12.5, fontweight='bold', color=CHARCOAL,
            ha='center', va='center', zorder=5)

    # BL -> Center: 认知内化保障
    v_bl_c = P_c - P_bl  # [33, 31]
    dist_bl_c = np.linalg.norm(v_bl_c)
    u_bl_c = v_bl_c / dist_bl_c
    angle_bl_c = np.degrees(np.arctan2(u_bl_c[1], u_bl_c[0])) # ~ 43.21 degrees
    n_bl_c = np.array([-u_bl_c[1], u_bl_c[0]]) # northwest normal

    # Continuous straight dashed line from BL oval edge to center circle edge
    pt_start_bl = P_bl + u_bl_c * 9.8
    pt_end_bl = P_c - u_bl_c * (cr + 0.5)
    ax.plot([pt_start_bl[0], pt_end_bl[0]], [pt_start_bl[1], pt_end_bl[1]],
            color=DASH_LINE, linestyle='--', linewidth=2.0, zorder=2)
    
    # Text '认知内化保障' placed parallel above the dashed line
    pos_txt_bl = P_bl + u_bl_c * (dist_bl_c * 0.52) + n_bl_c * 2.8
    ax.text(pos_txt_bl[0], pos_txt_bl[1], '认知内化保障',
            fontsize=12.0, fontweight='bold', color=CHARCOAL,
            rotation=angle_bl_c, rotation_mode='anchor',
            ha='center', va='center', zorder=5)

    # BR -> Center: 认知深化路径
    v_br_c = P_c - P_br  # [-33, 31]
    dist_br_c = np.linalg.norm(v_br_c)
    u_br_c = v_br_c / dist_br_c
    angle_br_c = -angle_bl_c # -43.21 degrees
    n_br_read = np.array([u_bl_c[1], u_bl_c[0]]) # northeast normal

    pt_start_br = P_br + u_br_c * 9.8
    pt_end_br = P_c - u_br_c * (cr + 0.5)
    ax.plot([pt_start_br[0], pt_end_br[0]], [pt_start_br[1], pt_end_br[1]],
            color=DASH_LINE, linestyle='--', linewidth=2.0, zorder=2)
    
    # Text '认知深化路径' placed parallel above the dashed line
    pos_txt_br = P_br + u_br_c * (dist_br_c * 0.52) + n_br_read * 2.8
    ax.text(pos_txt_br[0], pos_txt_br[1], '认知深化路径',
            fontsize=12.0, fontweight='bold', color=CHARCOAL,
            rotation=angle_br_c, rotation_mode='anchor',
            ha='center', va='center', zorder=5)

    # 2. Outer double parallel arrows (zorder=3)
    # Left edge: P_bl -> P_top
    v_left = P_top - P_bl  # [33, 71]
    dist_left = np.linalg.norm(v_left)
    u_left = v_left / dist_left
    angle_left = np.degrees(np.arctan2(u_left[1], u_left[0])) # ~ 65.07 degrees
    n_left = np.array([-u_left[1], u_left[0]]) # normal pointing outwards (up-left)

    sep_left = 1.9
    # Outer arrow: BL -> Top (pointing up)
    p1_out = P_bl + n_left * sep_left + u_left * 10.2
    p2_out = P_top + n_left * sep_left - u_left * 9.2
    ax.annotate('', xy=(p2_out[0], p2_out[1]), xytext=(p1_out[0], p1_out[1]),
                arrowprops=dict(arrowstyle='->', color=NAVY, lw=2.2), zorder=3)
    # Text '共在性凝聚': placed outside outer arrow, parallel to line
    pos_txt_gz = P_bl + u_left * (dist_left * 0.52) + n_left * (sep_left + 3.2)
    ax.text(pos_txt_gz[0], pos_txt_gz[1], '共在性凝聚',
            fontsize=12.5, fontweight='bold', color=NAVY,
            rotation=angle_left, rotation_mode='anchor',
            ha='center', va='center', zorder=5)

    # Inner arrow: Top -> BL (pointing down)
    p1_in = P_top - n_left * sep_left - u_left * 9.2
    p2_in = P_bl - n_left * sep_left + u_left * 10.2
    ax.annotate('', xy=(p2_in[0], p2_in[1]), xytext=(p1_in[0], p1_in[1]),
                arrowprops=dict(arrowstyle='->', color=NAVY, lw=2.2), zorder=3)
    # Text '场域性保障': placed inside inner arrow, parallel to line
    pos_txt_cy = P_bl + u_left * (dist_left * 0.52) - n_left * (sep_left + 3.2)
    ax.text(pos_txt_cy[0], pos_txt_cy[1], '场域性保障',
            fontsize=12.5, fontweight='bold', color=NAVY,
            rotation=angle_left, rotation_mode='anchor',
            ha='center', va='center', zorder=5)

    # Right edge: P_top -> P_br
    v_right = P_br - P_top # [33, -71]
    dist_right = np.linalg.norm(v_right)
    u_right = v_right / dist_right
    angle_right = np.degrees(np.arctan2(u_right[1], u_right[0])) # ~ -65.07 degrees
    n_right = np.array([-u_right[1], u_right[0]]) # normal pointing outwards (up-right)

    # Outer arrow: Top -> BR (pointing down)
    p1_rout = P_top + n_right * sep_left + u_right * 9.2
    p2_rout = P_br + n_right * sep_left - u_right * 10.2
    ax.annotate('', xy=(p2_rout[0], p2_rout[1]), xytext=(p1_rout[0], p1_rout[1]),
                arrowprops=dict(arrowstyle='->', color=NAVY, lw=2.2), zorder=3)
    # Text '意义构建': placed outside outer arrow, parallel to line
    pos_txt_yy = P_top + u_right * (dist_right * 0.52) + n_right * (sep_left + 3.2)
    ax.text(pos_txt_yy[0], pos_txt_yy[1], '意义构建',
            fontsize=12.5, fontweight='bold', color=NAVY,
            rotation=angle_right, rotation_mode='anchor',
            ha='center', va='center', zorder=5)

    # Inner arrow: BR -> Top (pointing up)
    p1_rin = P_br - n_right * sep_left - u_right * 10.2
    p2_rin = P_top - n_right * sep_left + u_right * 9.2
    ax.annotate('', xy=(p2_rin[0], p2_rin[1]), xytext=(p1_rin[0], p1_rin[1]),
                arrowprops=dict(arrowstyle='->', color=NAVY, lw=2.2), zorder=3)
    # Text '具身情境': placed inside inner arrow, parallel to line
    pos_txt_js = P_top + u_right * (dist_right * 0.52) - n_right * (sep_left + 3.2)
    ax.text(pos_txt_js[0], pos_txt_js[1], '具身情境',
            fontsize=12.5, fontweight='bold', color=NAVY,
            rotation=angle_right, rotation_mode='anchor',
            ha='center', va='center', zorder=5)

    # Bottom edge: horizontal parallel arrows
    # Top arrow: BR -> BL (pointing left)
    y_btop = P_bl[1] + 1.8
    ax.annotate('', xy=(P_bl[0] + ew/2 + 0.5, y_btop), xytext=(P_br[0] - ew/2 - 0.5, y_btop),
                arrowprops=dict(arrowstyle='->', color=NAVY, lw=2.2), zorder=3)
    ax.text(50.0, y_btop + 2.4, '整合性实践能力', fontsize=12.5, fontweight='bold', color=NAVY,
            ha='center', va='bottom', zorder=5)

    # Bottom arrow: BL -> BR (pointing right)
    y_bbot = P_bl[1] - 1.8
    ax.annotate('', xy=(P_br[0] - ew/2 - 0.5, y_bbot), xytext=(P_bl[0] + ew/2 + 0.5, y_bbot),
                arrowprops=dict(arrowstyle='->', color=NAVY, lw=2.2), zorder=3)
    ax.text(50.0, y_bbot - 2.4, '主体性驱动', fontsize=12.5, fontweight='bold', color=NAVY,
            ha='center', va='top', zorder=5)

    # 3. Draw Nodes (zorder=6)
    e_top = Ellipse(P_top, width=ew, height=eh, facecolor='#F0F7FF', edgecolor=NAVY, linewidth=2.6, zorder=6)
    ax.add_patch(e_top)
    ax.text(P_top[0], P_top[1], '空间社群', fontsize=17.0, fontweight='bold', color=NAVY,
            ha='center', va='center', zorder=7)

    e_bl = Ellipse(P_bl, width=ew, height=eh, facecolor='#F0F7FF', edgecolor=NAVY, linewidth=2.6, zorder=6)
    ax.add_patch(e_bl)
    ax.text(P_bl[0], P_bl[1], '组织治理', fontsize=17.0, fontweight='bold', color=NAVY,
            ha='center', va='center', zorder=7)

    e_br = Ellipse(P_br, width=ew, height=eh, facecolor='#F0F7FF', edgecolor=NAVY, linewidth=2.6, zorder=6)
    ax.add_patch(e_br)
    ax.text(P_br[0], P_br[1], '课程教学', fontsize=17.0, fontweight='bold', color=NAVY,
            ha='center', va='center', zorder=7)

    c_center = Circle(P_c, radius=cr, facecolor=AMBER_BG, edgecolor=AMBER, linewidth=3.2, zorder=6)
    ax.add_patch(c_center)
    ax.text(P_c[0], P_c[1] + 2.2, '科技与人文', fontsize=14.5, fontweight='bold', color=AMBER_TEXT,
            ha='center', va='center', zorder=7)
    ax.text(P_c[0], P_c[1] - 2.5, '协同', fontsize=14.5, fontweight='bold', color=AMBER_TEXT,
            ha='center', va='center', zorder=7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
    plt.close()
    print(f"Generated {output_path} successfully!")

def draw_curriculum_figure(output_path="fig_curriculum_horizontal.png"):
    """
    Figure 3: LSA住宿书院课程构建的四维机制图
    """
    fig, ax = plt.subplots(figsize=(9, 9), dpi=300)
    fig.patch.set_facecolor(CARD_BG)
    ax.set_facecolor(CARD_BG)
    ax.set_aspect('equal')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Outer bounding dashed rounded box
    outer_box = FancyBboxPatch((16, 16), 68, 68, boxstyle="round,pad=1.2,rounding_size=5",
                               edgecolor='#94A3B8', facecolor='#F8FAFC',
                               linestyle='--', linewidth=1.8, zorder=1)
    ax.add_patch(outer_box)

    # Center triangle
    tri_pts = np.array([[50.0, 62.0], [38.0, 42.0], [62.0, 42.0]])
    tri = Polygon(tri_pts, closed=True, facecolor='#E2E8F0', edgecolor=NAVY, linewidth=2.2, zorder=2)
    ax.add_patch(tri)
    ax.text(50.0, 49.5, "整合\n学习", fontsize=15.5, fontweight='bold', color=NAVY,
            ha='center', va='center', zorder=5)

    # 3 Circles at vertices
    P_top = np.array([50.0, 71.5])
    P_bl = np.array([31.0, 37.5])
    P_br = np.array([69.0, 37.5])
    r_cir = 8.5

    # Connecting arrows & parallel rotated text
    # 1. Left diagonal: 公民责任 <---> 整合思维 (思维方式)
    v_left = P_top - P_bl # [19, 34]
    dist_left = np.linalg.norm(v_left)
    u_left = v_left / dist_left
    angle_left = np.degrees(np.arctan2(u_left[1], u_left[0])) # ~ 60.8 degrees
    n_left = np.array([-u_left[1], u_left[0]]) # northwest normal

    p_start_l = P_bl + u_left * (r_cir + 0.8)
    p_end_l = P_top - u_left * (r_cir + 0.8)
    ax.annotate("", xy=(p_end_l[0], p_end_l[1]), xytext=(p_start_l[0], p_start_l[1]),
                arrowprops=dict(arrowstyle="<->", color='#475569', lw=2.0, shrinkA=0, shrinkB=0), zorder=3)
    pos_txt_sw = P_bl + u_left * (dist_left * 0.50) + n_left * 2.8
    ax.text(pos_txt_sw[0], pos_txt_sw[1], "思维方式",
            fontsize=12.0, color='#1E293B', fontweight='bold',
            rotation=angle_left, rotation_mode='anchor',
            ha='center', va='center', zorder=5)

    # 2. Right diagonal: 整合思维 <---> 知识迁移 (跨界整合)
    v_right = P_br - P_top # [19, -34]
    dist_right = np.linalg.norm(v_right)
    u_right = v_right / dist_right
    angle_right = np.degrees(np.arctan2(u_right[1], u_right[0])) # ~ -60.8 degrees
    n_right = np.array([-u_right[1], u_right[0]]) # northeast normal

    p_start_r = P_top + u_right * (r_cir + 0.8)
    p_end_r = P_br - u_right * (r_cir + 0.8)
    ax.annotate("", xy=(p_end_r[0], p_end_r[1]), xytext=(p_start_r[0], p_start_r[1]),
                arrowprops=dict(arrowstyle="<->", color='#475569', lw=2.0, shrinkA=0, shrinkB=0), zorder=3)
    pos_txt_kj = P_top + u_right * (dist_right * 0.50) + n_right * 2.8
    ax.text(pos_txt_kj[0], pos_txt_kj[1], "跨界整合",
            fontsize=12.0, color='#1E293B', fontweight='bold',
            rotation=angle_right, rotation_mode='anchor',
            ha='center', va='center', zorder=5)

    # 3. Bottom horizontal: 公民责任 <---> 知识迁移 (行动载体)
    ax.annotate("", xy=(P_br[0] - r_cir - 0.8, P_bl[1]), xytext=(P_bl[0] + r_cir + 0.8, P_bl[1]),
                arrowprops=dict(arrowstyle="<->", color='#475569', lw=2.0, shrinkA=0, shrinkB=0), zorder=3)
    ax.text(50.0, P_bl[1] - 3.2, "行动载体", fontsize=12.0, color='#1E293B', fontweight='bold',
            ha='center', va='top', zorder=5)

    # Draw Circles (zorder=4)
    circles = [
        (P_top[0], P_top[1], "整合\n思维", SLATE, '#EFF6FF'),
        (P_bl[0], P_bl[1], "公民\n责任", '#0D9488', '#F0FDFA'),
        (P_br[0], P_br[1], "知识\n迁移", AMBER, '#FFFBEB')
    ]
    for cx, cy, txt, col, bg_col in circles:
        c = Circle((cx, cy), radius=r_cir, facecolor=bg_col, edgecolor=col, linewidth=2.6, zorder=4)
        ax.add_patch(c)
        ax.text(cx, cy, txt, fontsize=13.5, fontweight='bold', color=CHARCOAL,
                ha='center', va='center', zorder=5)

    # 4 Outer Rectangular Boxes
    # Top: 课程结构重构
    rect_top = FancyBboxPatch((28, 88.5), 44, 9, boxstyle="round,pad=0.2,rounding_size=2",
                              facecolor='#FFFFFF', edgecolor=NAVY, linewidth=2.4, zorder=6)
    ax.add_patch(rect_top)
    ax.text(50, 93, "课程结构重构", fontsize=15.5, fontweight='bold', color=NAVY,
            ha='center', va='center', zorder=7)

    # Right: 内容联动 (Upright vertically stacked characters)
    rect_right = FancyBboxPatch((88.5, 26), 9.5, 48, boxstyle="round,pad=0.2,rounding_size=2",
                                facecolor='#FFFFFF', edgecolor=NAVY, linewidth=2.4, zorder=6)
    ax.add_patch(rect_right)
    chars_r = ["内", "容", "联", "动"]
    for idx, ch in enumerate(chars_r):
        ax.text(93.25, 62 - idx * 8, ch, fontsize=15.0, fontweight='bold', color=NAVY,
                ha='center', va='center', zorder=7)

    # Bottom: 实践嵌入
    rect_bottom = FancyBboxPatch((28, 2.5), 44, 9, boxstyle="round,pad=0.2,rounding_size=2",
                                 facecolor='#FFFFFF', edgecolor=NAVY, linewidth=2.4, zorder=6)
    ax.add_patch(rect_bottom)
    ax.text(50, 7, "实践嵌入", fontsize=15.5, fontweight='bold', color=NAVY,
            ha='center', va='center', zorder=7)

    # Left: 评估革新 (Upright vertically stacked characters)
    rect_left = FancyBboxPatch((2.0, 26), 9.5, 48, boxstyle="round,pad=0.2,rounding_size=2",
                               facecolor='#FFFFFF', edgecolor=NAVY, linewidth=2.4, zorder=6)
    ax.add_patch(rect_left)
    chars_l = ["评", "估", "革", "新"]
    for idx, ch in enumerate(chars_l):
        ax.text(6.75, 62 - idx * 8, ch, fontsize=15.0, fontweight='bold', color=NAVY,
                ha='center', va='center', zorder=7)

    # 4 Thick outward hollow arrows
    ax.add_patch(FancyArrowPatch((50, 81), (50, 88), arrowstyle='simple,head_width=11,head_length=9',
                                 facecolor='#CBD5E1', edgecolor='#64748B', lw=1, zorder=3))
    ax.add_patch(FancyArrowPatch((81, 50), (88, 50), arrowstyle='simple,head_width=11,head_length=9',
                                 facecolor='#CBD5E1', edgecolor='#64748B', lw=1, zorder=3))
    ax.add_patch(FancyArrowPatch((50, 19), (50, 12), arrowstyle='simple,head_width=11,head_length=9',
                                 facecolor='#CBD5E1', edgecolor='#64748B', lw=1, zorder=3))
    ax.add_patch(FancyArrowPatch((19, 50), (12, 50), arrowstyle='simple,head_width=11,head_length=9',
                                 facecolor='#CBD5E1', edgecolor='#64748B', lw=1, zorder=3))

    # Outer cycle arrows (knowledge flow)
    ax.annotate("", xy=(93.25, 75), xytext=(72, 93),
                arrowprops=dict(arrowstyle="->", color=NAVY, lw=2.2,
                                connectionstyle="angle,angleA=0,angleB=90,rad=0"), zorder=5)
    ax.text(85, 95.5, "知识整合", fontsize=12.5, fontweight='bold', color=NAVY, ha='center', va='bottom')

    ax.annotate("", xy=(72, 7), xytext=(93.25, 25),
                arrowprops=dict(arrowstyle="->", color=NAVY, lw=2.2,
                                connectionstyle="angle,angleA=-90,angleB=180,rad=0"), zorder=5)
    ax.text(86, 9.5, "知识运用", fontsize=12.5, fontweight='bold', color=NAVY, ha='center', va='bottom')

    ax.annotate("", xy=(6.75, 25), xytext=(28, 7),
                arrowprops=dict(arrowstyle="->", color=NAVY, lw=2.2,
                                connectionstyle="angle,angleA=180,angleB=-90,rad=0"), zorder=5)
    ax.text(14, 9.5, "制度保障", fontsize=12.5, fontweight='bold', color=NAVY, ha='center', va='bottom')

    ax.annotate("", xy=(28, 93), xytext=(6.75, 75),
                arrowprops=dict(arrowstyle="->", color=NAVY, lw=2.2,
                                connectionstyle="angle,angleA=90,angleB=0,rad=0"), zorder=5)
    ax.text(14, 95.5, "闭环驱动", fontsize=12.5, fontweight='bold', color=NAVY, ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=False)
    plt.close()
    print(f"Generated {output_path} successfully!")

if __name__ == '__main__':
    draw_ecosystem_figure("fig_ecosystem_horizontal.png")
    draw_curriculum_figure("fig_curriculum_horizontal.png")
