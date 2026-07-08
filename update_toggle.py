import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Remove min-width: 500px
text = text.replace('min-width: 500px;', '')

# 2. Add toggleCountry function to JS
toggle_func = '''        function toggleCountry(btn) {
            if (btn.value === '미국') {
                btn.value = '한국';
                btn.innerText = '한국';
                btn.style.background = '#e2e8f0';
                btn.style.color = '#334155';
            } else {
                btn.value = '미국';
                btn.innerText = '미국';
                btn.style.background = '#eff6ff';
                btn.style.color = '#2563eb';
            }
        }'''
if 'function toggleCountry' not in text:
    text = text.replace('function addRow', toggle_func + '\n\n        function addRow')

# 3. Replace <select class="country-input"> with <button class="country-input country-toggle" value="미국">미국</button> in the static HTML
html_select_pattern = r'<select class="country-input">\s*<option value="미국">미국</option>\s*<option value="한국">한국</option>\s*</select>'
html_btn = '<button type="button" class="country-input country-toggle" value="미국" onclick="toggleCountry(this)" style="background: #eff6ff; color: #2563eb; font-weight: 600; cursor: pointer; padding: 6px 12px; border: 1px solid transparent; border-radius: 6px; width: 100%; transition: all 0.2s;">미국</button>'
text = re.sub(html_select_pattern, html_btn, text)

# 4. Replace <select class="country-input"> inside addRow JS
add_row_select_pattern = r'<select class="country-input">\s*<option value="미국" \$\{country === \'미국\' \? \'selected\' : \'\'\}>미국</option>\s*<option value="한국" \$\{country === \'한국\' \? \'selected\' : \'\'\}>한국</option>\s*</select>'
add_row_btn = '<button type="button" class="country-input country-toggle" value="${country}" onclick="toggleCountry(this)" style="background: ${country === \'미국\' ? \'#eff6ff\' : \'#e2e8f0\'}; color: ${country === \'미국\' ? \'#2563eb\' : \'#334155\'}; font-weight: 600; cursor: pointer; padding: 6px 12px; border: 1px solid transparent; border-radius: 6px; width: 100%; transition: all 0.2s;">${country}</button>'
text = re.sub(add_row_select_pattern, add_row_btn, text)

# 5. Replace <select class="dca-country-input"> inside addDcaRow JS
add_dca_row_select_pattern = r'<select class="dca-country-input">\s*<option value="미국" \$\{country === \'미국\' \? \'selected\' : \'\'\}>미국</option>\s*<option value="한국" \$\{country === \'한국\' \? \'selected\' : \'\'\}>한국</option>\s*</select>'
add_dca_row_btn = '<button type="button" class="dca-country-input country-toggle" value="${country}" onclick="toggleCountry(this)" style="background: ${country === \'미국\' ? \'#eff6ff\' : \'#e2e8f0\'}; color: ${country === \'미국\' ? \'#2563eb\' : \'#334155\'}; font-weight: 600; cursor: pointer; padding: 6px 12px; border: 1px solid transparent; border-radius: 6px; width: 100%; transition: all 0.2s;">${country}</button>'
text = re.sub(add_dca_row_select_pattern, add_dca_row_btn, text)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('Applied toggle updates successfully.')
