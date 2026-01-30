"""文件搜索核心模块"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


class FileSearcher:
    """文件搜索引擎（优化版）"""
    
    def __init__(self, max_workers=None):
        # 大幅增加线程数以提高并行度（I/O密集型任务，CPU核心数的4-8倍）
        default_workers = (os.cpu_count() or 4) * 8
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
        """在单个文件中搜索所有关键字，并排除包含排除关键字的文件（高性能版）"""
        try:
            # 快速检查文件扩展名，跳过明显的二进制文件
            ext = os.path.splitext(filepath)[1].lower()
            if ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', 
                      '.exe', '.dll', '.jpg', '.png', '.gif', '.mp4', '.mp3', '.avi',
                      '.bin', '.iso', '.dmg', '.tar', '.gz', '.7z', '.pyc', '.class'}:
                return None
            
            # 获取文件大小，跳过过大的文件（超过50MB）和空文件
            try:
                file_size = os.path.getsize(filepath)
                if file_size > 50 * 1024 * 1024 or file_size == 0:
                    return None
            except:
                return None
            
            # 预先转换关键字为小写（避免重复转换）
            keywords_lower = [kw.lower() for kw in keywords]
            exclude_keywords_lower = [kw.lower() for kw in exclude_keywords] if exclude_keywords else []
            
            # 使用流式读取和快速搜索算法
            chunk_size = 65536  # 64KB块
            overlap_size = 1024  # 1KB重叠区防止跨块匹配
            
            found_keywords = set()
            found_exclude = False
            previous_chunk = b''
            
            try:
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        
                        # 与上一块的尾部合并，避免跨块匹配丢失
                        search_chunk = previous_chunk + chunk
                        
                        # 快速二进制文件检测（只检查第一块）
                        if not previous_chunk and ext != '.dat':
                            null_count = search_chunk[:8192].count(b'\x00')
                            if null_count > 100:
                                return None
                        
                        # 尝试解码（UTF-8优先，失败则用latin-1保证不出错）
                        try:
                            text = search_chunk.decode('utf-8', errors='ignore').lower()
                        except:
                            try:
                                text = search_chunk.decode('gbk', errors='ignore').lower()
                            except:
                                text = search_chunk.decode('latin-1').lower()
                        
                        # 先检查排除关键字（如果有）- 一旦找到立即返回
                        if exclude_keywords_lower:
                            for exclude_kw in exclude_keywords_lower:
                                if exclude_kw in text:
                                    return None
                        
                        # 检查所有待查找的关键字
                        for kw in keywords_lower:
                            if kw not in found_keywords and kw in text:
                                found_keywords.add(kw)
                        
                        # 所有关键字都找到了，提前返回
                        if len(found_keywords) == len(keywords_lower):
                            size_kb = file_size / 1024
                            return (filepath, size_kb)
                        
                        # 保存块尾部用于下次合并
                        if len(chunk) == chunk_size:  # 不是最后一块
                            previous_chunk = search_chunk[-overlap_size:]
                        else:
                            break
            except:
                return None
            
            # 文件读完了，检查是否所有关键字都找到
            if len(found_keywords) == len(keywords_lower):
                size_kb = file_size / 1024
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
        except Exception:
            pass
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
