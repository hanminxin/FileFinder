"""缓存管理模块 - 仅缓存文件列表"""
import os
import pickle
import hashlib


class CacheManager:
    """文件列表缓存管理器（不缓存搜索结果）"""
    
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_folder_hash(self, folder_path):
        """生成文件夹的哈希值用于识别文件夹内容是否改变"""
        try:
            # 统计文件夹的文件数量和最后修改时间
            file_count = 0
            max_mtime = 0
            
            for root, dirs, files in os.walk(folder_path):
                file_count += len(files)
                for file in files:
                    filepath = os.path.join(root, file)
                    try:
                        mtime = os.path.getmtime(filepath)
                        max_mtime = max(max_mtime, mtime)
                    except:
                        pass
            
            # 使用文件数量和最后修改时间生成哈希
            hash_str = f"{folder_path}_{file_count}_{max_mtime}"
            return hashlib.md5(hash_str.encode()).hexdigest()
        except Exception:
            return None
    
    def get_cache_path(self, folder_path):
        """获取缓存文件路径"""
        folder_hash = self.get_folder_hash(folder_path)
        if not folder_hash:
            return None
        return os.path.join(self.cache_dir, f"files_{folder_hash}.cache")
    
    def load_file_cache(self, folder_path):
        """从缓存加载文件列表"""
        cache_path = self.get_cache_path(folder_path)
        if not cache_path or not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None
    
    def save_file_cache(self, folder_path, files):
        """保存文件列表到缓存"""
        cache_path = self.get_cache_path(folder_path)
        if not cache_path:
            return
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(files, f)
        except Exception:
            pass
