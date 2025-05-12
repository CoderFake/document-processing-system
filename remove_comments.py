import os
import re
import sys

def remove_comments_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        
    new_lines = []
    in_docstring = False
    docstring_marker = None
    
    for line in lines:
        if not in_docstring:
            if '"""' in line or "'''" in line:
                marker = '"""' if '"""' in line else "'''"
                count = line.count(marker)
                if count % 2 == 1:
                    in_docstring = True
                    docstring_marker = marker
                new_lines.append(line)
                continue
                
            if line.strip().startswith('#'):
                continue
            elif '#' in line:
                code_part = line.split('#')[0]
                if code_part.strip():
                    new_lines.append(code_part + '\n')
                continue
            
            new_lines.append(line)
        else:
            new_lines.append(line)
            if docstring_marker in line:
                count = line.count(docstring_marker)
                if count % 2 == 1:
                    in_docstring = False
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(new_lines)
    
    print(f"Đã xóa comment trong file: {file_path}")

def process_directory(dir_path, excluded_files=None, excluded_dirs=None):
    if excluded_files is None:
        excluded_files = []
    if excluded_dirs is None:
        excluded_dirs = []
    
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in excluded_dirs and not d.startswith('.')]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if file not in excluded_files and not any(file.endswith(ext) for ext in ['.md', '.env.example']):
                    try:
                        remove_comments_from_file(file_path)
                    except Exception as e:
                        print(f"Lỗi khi xử lý file {file_path}: {e}")

if __name__ == "__main__":
    root_dir = '.'
    excluded_dirs = ['.git', '.venv', '.idea']
    excluded_files = ['document-processing-system.md', 'README.md', '.env.example', 'docker-compose.yml']
    
    process_directory(root_dir, excluded_files, excluded_dirs)
    print("Hoàn tất xóa comment!")