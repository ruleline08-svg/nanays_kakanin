#!/usr/bin/env python3
"""Fix remaining tailwind.config scripts in templates"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / 'kakanin' / 'templates' / 'kakanin'

PATTERN = r'<script>\s*tailwind\.config\s*=\s*\{[\s\S]*?\}\s*\}\s*</script>'
REPLACEMENT = '''<style>
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

count = 0
for html_file in TEMPLATES_DIR.glob('*.html'):
    content = html_file.read_text(encoding='utf-8')
    if 'tailwind.config' in content:
        new_content = re.sub(PATTERN, REPLACEMENT, content, flags=re.DOTALL)
        html_file.write_text(new_content, encoding='utf-8')
        print(f"Fixed: {html_file.name}")
        count += 1

print(f"\nTotal files fixed: {count}")
