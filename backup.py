import os
import markdown
import shutil

# 增强版的 HTML 模板，包含响应式 Nav
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>

    <link href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.min.css" rel="stylesheet" />
    <link href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-okaidia.min.css" rel="stylesheet" />
    <link href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/line-numbers/prism-line-numbers.min.css" rel="stylesheet" />

    <script>
        window.MathJax = {{
            tex: {{
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            }}
        }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

    <style>
        :root {{ 
            --nav-bg: #2d3436; 
            --nav-text: #dfe6e9; 
            --accent: #ffffff; 
            --content-width: 800px;
        }}
        body {{ font-family: "Times New Roman", Times, serif; margin: 0; background: #ffffff; }}

        /* --- 导航栏容器 --- */
        nav {{ 
            background: #2d3436; 
            color: var(--nav-text); 
            position: sticky; 
            top: 0; 
            z-index: 1000; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .nav-container {{
            max-width: var(--content-width);
            margin: 0 auto;
            padding: 0.8rem 2rem;
            display: flex; justify-content: space-between; align-items: center;
            position: relative; /* 为子元素定位提供参考 */
        }}
        .nav-title {{ font-weight: bold; font-size: 1.5rem; }}

        /* --- 导航链接 (PC端) --- */
        .nav-links {{ 
            display: flex; 
            gap: 25px; 
            list-style: none; 
            margin: 0; 
            padding: 0; 
            transition: all 0.4s ease-in-out; 
        }}
        .nav-links a {{ color: var(--nav-text); text-decoration: none; font-size: 1.1rem; font-weight: 500; }}
        .nav-links a:hover {{ color: var(--accent); }}

        #menu-toggle {{ display: none; }}

        /* --- 汉堡图标线条动画 (保持之前的酷炫效果) --- */
        .hamburger {{
            display: none; width: 26px; height: 18px; position: relative; cursor: pointer; z-index: 1001;
        }}
        .hamburger span {{
            display: block; position: absolute; height: 3px; width: 100%; background: var(--nav-text);
            border-radius: 3px; transition: .25s ease-in-out;
        }}
        .hamburger span:nth-child(1) {{ top: 0; }}
        .hamburger span:nth-child(2) {{ top: 7px; }}
        .hamburger span:nth-child(3) {{ top: 14px; }}

        #menu-toggle:checked ~ .hamburger span:nth-child(1) {{ top: 7px; transform: rotate(135deg); }}
        #menu-toggle:checked ~ .hamburger span:nth-child(2) {{ opacity: 0; transform: translateX(-20px); }}
        #menu-toggle:checked ~ .hamburger span:nth-child(3) {{ top: 7px; transform: rotate(-135deg); }}

        /* --- 向下滑动逻辑 (核心修改) --- */
        @media (max-width: 768px) {{
            .hamburger {{ display: block; }}

            .nav-links {{
                position: absolute;
                top: 100%; /* 从导航栏底部开始 */
                left: 0;
                width: 100%;
                background: #353b48;
                flex-direction: column;
                gap: 0;
                /* 关键：使用高度和缩放实现向下滑动 */
                max-height: 0;
                overflow: hidden;
                opacity: 0;
                transform-origin: top;
                transform: scaleY(0);
                box-shadow: 0 10px 15px rgba(0,0,0,0.1);
            }}

            .nav-links li {{ width: 100%; text-align: center; border-top: 1px solid rgba(255,255,255,0.05); }}
            .nav-links a {{ display: block; padding: 1.2rem 0; width: 100%; }}

            /* 展开状态 */
            #menu-toggle:checked ~ .nav-links {{
                max-height: 500px; /* 足够容纳菜单的高度 */
                opacity: 1;
                transform: scaleY(1);
            }}
        }}

        article {{ 
            max-width: var(--content-width); margin: 0 auto; padding: 1rem 2.5rem; 
            background: white; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            box-sizing: border-box;
        }}
        article h1 {{ 
            margin-top: 1rem;
            margin-bottom: 1rem;
            font-weight: normal;
            text-align: center;
        }}
    </style>
</head>
<body>
    <nav>
        <div class="nav-container">
            <div class="nav-title">Jinbao</div>

            <input type="checkbox" id="menu-toggle">
            <label for="menu-toggle" class="hamburger">
                <span></span><span></span><span></span>
            </label>

            <ul class="nav-links">
                {nav_items}
            </ul>
        </div>
    </nav>

    <article class="line-numbers">
        {content}
    </article>

    <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-core.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
</body>
</html>
"""

def generate_nav_items(src_dir, current_depth):
    """
    生成动态导航 HTML 字符串。
    current_depth 用于处理相对路径，确保在子目录中也能正确跳转。
    """
    prefix = "/" * current_depth
    items = [f'<li><a href="{prefix}">首页</a></li>']
    # 获取 src_dir 下的所有一级目录
    dirs = [d for d in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, d)) and d not in [dest_dir, '.github', '.git']]
    dirs.sort()  # 排序确保顺序稳定

    for d in dirs:
        # 假设每个目录下都有一个 index.html 或者跳转到该目录
        items.append(f'<li><a href="/{d}">{d}</a></li>')

    items.append(f'<li><a href="{prefix}about">关于</a></li>')
    return "\n".join(items)

def convert_md_to_html_with_nav(src_dir: str, dest_dir: str):
    nav_items = generate_nav_items(src_dir, 1)
    print(nav_items)
    for root, dirs, files in os.walk(src_dir):
        if any(exclude in root for exclude in [dest_dir, '.github', '.git']):
            continue
        # 建立目标文件夹结构
        rel_path = os.path.relpath(root, src_dir)
        target_path = os.path.join(dest_dir, rel_path)
        os.makedirs(target_path, exist_ok=True)

        for file in files:
            src_file_path = os.path.join(root, file)
            if file.lower().endswith('.md'):
                output_file_name = os.path.splitext(file)[0] + ".html"
                dest_file_path = os.path.join(target_path, output_file_name)

                with open(src_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 转换 Markdown
                html_body = markdown.markdown(content, extensions=['extra', 'toc', 'tables'])

                # 渲染模板
                final_html = HTML_TEMPLATE.format(title=os.path.splitext(file)[0], content=html_body, nav_items=nav_items)

                with open(dest_file_path, 'w', encoding='utf-8') as f:
                    f.write(final_html)
                print(f"成功: {file} -> HTML")
            else:
                # 复制其他静态资源
                shutil.copy2(src_file_path, os.path.join(target_path, file))


if __name__ == "__main__":
    src_dir = "."
    dest_dir = "output"
    convert_md_to_html_with_nav(src_dir, dest_dir)
