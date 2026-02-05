"""主应用程序 - UI和主逻辑"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
from queue import Queue, Empty
import subprocess

from cache_manager import CacheManager
from config_manager import ConfigManager
from file_searcher import FileSearcher
from utils import parse_keywords, parse_extensions


class FileFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件搜索工具")
        self.root.geometry("1000x750")  # 增加高度以容纳排序按钮
        
        # 初始化管理器
        config_file = os.path.join(os.path.expanduser("~"), ".file_finder_config.json")
        cache_dir = os.path.join(os.path.expanduser("~"), ".file_finder_cache")
        
        self.config_manager = ConfigManager(config_file)
        self.cache_manager = CacheManager(cache_dir)
        self.searcher = FileSearcher()
        
        # 当前搜索结果（用于排序）
        self.current_results = []
        
        # 排除关键字框的显示状态
        self.exclude_frame = None
        self.exclude_visible = False

        # UI队列（确保线程安全更新UI）
        self.ui_queue = Queue()
        
        self.setup_ui()
        self.load_config()
        
        # 绑定快捷键
        self.root.bind('<Return>', lambda e: self.start_search())
        self.root.bind('<Escape>', lambda e: self.stop_search())
        
        # 程序关闭时保存配置
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 启动UI队列处理
        self.root.after(50, self.process_ui_queue)

    def run_on_ui_thread(self, func, *args, **kwargs):
        """将UI更新任务投递到主线程"""
        self.ui_queue.put((func, args, kwargs))
    
    def _enable_undo(self, combobox):
        """为 Combobox 启用撤销/重做功能"""
        # 获取 Combobox 内部的 Entry 控件
        entry = combobox
        
        # 初始化撤销栈
        if not hasattr(self, '_undo_stacks'):
            self._undo_stacks = {}
            self._redo_stacks = {}
        
        self._undo_stacks[entry] = []
        self._redo_stacks[entry] = []
        
        # 记录初始值
        def record_change(event=None):
            current = combobox.get()
            stack = self._undo_stacks[entry]
            if not stack or stack[-1] != current:
                stack.append(current)
                # 限制栈大小
                if len(stack) > 50:
                    stack.pop(0)
                # 清空重做栈
                self._redo_stacks[entry].clear()
        
        # 撤销操作
        def undo(event=None):
            stack = self._undo_stacks[entry]
            redo_stack = self._redo_stacks[entry]
            if len(stack) > 1:
                current = stack.pop()
                redo_stack.append(current)
                combobox.set(stack[-1])
            return "break"
        
        # 重做操作
        def redo(event=None):
            redo_stack = self._redo_stacks[entry]
            stack = self._undo_stacks[entry]
            if redo_stack:
                value = redo_stack.pop()
                stack.append(value)
                combobox.set(value)
            return "break"
        
        # 绑定事件
        combobox.bind('<KeyRelease>', record_change)
        combobox.bind('<Control-z>', undo)
        combobox.bind('<Control-y>', redo)
        combobox.bind('<Control-Shift-Z>', redo)

    def process_ui_queue(self):
        """处理UI队列中的任务"""
        try:
            while True:
                func, args, kwargs = self.ui_queue.get_nowait()
                try:
                    func(*args, **kwargs)
                except Exception:
                    pass
        except Empty:
            pass
        self.root.after(50, self.process_ui_queue)
    
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重 - 统一设置所有可能的行
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        # 设置所有可能的行高
        for i in range(10):
            main_frame.rowconfigure(i, weight=0)
        # 不设置任何行为weight=1，让所有内容按需要显示，最后留出扩展空间
        main_frame.rowconfigure(9, weight=1)  # 最后一行留出扩展空间
        self.main_frame = main_frame  # 保存引用
        
        # 文件夹路径选择（下拉历史）
        ttk.Label(main_frame, text="文件夹路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.folder_var = tk.StringVar()
        self.folder_combobox = ttk.Combobox(main_frame, textvariable=self.folder_var, width=58)
        self.folder_combobox.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self._enable_undo(self.folder_combobox)
        ttk.Button(main_frame, text="浏览...", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # 关键字输入（改为下拉框）
        ttk.Label(main_frame, text="关键字:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.keywords_var = tk.StringVar()
        self.keywords_combobox = ttk.Combobox(main_frame, textvariable=self.keywords_var, width=58)
        self.keywords_combobox.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self._enable_undo(self.keywords_combobox)
        ttk.Label(main_frame, text='(空格分隔，引号包裹短语如"hello world")').grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # 后缀名过滤（下拉历史）
        ttk.Label(main_frame, text="后缀名:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.extensions_var = tk.StringVar()
        self.extensions_combobox = ttk.Combobox(main_frame, textvariable=self.extensions_var, width=58)
        self.extensions_combobox.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self._enable_undo(self.extensions_combobox)
        ttk.Label(main_frame, text='(可选，多个用空格分隔如: .py .txt .log)').grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # 排除关键字框（初始隐藏）
        self.exclude_frame = ttk.LabelFrame(main_frame, text="排除关键字（可选）", padding="5")
        # 不显示排除框，初始状态下隐藏
        # row号会动态更新
        
        # 设置列权重，使输入框宽度与其他行一致
        self.exclude_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.exclude_frame, text="排除关键字:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.exclude_var = tk.StringVar()
        self.exclude_combobox = ttk.Combobox(self.exclude_frame, textvariable=self.exclude_var, width=58)
        self.exclude_combobox.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self._enable_undo(self.exclude_combobox)
        ttk.Label(self.exclude_frame, text='(空格分隔，匹配任一关键字则排除)').grid(row=0, column=2, sticky=tk.W, pady=5)

        self.ignore_comments_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.exclude_frame,
            text='忽略注释（每行“$”后内容）',
            variable=self.ignore_comments_var
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        # 搜索按钮
        button_frame = ttk.Frame(main_frame)
        self.button_frame = button_frame  # 保存引用以便动态调整
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)  # row=3，排除框隐藏时在row=3之下
        self.search_button = ttk.Button(button_frame, text="开始搜索 (Enter)", command=self.start_search)
        self.search_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text="停止搜索 (Esc)", command=self.stop_search, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        self.toggle_exclude_btn = ttk.Button(button_frame, text="高级选项 ▼", command=self.toggle_exclude_frame)
        self.toggle_exclude_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="帮助", command=self.show_help).pack(side=tk.LEFT, padx=5)
        
        # 进度显示框
        progress_frame = ttk.Frame(main_frame)
        self.progress_frame = progress_frame
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 结果显示区域（表格视图）
        result_frame = ttk.LabelFrame(main_frame, text="搜索结果", padding="5")
        self.result_frame = result_frame
        # 只在水平方向扩展，不在垂直方向扩展
        result_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        # 创建表格，使用固定高度（约10行显示）
        columns = ('filename', 'path', 'size')
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=10)
        
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
        self.sort_frame = sort_frame
        sort_frame.grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Label(sort_frame, text="排序:").pack(side=tk.LEFT, padx=5)
        ttk.Button(sort_frame, text="按大小升序", command=self.sort_by_size_asc).pack(side=tk.LEFT, padx=5)
        ttk.Button(sort_frame, text="按大小降序", command=self.sort_by_size_desc).pack(side=tk.LEFT, padx=5)
        
        # 统计信息
        self.stats_label = ttk.Label(main_frame, text="找到 0 个文件")
        self.stats_label.grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=5)
        self.stats_row = 7

        instruction_frame = ttk.LabelFrame(main_frame, text="使用说明", padding="8")
        self.instruction_frame = instruction_frame
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
        
        # 解析排除关键字
        exclude_text = self.exclude_var.get().strip()
        exclude_keywords = parse_keywords(exclude_text) if exclude_text else []
        # 如果有排除关键字，保存到历史
        if exclude_text:
            self.config_manager.add_exclude_history(exclude_text)
        self.update_exclude_history_ui()
        
        # 清空之前的结果
        self.clear_results()
        
        # 重置进度条
        self.progress_bar['value'] = 0
        
        # 禁用搜索按钮，启用停止按钮
        self.search_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # 线程安全的UI回调
        def safe_update_progress(message, current=0, total=0):
            self.run_on_ui_thread(self.update_progress, message, current, total)

        def safe_display_result(filepath, size_kb):
            self.run_on_ui_thread(self.display_result, filepath, size_kb)

        def safe_update_stats(count):
            self.run_on_ui_thread(self.update_stats, count)
        
        ignore_comments = self.ignore_comments_var.get()

        # 在新线程中执行搜索
        def search_thread_func():
            try:
                results = self.searcher.search_files_parallel(
                    folder, keywords, extensions, exclude_keywords,
                    ignore_comments,
                    self.cache_manager,
                    safe_update_progress,
                    safe_display_result,
                    safe_update_stats
                )
                # 保存当前结果供排序使用
                self.current_results = results
            except Exception as e:
                self.run_on_ui_thread(messagebox.showerror, "错误", f"搜索过程中出错: {str(e)}")
            finally:
                # 重新启用搜索按钮
                self.run_on_ui_thread(self.search_button.config, state=tk.NORMAL)
                self.run_on_ui_thread(self.stop_button.config, state=tk.DISABLED)
        
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
    
    def update_exclude_history_ui(self):
        """更新排除关键字历史下拉框"""
        config = self.config_manager.load_config()
        history = config.get("exclude_history", [])
        self.exclude_combobox['values'] = history
    
    def toggle_exclude_frame(self):
        """切换排除关键字框的显示/隐藏"""
        if self.exclude_visible:
            # 隐藏排除框
            self.exclude_frame.grid_forget()
            self.exclude_visible = False
            self.toggle_exclude_btn.config(text="高级选项 ▼")
            # 恢复原始的rowconfigure权重
            self.main_frame.rowconfigure(5, weight=0)
            self.main_frame.rowconfigure(6, weight=0)
            self.main_frame.rowconfigure(7, weight=0)
            self.main_frame.rowconfigure(8, weight=0)
            self.main_frame.rowconfigure(9, weight=1)  # 最后一行留出扩展空间
            # 隐藏后恢复原始行号
            self.button_frame.grid(row=3, column=0, columnspan=3, pady=10)
            self.progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
            self.result_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
            self.sort_frame.grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=5)
            self.stats_label.grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=5)
            self.instruction_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
        else:
            # 显示排除框（在后缀名框之后）
            self.exclude_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=0, pady=5)
            self.exclude_visible = True
            self.toggle_exclude_btn.config(text="高级选项 ▲")
            # 更新rowconfigure权重
            self.main_frame.rowconfigure(5, weight=0)
            self.main_frame.rowconfigure(6, weight=0)
            self.main_frame.rowconfigure(7, weight=0)
            self.main_frame.rowconfigure(8, weight=0)
            self.main_frame.rowconfigure(9, weight=1)  # 最后一行留出扩展空间
            # 显示后调整所有元素的行号
            self.button_frame.grid(row=4, column=0, columnspan=3, pady=10)  # 搜索按钮移到row=4
            self.progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
            self.result_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
            self.sort_frame.grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=5)
            self.stats_label.grid(row=8, column=0, columnspan=3, sticky=tk.W, pady=5)
            self.instruction_frame.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=8)
            # 更新排除历史
            self.update_exclude_history_ui()
    
    def show_help(self):
        """显示帮助窗口"""
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("700x750")
        help_window.resizable(True, True)
        
        main_frame = ttk.Frame(help_window, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        help_window.columnconfigure(0, weight=1)
        help_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        title_label = ttk.Label(main_frame, text="文件搜索工具 - 使用说明", font=("Arial", 13, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        help_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=85, height=30)
        help_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        help_text.config(state=tk.NORMAL)
        
        help_content = """【快速上手】

1. 选择文件夹 → 输入关键字 → 点击“开始搜索”。
2. 多个关键字用空格分隔，需全部匹配；引号可包住短语。
3. 后缀名可选：如 .py .txt .log；留空表示全部。

【高级选项】

• 排除关键字：包含任一排除词的文件会被过滤。
• 忽略注释：勾选后，忽略每行“$”后的内容。

【结果操作】

• 右键结果可打开文件/打开所在文件夹/复制路径。
• 支持按文件大小升序/降序排序。

【提示】

• 第一次搜索较慢是正常的，会自动缓存文件列表。
• 搜索不区分大小写。
• Esc 可停止搜索。
"""
        
        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky=tk.E, pady=10)
        ttk.Button(button_frame, text="清理缓存", command=self.clear_cache).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空历史记录", command=self.clear_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=help_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def save_config(self):
        """保存配置"""
        folder_path = self.folder_var.get()
        keywords = self.keywords_var.get()
        extensions = self.extensions_var.get()
        exclude_text = self.exclude_var.get().strip()
        
        # 保存当前搜索字段状态
        self.config_manager.save_last_search_state(
            folder_path,
            keywords,
            extensions,
            exclude_text
        )
        
        # 保存排除关键字
        self.config_manager.config['exclude_keywords'] = exclude_text
        self.config_manager.save_config_to_file()
    
    def load_config(self):
        """加载配置"""
        config = self.config_manager.load_config()
        
        # 恢复上次搜索的字段状态（无论是否为空都要设置）
        last_state = self.config_manager.get_last_search_state()
        self.folder_var.set(last_state.get("folder_path", ""))
        self.keywords_var.set(last_state.get("keywords", ""))
        self.extensions_var.set(last_state.get("extensions", ""))
        # 排除关键字不自动恢复上次输入
        self.exclude_var.set("")
        
        # 加载搜索历史到下拉框
        self.update_search_history()
        self.update_folder_history_ui()
        self.update_extension_history_ui()
        self.update_exclude_history_ui()
    
    def clear_cache(self):
        """清理文件列表缓存（不清理历史记录）"""
        import shutil
        try:
            cache_dir = os.path.join(os.path.expanduser("~"), ".file_finder_cache")
            
            # 只删除缓存目录
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                messagebox.showinfo("成功", "文件列表缓存已清理，历史记录保留\n下次搜索时将重新扫描文件夹")
            else:
                messagebox.showinfo("提示", "缓存目录不存在，无需清理")
        except Exception as e:
            messagebox.showerror("错误", f"清理缓存时出错: {str(e)}")
    
    def clear_history(self):
        """清空所有历史记录"""
        result = messagebox.askyesno(
            "确认", 
            "确定要清空所有历史记录吗？\n\n这将清空：\n• 搜索关键字历史\n• 文件夹路径历史\n• 文件扩展名历史\n• 排除关键字历史\n\n此操作不可恢复！"
        )
        
        if not result:
            return
        
        try:
            # 重置配置中的历史记录
            self.config_manager.config["search_history"] = []
            self.config_manager.config["folder_history"] = []
            self.config_manager.config["extension_history"] = []
            self.config_manager.config["exclude_history"] = []
            
            # 保存配置
            self.config_manager.save_config_to_file()
            
            # 清空UI中的下拉列表
            self.keywords_combobox['values'] = []
            self.folder_combobox['values'] = []
            self.extensions_combobox['values'] = []
            self.exclude_combobox['values'] = []
            
            # 不清空当前输入框的内容，保留当前工作状态
            
            messagebox.showinfo("成功", "历史记录已清空！\n当前输入框的内容已保留")
        except Exception as e:
            messagebox.showerror("错误", f"清空历史记录时出错: {str(e)}")
    
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
