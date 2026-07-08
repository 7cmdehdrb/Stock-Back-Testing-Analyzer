import re
with open('templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'type="checkbox"' in line or 'dca' in line.lower():
        print(f'{i}: {line.strip()}')
