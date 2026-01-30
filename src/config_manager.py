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
        """从文件加载配置（带版本迁移）"""
        default_config = {
            "version": 2,  # 配置文件版本号
            "search_history": [],
            "folder_history": [],
            "extension_history": [],
            "exclude_history": [],
            "exclude_keywords": "",
            "last_search_state": {
                "folder_path": "",
                "keywords": "",
                "extensions": "",
                "exclude_keywords": ""
            }
        }
        
        if not os.path.exists(self.config_file):
            print(f"配置文件不存在，使用默认配置: {self.config_file}")
            return default_config
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    print("配置文件为空，使用默认配置")
                    return default_config
                config = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"配置文件JSON格式错误: {e}")
            # 备份损坏的配置
            try:
                backup_file = self.config_file + '.broken'
                import shutil
                shutil.copy2(self.config_file, backup_file)
                print(f"已备份损坏的配置到: {backup_file}")
            except:
                pass
            return default_config
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            return default_config
        
        # 版本迁移：检查配置版本
        config_version = config.get("version", 1)
        print(f"配置文件版本: v{config_version}")
        
        if config_version < 2:
            print("检测到旧版本配置，开始迁移...")
            # 从v1迁移到v2：确保有last_search_state字段
            if "last_search_state" not in config:
                old_state = {
                    "folder_path": config.get("folder_path", ""),
                    "keywords": config.get("keywords", ""),
                    "extensions": config.get("extensions", ""),
                    "exclude_keywords": config.get("exclude_keywords", "")
                }
                config["last_search_state"] = old_state
                print(f"迁移旧状态: folder={old_state['folder_path']}, keywords={old_state['keywords']}")
            
            config["version"] = 2
            
            # 保存迁移后的配置
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print("配置迁移成功！")
            except Exception as e:
                print(f"保存迁移后的配置失败: {e}")
        
        return config
    
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
        """直接将当前配置保存到文件（带重试和备份）"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            # 备份现有配置（如果存在）
            if os.path.exists(self.config_file):
                backup_file = self.config_file + '.backup'
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                except:
                    pass
            
            # 保存配置
            self.config["version"] = 2  # 确保版本号
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            # 验证保存是否成功
            if os.path.exists(self.config_file):
                return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            # 尝试恢复备份
            backup_file = self.config_file + '.backup'
            if os.path.exists(backup_file):
                try:
                    import shutil
                    shutil.copy2(backup_file, self.config_file)
                except:
                    pass
        return False
    
    def save_last_search_state(self, folder_path, keywords, extensions, exclude_keywords):
        """保存最后一次搜索的状态（用于窗口关闭时）"""
        # 使用内存中的config，避免重复加载
        self.config["last_search_state"] = {
            "folder_path": folder_path,
            "keywords": keywords,
            "extensions": extensions,
            "exclude_keywords": exclude_keywords
        }
        self.config["version"] = 2  # 确保版本号正确
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")  # 调试用
            pass
    
    def get_last_search_state(self):
        """获取最后一次搜索的状态"""
        config = self.load_config()
        return config.get("last_search_state", {
            "folder_path": "",
            "keywords": "",
            "extensions": "",
            "exclude_keywords": ""
        })
