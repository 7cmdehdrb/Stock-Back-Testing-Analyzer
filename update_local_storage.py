import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

new_js = """
        const DB_KEY = 'saved_portfolios';

        function getLocalPortfolios() {
            const data = localStorage.getItem(DB_KEY);
            return data ? JSON.parse(data) : [];
        }

        function saveLocalPortfolio(portfolio) {
            const portfolios = getLocalPortfolios();
            portfolio.id = Date.now();
            portfolio.created_at = new Date().toLocaleString();
            portfolios.push(portfolio);
            localStorage.setItem(DB_KEY, JSON.stringify(portfolios));
        }

        function deleteLocalPortfolio(id) {
            let portfolios = getLocalPortfolios();
            portfolios = portfolios.filter(p => p.id !== id);
            localStorage.setItem(DB_KEY, JSON.stringify(portfolios));
        }

        async function fetchPortfolios() {
            try {
                const portfolios = getLocalPortfolios().sort((a,b) => b.id - a.id);
                const list = document.getElementById('portfolioList');
                if (portfolios.length > 0) {
                    list.innerHTML = portfolios.map(p => `
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

        async function loadPortfolioData(csvContent) {
            closePortfolioModal();
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
                
                document.getElementById('assetRows').innerHTML = '';
                
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
                deleteLocalPortfolio(pid);
                fetchPortfolios();
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
                saveLocalPortfolio(payload);
                alert('저장되었습니다!');
            } catch(e) {
                alert('저장 실패: ' + e.message);
            }
        }
"""

text = re.sub(r'async function fetchPortfolios\(\).*?async function savePortfolioToDB\(\).*?\}', new_js, text, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
