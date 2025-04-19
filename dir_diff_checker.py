import os
import filecmp
import difflib
import argparse
from pathlib import Path
import html
import sys
import datetime


def get_file_list(dir_path, extensions=None):
    """
    Get list of all files in a directory and its subdirectories.
    If extensions is provided, only include files with those extensions.
    """
    file_list = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            # Check if we should filter by extension
            if extensions and not any(file.endswith(ext) for ext in extensions):
                continue
                
            file_path = os.path.join(root, file)
            # Get relative path to the directory
            rel_path = os.path.relpath(file_path, dir_path)
            file_list.append(rel_path)
    return file_list


def compare_directories(dir1, dir2, extensions=None):
    """Compare two directories and report differences."""
    files1 = set(get_file_list(dir1, extensions))
    files2 = set(get_file_list(dir2, extensions))
    
    added = files2 - files1
    deleted = files1 - files2
    common = files1.intersection(files2)
    
    modified = []
    identical = []
    error_files = []
    
    # Compare common files for modifications
    for file in common:
        file1_path = os.path.join(dir1, file)
        file2_path = os.path.join(dir2, file)
        
        try:
            # Check if both files exist and are accessible before comparing
            if os.path.exists(file1_path) and os.path.exists(file2_path):
                if filecmp.cmp(file1_path, file2_path, shallow=False):
                    identical.append(file)
                else:
                    modified.append(file)
            else:
                # File was listed in directory walk but doesn't exist (symlink or permission issue)
                error_files.append((file, "File exists in listing but not accessible"))
        except Exception as e:
            error_files.append((file, str(e)))
    
    return {
        "added": sorted(list(added)),
        "deleted": sorted(list(deleted)),
        "modified": sorted(modified),
        "identical": sorted(identical),
        "errors": sorted(error_files)
    }


def show_file_diff(file1, file2):
    """Show the differences between two files."""
    try:
        with open(file1, 'r', encoding='utf-8', errors='replace') as f1:
            content1 = f1.readlines()
        
        with open(file2, 'r', encoding='utf-8', errors='replace') as f2:
            content2 = f2.readlines()
        
        diff = difflib.unified_diff(
            content1, content2,
            fromfile=file1,
            tofile=file2,
            lineterm=''
        )
        
        return '\n'.join(diff)
    except Exception as e:
        return f"Error generating diff: {str(e)}"


def generate_html_diff(file1, file2, file_path):
    """Generate HTML diff output for two files."""
    try:
        with open(file1, 'r', encoding='utf-8', errors='replace') as f1:
            content1 = f1.readlines()
        
        with open(file2, 'r', encoding='utf-8', errors='replace') as f2:
            content2 = f2.readlines()
        
        # Generate HTML diff
        diff_html = difflib.HtmlDiff(tabsize=4, wrapcolumn=80).make_file(
            content1, content2,
            fromdesc=f"Original: {file1}",
            todesc=f"Modified: {file2}"
        )
        
        # Enhance the HTML with our own styling (GitHub-like colors)
        diff_html = diff_html.replace(
            '</style>',
            '''
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
                color: #24292e;
                background-color: #fff;
            }
            .diff-header {
                padding: 10px 16px;
                background-color: #f6f8fa;
                border-bottom: 1px solid #d1d5da;
                font-weight: 600;
                position: sticky;
                top: 0;
                z-index: 100;
                box-shadow: 0 1px 2px rgba(0,0,0,0.075);
            }
            .diff-container {
                margin-bottom: 30px;
                border: 1px solid #e1e4e8;
                border-radius: 6px;
                overflow: hidden;
            }
            table.diff {
                width: 100%;
                font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 12px;
                border-collapse: collapse;
                table-layout: fixed;
            }
            .diff tbody {
                font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            }
            .diff_header {
                background-color: #f6f8fa !important;
                padding: 4px 10px !important;
                border-right: 1px solid #e1e4e8;
                color: #586069;
                text-align: right;
                vertical-align: top;
                font-size: 12px;
            }
            td {
                padding: 0 10px;
                vertical-align: top;
                white-space: pre-wrap;
                word-wrap: break-word;
                border-right: 1px solid #eaecef;
                line-height: 20px;
            }
            .diff_add {
                background-color: #e6ffec !important;
                border-color: #34d058;
            }
            .diff_chg {
                background-color: #fff5b1 !important;
                border-color: #f9c513;
            }
            .diff_sub {
                background-color: #ffeef0 !important;
                border-color: #d73a49;
            }
            tr.diff_add {
                background-color: #e6ffec;
            }
            tr.diff_chg {
                background-color: #fff5b1;
            }
            tr.diff_sub {
                background-color: #ffeef0;
            }
            tr:hover {
                background-color: rgba(0,0,0,0.02);
            }
            .diff td:nth-of-type(3), .diff td:nth-of-type(4) {
                width: 45%;
            }
            </style>'''
        )
        
        # Insert a better header
        diff_html = diff_html.replace(
            '<body>', 
            f'''<body>
            <div class="diff-header">
                <h3>Diff of {html.escape(file_path)}</h3>
            </div>
            <div class="diff-container">'''
        )
        
        diff_html = diff_html.replace('</body>', '</div></body>')
        
        return diff_html
    except Exception as e:
        return f"<html><body><h2>Error generating diff</h2><p>{html.escape(str(e))}</p></body></html>"


def get_file_type(file_path):
    """Get file type based on extension for syntax highlighting."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.c', '.h', '.cpp', '.hpp', '.cc']:
        return 'c_cpp'
    elif ext in ['.py']:
        return 'python'
    elif ext in ['.js']:
        return 'javascript'
    elif ext in ['.html']:
        return 'html'
    elif ext in ['.css']:
        return 'css'
    elif ext in ['.java']:
        return 'java'
    else:
        return 'text'


def generate_html_report(results, dir1, dir2, output_path=None, extensions=None):
    """Generate HTML report with clickable diff links."""
    # Create output directory for diff files
    if output_path:
        output_dir = os.path.dirname(output_path)
        diff_dir = os.path.join(output_dir, 'diffs')
    else:
        diff_dir = 'diffs'
    
    os.makedirs(diff_dir, exist_ok=True)
    
    # Generate diff files for each modified file
    diff_files = {}
    for file in results['modified']:
        file_id = file.replace('/', '_').replace('\\', '_').replace('.', '_').replace(' ', '_')
        diff_file = os.path.join(diff_dir, f"{file_id}.html")
        
        # Generate diff HTML file
        diff_html = generate_html_diff(
            os.path.join(dir1, file),
            os.path.join(dir2, file),
            file
        )
        
        with open(diff_file, 'w', encoding='utf-8') as f:
            f.write(diff_html)
        
        # Store relative path for linking
        diff_files[file] = os.path.relpath(diff_file, os.path.dirname(output_path) if output_path else '.')
    
    # Generate main HTML report
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory Comparison Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #24292e;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f6f8fa;
        }}
        h1, h2, h3 {{
            color: #24292e;
        }}
        .summary {{
            background-color: #fff;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            border: 1px solid #e1e4e8;
        }}
        .summary-row {{
            display: flex;
            margin-bottom: 12px;
        }}
        .summary-label {{
            font-weight: 600;
            width: 150px;
            color: #586069;
        }}
        .modified-list {{
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            margin-bottom: 24px;
            background-color: #fff;
            overflow: hidden;
        }}
        .modified-title {{
            background-color: #f1f8ff;
            color: #0366d6;
            padding: 12px 16px;
            border-bottom: 1px solid #e1e4e8;
            font-weight: 600;
        }}
        .file-item {{
            padding: 8px 16px;
            border-bottom: 1px solid #eaecef;
            display: flex;
            align-items: center;
        }}
        .file-item:last-child {{
            border-bottom: none;
        }}
        .file-item:hover {{
            background-color: #f6f8fa;
        }}
        .file-item a {{
            text-decoration: none;
            color: #0366d6;
            flex-grow: 1;
        }}
        .file-item a:hover {{
            text-decoration: underline;
        }}
        .file-icon {{
            margin-right: 12px;
            color: #586069;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section-title {{
            border-bottom: 1px solid #e1e4e8;
            padding-bottom: 8px;
            margin-bottom: 16px;
            color: #24292e;
        }}
        .added {{
            color: #28a745;
        }}
        .deleted {{
            color: #d73a49;
        }}
        .modified {{
            color: #f9c513;
        }}
        .error {{
            color: #cb2431;
        }}
        .collapsible {{
            margin-top: 24px;
        }}
        .collapsible-header {{
            background-color: #fff;
            padding: 12px 16px;
            cursor: pointer;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }}
        .collapsible-header:hover {{
            background-color: #f6f8fa;
        }}
        .collapsible-content {{
            display: none;
            padding: 0;
            max-height: 0;
            overflow: hidden;
            border: 1px solid #e1e4e8;
            border-top: none;
            margin-top: -5px;
            border-radius: 0 0 6px 6px;
            background-color: #fff;
            transition: max-height 0.3s ease-out;
        }}
        .show-content {{
            display: block;
            max-height: 1000px; /* adjust as needed */
            padding: 0;
        }}
        .count-badge {{
            background-color: #eaf5ff;
            border: 1px solid #c8e1ff;
            border-radius: 20px;
            padding: 3px 10px;
            font-size: 0.85em;
            color: #0366d6;
            font-weight: 600;
        }}
        .timestamp {{
            font-style: italic;
            color: #586069;
            font-size: 0.9em;
            margin-top: 5px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <h1>Directory Comparison Report</h1>
    
    <div class="timestamp">
        Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
    
    <div class="summary">
        <div class="summary-row">
            <div class="summary-label">Original Directory:</div>
            <div>{html.escape(dir1)}</div>
        </div>
        <div class="summary-row">
            <div class="summary-label">Modified Directory:</div>
            <div>{html.escape(dir2)}</div>
        </div>
        {f'<div class="summary-row"><div class="summary-label">File Extensions:</div><div>{", ".join(extensions)}</div></div>' if extensions else ''}
        <div class="summary-row">
            <div class="summary-label">Modified Files:</div>
            <div><strong>{len(results["modified"])}</strong></div>
        </div>
        <div class="summary-row">
            <div class="summary-label">Added Files:</div>
            <div><strong>{len(results["added"])}</strong></div>
        </div>
        <div class="summary-row">
            <div class="summary-label">Deleted Files:</div>
            <div><strong>{len(results["deleted"])}</strong></div>
        </div>
        <div class="summary-row">
            <div class="summary-label">Identical Files:</div>
            <div><strong>{len(results["identical"])}</strong></div>
        </div>
        <div class="summary-row">
            <div class="summary-label">Files with Errors:</div>
            <div><strong>{len(results["errors"])}</strong></div>
        </div>
    </div>
    
    <!-- Modified Files Section -->
    <div class="section">
        <h2 class="section-title">Modified Files <span class="count-badge">{len(results["modified"])}</span></h2>
        
        {f"<p>No modified files found.</p>" if not results["modified"] else ""}
        
        <div class="modified-list">
            {''.join([f"""
            <div class="file-item">
                <span class="file-icon modified">📝</span>
                <a href="{html.escape(diff_files[file])}" target="_blank">{html.escape(file)}</a>
            </div>
            """ for file in results["modified"]])}
        </div>
    </div>
    
    <!-- Added Files Section -->
    <div class="collapsible">
        <div class="collapsible-header" onclick="toggleSection('added-files')">
            <h2 style="margin: 0;">Added Files <span class="count-badge">{len(results["added"])}</span></h2>
            <span class="toggle-icon">▼</span>
        </div>
        <div id="added-files" class="collapsible-content">
            {f"<p style='padding: 16px;'>No added files found.</p>" if not results["added"] else ""}
            
            {''.join([f"""
            <div class="file-item">
                <span class="file-icon added">➕</span>
                <span>{html.escape(file)}</span>
            </div>
            """ for file in results["added"]])}
        </div>
    </div>
    
    <!-- Deleted Files Section -->
    <div class="collapsible">
        <div class="collapsible-header" onclick="toggleSection('deleted-files')">
            <h2 style="margin: 0;">Deleted Files <span class="count-badge">{len(results["deleted"])}</span></h2>
            <span class="toggle-icon">▼</span>
        </div>
        <div id="deleted-files" class="collapsible-content">
            {f"<p style='padding: 16px;'>No deleted files found.</p>" if not results["deleted"] else ""}
            
            {''.join([f"""
            <div class="file-item">
                <span class="file-icon deleted">➖</span>
                <span>{html.escape(file)}</span>
            </div>
            """ for file in results["deleted"]])}
        </div>
    </div>
    
    <!-- Error Files Section -->
    <div class="collapsible">
        <div class="collapsible-header" onclick="toggleSection('error-files')">
            <h2 style="margin: 0;">Files with Errors <span class="count-badge">{len(results["errors"])}</span></h2>
            <span class="toggle-icon">▼</span>
        </div>
        <div id="error-files" class="collapsible-content">
            {f"<p style='padding: 16px;'>No files with errors found.</p>" if not results["errors"] else ""}
            
            {''.join([f"""
            <div class="file-item">
                <span class="file-icon error">⚠️</span>
                <span>{html.escape(file)}: {html.escape(error)}</span>
            </div>
            """ for file, error in results["errors"]])}
        </div>
    </div>
    
    <script>
    function toggleSection(id) {{
        const content = document.getElementById(id);
        content.classList.toggle('show-content');
        
        // Update the toggle icon
        const header = content.previousElementSibling;
        const icon = header.querySelector('.toggle-icon');
        icon.textContent = content.classList.contains('show-content') ? '▲' : '▼';
    }}
    </script>
</body>
</html>
'''
    
    # Write the HTML report
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return output_path
    else:
        with open('comparison_report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        return 'comparison_report.html'


def main():
    parser = argparse.ArgumentParser(description='Compare two project directories')
    parser.add_argument('dir1', help='First directory path')
    parser.add_argument('dir2', help='Second directory path')
    parser.add_argument('--show-diff', action='store_true', help='Show file content differences')
    parser.add_argument('--output', help='Output file for the report')
    parser.add_argument('--extensions', help='Only compare files with specified extensions (comma-separated, e.g., ".c,.h")')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--html-output', help='HTML report output file path')
    
    args = parser.parse_args()
    
    dir1 = args.dir1
    dir2 = args.dir2
    
    # Process extensions if provided
    extensions = None
    if args.extensions:
        extensions = args.extensions.split(',')
        # Ensure all extensions have a dot prefix
        extensions = [ext if ext.startswith('.') else '.' + ext for ext in extensions]
    
    # Validate directories
    if not os.path.isdir(dir1):
        print(f"Error: {dir1} is not a valid directory")
        return
    
    if not os.path.isdir(dir2):
        print(f"Error: {dir2} is not a valid directory")
        return
    
    # Compare directories
    print(f"Comparing directories:\n  {dir1}\n  {dir2}")
    if extensions:
        print(f"Only comparing files with extensions: {', '.join(extensions)}")
    print()
    
    results = compare_directories(dir1, dir2, extensions)
    
    # Generate HTML report if requested
    if args.html or args.html_output:
        html_output = args.html_output if args.html_output else 'comparison_report.html'
        report_path = generate_html_report(results, dir1, dir2, html_output, extensions)
        print(f"HTML report generated: {report_path}")
        return
    
    # Otherwise, generate text report
    output = []
    output.append(f"Comparing: {dir1} and {dir2}")
    if extensions:
        output.append(f"File extensions filter: {', '.join(extensions)}")
    output.append("")
    
    output.append(f"Added files ({len(results['added'])}):")
    for file in results['added']:
        output.append(f"  + {file}")
    
    output.append(f"\nDeleted files ({len(results['deleted'])}):")
    for file in results['deleted']:
        output.append(f"  - {file}")
    
    output.append(f"\nModified files ({len(results['modified'])}):")
    for file in results['modified']:
        output.append(f"  * {file}")
        
        if args.show_diff:
            output.append("\n  Differences:")
            file1_path = os.path.join(dir1, file)
            file2_path = os.path.join(dir2, file)
            
            try:
                diff = show_file_diff(file1_path, file2_path)
                # Indent the diff output
                diff_lines = diff.split('\n')
                indented_diff = ['    ' + line for line in diff_lines]
                output.append('\n'.join(indented_diff))
                output.append("")
            except Exception as e:
                output.append(f"    Error generating diff: {str(e)}")
    
    output.append(f"\nIdentical files: {len(results['identical'])}")
    
    if results['errors']:
        output.append(f"\nFiles with errors ({len(results['errors'])}):")
        for file, error in results['errors']:
            output.append(f"  ! {file}: {error}")
    
    # Print summary
    summary = '\n'.join(output)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"Report saved to {args.output}")
    else:
        print(summary)


if __name__ == "__main__":
    main()

#Usage: python directory_diff.py path/to/project1 path/to/project2 --extensions ".c,.h" --html --html-output report.html