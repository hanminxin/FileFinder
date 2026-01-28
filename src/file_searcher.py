"""文件搜索核心模块"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import messagebox


class FileSearcher:
    """文件搜索引擎"""
    
    def __init__(self, max_workers=None):
        self.executor = ThreadPoolExecutor(max_workers=max_workers or os.cpu_count() or 4)
        self.is_searching = False
    
    def is_ascii_file(self, filepath):
        """检测文件是否为 ASCII 文本文件"""
        try:
            # 检查文件扩展名，排除常见的二进制文件
            binary_extensions = {
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
                '.exe', '.dll', '.so', '.dylib',
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
                '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wav', '.flac',
                '.db', '.sqlite', '.mdb',
                '.class', '.jar', '.war', '.ear',
                '.pyc', '.pyo', '.pyd'
            }
            
            ext = os.path.splitext(filepath)[1].lower()
            if ext in binary_extensions:
                return False
            
            with open(filepath, 'rb') as f:
                # 读取前 8KB 进行检测
                chunk = f.read(8192)
                if not chunk:
                    return False
                
                # 检查常见二进制文件的魔数（文件头）
                if chunk.startswith(b'%PDF'):  # PDF
                    return False
                if chunk.startswith(b'PK\x03\x04'):  # ZIP/Office文档
                    return False
                if chunk.startswith(b'\x89PNG'):  # PNG
                    return False
                if chunk.startswith(b'\xff\xd8\xff'):  # JPEG
                    return False
                if chunk.startswith(b'GIF8'):  # GIF
                    return False
                if chunk.startswith(b'MZ'):  # EXE/DLL
                    return False
                if chunk.startswith(b'\xd0\xcf\x11\xe0'):  # MS Office老格式
                    return False
                
                # 对于.dat文件，更宽松的检测，因为可能包含混合数据
                if ext.lower() == '.dat':
                    # 只要包含一些可搜索的文本就可以
                    null_byte_count = chunk.count(b'\x00')
                    # 超过90%都是null字节的话才判定为二进制
                    if null_byte_count / len(chunk) > 0.9:
                        return False
                    return True
                
                # 对于其他文件，检查是否包含空字节
                if b'\x00' in chunk:
                    return False
                
                # 检查是否包含过多的非 ASCII 字符
                non_ascii_count = sum(1 for byte in chunk if byte > 127)
                # 如果非 ASCII 字符超过 30%，认为不是 ASCII 文件
                if non_ascii_count / len(chunk) > 0.3:
                    return False
                
                return True
        except Exception:
            return False
    
    def search_file(self, filepath, keywords):
        """在单个文件中搜索所有关键字"""
        try:
            # 检查是否为 ASCII 文件
            if not self.is_ascii_file(filepath):
                return None
            
            ext = os.path.splitext(filepath)[1].lower()
            
            # 对于.dat文件，尝试二进制搜索
            if ext == '.dat':
                try:
                    with open(filepath, 'rb') as f:
                        content_bytes = f.read()
                    
                    # 检查所有关键字是否存在（不区分大小写）
                    all_found = True
                    for keyword in keywords:
                        keyword_lower = keyword.lower()
                        keyword_bytes_utf8 = keyword_lower.encode('utf-8')
                        keyword_bytes_gbk = None
                        try:
                            keyword_bytes_gbk = keyword_lower.encode('gbk')
                        except:
                            pass
                        
                        found = keyword_bytes_utf8 in content_bytes
                        if not found and keyword_bytes_gbk:
                            found = keyword_bytes_gbk in content_bytes
                        
                        # 也尝试直接搜索小写版本
                        if not found:
                            try:
                                content_str = content_bytes.decode('utf-8', errors='ignore').lower()
                                if keyword_lower in content_str:
                                    found = True
                            except:
                                pass
                        
                        if not found:
                            try:
                                content_str = content_bytes.decode('gbk', errors='ignore').lower()
                                if keyword_lower in content_str:
                                    found = True
                            except:
                                pass
                        
                        if not found:
                            all_found = False
                            break
                    
                    if all_found:
                        size_kb = os.path.getsize(filepath) / 1024
                        return (filepath, size_kb)
                    return None
                except Exception:
                    pass
            
            # 对于其他文件，尝试多种编码读取
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']
            content = None
            
            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read().lower()
                    break
                except Exception:
                    continue
            
            # 如果所有编码都失败，跳过此文件
            if content is None:
                return None
            
            # 检查是否包含所有关键字
            if all(keyword.lower() in content for keyword in keywords):
                # 获取文件大小（KB）
                size_kb = os.path.getsize(filepath) / 1024
                return (filepath, size_kb)
            
            return None
        except Exception:
            return None
    
    def get_all_files(self, folder_path):
        """递归获取文件夹下的所有文件"""
        all_files = []
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    all_files.append(os.path.join(root, file))
        except Exception as e:
            messagebox.showerror("错误", f"访问文件夹时出错: {str(e)}")
        return all_files
    
    def search_files_parallel(self, folder_path, keywords, extensions, 
                            cache_manager,
                            progress_callback, result_callback, stats_callback):
        """并行搜索文件（每次都重新搜索内容，仅缓存文件列表）"""
        self.is_searching = True
        found_count = 0
        
        # 尝试从缓存加载文件列表
        all_files = cache_manager.load_file_cache(folder_path)
        
        if all_files is None:
            # 扫描文件夹
            progress_callback("正在扫描文件夹...", 0, 0)
            all_files = self.get_all_files(folder_path)
            # 保存到缓存
            cache_manager.save_file_cache(folder_path, all_files)
        else:
            progress_callback(f"使用缓存文件列表，共 {len(all_files)} 个文件", 0, 0)
        
        # 根据后缀名过滤文件
        if extensions:
            filtered_files = [f for f in all_files if os.path.splitext(f)[1].lower() in extensions]
            progress_callback(f"后缀名过滤：{len(all_files)} → {len(filtered_files)} 个文件", 0, 0)
            all_files = filtered_files
        
        total_files = len(all_files)
        
        if total_files == 0:
            progress_callback("文件夹中没有文件", 0, 0)
            self.is_searching = False
            return []
        
        progress_callback(f"准备搜索 {total_files} 个文件...", 0, total_files)
        
        # 并行处理文件
        processed = 0
        futures = []
        search_results = []
        
        for filepath in all_files:
            if not self.is_searching:
                break
            future = self.executor.submit(self.search_file, filepath, keywords)
            futures.append(future)
        
        # 收集结果
        for future in as_completed(futures):
            if not self.is_searching:
                break
            
            processed += 1
            result = future.result()
            
            if result:
                filepath, size_kb = result
                found_count += 1
                search_results.append((filepath, size_kb))
                result_callback(filepath, size_kb)
                stats_callback(found_count)
            
            # 更新进度（每处理一个文件就更新）
            progress_callback(f"已搜索 {processed}/{total_files} 个文件，找到 {found_count} 个", processed, total_files)
        
        progress_callback(f"搜索完成！共处理 {processed} 个文件，找到 {found_count} 个匹配文件", processed, total_files)
        self.is_searching = False
        
        return search_results
    
    def stop_search(self):
        """停止搜索"""
        self.is_searching = False
    
    def shutdown(self):
        """关闭线程池"""
        self.executor.shutdown(wait=False)
