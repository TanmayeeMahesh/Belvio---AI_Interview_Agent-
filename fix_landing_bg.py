import os
import glob
import re

dir_path = "frontend/src/components/landing/"
files = glob.glob(os.path.join(dir_path, "*.jsx"))

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Remove alternating backgrounds from sections
    content = re.sub(r'background:\s*"(?:#0B1120|#0F172A|#060A14)"\s*,?', '', content)
    # Remove the hard linear gradient in HeroSection that breaks the flow
    content = re.sub(r'background:\s*"linear-gradient\(180deg, rgba\(15,23,42,0\) 0%, #0F172A 100%\)"\s*,?', '', content)
    
    # Make cards more transparent glassmorphism
    # Currently cards use rgba(255,255,255,0.02) or 0.03 or 0.05
    # Let's add backdropFilter: "blur(12px)" to them if they have border: "1px solid rgba(255,255,255,0.05)"
    # A generic approach: any inline style dict that has background rgba(255,255,255,0.0... we add backdropFilter
    def add_glass(match):
        style_str = match.group(0)
        if 'backdropFilter' not in style_str and 'rgba(255,255,255,0.0' in style_str:
            return style_str.replace('}', ', backdropFilter: "blur(12px)" }')
        return style_str
        
    content = re.sub(r'style=\{\{[^}]+\}\}', add_glass, content)
    
    # Fix double commas or trailing commas that might have been left over by the first replacement
    content = re.sub(r',\s*,', ',', content)
    content = re.sub(r'\{\s*,', '{', content)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Backgrounds removed and glassmorphism added!")
