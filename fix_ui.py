import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update Navbar
new_navbar = """<div class="navbar-content">
                <a href="#" onclick="showAnalyzeView()" class="navbar-title">📊 포트폴리오 성과 분석기</a>
                <div class="navbar-links">
                    <a href="#" onclick="showAnalyzeView()" class="navbar-link active" id="navAnalyze">분석하기</a>
                    <a href="#" onclick="showPortfolioView()" class="navbar-link" id="navPortfolio">내 포트폴리오</a>
                </div>
            </div>"""
html = re.sub(r'<div class="navbar-content">.*?</div>\s*</div>', new_navbar + '\n        </div>', html, flags=re.DOTALL)

# 2. Extract and replace the modal with portfolio view card
old_modal_regex = r'<!-- 포트폴리오 불러오기 모달 -->.*?</div>\s*</div>\s*</div>'
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

# Replace the modal HTML
if re.search(old_modal_regex, html, re.DOTALL):
    html = re.sub(old_modal_regex, portfolio_card_html, html, flags=re.DOTALL)
else:
    # If the regex doesn't match perfectly, let's insert it before <script>
    html = html.replace('<script>', portfolio_card_html + '\n    <script>')

# 3. Modify the JS functions
new_js_functions = """
        function showAnalyzeView() {
            document.getElementById('analysisFormCard').style.display = 'block';
            if (document.getElementById('resultSection').innerHTML.trim() !== "") {
                // Only show result section if it has content, but actually it toggles via other logic.
                // We'll leave it alone, but ensure it's not hidden if there's a chart.
                if(window.myChart) document.getElementById('resultSection').style.display = 'block';
            }
            document.getElementById('portfolioViewCard').style.display = 'none';
            document.getElementById('navAnalyze').classList.add('active');
            document.getElementById('navPortfolio').classList.remove('active');
        }

        function showPortfolioView() {
            document.getElementById('analysisFormCard').style.display = 'none';
            document.getElementById('resultSection').style.display = 'none';
            document.getElementById('portfolioViewCard').style.display = 'block';
            document.getElementById('navAnalyze').classList.remove('active');
            document.getElementById('navPortfolio').classList.add('active');
            fetchPortfolios();
        }

        // Redirect openPortfolioModal to showPortfolioView
        function openPortfolioModal() {
            showPortfolioView();
        }

        function closePortfolioModal() {
            showAnalyzeView();
        }

        async function fetchPortfolios() {
            try {
                const response = await fetch('/api/portfolio');
                const data = await response.json();
                const list = document.getElementById('portfolioList');
                if (data.success && data.portfolios.length > 0) {
                    list.innerHTML = data.portfolios.map(p => `
                        <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: space-between;">
                            <div style="margin-bottom: 15px;">
                                <h3 style="color: #2d3748; margin-bottom: 8px; font-size: 1.2rem;">${p.name}</h3>
                                <p style="font-size: 0.85em; color: #718096; margin-bottom: 5px;">📅 ${p.created_at}</p>
                            </div>
                            <div style="display: flex; gap: 10px; margin-top: auto;">
                                <button onclick='loadPortfolioData(${JSON.stringify(p.csv_content)})' class="btn" style="flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600;">불러오기</button>
                                <button onclick='deletePortfolio(${p.id})' class="btn" style="background: #fee2e2; color: #ef4444; padding: 10px 15px; border-radius: 8px; border: 1px solid #fca5a5; cursor: pointer; font-weight: 600;">삭제</button>
                            </div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 50px; background: #f8fafc; border-radius: 12px; color: #718096;">저장된 포트폴리오가 없습니다.</div>';
                }
            } catch(e) {
                document.getElementById('portfolioList').innerHTML = '<p style="color:red; text-align:center; grid-column: 1 / -1;">오류가 발생했습니다.</p>';
            }
        }
"""

# Find fetchPortfolios in html and replace it and surrounding with new_js_functions
html = re.sub(r'function openPortfolioModal\(\) \{.*?(?=async function loadPortfolioData)', new_js_functions, html, flags=re.DOTALL)
html = html.replace('closePortfolioModal();', 'showAnalyzeView();')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
