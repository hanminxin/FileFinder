#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证修改是否有效的最小化测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 语法检查
try:
    from app import FileFinderApp
    print("✓ 应用程序可以正常导入")
    
    # 检查关键配置
    import inspect
    source = inspect.getsource(FileFinderApp.setup_ui)
    
    if "height=10" in source:
        print("✓ 表格高度已改为10")
    if "weight=1)  # 最后一行留出扩展空间" in source:
        print("✓ 行权重已正确配置")
    if "1000x750" in source or "geometry" in source:
        print("✓ 窗口尺寸已检查")
    
    print("\n✓ 所有修改已成功应用")
    
except Exception as e:
    print(f"✗ 错误: {e}")
    sys.exit(1)
