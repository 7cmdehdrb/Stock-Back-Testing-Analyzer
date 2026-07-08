import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Remove analyzeWithAI and related functions (openAIModal, closeAIModal)
text = re.sub(r'// AI 분석 결과 캐시.*?function closeAIModal\(\) \{.*?\}', '', text, flags=re.DOTALL)

# 2. Remove aiAnalysisBtn button
text = re.sub(r'<button id="aiAnalysisBtn".*?</button>', '', text, flags=re.DOTALL)

# 3. Remove aiAnalysisModal
text = re.sub(r'<div id="aiAnalysisModal".*?</div>\s*</div>\s*</div>', '', text, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
