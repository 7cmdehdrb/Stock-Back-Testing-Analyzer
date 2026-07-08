import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Remove AI Button and Modal
html = re.sub(r'<button id="aiAnalysisBtn".*?</button>', '', html, flags=re.DOTALL)
html = re.sub(r'<div id="aiAnalysisModal".*?</div>\s*</div>\s*</div>', '', html, flags=re.DOTALL) # Might be tricky, let's just use simple replace or ignore it since it's hidden anyway.
# Actually let's just remove the button so it can't be clicked.

# 2. Replace CSV Mode Button
html = html.replace('📁 CSV 불러오기', '📂 기록에서 불러오기')
html = html.replace('switchInputMode(\'csv\');', 'openPortfolioModal();')

# 3. Replace CSV Export Button with Save DB Button
save_btn = '''<button id="saveDbBtn" type="button" onclick="savePortfolioToDB()" class="btn" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 12px 24px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
    💾 내 포트폴리오 저장
</button>'''
html = re.sub(r'<button id="exportBtn".*?</button>', save_btn, html, flags=re.DOTALL)

# 4. Add Modal HTML and JS before </body>
modal_html = """
    <!-- 포트폴리오 불러오기 모달 -->
    <div id="portfolioModal" class="modal">
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2>📂 저장된 포트폴리오 불러오기</h2>
                <span class="close" onclick="closePortfolioModal()">&times;</span>
            </div>
            <div class="modal-body" style="max-height: 400px; overflow-y: auto;">
                <div id="portfolioList">
                    <p style="text-align:center; color:#666;">포트폴리오 목록을 불러오는 중...</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        function openPortfolioModal() {
            document.getElementById('portfolioModal').style.display = 'block';
            fetchPortfolios();
        }

        function closePortfolioModal() {
            document.getElementById('portfolioModal').style.display = 'none';
        }

        async function fetchPortfolios() {
            try {
                const response = await fetch('/api/portfolio');
                const data = await response.json();
                const list = document.getElementById('portfolioList');
                if (data.success && data.portfolios.length > 0) {
                    list.innerHTML = data.portfolios.map(p => `
                        <div style="border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h3>${p.name}</h3>
                                <p style="font-size: 0.9em; color: #666;">${p.created_at}</p>
                            </div>
                            <div>
                                <button onclick='loadPortfolioData(${JSON.stringify(p.csv_content)})' class="btn" style="background: #667eea; color: white; padding: 8px 15px; border-radius: 5px; border: none; cursor: pointer;">불러오기</button>
                                <button onclick='deletePortfolio(${p.id})' class="btn" style="background: #ef4444; color: white; padding: 8px 15px; border-radius: 5px; border: none; cursor: pointer; margin-left: 5px;">삭제</button>
                            </div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<p style="text-align:center; color:#666;">저장된 포트폴리오가 없습니다.</p>';
                }
            } catch(e) {
                document.getElementById('portfolioList').innerHTML = '<p style="color:red; text-align:center;">오류가 발생했습니다.</p>';
            }
        }

        async function loadPortfolioData(csvContent) {
            closePortfolioModal();
            // Create a blob and simulate file upload to reuse existing parse-csv logic
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const file = new File([blob], 'loaded_portfolio.csv', { type: 'text/csv' });
            
            const formData = new FormData();
            formData.append('csv_file', file);
            
            try {
                const response = await fetch('/parse-csv', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error);
                
                // Clear existing inputs
                document.getElementById('assetRows').innerHTML = '';
                
                // Add rows
                data.assets.forEach(asset => {
                    addAssetRow(asset.ticker, asset.quantity);
                });
                
                document.getElementById('cashKRW').value = data.cash.krw || 0;
                document.getElementById('cashUSD').value = data.cash.usd || 0;
                
                alert('포트폴리오를 성공적으로 불러왔습니다!');
            } catch(e) {
                alert('포트폴리오 로드 중 오류: ' + e.message);
            }
        }

        async function deletePortfolio(pid) {
            if(!confirm('정말 삭제하시겠습니까?')) return;
            try {
                const res = await fetch('/api/portfolio/' + pid, {method: 'DELETE'});
                const data = await res.json();
                if(data.success) {
                    fetchPortfolios();
                } else {
                    alert('삭제 실패: ' + data.error);
                }
            } catch(e) {
                alert('오류 발생');
            }
        }

        async function savePortfolioToDB() {
            const name = prompt('저장할 포트폴리오 이름을 입력하세요:');
            if(!name) return;
            
            const csvContent = convertManualInputToCSV(); // existing function
            if(!csvContent) {
                alert('포트폴리오 내용이 없습니다.');
                return;
            }
            
            const payload = {
                name: name,
                csv_content: csvContent,
                start_date: document.getElementById('startDate').value,
                benchmark_ticker: document.getElementById('benchmarkTicker').value,
                base_currency: document.getElementById('baseCurrency').value
            };
            
            try {
                const res = await fetch('/api/portfolio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if(data.success) {
                    alert('저장되었습니다!');
                } else {
                    alert('저장 실패: ' + data.error);
                }
            } catch(e) {
                alert('오류 발생');
            }
        }
    </script>
</body>"""

html = html.replace('</body>', modal_html)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
