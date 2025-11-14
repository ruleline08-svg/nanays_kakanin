#!/usr/bin/env python3
"""
Script to update all HTML templates to use local CSS instead of CDN
This fixes the offline loading issue
"""

import os
import re
from pathlib import Path

# Define the base directory
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / 'kakanin' / 'templates' / 'kakanin'

# Old CDN patterns to replace
OLD_PATTERNS = [
    (
        r'<script src="https://cdn\.tailwindcss\.com"></script>',
        '<!-- Local Tailwind CSS -->\n  <link rel="stylesheet" href="{% static \'kakanin/dist/output.css\' %}" />'
    ),
    (
        r'<link rel="stylesheet" href="https://cdnjs\.cloudflare\.com/ajax/libs/font-awesome/[\d.]+/css/all\.min\.css"\s*/?>',
        '<!-- Icon Libraries with CDN fallback -->\n  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" onerror="this.onerror=null;this.href=\'{% static \'kakanin/css/icons-fallback.css\' %}\';\" />'
    ),
    (
        r'<link rel="stylesheet" href="https://cdn\.jsdelivr\.net/npm/bootstrap-icons@[\d.]+/font/bootstrap-icons\.(?:min\.)?css"\s*/?>',
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" onerror="this.onerror=null;this.href=\'{% static \'kakanin/css/icons-fallback.css\' %}\';\">'
    ),
]

# Tailwind config to replace with custom colors
TAILWIND_CONFIG_PATTERN = r'<script>\s*tailwind\.config\s*=\s*\{[^}]+\}\s*</script>'
TAILWIND_CONFIG_REPLACEMENT = '''<style>
    /* Tailwind custom colors */
    :root {
      --color-primary: #16a34a;
      --color-secondary: #15803d;
    }
    .bg-primary { background-color: var(--color-primary) !important; }
    .text-primary { color: var(--color-primary) !important; }
    .border-primary { border-color: var(--color-primary) !important; }
    .ring-primary { --tw-ring-color: var(--color-primary) !important; }
    .bg-secondary { background-color: var(--color-secondary) !important; }
    .text-secondary { color: var(--color-secondary) !important; }
  </style>'''

def update_template(file_path):
    """Update a single template file"""
    print(f"Processing: {file_path.name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Apply replacements
    for pattern, replacement in OLD_PATTERNS:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Replace tailwind config
    content = re.sub(TAILWIND_CONFIG_PATTERN, TAILWIND_CONFIG_REPLACEMENT, content, flags=re.DOTALL)
    
    # Only write if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Updated: {file_path.name}")
        return True
    else:
        print(f"  - No changes needed: {file_path.name}")
        return False

def main():
    """Main function to update all templates"""
    print("=" * 60)
    print("Updating HTML templates to use local CSS resources")
    print("=" * 60)
    print()
    
    if not TEMPLATES_DIR.exists():
        print(f"Error: Templates directory not found: {TEMPLATES_DIR}")
        return
    
    # Find all HTML files
    html_files = list(TEMPLATES_DIR.glob('*.html'))
    
    if not html_files:
        print("No HTML files found!")
        return
    
    print(f"Found {len(html_files)} HTML files\n")
    
    updated_count = 0
    for html_file in html_files:
        if update_template(html_file):
            updated_count += 1
    
    print()
    print("=" * 60)
    print(f"Summary: Updated {updated_count} out of {len(html_files)} files")
    print("=" * 60)

if __name__ == '__main__':
    main()
