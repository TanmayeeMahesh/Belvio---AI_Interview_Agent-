import os
import glob

dir_path = "frontend/src/components/landing/"
files = glob.glob(os.path.join(dir_path, "*.jsx"))

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Fix the double replacement issue
    content = content.replace(', backdropFilter: "blur(12px)" }, backdropFilter: "blur(12px)" }', ', backdropFilter: "blur(12px)" }}')
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Syntax fixed!")
