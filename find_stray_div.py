import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('id="analysisFormCard"')
end = text.find('class="results" id="results"')
fragment = text[start:end]

stack = []
stray_index = -1
for m in re.finditer(r'<(div[^>]*)>|</(div)>', fragment):
    if m.group(1): # open
        stack.append(m.start())
    elif m.group(2): # close
        if stack:
            stack.pop()
        else:
            stray_index = m.start()
            break

if stray_index != -1:
    print('Stray </div> at index:', stray_index)
    print('Context:')
    print(fragment[max(0, stray_index-50):stray_index+50])
else:
    print('No stray </div> found during linear parse (it might be at the end closing a parent before its time)')
