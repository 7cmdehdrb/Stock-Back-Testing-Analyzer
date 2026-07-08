import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update .action-buttons-container to have margin-top: 15px;
text = text.replace('<div class="action-buttons-container" style="display: flex; gap: 10px;">', '<div class="action-buttons-container" style="display: flex; gap: 10px; margin-top: 15px;">')

# 2. Update .card padding on mobile
media_card = '''
        @media (max-width: 480px) {
            .card {
                padding: 15px;
            }
        }
'''
if 'padding: 15px;' not in text:
    text = text.replace('</style>', media_card + '\n    </style>', 1)

# 3. Update delete-row-btn padding and font-size
delete_css_old = '''        .delete-row-btn {
            background: #ef4444;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;'''
delete_css_new = '''        .delete-row-btn {
            background: #ef4444;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;'''
text = text.replace(delete_css_old, delete_css_new)

# 4. Make sure inline styles for country-toggle match padding 8px 12px and font-size 14px
text = text.replace('padding: 6px 12px;', 'padding: 8px 12px; font-size: 14px; height: 38px;')

# 5. Make sure inputs have height: 38px and delete button has height: 38px for absolute consistency
text = text.replace('box-shadow: inset 0 1px 2px rgba(0,0,0,0.02);', 'box-shadow: inset 0 1px 2px rgba(0,0,0,0.02);\n            height: 38px;\n            box-sizing: border-box;')
text = text.replace('transition: all 0.2s ease;\n            width: 100%;\n        }\n\n        .delete-row-btn:hover', 'transition: all 0.2s ease;\n            width: 100%;\n            height: 38px;\n            box-sizing: border-box;\n        }\n\n        .delete-row-btn:hover')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Applied UI fixes successfully.")
