import re
with open('templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'id="results"' in line:
        print(f'{i}: {line.strip()}')
