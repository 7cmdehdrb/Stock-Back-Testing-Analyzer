import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Move the closing </div> of input-table-container to be right after </table>
# The current structure:
# </table>
# <div class="action-buttons-container" ...> ... </div>
# ... wait, does it close after the buttons? Let's find out where input-table-container closes.
# It's probably right after the buttons.
pattern = r'(</table>)\s*(<div class="action-buttons-container" style="display: flex; gap: 10px; margin-top: 15px;">\s*<button.*?</button>\s*<button.*?</button>\s*</div>)\s*</div>'
# If it's structured like that, we want to change it to:
# </table>
# </div>
# <div class="action-buttons-container"> ... </div>
replacement = r'\1\n                    </div>\n                    \2'

new_text = re.sub(pattern, replacement, text, flags=re.DOTALL)

# Let's verify if the pattern matched. If not, it means the </div> is elsewhere.
if text == new_text:
    print("Pattern 1 didn't match. Attempting alternative.")
    # Let's just blindly insert </div> after </table> and remove the </div> that comes after action-buttons-container
    pattern2 = r'(</table>)\s*<div class="action-buttons-container"'
    new_text = re.sub(pattern2, r'\1\n                    </div>\n                    <div class="action-buttons-container"', new_text)
    
    # Now we need to remove the extra </div> that was closing input-table-container.
    # It usually comes right after the action-buttons-container
    pattern3 = r'(</button>\s*</div>)\s*</div>'
    new_text = re.sub(pattern3, r'\1', new_text)

# Also strip the inline margin-top from action-buttons-container since our CSS has it.
new_text = new_text.replace('<div class="action-buttons-container" style="display: flex; gap: 10px; margin-top: 15px;">', '<div class="action-buttons-container">')

# 2. Fix the CSS for .add-row-btn to use padding instead of strict height
css_old = r'''        \.add-row-btn \{
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0 16px;
            height: 42px; /\* Distinct height from table rows but consistent across buttons \*/
            border-radius: 8px;'''
css_new = '''        .add-row-btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 12px 16px;
            height: auto;
            border-radius: 8px;'''
new_text = re.sub(css_old, css_new, new_text)

# 3. Fix the mobile add-row-btn height
mobile_css_old = r'''            \.add-row-btn \{
                height: 44px; /\* Larger tap target on mobile \*/
            \}'''
mobile_css_new = '''            .add-row-btn {
                padding: 14px 16px;
                height: auto;
            }'''
new_text = re.sub(mobile_css_old, mobile_css_new, new_text)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Applied HTML layout and CSS fixes.")
