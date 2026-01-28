"""工具函数模块"""


def parse_keywords(keywords_text):
    """解析关键字，支持引号包裹的短语"""
    keywords = []
    current = []
    in_quotes = False
    quote_char = None
    
    for char in keywords_text:
        if char in ('"', "'") and not in_quotes:
            # 开始引号
            in_quotes = True
            quote_char = char
        elif char == quote_char and in_quotes:
            # 结束引号
            in_quotes = False
            if current:
                keywords.append(''.join(current).strip())
                current = []
            quote_char = None
        elif char == ' ' and not in_quotes:
            # 空格分隔（引号外）
            if current:
                keywords.append(''.join(current).strip())
                current = []
        else:
            current.append(char)
    
    # 处理最后一个关键字
    if current:
        keywords.append(''.join(current).strip())
    
    # 过滤空字符串
    return [kw for kw in keywords if kw]


def parse_extensions(extensions_text):
    """解析后缀名列表"""
    if not extensions_text or not extensions_text.strip():
        return None  # 返回None表示不过滤
    
    extensions = []
    for ext in extensions_text.split():
        ext = ext.strip()
        if ext:
            # 确保以点开头
            if not ext.startswith('.'):
                ext = '.' + ext
            extensions.append(ext.lower())
    
    return extensions if extensions else None
