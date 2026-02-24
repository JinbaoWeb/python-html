import os
import markdown
import json
from datetime import datetime

INPUT_DIR = '.'
OUTPUT_DIR = 'output'
SEARCH_INDEX_FILE = 'search_index.json'

os.makedirs(OUTPUT_DIR, exist_ok=True)
search_data = []

def convert():
    md_files = []
    
    # 初始化 Markdown 工具，启用：
    # extra: 包含表格、属性列表、Fenced Code 等
    # codehilite: 代码高亮支持
    # toc: 目录支持
    md_processor = markdown.Markdown(extensions=[
        'extra', 
        'codehilite', 
        'toc', 
        'fenced_code'
    ])

    for root, dirs, files in os.walk(INPUT_DIR):
        if any(exclude in root for exclude in [OUTPUT_DIR, '.github', '.git']):
            continue
            
        for file in files:
            if file.endswith('.md'):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, INPUT_DIR)
                html_rel_path = rel_path.replace('.md', '.html')
                title = os.path.splitext(file)[0].replace('-', ' ').title()
                
                with open(path, 'r', encoding='utf-8') as f:
                    md_text = f.read()
                
                # 转换 Markdown
                html_body = md_processor.convert(md_text)
                
                # 搜索索引
                search_data.append({'title': title, 'path': html_rel_path, 'content': md_text})
                
                depth = html_rel_path.count(os.sep)
                root_prefix = "./" if depth == 0 else "../" * depth

                # 注入 HTML 模板
                full_html = f"""
                <!DOCTYPE html>
                <html lang="zh">
                <head>
                    <meta charset="utf-8">
                    <title>{title}</title>
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
                    <style>
                        body {{ box-sizing: border-box; min-width: 200px; max-width: 980px; margin: 0 auto; padding: 45px; }}
                        .nav-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
                        @media (max-width: 767px) {{ body {{ padding: 15px; }} }}
                    </style>
                    
                    <script>
                    window.MathJax = {{
                      tex: {{
                        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                        processEscapes: true
                      }}
                    }};
                    </script>
                    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
                </head>
                <body class="markdown-body">
                    <div class="nav-header">
                        <a href="{root_prefix}index.html">🏠 首页</a>
                        <input type="text" id="searchInput" placeholder="搜索..." style="padding:5px; border-radius:4px; border:1px solid #ccc;">
                    </div>
                    <div id="searchResults" style="display:none; background:#f6f8fa; padding:10px; border-radius:6px; margin-bottom:20px;">
                        <ul id="searchResultsList"></ul>
                    </div>

                    {html_body}
                    
                    <hr><p style="font-size: 0.8em; color: #666;">Updated: {datetime.now().strftime('%Y-%m-%d')}</p>

                    <script>
                        /* 之前的搜索 JS 逻辑保持不变... */
                    </script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
                </body>
                </html>
                """
                
                dest_path = os.path.join(OUTPUT_DIR, html_rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(full_html)
                md_files.append((title, html_rel_path))
                md_processor.reset()

    # 保存索引文件
    with open(os.path.join(OUTPUT_DIR, SEARCH_INDEX_FILE), 'w', encoding='utf-8') as f:
        json.dump(search_data, f, ensure_ascii=False)

if __name__ == "__main__":
    convert()
