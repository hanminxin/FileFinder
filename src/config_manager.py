"""配置管理模块"""
import os
import json


class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = self.load_config()  # 在初始化时加载配置
    
    def save_config(self, folder_path, keywords, extensions, search_history=None):
        """保存配置到文件"""
        try:
            # 加载现有配置以保留搜索历史
            config = self.load_config()
            
            config["folder_path"] = folder_path
            config["keywords"] = keywords
            config["extensions"] = extensions
            
            # 更新搜索历史（如果提供）
            if search_history is not None:
                config["search_history"] = search_history
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config
        except Exception:
            pass
        return {
            "search_history": [],
            "folder_history": [],
            "extension_history": [],
            "exclude_history": [],
            "exclude_keywords": ""
        }
    
    def add_search_history(self, keywords):
        """添加搜索历史"""
        if not keywords.strip():
            return
        
        config = self.load_config()
        history = config.get("search_history", [])
        
        # 如果已存在，先移除
        if keywords in history:
            history.remove(keywords)
        
        # 添加到最前面
        history.insert(0, keywords)
        
        # 只保留最近10条
        history = history[:10]
        
        config["search_history"] = history
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_folder_history(self, folder_path):
        """添加文件夹路径历史"""
        if not folder_path.strip():
            return

        config = self.load_config()
        history = config.get("folder_history", [])

        if folder_path in history:
            history.remove(folder_path)

        history.insert(0, folder_path)
        history = history[:10]

        config["folder_history"] = history

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_extension_history(self, extensions_text):
        """添加后缀名历史（原样保存输入）"""
        text = (extensions_text or "").strip()
        if not text:
            return

        config = self.load_config()
        history = config.get("extension_history", [])

        if text in history:
            history.remove(text)

        history.insert(0, text)
        history = history[:10]

        config["extension_history"] = history

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def add_exclude_history(self, exclude_text):
        """添加排除关键字历史"""
        text = (exclude_text or "").strip()
        if not text:
            return

        config = self.load_config()
        history = config.get("exclude_history", [])

        if text in history:
            history.remove(text)

        history.insert(0, text)
        history = history[:10]

        config["exclude_history"] = history

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def save_config_to_file(self):
        """直接将当前配置保存到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
