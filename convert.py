#!/usr/bin/env python3
"""
Markdown 转 HTML 转换器
将 docs 目录下的所有 md 文件转换为 HTML，支持 MathJax 和代码高亮
"""

import os
import re
import shutil
import yaml
import subprocess
import argparse
import tempfile
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

# 配置
DOCS_DIR = "."
OUTPUT_DIR = "output"
TEMPLATE_DIR = Path(__file__).parent.resolve()

# 默认配置
DEFAULT_CONFIG = {
    "site": {
        "title": "Alex's Blog",
        "subtitle": "技术与思考",
        "author": "Alex",
        "description": "个人博客"
    },
    "nav_menu": [
        {"name": "首页", "href": "index.html", "is_home": True},
        {"name": "推荐算法", "href": "rec-sys"},
        {"name": "机器学习", "href": "ml"},
        {"name": "深度学习", "href": "dl"},
        {"name": "Agent", "href": "agent"},
        {"name": "GitHub", "href": "https://github.com", "external": True},
        {"name": "关于", "href": "#about"}
    ],
    "hero": {
        "title": "你好，我是 {author}",
        "subtitle": "推荐算法 | 机器学习 | 深度学习 | Agent",
        "bio": "专注于推荐系统算法研究与实践。\n热爱机器学习与深度学习。\n在这里记录学习笔记与技术思考。"
    },
    "social": [
        {"name": "GitHub", "url": "https://github.com", "icon": "github"},
        {"name": "Twitter", "url": "https://twitter.com", "icon": "twitter"},
        {"name": "Email", "url": "mailto:hello@example.com", "icon": "email"}
    ],
    "footer": {
        "copyright": "© 2026 Alex's Blog. All rights reserved.",
        "built_with": "Built with love using HTML, CSS & JavaScript"
    }
}

# Category 映射（文件夹名 -> 显示名称）- 从 nav_menu 中自动提取
CATEGORY_NAMES = {}

def load_config():
    """加载配置文件"""
    config = DEFAULT_CONFIG.copy()

    config_path = Path(DOCS_DIR) / "_config.yml"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    # 深度合并配置
                    for key, value in user_config.items():
                        if isinstance(value, dict) and key in config:
                            config[key].update(value)
                        else:
                            config[key] = value
        except Exception as e:
            print(f"[警告] 加载配置文件失败: {e}")

    # 从 nav_menu 中提取 Category 映射
    global CATEGORY_NAMES
    for item in config.get('nav_menu', []):
        href = item.get('href', '')
        name = item.get('name', '')
        # 排除首页、外部链接和锚点
        if href and not item.get('external') and not href.startswith('#') and not href.startswith('http'):
            if not item.get('is_home'):
                CATEGORY_NAMES[href] = name

    return config


# ============================================================
# HTML 模板模块 - 按生成顺序: 文章 -> Category Index -> 首页
# ============================================================

# ---------- 公共模块 ----------

# 基础 HTML 头部（所有页面共用）
HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Source+Sans+3:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{css_path}styles.css">
    {extra_head}
</head>
<body>"""

# 导航栏
HTML_NAV = """    <nav class="navbar" id="navbar">
        <div class="nav-container">
            <a href="{home_link}" class="nav-logo">
                <span class="logo-icon">◈</span>
                <span class="logo-text">{site_title}</span>
            </a>
            <button class="nav-toggle" id="navToggle" aria-label="Toggle navigation">
                <span class="bar"></span>
                <span class="bar"></span>
                <span class="bar"></span>
            </button>
            <ul class="nav-menu" id="navMenu">
                {nav_items}
            </ul>
        </div>
    </nav>"""

# 页脚
HTML_FOOTER = """    <footer class="footer">
        <div class="container">
            <p class="footer-text">{author}</p>
            <p class="footer-text">{copyright}</p>
            <p class="footer-text">{built_with}</p>
        </div>
    </footer>"""

# 基础 JS 引用
HTML_BASE_SCRIPTS = """    <script src="{script_path}script.js"></script>
</body>
</html>"""


# ---------- 文章页面模块 ----------

# 文章页面专用头部（包含 highlight.js 和 MathJax）
ARTICLE_EXTRA_HEAD = """    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
    <script>
        window.MathJax = {{
            tex: {{
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            }},
            svg: {{ fontCache: 'global' }},
            startup: {{
                ready: () => {{
                    MathJax.startup.defaultReady();
                }}
            }}
        }};
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>"""

# 文章内容区域
ARTICLE_CONTENT = """    <main class="article-container">
        <article class="article">
            <header class="article-header">
                <div class="article-meta">
                    <time class="article-date">{date}</time>
                    <span class="article-tag">{category}</span>
                </div>
                <h1 class="article-title">{title}</h1>
            </header>

            <div class="article-content">
                {content}
            </div>

            <footer class="article-footer">
                <nav class="article-nav">
                    <a href="{prev_link}" class="nav-prev">← 上一篇</a>
                    <a href="{next_link}" class="nav-next">下一篇 →</a>
                </nav>
            </footer>
        </article>
    </main>"""


# ---------- Category Index 模块 ----------

# Category 头部区域
CATEGORY_HEADER = """    <section class="category-header">
        <div class="container">
            <h1 class="category-title">{category_name}</h1>
            <p class="category-subtitle">{article_count} 篇文章</p>
        </div>
    </section>"""

# Category 文章列表区域
CATEGORY_CONTENT = """    <section class="blog-section">
        <div class="container">
            <div class="blog-grid">
                {articles}
            </div>
        </div>
    </section>"""

# 文章卡片模板
ARTICLE_CARD = """<article class="blog-card">
    <div class="card-header">
        <time class="card-date">{date}</time>
        <div class="card-tags">
            <span class="card-tag">{tag}</span>
        </div>
    </div>
    <h3 class="card-title">
        <a href="{link}">{title}</a>
    </h3>
    <p class="card-excerpt">
        {excerpt}
    </p>
    <a href="{link}" class="card-link">阅读全文 →</a>
</article>"""


# ---------- 首页模块 ----------

# Hero 区域
HERO_SECTION = """    <section class="hero" id="about">
        <div class="hero-bg"></div>
        <div class="hero-content">
            <h1 class="hero-title">{hero_title}</h1>
            <p class="hero-subtitle">{hero_subtitle}</p>
            <p class="hero-bio">
                {hero_bio}
            </p>

            <div class="category-grid">
                {category_cards}
            </div>

            <div class="hero-social">
                {social_icons}
            </div>
        </div>
    </section>"""


# ============================================================
# 模板组装函数 - 按生成顺序
# ============================================================

def build_nav_html(config, active_href='', relative_path=''):
    """构建导航栏 HTML"""
    nav_menu = config.get('nav_menu', [])
    site_title = config.get('site', {}).get('title', "Alex's Blog")

    # 计算相对路径
    if relative_path:
        home_link = f"{relative_path}index.html"
    else:
        home_link = "index.html"

    nav_items = ""
    for item in nav_menu:
        href = item.get('href', '#')
        name = item.get('name', '')
        is_external = item.get('external', False)

        # 保存原始 href 用于匹配激活状态
        original_href = href

        # 处理链接前缀
        if not is_external and not href.startswith('#') and not href.startswith('http'):
            if relative_path:
                href = f"{relative_path}{href}"

        # 处理激活状态（使用原始 href 匹配，不包含相对路径前缀）
        is_active = 'active' if (active_href and original_href == active_href) else ''

        # 外部链接处理
        target = 'target="_blank"' if is_external or href.startswith('http') else ''

        nav_items += f'<li><a href="{href}" class="nav-link {is_active}" {target}>{name}</a></li>\n                '

    return HTML_NAV.format(
        home_link=home_link,
        site_title=site_title,
        nav_items=nav_items
    )


def build_footer_html(config, author=''):
    """构建页脚 HTML"""
    footer = config.get('footer', {})
    # 如果没有传入 author，从配置中获取
    if not author:
        author = config.get('site', {}).get('author', '')
    return HTML_FOOTER.format(
        author=author,
        copyright=footer.get('copyright', ''),
        built_with=footer.get('built_with', '')
    )


def build_article_html(config, title, date, category, content, prev_link, next_link, relative_path=''):
    """组装文章页面 HTML"""
    site = config.get('site', {})

    # 计算资源路径
    css_path = '/'
    script_path = '/'

    # 构建各部分
    head_title = f"{title} | {site.get('title', 'Alex\'s Blog')}"

    html = HTML_HEAD.format(
        title=head_title,
        css_path=css_path,
        extra_head=ARTICLE_EXTRA_HEAD
    )

    html += build_nav_html(config, active_href='', relative_path=relative_path)
    html += ARTICLE_CONTENT.format(
        date=date,
        category=category,
        title=title,
        content=content,
        prev_link=prev_link,
        next_link=next_link
    )
    html += build_footer_html(config)
    html += HTML_BASE_SCRIPTS.format(script_path=script_path)

    return html


def build_category_index_html(config, category_name, display_name, articles, relative_path=''):
    """组装 Category 索引页 HTML"""
    site = config.get('site', {})

    # 计算资源路径（Category 页在子目录，默认使用 ../）
    css_path = relative_path if relative_path else '../'
    script_path = relative_path if relative_path else '../'

    # 构建各部分
    head_title = f"{display_name} | {site.get('title', '')}"

    html = HTML_HEAD.format(
        title=head_title,
        css_path=css_path,
        extra_head=''
    )

    # 导航栏（Category 页需要激活对应 category，并使用 ../ 相对路径）
    nav_relative_path = '../' if not relative_path else relative_path
    html += build_nav_html(config, active_href=category_name, relative_path=nav_relative_path)

    # Category 头部
    html += CATEGORY_HEADER.format(
        category_name=display_name,
        article_count=len(articles)
    )

    # 文章列表
    cards_html = ""
    for article in articles:
        # 去掉 category_name/ 前缀和 .html 后缀
        filename = article['filename'].replace(f'{category_name}/', '').replace('.html', '')
        cards_html += ARTICLE_CARD.format(
            date=article['date'],
            tag=display_name,
            title=article['title'],
            excerpt=article['excerpt'],
            link=filename
        ) + "\n"

    html += CATEGORY_CONTENT.format(articles=cards_html)
    html += build_footer_html(config)
    html += HTML_BASE_SCRIPTS.format(script_path=script_path)

    return html


def build_index_html(config, categories_info):
    """组装首页 HTML"""
    site = config.get('site', {})
    nav_menu = config.get('nav_menu', [])
    hero = config.get('hero', {})
    social = config.get('social', [])
    footer = config.get('footer', {})

    # 构建各部分
    head_title = f"{site.get('title', 'Alex\'s Blog')} | {site.get('subtitle', '技术与思考')}"

    html = HTML_HEAD.format(
        title=head_title,
        css_path='/',
        extra_head=''
    )

    # 导航栏（首页激活）
    html += build_nav_html(config, active_href='index.html', relative_path='')

    # 生成导航菜单项（用于首页）
    nav_html = ""
    for item in nav_menu:
        href = item.get('href', '#')
        name = item.get('name', '')
        is_active = 'active' if item.get('is_home') else ''
        external = 'target="_blank"' if item.get('external') else ''
        nav_html += f'<li><a href="{href}" class="nav-link {is_active}" {external}>{name}</a></li>\n                '

    # 生成分类卡片
    category_cards = ""
    for cat in categories_info:
        category_cards += f"""                <a href="{cat['name']}" class="category-card">
                    <span class="category-card-name">{cat['display_name']}</span>
                    <span class="category-card-count">{cat['count']} 篇</span>
                </a>
"""

    # 生成社交链接
    social_icons = {
        'github': '<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>',
        'twitter': '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>',
        'email': '<path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>'
    }

    social_html = ""
    for item in social:
        url = item.get('url', '#')
        name = item.get('name', '')
        icon = item.get('icon', 'github')
        icon_path = social_icons.get(icon, social_icons['github'])
        target = 'target="_blank"' if item.get('external') or url.startswith('http') else ''
        social_html += f"""                <a href="{url}" class="social-btn" aria-label="{name}" {target}>
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                        {icon_path}
                    </svg>
                </a>
"""

    # Hero 标题替换 author
    hero_title = hero.get('title', '').format(author=site.get('author', 'Alex'))

    html += HERO_SECTION.format(
        hero_title=hero_title,
        hero_subtitle=hero.get('subtitle', ''),
        hero_bio=hero.get('bio', '').replace(chr(10), '<br>'),
        category_cards=category_cards,
        social_icons=social_html
    )

    html += build_footer_html(config)
    html += HTML_BASE_SCRIPTS.format(script_path='/')

    return html


# ============================================================
# Markdown 转换函数
# ============================================================

def convert_markdown_to_html(markdown_text):
    """将 Markdown 转换为 HTML"""
    html = markdown_text

    # 转义 HTML 特殊字符（但保留已存在的 HTML 标签）
    # 先处理代码块外部的内容
    html = re.sub(r'<(pre|code|table|tr|td|th|blockquote)(?:\s|>)', r'<\1>', html)

    # 先处理 MathJax 公式，保护它们不被其他规则影响
    # 块级公式 $$...$$ (必须先处理，因为行内公式的正则可能会误匹配)
    math_blocks = {}
    block_counter = [0]

    def protect_math_block(match):
        block_counter[0] += 1
        placeholder = f"__MATH_BLOCK_{block_counter[0]}__"
        math_blocks[placeholder] = match.group(0)
        return placeholder

    # 先保护所有块级公式
    html = re.sub(r'\$\$.+?\$\$', protect_math_block, html, flags=re.DOTALL)

    # 行内公式 $...$ (只在单行内匹配，不跨越 $$)
    html = re.sub(
        r'\$([^\$\n]+?)\$',
        r'<span class="math-inline">$\1$</span>',
        html
    )

    # 恢复块级公式
    for placeholder, original in math_blocks.items():
        html = html.replace(placeholder, f'<p class="math-block">{original}</p>')

    # 代码块 ```...```
    html = re.sub(
        r'```(\w*)\n(.*?)```',
        r'<div class="code-block"><div class="code-header"><span class="code-lang">\1</span><button class="code-copy" onclick="copyCode(this)" aria-label="Copy code"><svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg></button></div><pre><code class="language-\1">\2</code></pre></div>',
        html,
        flags=re.DOTALL
    )

    # 行内代码 `...`
    html = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', html)

    # 标题
    html = re.sub(r'^###### (.+)$', r'<h6 id="\1">\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^##### (.+)$', r'<h5 id="\1">\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', r'<h4 id="\1">\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3 id="\1">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 id="\1">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1 id="\1">\1</h1>', html, flags=re.MULTILINE)

    # 粗体 **...** 或 __...__ (排除 MathJax 公式内的)
    # 先将公式部分替换为占位符
    math_placeholders = {}
    math_counter = [0]

    def replace_math(match):
        math_counter[0] += 1
        placeholder = f"__MATH_PLACEHOLDER_{math_counter[0]}__"
        math_placeholders[placeholder] = match.group(0)
        return placeholder

    # 保护 MathJax 公式（更精确的匹配）
    # 注意：需要匹配完整的标签内容
    html = re.sub(r'<span class="math-inline">[^$]*\$</span>', replace_math, html)
    html = re.sub(r'<p class="math-block">.*?</p>', replace_math, html, flags=re.DOTALL)

    # 粗体 **...** 或 __...__ (只匹配独立的，不在公式内)
    # 匹配整个 **...** 块
    html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
    # 匹配整个 __...__ 块，但排除下划线后跟字母数字的情况
    html = re.sub(r'__(?![\s\S]*?[a-zA-Z0-9]_|[\s\S]*?\|)([^_]+)__', r'<strong>\1</strong>', html)

    # 斜体 *...* (只匹配独立的)
    html = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', html)
    # 斜体 _..._ (不处理，保留给公式下标使用)

    # 恢复 MathJax 公式
    for placeholder, original in math_placeholders.items():
        html = html.replace(placeholder, original)

    # 删除线 ~~...~~
    html = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', html)

    # 表格处理
    def convert_table(match):
        lines = match.group(0).strip().split('\n')
        if len(lines) < 2:
            return match.group(0)

        # 解析表头
        header_cells = [cell.strip() for cell in lines[0].strip('|').split('|')]

        # 解析对齐方式
        align_cells = []
        if len(lines) > 1:
            align_line = lines[1].strip('|').split('|')
            for cell in align_line:
                cell = cell.strip()
                if cell.startswith(':') and cell.endswith(':'):
                    align_cells.append('center')
                elif cell.endswith(':'):
                    align_cells.append('right')
                elif cell.startswith(':'):
                    align_cells.append('left')
                else:
                    align_cells.append('')

        # 如果没有对齐行，使用默认对齐
        while len(align_cells) < len(header_cells):
            align_cells.append('')

        # 生成表头 HTML
        thead = '<thead><tr>'
        for i, cell in enumerate(header_cells):
            align = align_cells[i] if i < len(align_cells) else ''
            style = f' style="text-align:{align}"' if align else ''
            thead += f'<th{style}>{cell}</th>'
        thead += '</tr></thead>'

        # 生成表格 body
        tbody = '<tbody>'
        for line in lines[2:]:
            if line.strip().startswith('|'):
                cells = [c.strip() for c in line.strip('|').split('|')]
                tbody += '<tr>'
                for i, cell in enumerate(cells):
                    align = align_cells[i] if i < len(align_cells) else ''
                    style = f' style="text-align:{align}"' if align else ''
                    tbody += f'<td{style}>{cell}</td>'
                tbody += '</tr>'
        tbody += '</tbody>'

        return f'<table class="table">{thead}{tbody}</table>'

    # 匹配整个表格（至少2行，每行以 | 开头或结尾）
    html = re.sub(r'^\|.+\|(?:\n\|.+\|)+', convert_table, html, flags=re.MULTILINE)

    # 链接 [text](url)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # 图片 ![alt](url)
    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" class="article-image">', html)

    # 无序列表 - 或 *
    html = re.sub(r'^[*-] (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html)

    # 有序列表
    html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # 引用 > ...
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    html = re.sub(r'(<blockquote>.*</blockquote>\n?)+', lambda m: '<blockquote>' + ''.join(re.findall(r'<blockquote>(.*?)</blockquote>', m.group(0))) + '</blockquote>', html)

    # 水平线 --- 或 *** 或 ___
    html = re.sub(r'^[-*_]{3,}$', r'<hr>', html, flags=re.MULTILINE)

    # 段落（用空行分隔）
    html = re.sub(r'\n\n+', '\n', html)
    html = re.sub(r'^(?!<[hupolbtd]|<ul|<ol|<li|<blockquote|<hr|<div|<img|<code)(.+)$', r'<p>\1</p>', html, flags=re.MULTILINE)

    # 清理空段落
    html = re.sub(r'<p>\s*</p>', '', html)
    html = re.sub(r'<p>\s*<(h[1-6]|ul|ol|li|blockquote|hr|div|code|pre|img)</', r'<\1', html)
    html = re.sub(r'</(h[1-6]|ul|ol|li|blockquote|hr|div|pre)>\s*</p>', r'</\1>', html)

    return html


def extract_title(markdown_text):
    """从 Markdown 中提取标题"""
    match = re.search(r'^# (.+)$', markdown_text, re.MULTILINE)
    return match.group(1) if match else "无标题"


def extract_excerpt(markdown_text, max_length=100):
    """从 Markdown 中提取摘要"""
    # 移除标题
    text = re.sub(r'^# .+$', '', markdown_text, flags=re.MULTILINE)
    # 移除代码块
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # 移除行内代码
    text = re.sub(r'`[^`]+`', '', text)
    # 移除图片
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # 移除链接
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # 移除粗体斜体标记
    text = re.sub(r'[*_]+', '', text)
    # 移除特殊字符
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def get_date_from_filename(filename):
    """从文件名提取日期，格式: YYYY-MM-DD-title.md"""
    match = re.match(r'^(\d{4}-\d{2}-\d{2})-.+\.md$', filename)
    if match:
        return match.group(1)
    return datetime.now().strftime("%Y-%m-%d")


# ============================================================
# 主处理函数 - 按生成顺序: 文章 -> Category Index -> 首页
# ============================================================

def process_category(category_dir, category_name, config, output_dir):
    """处理单个 category 目录 - 生成文章"""
    articles = []

    # 创建输出子目录（保持目录结构）
    output_subdir = Path(output_dir) / category_dir.name
    output_subdir.mkdir(parents=True, exist_ok=True)

    # 获取目录下的所有文件
    all_files = list(category_dir.iterdir())

    # 处理 md 文件
    md_files = sorted([f for f in all_files if f.suffix == '.md'], key=lambda x: x.name, reverse=True)

    # 复制非 md 文件（如图片）
    for file in all_files:
        if file.is_file() and file.suffix != '.md':
            dest = output_subdir / file.name
            shutil.copy2(file, dest)
            print(f"  + {file.name} (copied)")

    for md_file in md_files:
        # 读取 md 文件
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取标题
        title = extract_title(content)

        # 提取日期
        date = get_date_from_filename(md_file.name)

        # 生成 HTML 文件名（放在子目录中）
        html_filename = md_file.stem + ".html"
        output_path = output_subdir / html_filename

        # 转换内容（跳过第一个标题，因为它会作为页面标题显示）
        content_without_title = re.sub(r'^# .+$', '', content, count=1, flags=re.MULTILINE)
        html_content = convert_markdown_to_html(content_without_title)

        # 查找上一讲和下一篇文章（不带 .html 后缀，因为在同一目录）
        idx = md_files.index(md_file)
        prev_link = ""
        next_link = ""
        if idx < len(md_files) - 1:
            next_link = md_files[idx + 1].stem
        if idx > 0:
            prev_link = md_files[idx - 1].stem
        if not prev_link:
            prev_link = "#"
        if not next_link:
            next_link = "#"

        # ========== 步骤 1: 生成文章页面 ==========
        # 使用模块化模板生成文章
        relative_path = f"{category_dir.name}/"
        html = build_article_html(
            config=config,
            title=title,
            date=date,
            category=category_name,
            content=html_content,
            prev_link=prev_link,
            next_link=next_link,
            relative_path=relative_path
        )

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"  ✓ {category_dir.name}/{html_filename}")

        # 提取摘要用于列表页
        excerpt = extract_excerpt(content)

        articles.append({
            'title': title,
            'date': date,
            'filename': f"{category_dir.name}/{html_filename}",
            'excerpt': excerpt,
            'tag': category_name
        })

    return articles


def generate_category_index(category_name, display_name, articles, config, output_dir):
    """生成 category 的 index.html - 步骤 2"""
    # 按日期排序
    articles = sorted(articles, key=lambda x: x['date'], reverse=True)

    # ========== 步骤 2: 生成 Category Index ==========
    # 使用模块化模板生成分类索引页
    html = build_category_index_html(
        config=config,
        category_name=category_name,
        display_name=display_name,
        articles=articles,
        relative_path=''
    )

    # 写入文件到子目录下的 index.html
    output_subdir = Path(output_dir) / category_name
    output_path = output_subdir / "index.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  - {category_name}/index.html (索引页)")


def generate_index_page(config, categories_info, output_dir):
    """生成首页 index.html - 步骤 3"""
    # ========== 步骤 3: 生成首页 ==========
    # 使用模块化模板生成首页
    html = build_index_html(config, categories_info)

    # 写入文件
    output_path = Path(output_dir) / "index.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  - index.html (首页)")


def main():
    # 设置输出编码为 UTF-8
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    # 加载配置
    config = load_config()

    print("=" * 50)
    print("Markdown to HTML 转换器")
    print("=" * 50)

    # 检查 docs 目录
    docs_path = Path(DOCS_DIR)
    if not docs_path.exists():
        print(f"\n[错误] {DOCS_DIR} 目录不存在!")
        print(f"请创建 {DOCS_DIR} 目录并放入 Markdown 文件。")
        print("\n目录结构示例:")
        print(f"""
{DOCS_DIR}/
├── rec-sys/
│   ├── 2026-03-15-collaborative-filtering.md
│   └── 2026-03-08-matrix-factorization.md
├── ml/
│   ├── 2026-03-10-linear-regression.md
│   └── 2026-03-05-kmeans.md
├── dl/
│   ├── 2026-03-01-backpropagation.md
│   └── 2026-02-25-transformer.md
└── agent/
    ├── 2026-02-20-llm-agent.md
    └── 2026-02-15-rag-agent.md
""")
        return

    print(f"\n输入目录: {DOCS_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print()

    # 创建输出目录
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    # 复制静态文件到输出目录
    static_files = ['styles.css', 'script.js']
    for static_file in static_files:
        src = TEMPLATE_DIR / static_file
        if src.exists():
            dest = output_path / static_file
            shutil.copy2(src, dest)
            print(f"[复制] {static_file}")
        else:
            print(f"❌ [未找到源文件] {src}")

    total_articles = 0
    categories_info = []  # 收集分类信息用于生成首页

    # ========== 步骤 1 & 2: 处理所有分类 ==========
    # 遍历所有 category 目录
    for category_dir in sorted(docs_path.iterdir()):
        if not category_dir.is_dir():
            continue

        category_name = category_dir.name
        display_name = CATEGORY_NAMES.get(category_name, category_name)

        print(f"[处理] 分类: {display_name}")

        # 处理该分类下的所有 md 文件 (步骤1: 生成文章)
        articles = process_category(category_dir, category_name, config, OUTPUT_DIR)

        if articles:
            # 生成索引页 (步骤2: 生成 Category Index)
            generate_category_index(category_name, display_name, articles, config, OUTPUT_DIR)
            total_articles += len(articles)
            # 收集分类信息
            categories_info.append({
                'name': category_name,
                'display_name': display_name,
                'count': len(articles)
            })
        else:
            print(f"  [警告] 没有找到 Markdown 文件")

    # ========== 步骤 3: 生成首页 index.html ==========
    generate_index_page(config, categories_info, OUTPUT_DIR)

    print()
    print("=" * 50)
    print(f"[完成] 转换完成! 共处理 {total_articles} 篇文章")
    print("=" * 50)


if __name__ == "__main__":
    main()
