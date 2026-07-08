import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Rollback the vertical spacing on .form-group
text = text.replace('margin-bottom: 24px;', 'margin-bottom: 16px;')

# 2. Rollback the analyzeBtn margin
text = text.replace('<button type="submit" class="btn" id="analyzeBtn" style="margin-top: 16px; margin-bottom: 8px;">', '<button type="submit" class="btn" id="analyzeBtn">')

# 3. Fix the mobile styling so it has left/right margin (not edge-to-edge)
mobile_css_old = '''        @media (max-width: 480px) {
            body {
                padding: 0; /* No body padding on very small screens */
            }
            .card {
                padding: 12px;
                border-radius: 0; /* Remove border radius to maximize edge-to-edge */
                border-left: none;
                border-right: none;
            }'''

mobile_css_new = '''        @media (max-width: 480px) {
            body {
                padding: 10px; /* Restored left/right body padding */
            }
            .card {
                padding: 16px;
                border-radius: 12px; /* Restored border radius */
                border: 1px solid #e2e8f0; /* Restored border */
            }'''

text = text.replace(mobile_css_old, mobile_css_new)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Rolled back vertical margins and restored left/right margins on mobile.")
