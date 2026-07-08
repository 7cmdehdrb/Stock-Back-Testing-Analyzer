import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('id="analysisFormCard"')
end = text.find('class="results" id="results"')

fragment = text[start:end]

open_divs = len(re.findall(r'<div\b', fragment))
close_divs = len(re.findall(r'</div>', fragment))

print('Open divs:', open_divs)
print('Close divs:', close_divs)
