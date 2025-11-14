#!/usr/bin/env python3
"""
Revert templates to use CDN Tailwind CSS instead of local build
This fixes the design issues caused by incomplete local Tailwind build
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / 'kakanin' / 'templates' / 'kakanin'

# Revert to CDN Tailwind
OLD_LOCAL_CSS = r'<!-- Local Tailwind CSS -->\s*<link rel="stylesheet" href="{% static \'kakanin/dist/output\.css\' %}" />'
NEW_CDN_SCRIPT = '<script src="https://cdn.tailwindcss.com"></script>'

# Keep icon fallbacks but restore original pattern
OLD_ICON_PATTERN = r'<!-- Icon Libraries with CDN fallback -->\s*<link rel="stylesheet" href="https://cdnjs\.cloudflare\.com/ajax/libs/font-awesome/6\.4\.0/css/all\.min\.css" onerror="[^"]*" />\s*<link rel="stylesheet" href="https://cdn\.jsdelivr\.net/npm/bootstrap-icons@1\.11\.1/font/bootstrap-icons\.css" onerror="[^"]*">'
NEW_ICON_PATTERN = '''<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">'''

# Restore Tailwind config
OLD_CUSTOM_COLORS = r'<style>\s*/\* Tailwind custom colors \*/\s*:root \{[^}]+\}[^<]+</style>'
NEW_TAILWIND_CONFIG = '''<script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            primary: '#16a34a',
            secondary: '#15803d',
          }
        }
      }
    }
  </script>'''

count = 0
for html_file in TEMPLATES_DIR.glob('*.html'):
    content = html_file.read_text(encoding='utf-8')
    original = content
    
    # Revert Tailwind CSS
    content = re.sub(OLD_LOCAL_CSS, NEW_CDN_SCRIPT, content, flags=re.MULTILINE)
    
    # Revert icon libraries
    content = re.sub(OLD_ICON_PATTERN, NEW_ICON_PATTERN, content, flags=re.DOTALL)
    
    # Restore Tailwind config
    content = re.sub(OLD_CUSTOM_COLORS, NEW_TAILWIND_CONFIG, content, flags=re.DOTALL)
    
    if content != original:
        html_file.write_text(content, encoding='utf-8')
        print(f"Reverted: {html_file.name}")
        count += 1

print(f"\nTotal files reverted: {count}")
print("\nNote: CDN resources will now load from internet.")
print("For offline support, the service worker will cache them on first load.")
