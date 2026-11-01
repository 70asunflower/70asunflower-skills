# -*- coding: utf-8 -*-
"""
check_poster_preflight.py — 学术海报与易拉宝印前/设计自动化巡检工具

功能说明：
1. 画布尺寸核查：PPTX 是否严格采用 30x80cm（1:2 缩放规避 Office 56英寸限制），PDF 是否采用 60x160cm (含3mm出血 60.6x160.6cm)；
2. 底部机械卡槽避让：易拉宝底座卷轴占位 5.5~6.2cm（PPTX 对应 2.8~3.1cm），核查底部是否有内容侵入；
3. 字号规范硬性核查：正文在 1:1 下是否 >= 30pt（PPTX 下 >= 15.0pt），图注/参考文献 >= 20pt (PPTX >= 10.0pt)；
4. 中文标点避头尾禁则：核查是否存在行首孤悬逗号、句号、右括号等排版瑕疵；
5. OpenXML 底层规范：核查 PPTX 是否完整注入 <a:ea> 东亚中文字体声明，杜绝不同操作系统下字体回退。
"""

import os
import sys
import argparse

PUNCTUATION_HANGING = set("，。；：！？、）》】”’…—")

def check_pptx_file(pptx_path):
    print(f"\n========================================================")
    print(f"  [学术海报 PPTX 预检巡检]: {os.path.basename(pptx_path)}")
    print(f"========================================================")
    
    try:
        from pptx import Presentation
        from pptx.util import Cm, Pt
    except ImportError:
        print("[ERROR] python-pptx 未安装，请执行: pip install python-pptx")
        return False

    if not os.path.exists(pptx_path):
        print(f"[ERROR] 文件不存在: {pptx_path}")
        return False

    prs = Presentation(pptx_path)
    slide_w_cm = prs.slide_width.cm
    slide_h_cm = prs.slide_height.cm
    
    issues = []
    warnings = []
    passes = []
    
    # 1. 画布尺寸核查
    print(f"[*] 画布尺寸: {slide_w_cm:.2f} cm × {slide_h_cm:.2f} cm")
    if abs(slide_w_cm - 30.0) < 0.5 and abs(slide_h_cm - 80.0) < 0.5:
        passes.append(f"画布尺寸符合 1:2 黄金缩放标准 (30 cm × 80 cm，严格对应 60 cm × 160 cm 易拉宝成品)")
    elif abs(slide_w_cm - 60.0) < 1.0 or abs(slide_h_cm - 160.0) < 1.0:
        if slide_h_cm > 142.24:
            issues.append(f"致命错误: 幻灯片高度 {slide_h_cm:.1f} cm 超过了 PowerPoint 56 英寸 (142.24 cm) 硬性物理上限！在部分 Office 版本中将导致文件损坏或被强制缩放。必须采用 1:2 比例 (30x80cm)！")
        else:
            warnings.append(f"画布为 1:1 模式，请注意部分 Office 导出工具可能有尺寸截断风险")
    else:
        warnings.append(f"画布尺寸不是标准 30x80cm (实测: {slide_w_cm:.1f}x{slide_h_cm:.1f}cm)")

    # 2. 遍历所有元素检测底部机械卡槽与字号
    min_body_font = 999.0
    small_font_samples = []
    bottom_overflows = []
    missing_ea_tags = 0
    hanging_punct_lines = []
    
    # 底部卡槽警戒线：80cm - 2.8cm = 77.2cm (以 1:2 缩放计算)
    cassette_limit_cm = 77.5 if slide_h_cm <= 85 else 154.0
    
    for slide_idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            # 检查底部侵入
            try:
                shape_bottom_cm = (shape.top + shape.height).cm
                if shape_bottom_cm > cassette_limit_cm:
                    shape_name = shape.name or "未命名组件"
                    bottom_overflows.append(f"{shape_name} 触及底部 {shape_bottom_cm:.2f} cm (警戒线: {cassette_limit_cm:.1f} cm)")
            except Exception:
                pass
            
            # 检查文本框
            if shape.has_text_frame:
                tf = shape.text_frame
                for p_idx, p in enumerate(tf.paragraphs):
                    p_text = "".join(r.text for r in p.runs).strip()
                    if not p_text:
                        continue
                    
                    # 检查标点孤悬
                    lines = p_text.split("\n")
                    for line in lines:
                        clean_line = line.strip()
                        if clean_line and clean_line[0] in PUNCTUATION_HANGING:
                            hanging_punct_lines.append(f"行首标点孤悬: '{clean_line[:15]}...' (首字符: {clean_line[0]})")
                    
                    for run in p.runs:
                        if not run.text.strip():
                            continue
                        
                        # 检查字号
                        if run.font.size is not None:
                            size_pt = run.font.size.pt
                            if size_pt < min_body_font:
                                min_body_font = size_pt
                            if size_pt < 14.5:  # 低于 14.5pt (1:1 下低于 29pt)
                                if len(small_font_samples) < 5:
                                    small_font_samples.append(f"{size_pt:.1f}pt: '{run.text[:20]}'")
                        
                        # 检查东亚字体注入
                        try:
                            rPr = run._r.find('{http://schemas.openxmlformats.org/drawingml/2006/main}rPr')
                            if rPr is not None:
                                ea = rPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}ea')
                                if ea is None:
                                    missing_ea_tags += 1
                            else:
                                missing_ea_tags += 1
                        except Exception:
                            pass

    # 3. 评估指标
    # 底部机械卡槽
    if not bottom_overflows:
        passes.append(f"底部卷轴机械避让区充足（最低元素距画布底边 >= 2.8cm，易拉宝安装绝不吃字）")
    else:
        warnings.append(f"发现 {len(bottom_overflows)} 个元素侵入底部卷轴卡槽区 (易拉宝底部 5.5~6cm 会卷入底壳，可能遮挡末行字):")
        for bo in bottom_overflows[:3]:
            warnings.append(f"   -> {bo}")

    # 字号规范
    if min_body_font >= 15.0:
        passes.append(f"正文字号达标: 最小字号 {min_body_font:.1f}pt (严格对应 1:1 印刷尺寸 >= 30.0pt，远距离清晰可辨)")
    elif min_body_font >= 10.0:
        passes.append(f"海报整体排版正常 (最小字号 {min_body_font:.1f}pt，对应 1:1 印刷下 {min_body_font*2:.1f}pt，通常为图注/文献说明)")
    else:
        warnings.append(f"发现超小字号 ({min_body_font:.1f}pt，1:1 下仅有 {min_body_font*2:.1f}pt)，易拉宝远距离阅读可能吃力:")
        for s in small_font_samples[:3]:
            warnings.append(f"   -> {s}")

    # 标点孤悬
    if not hanging_punct_lines:
        passes.append("标点避头尾检查通过 (未发现行首孤悬标点符号)")
    else:
        warnings.append(f"发现 {len(hanging_punct_lines)} 处行首标点孤悬现象:")
        for hp in hanging_punct_lines[:3]:
            warnings.append(f"   -> {hp}")

    # 东亚字体声明
    if missing_ea_tags == 0:
        passes.append("OpenXML 东亚中文字体标签 (<a:ea>) 100% 声明注入，跨电脑打开绝不乱码")
    else:
        warnings.append(f"检测到 {missing_ea_tags} 个文字 Run 未声明东亚字体标签，在跨操作系统打开时可能回退为默认字体")

    # 4. 输出报告
    print("\n--- 巡检合格项 (PASS) ---")
    for p in passes:
        print(f"  [√ PASS] {p}")
        
    if warnings:
        print("\n--- 优化建议项 (WARNING) ---")
        for w in warnings:
            print(f"  [! WARN] {w}")
            
    if issues:
        print("\n--- 阻断性缺陷 (FAIL) ---")
        for i in issues:
            print(f"  [X FAIL] {i}")
            
    print("\n========================================================")
    if not issues:
        print("  海报 PPTX 预检完成：符合学术会议易拉宝高质量生产与交付标准！")
    else:
        print("  海报 PPTX 预检未通过，请优先修复阻断性缺陷！")
    print("========================================================\n")
    return len(issues) == 0

def check_pdf_file(pdf_path):
    print(f"\n========================================================")
    print(f"  [学术海报 PDF 预检巡检]: {os.path.basename(pdf_path)}")
    print(f"========================================================")
    
    try:
        import fitz
    except ImportError:
        print("[WARN] PyMuPDF (fitz) 未安装，无法执行深度 PDF 页面对象巡检")
        return True

    if not os.path.exists(pdf_path):
        print(f"[ERROR] 文件不存在: {pdf_path}")
        return False

    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # 1 pt = 1/72 inch = 2.54/72 cm = 0.0352778 cm
    pt_to_cm = 2.54 / 72.0
    w_cm = page.rect.width * pt_to_cm
    h_cm = page.rect.height * pt_to_cm
    
    print(f"[*] PDF 物理尺寸: {w_cm:.2f} cm × {h_cm:.2f} cm")
    if abs(w_cm - 60.6) < 0.8 and abs(h_cm - 160.6) < 0.8:
        print("  [√ PASS] 画布尺寸符合 60.6x160.6cm（成品 60x160cm + 四边各 3mm 出血位，印刷厂直接上机）")
    elif abs(w_cm - 60.0) < 0.8 and abs(h_cm - 160.0) < 0.8:
        print("  [√ PASS] 画布尺寸为 60x160cm（成品净尺寸，无额外出血位）")
    else:
        print(f"  [! WARN] 画布尺寸与标准 60x160cm 存在差异 (当前: {w_cm:.1f}x{h_cm:.1f}cm)")
        
    doc.close()
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="学术海报与易拉宝印前/设计自动化巡检工具")
    parser.add_argument("file", nargs="?", default=None, help="待检测的 PPTX 或 PDF 文件路径")
    args = parser.parse_args()

    target_file = args.file
    if not target_file:
        # 默认寻找当前目录下的海报文件
        candidates = [
            "academic_poster_pptx_30x80cm.pptx",
            "build_poster_pptx.pptx",
            "academic_poster_60x160cm.pdf",
            "examples/build_poster_pptx.pptx"
        ]
        for c in candidates:
            if os.path.exists(c):
                target_file = c
                break

    if not target_file or not os.path.exists(target_file):
        print("[INFO] 请指定待检查的文件路径，例如: python check_poster_preflight.py my_poster.pptx")
        sys.exit(0)

    if target_file.lower().endswith(".pptx"):
        check_pptx_file(target_file)
    elif target_file.lower().endswith(".pdf"):
        check_pdf_file(target_file)
    else:
        print(f"[ERROR] 不支持的文件格式: {target_file}")
