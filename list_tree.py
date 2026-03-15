import os
from pathlib import Path

def list_tree(directory='.', prefix='', max_depth=None, current_depth=0):
    """List files in tree structure"""
    if max_depth and current_depth >= max_depth:
        return
    
    path = Path(directory)
    items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = '└── ' if is_last else '├── '
        print(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
        
        if item.is_dir() and not item.name.startswith('.') and item.name not in ['node_modules', '__pycache__', 'venv']:
            extension = '    ' if is_last else '│   '
            list_tree(item, prefix + extension, max_depth, current_depth + 1)

if __name__ == '__main__':
    print(Path.cwd().name + '/')
    list_tree()
