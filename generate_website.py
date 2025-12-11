#!/usr/bin/env python3
"""
Generate GitHub Pages website from markdown records
Converts all markdown files to HTML with Bootstrap styling and navigation
"""

import re
from pathlib import Path
from datetime import datetime


def create_nav_html():
    """Create single-row navigation header with dropdowns"""
    return '''
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/tvhs/index.html">
                <img src="/tvhs/images/hawk-logo.svg" alt="Tanque Verde Hawks" class="navbar-logo">
                Tanque Verde Swimming
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <!-- Overall Records Dropdown -->
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                            Overall Records
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/tvhs/records/girls-overall.html">Girls</a></li>
                            <li><a class="dropdown-item" href="/tvhs/records/boys-overall.html">Boys</a></li>
                        </ul>
                    </li>
                    <!-- Relay Records Dropdown -->
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                            Relay Records
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/tvhs/records/girls-relays.html">Girls</a></li>
                            <li><a class="dropdown-item" href="/tvhs/records/boys-relays.html">Boys</a></li>
                        </ul>
                    </li>
                    <!-- Top 10 Overall Dropdown -->
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                            Top 10 Overall
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/tvhs/top10/girls-alltime.html">Girls All-Time</a></li>
                            <li><a class="dropdown-item" href="/tvhs/top10/boys-alltime.html">Boys All-Time</a></li>
                        </ul>
                    </li>
                    <!-- Top 10 By Season Dropdown -->
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                            Top 10 By Season
                        </a>
                        <ul class="dropdown-menu dropdown-menu-scroll">
                            <li class="dropdown-header">Girls</li>
                            <li><a class="dropdown-item" href="/tvhs/top10/girls-2025-26.html">2025-26</a></li>
                            <li><a class="dropdown-item" href="/tvhs/top10/girls-2024-25.html">2024-25</a></li>
                            <li><a class="dropdown-item" href="/tvhs/top10/girls-2023-24.html">2023-24</a></li>
                            <li><a class="dropdown-item" href="/tvhs/top10/girls-2022-23.html">2022-23</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li class="dropdown-header">Boys</li>
                            <li><a class="dropdown-item" href="/tvhs/top10/boys-2025-26.html">2025-26</a></li>
                            <li><a class="dropdown-item" href="/tvhs/top10/boys-2024-25.html">2024-25</a></li>
                            <li><a class="dropdown-item" href="/tvhs/top10/boys-2023-24.html">2023-24</a></li>
                            <li><a class="dropdown-item" href="/tvhs/top10/boys-2022-23.html">2022-23</a></li>
                        </ul>
                    </li>
                    <!-- Annual Summaries Dropdown -->
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                            Annual Summaries
                        </a>
                        <ul class="dropdown-menu dropdown-menu-scroll dropdown-menu-end">
                            <li><a class="dropdown-item" href="/tvhs/annual/2025-26.html">2025-26</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2024-25.html">2024-25</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2023-24.html">2023-24</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2022-23.html">2022-23</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2021-22.html">2021-22</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2020-21.html">2020-21</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2019-20.html">2019-20</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2018-19.html">2018-19</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2017-18.html">2017-18</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2016-17.html">2016-17</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2015-16.html">2015-16</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2014-15.html">2014-15</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2013-14.html">2013-14</a></li>
                            <li><a class="dropdown-item" href="/tvhs/annual/2012-13.html">2012-13</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    '''


def create_html_page(title, content, page_type="default"):
    """Create a complete HTML page with Bootstrap and navigation"""
    nav_html = create_nav_html()
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Tanque Verde Swimming</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="/tvhs/css/style.css">
    
    <!-- Favicon -->
    <link rel="icon" type="image/svg+xml" href="/tvhs/images/favicon.svg">
    <link rel="apple-touch-icon" href="/tvhs/images/hawk-logo.svg">
</head>
<body>
    {nav_html}
    
    <!-- Page Header -->
    <div class="page-header">
        <div class="container">
            <h1>{title}</h1>
            <div class="subtitle">Tanque Verde High School Swimming & Diving</div>
        </div>
    </div>
    
    <!-- Main Content -->
    <div class="container my-4">
        {content}
    </div>
    
    <!-- Footer -->
    <footer class="mt-5">
        <div class="container text-center">
            <p class="mb-2">&copy; {datetime.now().year} Tanque Verde High School Swimming</p>
            <p class="mb-0">
                <small>
                    Generated on {datetime.now().strftime('%B %d, %Y')} | 
                    <a href="https://github.com/aaryno/tvhs">View on GitHub</a>
                </small>
            </p>
        </div>
    </footer>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>'''


def markdown_to_html_table(md_text):
    """Convert markdown tables to Bootstrap-styled HTML tables"""
    # Find all markdown tables
    table_pattern = r'\|(.+?)\|\n\|[-: |]+\|\n((?:\|.+?\|\n)+)'
    
    def replace_table(match):
        header_row = match.group(1)
        data_rows = match.group(2)
        
        # Parse header
        headers = [h.strip() for h in header_row.split('|') if h.strip()]
        
        # Parse data rows
        rows = []
        for row in data_rows.strip().split('\n'):
            if row.strip():
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if cells:
                    rows.append(cells)
        
        # Build HTML table
        html = '<div class="table-responsive record-table">\n'
        html += '<table class="table table-striped table-hover">\n'
        html += '<thead>\n<tr>\n'
        for header in headers:
            html += f'<th>{header}</th>\n'
        html += '</tr>\n</thead>\n<tbody>\n'
        
        for row in rows:
            html += '<tr>\n'
            for i, cell in enumerate(row):
                # Check if this is a record holder (bold text)
                if '**' in cell:
                    cell = cell.replace('**', '')
                    html += f'<td class="record-holder">{cell}</td>\n'
                else:
                    html += f'<td>{cell}</td>\n'
            html += '</tr>\n'
        
        html += '</tbody>\n</table>\n</div>\n'
        return html
    
    # Replace all tables
    result = re.sub(table_pattern, replace_table, md_text, flags=re.MULTILINE)
    return result


def convert_markdown_file(md_file, output_file, title=None):
    """Convert a markdown file to HTML"""
    print(f"Converting {md_file.name} → {output_file.name}")
    
    # Read markdown
    with open(md_file, 'r') as f:
        md_content = f.read()
    
    # Extract title from first heading if not provided
    if not title:
        title_match = re.search(r'^#\s+(.+)$', md_content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
        else:
            title = md_file.stem.replace('-', ' ').title()
    
    # Convert tables first
    html_content = markdown_to_html_table(md_content)
    
    # Convert remaining markdown elements
    # Headings
    html_content = re.sub(r'^### (.+)$', r'<h3 class="event-heading">\1</h3>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
    
    # Bold text
    html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
    
    # Italic text
    html_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_content)
    
    # Horizontal rules
    html_content = re.sub(r'^---$', '<hr>', html_content, flags=re.MULTILINE)
    
    # Paragraphs (lines separated by blank lines)
    paragraphs = html_content.split('\n\n')
    formatted_paragraphs = []
    for para in paragraphs:
        para = para.strip()
        if para and not para.startswith('<'):
            para = f'<p>{para}</p>'
        formatted_paragraphs.append(para)
    html_content = '\n'.join(formatted_paragraphs)
    
    # Wrap in sections for better styling
    html_content = f'<div class="content">\n{html_content}\n</div>'
    
    # Create full HTML page
    full_html = create_html_page(title, html_content)
    
    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(full_html)


def main():
    print("=" * 80)
    print("GENERATING TANQUE VERDE SWIM WEBSITE")
    print("=" * 80)
    print()
    
    records_dir = Path('records')
    docs_dir = Path('docs')
    
    # Convert team records
    print("📊 Converting Team Records...")
    for record_file in records_dir.glob('records-*.md'):
        if 'boys' in record_file.name:
            output = docs_dir / 'records' / 'boys-overall.html'
            title = "Boys Team Records"
        elif 'girls' in record_file.name:
            output = docs_dir / 'records' / 'girls-overall.html'
            title = "Girls Team Records"
        else:
            continue
        convert_markdown_file(record_file, output, title)
    
    # Convert relay records
    print("\n🏃 Converting Relay Records...")
    for relay_file in records_dir.glob('relay-records-*.md'):
        if 'boys' in relay_file.name:
            output = docs_dir / 'records' / 'boys-relays.html'
            title = "Boys Relay Records"
        elif 'girls' in relay_file.name:
            output = docs_dir / 'records' / 'girls-relays.html'
            title = "Girls Relay Records"
        else:
            continue
        convert_markdown_file(relay_file, output, title)
    
    # Convert top 10 lists
    print("\n🔟 Converting Top 10 Lists...")
    for top10_file in records_dir.glob('top10-*.md'):
        gender = 'boys' if 'boys' in top10_file.name else 'girls'
        season = top10_file.stem.replace(f'top10-{gender}-', '')
        
        if season == 'alltime':
            title = f"{gender.title()} All-Time Top 10"
            output_name = f"{gender}-alltime.html"
        else:
            title = f"{gender.title()} Top 10 - {season}"
            output_name = f"{gender}-{season}.html"
        
        output = docs_dir / 'top10' / output_name
        convert_markdown_file(top10_file, output, title)
    
    # Convert annual summaries
    print("\n📅 Converting Annual Summaries...")
    for annual_file in records_dir.glob('annual-summary-*.md'):
        season = annual_file.stem.replace('annual-summary-', '')
        title = f"{season} Season Summary"
        output = docs_dir / 'annual' / f"{season}.html"
        convert_markdown_file(annual_file, output, title)
    
    print("\n" + "=" * 80)
    print("✅ Website generation complete!")
    print(f"📁 Output directory: {docs_dir.absolute()}")
    print("=" * 80)


if __name__ == '__main__':
    main()

