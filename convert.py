import os
import markdown

# 配置输入和输出目录
INPUT_DIR = '.'  # 文档仓库根目录
OUTPUT_DIR = 'output'  # 生成的 HTML 存放位置

# 确保输出目录存在
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def convert_md_to_html():
    for root, dirs, files in os.walk(INPUT_DIR):
        # 排除 output 目录和 .github 目录
        if OUTPUT_DIR in root or '.github' in root:
            continue
            
        for file in files:
            if file.endswith('.md'):
                # 构建完整路径
                md_path = os.path.join(root, file)
                
                # 读取内容
                with open(md_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # 转换 HTML (启用表格和代码高亮支持)
                html_content = markdown.markdown(text, extensions=['fenced_code', 'tables'])
                
                # 包装基础 HTML 结构
                full_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
                    <style>
                        .markdown-body {{ box-sizing: border-box; min-width: 200px; max-width: 980px; margin: 0 auto; padding: 45px; }}
                        @media (max-width: 767px) {{ .markdown-body {{ padding: 15px; }} }}
                    </style>
                </head>
                <body class="markdown-body">
                    {html_content}
                </body>
                </html>
                """
                
                # 确定输出文件名 (例如 index.md -> index.html)
                rel_path = os.path.relpath(root, INPUT_DIR)
                dest_dir = os.path.join(OUTPUT_DIR, rel_path)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                
                dest_file = os.path.join(dest_dir, file.replace('.md', '.html'))
                
                with open(dest_file, 'w', encoding='utf-8') as f:
                    f.write(full_html)
                print(f"Converted: {md_path} -> {dest_file}")

if __name__ == "__main__":
    convert_md_to_html()
