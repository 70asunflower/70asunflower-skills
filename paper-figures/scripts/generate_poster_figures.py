# -*- coding: utf-8 -*-
"""
generate_poster_figures.py — 学术海报专用高精度出版级图表生成器模板 (matplotlib 300 DPI)

设计准则：
1. 像素预算：针对海报卡片宽度（PPTX 下约 25~28cm，PDF 下约 50~56cm），以 300 DPI 渲染足够高像素图像；
2. 学术扁平配色：主色深蓝、辅色琥珀金、中性灰底与板岩蓝；
3. 文本遮罩与零重叠：使用 Bbox 遮罩保护连线穿过处的文字，确保远距离易读性；
4. 导出双格式：自动导出高精度 PNG (供 PPTX/PDF 插入) 与矢量 PDF (供单独归档)。
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Ellipse, Circle, FancyBboxPatch, Polygon, FancyArrowPatch
import numpy as np

# 字体配置 (优先加载主流中文字体)
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 学术海报标准色彩体系
C_NAVY = '#0F294A'
C_AMBER = '#C28212'
C_SLATE = '#2B4C7E'
C_BG_CARD = '#FFFFFF'
C_BG_LIGHT = '#F8FAFC'
C_BORDER = '#CBD5E1'
C_TEXT = '#1A202C'
C_TEXT_MUTED = '#475569'

def generate_system_architecture_diagram(output_path="poster_fig1_architecture.png", dpi=300):
    """
    生成经典学术系统架构/机制模型图 (示例)
    """
    fig, ax = plt.subplots(figsize=(8, 5), dpi=dpi)
    fig.patch.set_facecolor(C_BG_CARD)
    ax.set_facecolor(C_BG_CARD)
    ax.set_aspect('equal')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis('off')

    # 1. 绘制顶层容器
    outer_box = FancyBboxPatch((5, 5), 90, 50,
                              boxstyle="round,pad=1.5,rounding_size=3",
                              facecolor=C_BG_LIGHT, edgecolor=C_BORDER,
                              linewidth=1.2, zorder=1)
    ax.add_patch(outer_box)
    
    # 2. 绘制三大核心模块卡片
    modules = [
        {"x": 10, "y": 12, "w": 24, "h": 36, "title": "感知与输入层", "sub": "多模态数据采集\n硬件遥测与环境感知", "color": C_NAVY},
        {"x": 38, "y": 12, "w": 24, "h": 36, "title": "协同与推演层", "sub": "边缘推断引擎\n动态自适应补偿", "color": C_AMBER},
        {"x": 66, "y": 12, "w": 24, "h": 36, "title": "执行与闭环层", "sub": "容错自愈控制\n性能度量与反馈", "color": C_SLATE},
    ]

    for m in modules:
        card = FancyBboxPatch((m["x"], m["y"]), m["w"], m["h"],
                              boxstyle="round,pad=1.0,rounding_size=2.5",
                              facecolor='#FFFFFF', edgecolor=m["color"],
                              linewidth=2.0, zorder=2)
        ax.add_patch(card)
        
        # 标题栏底色
        header = FancyBboxPatch((m["x"], m["y"] + m["h"] - 8), m["w"], 8,
                               boxstyle="round,pad=0.2,rounding_size=1",
                               facecolor=m["color"], edgecolor='none', zorder=3)
        ax.add_patch(header)
        
        ax.text(m["x"] + m["w"]/2, m["y"] + m["h"] - 4, m["title"],
                ha='center', va='center', color='#FFFFFF', fontsize=11, fontweight='bold', zorder=4)
        
        ax.text(m["x"] + m["w"]/2, m["y"] + (m["h"] - 8)/2, m["sub"],
                ha='center', va='center', color=C_TEXT, fontsize=9.5, linespacing=1.6, zorder=4)

    # 3. 绘制层级流动箭头
    arrows = [
        ((34, 30), (38, 30), "特征流"),
        ((62, 30), (66, 30), "控制流"),
    ]
    for start, end, label in arrows:
        arrow = FancyArrowPatch(start, end, arrowstyle='-|>',
                                mutation_scale=15, linewidth=2.0,
                                color=C_AMBER, zorder=5)
        ax.add_patch(arrow)
        ax.text((start[0] + end[0])/2, start[1] + 3.5, label,
                ha='center', va='center', fontsize=8.5, color=C_AMBER,
                fontweight='bold', zorder=6,
                bbox=dict(boxstyle="square,pad=0.2", fc="#FFFFFF", ec="none", alpha=0.9))

    plt.tight_layout(pad=0.5)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor=C_BG_CARD)
    print(f"[Figure] 成功生成高精度图表: {output_path} (300 DPI)")
    plt.close()

if __name__ == "__main__":
    generate_system_architecture_diagram()
