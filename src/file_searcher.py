"""文件搜索核心模块"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import messagebox


class FileSearcher:
    """文件搜索引擎（优化版）"""
    
    def __init__(self, max_workers=None):
        # 增加线程数以提高并行度（CPU核心数的2-3倍）
        default_workers = (os.cpu_count() or 4) * 3
        self.executor = ThreadPoolExecutor(max_workers=max_workers or default_workers)
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
    
    def search_file(self, filepath, keywords, exclude_keywords=None):
        """在单个文件中搜索所有关键字，并排除包含排除关键字的文件（优化版）"""
        try:
            # 快速检查文件扩展名，跳过明显的二进制文件
            ext = os.path.splitext(filepath)[1].lower()
            if ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', 
                      '.exe', '.dll', '.jpg', '.png', '.gif', '.mp4', '.mp3'}:
                return None
            
            # 获取文件大小，跳过过大的文件（超过10MB）
            try:
                file_size = os.path.getsize(filepath)
                if file_size > 10 * 1024 * 1024:  # 10MB
                    return None
                if file_size == 0:
                    return None
            except:
                return None
            
            # 对于.dat文件和其他文件使用统一的优化搜索策略
            # 读取文件内容（二进制模式，避免编码错误）
            try:
                with open(filepath, 'rb') as f:
                    content_bytes = f.read()
            except:
                return None
            
            # 快速检测是否为纯二进制文件（检查null字节比例）
            if ext != '.dat':  # .dat允许包含二进制
                null_count = content_bytes[:min(8192, len(content_bytes))].count(b'\x00')
                if null_count > 100:  # 太多null字节，跳过
                    return None
            
            # 转换为小写字符串用于搜索（只做一次）
            content_str = None
            try:
                # 先尝试UTF-8（最常见）
                content_str = content_bytes.decode('utf-8', errors='ignore').lower()
            except:
                try:
                    # 再尝试GBK
                    content_str = content_bytes.decode('gbk', errors='ignore').lower()
                except:
                    return None
            
            if not content_str:
                return None
            
            # 检查是否包含所有关键字（短路求值，找不到立即返回）
            for keyword in keywords:
                if keyword.lower() not in content_str:
                    return None
            
            # 检查排除关键字：如果包含任何排除关键字，则排除该文件
            if exclude_keywords:
                for exclude_kw in exclude_keywords:
                    if exclude_kw.lower() in content_str:
                        return None
            
            # 所有关键字都找到了，且不包含排除关键字
            size_kb = file_size / 1024
            return (filepath, size_kb)
            
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
    
    def search_files_parallel(self, folder_path, keywords, extensions, exclude_keywords,
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
            future = self.executor.submit(self.search_file, filepath, keywords, exclude_keywords)
            futures.append(future)
        
        # 收集结果（优化进度更新频率）
        update_interval = max(1, total_files // 100)  # 最多更新100次
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
            
            # 减少进度更新频率（每处理多个文件更新一次，或找到结果时立即更新）
            if processed % update_interval == 0 or result or processed == total_files:
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
