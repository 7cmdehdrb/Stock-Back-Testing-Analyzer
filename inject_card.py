import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Make sure we don't duplicate
if 'id="portfolioViewCard"' not in html:
    portfolio_card_html = """
        <!-- 내 포트폴리오 뷰 -->
        <div class="card" id="portfolioViewCard" style="display: none; min-height: 500px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-bottom: 20px;">
                <h2 style="color: #4a5568;">📂 내 포트폴리오 목록</h2>
            </div>
            <div id="portfolioList" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px;">
                <p style="text-align:center; color:#666; grid-column: 1 / -1;">포트폴리오 목록을 불러오는 중...</p>
            </div>
        </div>
    """
    
    # Inject before resultSection
    html = html.replace('<div class="card" id="resultSection"', portfolio_card_html + '\n        <div class="card" id="resultSection"')

# Also remove the old modal if it's there
old_modal_regex = r'<!-- 포트폴리오 불러오기 모달 -->.*?<div id="portfolioModal" class="modal">.*?</div>\s*</div>\s*</div>'
html = re.sub(old_modal_regex, '', html, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
