#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""将 icon.png 转换为 icon.ico"""

import sys
import os

# 检查 PIL 是否可用
try:
    from PIL import Image
except ImportError:
    print("Error: PIL not found. Installing Pillow...")
    os.system(f"{sys.executable} -m pip install Pillow -q")
    from PIL import Image

base_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(base_dir, ".."))
icon_path = os.path.join(project_root, "assets", "icon.png")
ico_path = os.path.join(project_root, "assets", "icon.ico")

try:
    print(f"打开图片: {icon_path}")
    img = Image.open(icon_path)
    print(f"原始图片大小: {img.size}")
    print(f"原始图片模式: {img.mode}")
    
    # 转换为RGB（如果有透明通道）
    if img.mode in ('RGBA', 'LA', 'P'):
        # 创建白色背景
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode in ('RGBA', 'LA'):
            rgb_img.paste(img, mask=img.split()[-1])
        else:
            rgb_img.paste(img)
        img = rgb_img
        print("已转换透明通道为白色背景")
    elif img.mode != 'RGB':
        img = img.convert('RGB')
        print(f"已转换为RGB模式")
    
    # 转换为.ico格式（支持多尺寸）
    print(f"转换为.ico格式...")
    img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    
    if os.path.exists(ico_path):
        size = os.path.getsize(ico_path)
        print(f"✓ 成功转换为.ico格式")
        print(f"  输出文件: {ico_path}")
        print(f"  文件大小: {size} bytes")
    else:
        print("✗ 转换失败")
        sys.exit(1)
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
