import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the 5 closing divs with 4 closing divs
target = '''                            </div>
                        </div>
                    </div>
                </div>

                <div class="form-group">
                    <label for="startDate">'''

replacement = '''                            </div>
                        </div>
                    </div>

                <div class="form-group">
                    <label for="startDate">'''

new_text = text.replace(target, replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Removed stray </div>")
