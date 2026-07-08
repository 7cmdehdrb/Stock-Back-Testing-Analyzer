import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# I will find the end of the <style> block and insert the missing media query.
media_query = '''
        @media (max-width: 480px) {
            .input-table th, .input-table td {
                padding: 6px 2px;
                font-size: 11px;
            }
            .input-table input[type="text"],
            .input-table input[type="number"],
            .input-table select,
            .country-toggle {
                padding: 4px;
                font-size: 11px;
                min-width: 40px;
            }
            .delete-row-btn {
                padding: 6px 4px;
                font-size: 10px;
            }
        }
'''

# Find the first </style> tag and insert before it
text = text.replace('</style>', media_query + '\n    </style>', 1)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('Restored mobile CSS for table inputs')
