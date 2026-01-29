"""主应用程序 - UI和主逻辑"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import subprocess

from cache_manager import CacheManager
from config_manager import ConfigManager
from file_searcher import FileSearcher
from utils import parse_keywords, parse_extensions


class FileFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件搜索工具")
        self.root.geometry("1000x700")
        
        # 初始化管理器
        config_file = os.path.join(os.path.expanduser("~"), ".file_finder_config.json")
        cache_dir = os.path.join(os.path.expanduser("~"), ".file_finder_cache")
        
        self.config_manager = ConfigManager(config_file)
        self.cache_manager = CacheManager(cache_dir)
        self.searcher = FileSearcher()
        
        # 当前搜索结果（用于排序）
        self.current_results = []
        
        self.setup_ui()
        self.load_config()
        
        # 绑定快捷键
        self.root.bind('<Return>', lambda e: self.start_search())
        self.root.bind('<Escape>', lambda e: self.stop_search())
        
        # 程序关闭时保存配置
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # 文件夹路径选择（下拉历史）
        ttk.Label(main_frame, text="文件夹路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.folder_var = tk.StringVar()
        self.folder_combobox = ttk.Combobox(main_frame, textvariable=self.folder_var, width=58)
        self.folder_combobox.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(main_frame, text="浏览...", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # 关键字输入（改为下拉框）
        ttk.Label(main_frame, text="关键字:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.keywords_var = tk.StringVar()
        self.keywords_combobox = ttk.Combobox(main_frame, textvariable=self.keywords_var, width=58)
        self.keywords_combobox.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(main_frame, text='(空格分隔，引号包裹短语如"hello world")').grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # 后缀名过滤（下拉历史）
        ttk.Label(main_frame, text="后缀名:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.extensions_var = tk.StringVar()
        self.extensions_combobox = ttk.Combobox(main_frame, textvariable=self.extensions_var, width=58)
        self.extensions_combobox.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(main_frame, text='(可选，多个用空格分隔如: .py .txt .log)').grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # 搜索按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        self.search_button = ttk.Button(button_frame, text="开始搜索 (Enter)", command=self.start_search)
        self.search_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text="停止搜索 (Esc)", command=self.stop_search, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="帮助", command=self.show_help).pack(side=tk.LEFT, padx=5)
        
        # 进度显示
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 结果显示区域（表格视图）
        result_frame = ttk.LabelFrame(main_frame, text="搜索结果", padding="5")
        result_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        # 创建表格
        columns = ('filename', 'path', 'size')
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=20)
        
        # 定义列标题
        self.result_tree.heading('filename', text='文件名')
        self.result_tree.heading('path', text='路径')
        self.result_tree.heading('size', text='大小 (KB)')
        
        # 定义列宽
        self.result_tree.column('filename', width=200)
        self.result_tree.column('path', width=550)
        self.result_tree.column('size', width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        
        self.result_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定双击和右键
        self.result_tree.bind('<Double-Button-1>', self.on_double_click)
        self.result_tree.bind('<Button-3>', self.show_tree_context_menu)
        
        # 排序按钮
        sort_frame = ttk.Frame(main_frame)
        sort_frame.grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Label(sort_frame, text="排序:").pack(side=tk.LEFT, padx=5)
        ttk.Button(sort_frame, text="按大小升序", command=self.sort_by_size_asc).pack(side=tk.LEFT, padx=5)
        ttk.Button(sort_frame, text="按大小降序", command=self.sort_by_size_desc).pack(side=tk.LEFT, padx=5)
        
        # 统计信息
        self.stats_label = ttk.Label(main_frame, text="找到 0 个文件")
        self.stats_label.grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=5)

        instruction_frame = ttk.LabelFrame(main_frame, text="使用说明", padding="8")
        instruction_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        instruction_text = (
            "1. 选择文件夹并输入关键字（空格分隔，需全部匹配）。\n"
            "2. 后缀名过滤可选，多个后缀用空格分隔（如：.py .txt .log）。\n"
            "3. 双击结果打开文件，右键可打开文件夹或复制路径。\n"
            "4. 快捷键：Enter 开始搜索，Esc 停止搜索。"
        )
        ttk.Label(instruction_frame, text=instruction_text, justify=tk.LEFT, wraplength=920).grid(row=0, column=0, sticky=tk.W)
    
    def browse_folder(self):
        """浏览文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            self.save_config()
    
    def start_search(self):
        """开始搜索"""
        folder = self.folder_var.get().strip()
        keywords_text = self.keywords_var.get().strip()
        
        # 验证输入
        if not folder:
            messagebox.showwarning("警告", "请选择文件夹路径")
            return
        
        if not os.path.isdir(folder):
            messagebox.showerror("错误", "指定的文件夹不存在")
            return
        
        if not keywords_text:
            messagebox.showwarning("警告", "请输入至少一个关键字")
            return
        
        # 解析关键字（支持引号）
        keywords = parse_keywords(keywords_text)
        if not keywords:
            messagebox.showwarning("警告", "请输入有效的关键字")
            return
        
        # 添加到搜索历史
        self.config_manager.add_search_history(keywords_text)
        self.update_search_history()
        # 记录文件夹历史
        self.config_manager.add_folder_history(folder)
        self.update_folder_history_ui()
        
        # 解析后缀名过滤
        extensions_text = self.extensions_var.get().strip()
        extensions = parse_extensions(extensions_text)
        # 记录后缀名历史
        self.config_manager.add_extension_history(extensions_text)
        self.update_extension_history_ui()
        
        # 清空之前的结果
        self.clear_results()
        
        # 重置进度条
        self.progress_bar['value'] = 0
        
        # 禁用搜索按钮，启用停止按钮
        self.search_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 保存配置
        self.save_config()
        
        # 在新线程中执行搜索
        def search_thread_func():
            results = self.searcher.search_files_parallel(
                folder, keywords, extensions,
                self.cache_manager,
                self.update_progress,
                self.display_result,
                self.update_stats
            )
            # 保存当前结果供排序使用
            self.current_results = results
            # 重新启用搜索按钮
            self.search_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
        
        search_thread = threading.Thread(target=search_thread_func)
        search_thread.daemon = True
        search_thread.start()
    
    def stop_search(self):
        """停止搜索"""
        self.searcher.stop_search()
        self.update_progress("正在停止搜索...")
        self.search_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def clear_results(self):
        """清空结果"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.stats_label.config(text="找到 0 个文件")
        self.current_results = []
        self.progress_bar['value'] = 0
    
    def sort_by_size_asc(self):
        """按文件大小升序"""
        if not self.current_results:
            messagebox.showinfo("提示", "没有搜索结果可排序")
            return
        
        sorted_results = sorted(self.current_results, key=lambda x: x[1])
        self._display_sorted_results(sorted_results, "升序")
    
    def sort_by_size_desc(self):
        """按文件大小降序"""
        if not self.current_results:
            messagebox.showinfo("提示", "没有搜索结果可排序")
            return
        
        sorted_results = sorted(self.current_results, key=lambda x: x[1], reverse=True)
        self._display_sorted_results(sorted_results, "降序")
    
    def _display_sorted_results(self, sorted_results, sort_type):
        """显示排序后的结果"""
        # 清空表格
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # 重新添加排序后的结果
        for filepath, size_kb in sorted_results:
            filename = os.path.basename(filepath)
            self.result_tree.insert('', tk.END, values=(filename, filepath, f"{size_kb:.2f}"))
        
        self.update_progress(f"已按大小{sort_type}排列，共 {len(sorted_results)} 个文件", 0, 0)
    
    def display_result(self, filepath, size_kb):
        """在结果表格中显示找到的文件"""
        filename = os.path.basename(filepath)
        self.result_tree.insert('', tk.END, values=(filename, filepath, f"{size_kb:.2f}"))
    
    def on_double_click(self, event):
        """双击打开文件"""
        selection = self.result_tree.selection()
        if selection:
            item = self.result_tree.item(selection[0])
            filepath = item['values'][1]  # 路径在第二列
            self.open_file(filepath)
    
    def show_tree_context_menu(self, event):
        """显示表格右键菜单"""
        # 选中点击的行
        item_id = self.result_tree.identify_row(event.y)
        if item_id:
            self.result_tree.selection_set(item_id)
            item = self.result_tree.item(item_id)
            filepath = item['values'][1]  # 路径在第二列
            
            if os.path.exists(filepath):
                menu = tk.Menu(self.result_tree, tearoff=False)
                menu.add_command(label="打开文件", command=lambda: self.open_file(filepath))
                menu.add_command(label="打开所在文件夹", command=lambda: self.open_folder(filepath))
                menu.add_separator()
                menu.add_command(label="复制文件路径", command=lambda: self.copy_to_clipboard(filepath))
                menu.add_command(label="复制文件名", command=lambda: self.copy_to_clipboard(os.path.basename(filepath)))
                menu.post(event.x_root, event.y_root)
    
    def show_context_menu(self, event):
        """显示右键菜单（旧版文本框版本，保留兼容）"""
        try:
            line_start = self.result_text.index(f"@{event.x},{event.y} linestart")
            line_end = self.result_text.index(f"@{event.x},{event.y} lineend")
            line_text = self.result_text.get(line_start, line_end)
            
            if line_text.startswith("文件: "):
                filepath = line_text.replace("文件: ", "").strip()
                
                if os.path.exists(filepath):
                    menu = tk.Menu(self.result_text, tearoff=False)
                    menu.add_command(label="打开文件", command=lambda: self.open_file(filepath))
                    menu.add_command(label="打开所在文件夹", command=lambda: self.open_folder(filepath))
                    menu.add_separator()
                    menu.add_command(label="复制文件路径", command=lambda: self.copy_to_clipboard(filepath))
                    menu.add_command(label="复制文件名", command=lambda: self.copy_to_clipboard(os.path.basename(filepath)))
                    menu.post(event.x_root, event.y_root)
        except Exception:
            pass
    
    def open_file(self, filepath):
        """打开文件"""
        try:
            # 检查文件是否存在
            if not os.path.isfile(filepath):
                messagebox.showerror("错误", f"文件不存在: {filepath}")
                return
            
            # 转换为标准Windows路径
            win_filepath = os.path.abspath(filepath)
            # 使用系统默认程序打开
            subprocess.Popen(f'start "" "{win_filepath}"', shell=True)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件: {str(e)}")
    
    def open_folder(self, filepath):
        """打开文件所在的文件夹"""
        try:
            # 获取文件所在目录
            folder_path = os.path.dirname(filepath)
            
            # 规范化路径（处理正斜杠等问题）
            folder_path = os.path.abspath(folder_path)
            
            # 检查文件夹是否存在
            if not os.path.isdir(folder_path):
                messagebox.showerror("错误", f"文件夹不存在: {folder_path}")
                return
            
            # 方法1：使用explorer打开文件夹并选中文件
            try:
                # 转换为标准Windows路径
                win_filepath = os.path.abspath(filepath)
                # 使用/select参数选中文件
                subprocess.Popen(f'explorer /select,"{win_filepath}"', shell=True)
            except:
                # 方法2：直接打开文件夹
                subprocess.Popen(f'explorer "{folder_path}"', shell=True)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {str(e)}")
    
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            messagebox.showinfo("成功", "已复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {str(e)}")
    
    def update_progress(self, message, current=0, total=0):
        """更新进度标签和进度条"""
        self.progress_label.config(text=message)
        if total > 0:
            progress_percent = (current / total) * 100
            self.progress_bar['value'] = progress_percent
        self.root.update_idletasks()
    
    def update_stats(self, count):
        """更新统计信息"""
        self.stats_label.config(text=f"找到 {count} 个文件")
        self.root.update_idletasks()
    
    def update_search_history(self):
        """更新搜索历史下拉框"""
        config = self.config_manager.load_config()
        history = config.get("search_history", [])
        self.keywords_combobox['values'] = history

    def update_folder_history_ui(self):
        """更新文件夹历史下拉框"""
        config = self.config_manager.load_config()
        history = config.get("folder_history", [])
        self.folder_combobox['values'] = history

    def update_extension_history_ui(self):
        """更新后缀名历史下拉框"""
        config = self.config_manager.load_config()
        history = config.get("extension_history", [])
        self.extensions_combobox['values'] = history
    
    def show_help(self):
        """显示帮助窗口"""
        help_window = tk.Toplevel(self.root)
        help_window.title("帮助")
        help_window.geometry("700x750")
        help_window.resizable(True, True)
        
        main_frame = ttk.Frame(help_window, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        help_window.columnconfigure(0, weight=1)
        help_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        title_label = ttk.Label(main_frame, text="文件搜索工具 - 功能说明", font=("Arial", 13, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        help_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=85, height=30)
        help_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        help_text.config(state=tk.NORMAL)
        
        help_content = """【基本功能】

1. 文件夹选择
   • 点击"浏览..."按钮选择要搜索的文件夹
   • 支持递归搜索所有子文件夹中的文件
   • 路径会自动保存供下次使用

2. 关键字搜索
   • 在"关键字"输入框输入要搜索的文本
   • 多个关键字用空格分隔，需全部匹配（AND逻辑）
   • 使用引号包裹短语：如 "hello world" 或 "hello world" 作为整体搜索
   • 支持中英文引号：英文 ""  ''  或中文 ""  ''
   • 搜索不区分大小写
   • 示例：输入 python test 只查找同时包含"python"和"test"的文件

3. 后缀名过滤（可选）
   • 在"后缀名"输入框输入文件扩展名来限制搜索范围
   • 多个后缀名用空格分隔：如 .py .txt .log
   • 可以省略点号，系统会自动添加
   • 留空则搜索所有支持的文件类型

4. 搜索功能
   • 点击"开始搜索"开始搜索文件
   • 支持停止搜索：点击"停止搜索"按钮可中断当前搜索
   • 搜索进度会实时显示
   • 找到的文件数量会在统计信息中显示

5. 结果操作
   • 搜索结果显示文件路径和文件大小
   • 右键点击结果行可进行以下操作：
     ✓ 打开文件 - 用默认程序打开选中的文件
     ✓ 打开所在文件夹 - 在资源管理器中定位该文件
     ✓ 复制文件路径 - 复制完整的文件路径到剪贴板
     ✓ 复制文件名 - 只复制文件名到剪贴板
   • 点击"清空结果"按钮清空搜索结果列表

6. 排序功能
   • 搜索完成后，可按文件大小排序
   • "按大小升序" - 从小到大排列
   • "按大小降序" - 从大到小排列

【自动缓存机制】

• 系统会自动缓存文件列表以加速文件夹扫描
• 当文件夹内容发生变化（增删改文件）时，自动更新缓存
• 每次搜索都会重新检查文件内容，确保结果准确
• 缓存存储在用户主目录下的 .file_finder_cache 文件夹
• 无需手动管理，系统自动维护

【支持的文件类型】

• 文本格式：.txt, .log, .csv, .json, .xml, .yaml, .toml, .ini
• 代码文件：.py, .java, .cpp, .c, .js, .html, .css, .php, .rb, .go
• 文档格式：.md, .doc, .txt
• 混合型文件：.dat等（使用二进制搜索）
• 自动过滤：图片、视频、压缩包等常见二进制文件

【编码支持】

• 自动检测文件编码：UTF-8, GBK, GB2312, Latin-1, CP1252
• 智能处理不同编码的文件
• 支持中文、英文等多种语言
• 对二进制混合文件使用字节级搜索

【使用提示】

• 首次扫描某个文件夹时会建立文件列表缓存，加速后续搜索
• 系统会自动检测文件夹变化并更新缓存，无需手动操作
• 使用后缀名过滤可以大幅减少搜索范围，提高搜索速度
• 配置信息（路径、关键字、后缀名）会自动保存，下次打开时恢复
• 使用多个关键字可以精确定位目标文件

【故障排除】

如果遇到问题：
1. 检查文件夹路径是否正确且有访问权限
2. 确认关键字拼写正确
3. 检查后缀名格式是否正确（如 .py 而非 py.）
4. 如果文件编码特殊，可能无法被识别

【常见问题】

Q: 为什么第一次搜索较慢？
A: 首次需要扫描文件夹建立文件列表，后续会使用缓存加速。

Q: 缓存占用多少空间？
A: 非常小，通常几KB到几十KB，仅存储文件路径列表。

Q: 能否搜索二进制文件？
A: 支持混合型二进制文件（如.dat），纯二进制文件会被自动过滤。

Q: 多个关键字如何工作？
A: 文件需要同时包含所有关键字才会显示（AND逻辑）。

Q: 搜索会缓存结果吗？
A: 不会。系统只缓存文件列表，每次搜索都重新检查文件内容。

Q: 搜索区分大小写吗？
A: 不区分，"Test"和"test"的搜索结果相同。
"""
        
        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky=tk.E, pady=10)
        ttk.Button(button_frame, text="清理缓存", command=self.clear_cache).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=help_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def save_config(self):
        """保存配置"""
        self.config_manager.save_config(
            self.folder_var.get(),
            self.keywords_var.get(),
            self.extensions_var.get()
        )
    
    def load_config(self):
        """加载配置"""
        config = self.config_manager.load_config()
        if config.get("folder_path"):
            self.folder_var.set(config["folder_path"])
        if config.get("keywords"):
            self.keywords_var.set(config["keywords"])
        if config.get("extensions"):
            self.extensions_var.set(config["extensions"])
        
        # 加载搜索历史
        self.update_search_history()
        self.update_folder_history_ui()
        self.update_extension_history_ui()
    
    def clear_cache(self):
        """清理缓存和配置"""
        import shutil
        try:
            cache_dir = os.path.join(os.path.expanduser("~"), ".file_finder_cache")
            config_file = os.path.join(os.path.expanduser("~"), ".file_finder_config.json")
            
            # 删除缓存目录
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
            
            # 删除配置文件
            if os.path.exists(config_file):
                os.remove(config_file)
            
            # 清空UI中的历史记录
            self.keywords_combobox['values'] = []
            self.folder_combobox['values'] = []
            self.extensions_combobox['values'] = []
            self.keywords_var.set("")
            self.folder_var.set("")
            self.extensions_var.set("")
            
            messagebox.showinfo("成功", "缓存和配置已清理完毕，下次扫描文件夹时将重新建立缓存")
        except Exception as e:
            messagebox.showerror("错误", f"清理缓存时出错: {str(e)}")
    
    def on_closing(self):
        """程序关闭时的处理"""
        self.save_config()
        self.searcher.stop_search()
        self.searcher.shutdown()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = FileFinderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
