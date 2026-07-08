import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix spacing around the Analyze button
# We will just add margin-top: 24px; and margin-bottom: 16px; to it inline for maximum safety and specificity
text = text.replace('<button type="submit" class="btn" id="analyzeBtn">', '<button type="submit" class="btn" id="analyzeBtn" style="margin-top: 16px; margin-bottom: 8px;">')

# Also, ensure .form-group has a bit more bottom margin globally
text = text.replace('margin-bottom: 16px;', 'margin-bottom: 24px;')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Applied margin fixes.")
