import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. NEW CSS STYLE BLOCK
new_style = '''<style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f8f9fa; /* Clean light gray */
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            color: #1e293b;
            margin-bottom: 30px;
            font-size: 2.2em;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .card {
            background: #ffffff;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            margin-bottom: 24px;
            border: 1px solid #e2e8f0;
        }

        /* 네비게이션 바 바로 다음의 카드는 상단 둥근 모서리 제거 */
        #analysisFormCard {
            border-radius: 0 0 12px 12px;
            margin-top: 0;
            border-top: none;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #475569;
            font-size: 14px;
        }

        input[type="file"],
        input[type="date"],
        input[type="text"],
        input[type="number"],
        select {
            width: 100%;
            padding: 12px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.2s ease;
            background-color: #ffffff;
            color: #1e293b;
        }

        input:focus,
        select:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }

        .btn {
            background: #2563eb; /* Modern Indigo */
            color: white;
            padding: 14px 28px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
        }

        .btn:hover {
            background: #1d4ed8;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);
        }

        .btn:active {
            transform: translateY(0);
            box-shadow: 0 1px 2px rgba(37, 99, 235, 0.2);
        }

        .btn:disabled {
            background: #94a3b8;
            box-shadow: none;
            cursor: not-allowed;
            transform: none;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #2563eb;
            font-weight: 600;
        }

        .spinner {
            border: 3px solid #e2e8f0;
            border-top: 3px solid #2563eb;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error {
            background: #fef2f2;
            color: #b91c1c;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #ef4444;
            display: none;
            font-weight: 500;
        }

        .results {
            display: none;
        }

        /* 수동 입력 테이블 스타일 */
        .input-table-container {
            margin-top: 20px;
            overflow-x: auto;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }

        .input-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }

        .input-table th {
            background: #f8fafc;
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
            font-weight: 600;
            font-size: 13px;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .input-table td {
            padding: 12px 16px;
            border-bottom: 1px solid #f1f5f9;
        }

        .input-table tr:last-child td {
            border-bottom: none;
        }

        .input-table input[type="text"],
        .input-table input[type="number"],
        .input-table select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 14px;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.02);
        }

        .input-table input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
            accent-color: #2563eb;
        }

        .delete-row-btn {
            background: #ef4444;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s ease;
            width: 100%;
        }

        .delete-row-btn:hover {
            background: #dc2626;
        }

        /* 모바일 반응형 - 직접 입력 테이블 */
        @media (max-width: 768px) {
            .input-table th, .input-table td {
                padding: 10px 8px;
                font-size: 12px;
            }
            .input-table input[type="text"],
            .input-table input[type="number"],
            .input-table select {
                padding: 8px;
                font-size: 13px;
            }
        }

        @media (max-width: 480px) {
            .input-table th, .input-table td {
                padding: 8px 4px;
                font-size: 11px;
            }
            .input-table input[type="text"],
            .input-table input[type="number"],
            .input-table select {
                padding: 6px;
                font-size: 12px;
                min-width: 50px;
            }
            .delete-row-btn {
                padding: 6px 8px;
                font-size: 10px;
            }
        }

        .add-row-btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }

        .add-row-btn:hover {
            background: #2563eb;
        }

        .input-mode-toggle {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
        }

        .mode-btn {
            flex: 1;
            padding: 12px;
            border: 2px solid #e2e8f0;
            background: #f8fafc;
            color: #64748b;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .mode-btn.active {
            background: #eff6ff;
            color: #2563eb;
            border-color: #2563eb;
        }

        .mode-btn:hover:not(.active) {
            background: #f1f5f9;
            color: #475569;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }

        .summary-item {
            background: #f8fafc;
            padding: 24px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #e2e8f0;
            transition: transform 0.2s ease;
        }
        
        .summary-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }

        .summary-label {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 8px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .summary-value {
            font-size: 28px;
            font-weight: 700;
            color: #0f172a;
            letter-spacing: -0.5px;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }

        .metric-card {
            padding: 24px;
            border-radius: 12px;
            color: white;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease;
            position: relative;
            overflow: hidden;
        }
        
        .metric-card::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0) 100%);
            pointer-events: none;
        }

        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }

        .metric-label {
            font-size: 13px;
            opacity: 0.9;
            margin-bottom: 12px;
            font-weight: 600;
            color: rgba(255,255,255,0.9);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .metric-value {
            font-size: 36px;
            font-weight: 700;
            color: white !important; /* Force white text for better contrast */
            margin-bottom: 8px;
            letter-spacing: -1px;
        }

        .metric-description {
            font-size: 12px;
            opacity: 0.85;
            color: rgba(255,255,255,0.8) !important; /* Adjust description color */
            line-height: 1.4;
        }

        .chart-container {
            margin-top: 24px;
            position: relative;
            height: 400px;
            background: #ffffff;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }

        .helper-text {
            font-size: 12px;
            color: #64748b;
            margin-top: 6px;
        }

        .positive { color: #10b981; }
        .negative { color: #ef4444; }

        /* 정렬 가능한 테이블 헤더 */
        .sortable-header {
            cursor: pointer;
            user-select: none;
            position: relative;
            padding-right: 20px !important;
        }
        .sortable-header:hover { background: #f1f5f9; }
        .sortable-header::after {
            content: '⇅';
            position: absolute;
            right: 8px;
            opacity: 0.3;
            font-size: 14px;
        }
        .sortable-header.sort-asc::after {
            content: '↑';
            opacity: 1;
            color: #2563eb;
        }
        .sortable-header.sort-desc::after {
            content: '↓';
            opacity: 1;
            color: #2563eb;
        }

        /* 네비게이션 바 스타일 */
        .navbar {
            background: #1e293b; /* Dark slate */
            padding: 0;
            margin: 0;
            border-radius: 12px 12px 0 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .navbar-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 32px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .navbar-title {
            color: white;
            font-size: 22px;
            font-weight: 700;
            text-decoration: none;
            cursor: pointer;
            transition: opacity 0.2s;
            letter-spacing: -0.5px;
        }

        .navbar-title:hover { opacity: 0.9; }

        .navbar-links {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .navbar-link {
            color: #cbd5e1;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s ease;
            white-space: nowrap;
        }

        .navbar-link:hover {
            color: white;
            background: rgba(255, 255, 255, 0.1);
        }

        .navbar-link.active {
            color: white;
            background: #2563eb;
        }

        /* Toast Notification */
        #toast-container {
            position: fixed;
            bottom: 32px;
            right: 32px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .toast {
            min-width: 280px;
            background: white;
            color: #1e293b;
            padding: 16px 24px;
            border-radius: 10px;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
            border-left: 4px solid #3b82f6;
            opacity: 0;
            transform: translateX(100%) scale(0.95);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        .toast.show {
            opacity: 1;
            transform: translateX(0) scale(1);
        }
        .toast.error { border-left-color: #ef4444; }
        .toast.success { border-left-color: #10b981; }

        /* Custom Modal */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(4px);
            z-index: 10000;
            display: none;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .modal-overlay.show {
            display: flex;
            opacity: 1;
        }
        .modal-content {
            background: white;
            padding: 32px;
            border-radius: 16px;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            transform: translateY(20px);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            text-align: center;
        }
        .modal-overlay.show .modal-content {
            transform: translateY(0);
        }
        .modal-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        .modal-title {
            font-size: 20px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 12px;
        }
        .modal-message {
            font-size: 14px;
            color: #64748b;
            margin-bottom: 24px;
            line-height: 1.5;
        }
        .modal-actions {
            display: flex;
            gap: 12px;
        }
        .modal-btn {
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            font-size: 14px;
            transition: all 0.2s ease;
        }
        .modal-btn-cancel {
            background: #f1f5f9;
            color: #475569;
        }
        .modal-btn-cancel:hover {
            background: #e2e8f0;
        }
        .modal-btn-confirm {
            background: #ef4444;
            color: white;
        }
        .modal-btn-confirm:hover {
            background: #dc2626;
        }

    </style>'''

html = re.sub(r'<style>.*?</style>', new_style, html, flags=re.DOTALL)


# 2. Modify Table Widths
html = html.replace('<th style="width: 30%;">티커</th>', '<th style="width: 35%;">티커</th>')
html = html.replace('<th style="width: 25%;">보유수량</th>', '<th style="width: 35%;">보유수량</th>')
html = html.replace('<th style="width: 20%;">국가</th>', '<th style="width: 20%;">국가</th>')
html = html.replace('<th style="width: 25%;">삭제</th>', '<th style="width: 60px;">삭제</th>')


# 3. Add Custom Modal HTML before closing body tag
modal_html = '''
    <!-- 커스텀 삭제 모달 -->
    <div id="deleteModal" class="modal-overlay">
        <div class="modal-content">
            <div class="modal-icon">🗑️</div>
            <div class="modal-title">포트폴리오 삭제</div>
            <div class="modal-message">정말 이 포트폴리오를 삭제하시겠습니까?<br>삭제된 데이터는 복구할 수 없습니다.</div>
            <div class="modal-actions">
                <button class="modal-btn modal-btn-cancel" onclick="closeDeleteModal()">취소</button>
                <button class="modal-btn modal-btn-confirm" id="confirmDeleteBtn">삭제하기</button>
            </div>
        </div>
    </div>
'''
html = html.replace('</body>', modal_html + '\n</body>')


# 4. Modify deletePortfolio JS and add closeDeleteModal
old_delete_func = '''        async function deletePortfolio(pid) {
            if (!confirm('정말 삭제하시겠습니까?')) return;
            try {
                deleteLocalPortfolio(pid);
                fetchPortfolios();
            } catch (e) {
                showToast('오류 발생', 'error');
            }
        }'''

new_delete_func = '''        let portfolioToDelete = null;

        function closeDeleteModal() {
            const modal = document.getElementById('deleteModal');
            modal.classList.remove('show');
            setTimeout(() => { modal.style.display = 'none'; }, 300);
            portfolioToDelete = null;
        }

        async function deletePortfolio(pid) {
            portfolioToDelete = pid;
            const modal = document.getElementById('deleteModal');
            modal.style.display = 'flex';
            // 약간의 딜레이를 주어 애니메이션이 작동하게 함
            setTimeout(() => { modal.classList.add('show'); }, 10);
        }

        document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
            if (portfolioToDelete) {
                try {
                    deleteLocalPortfolio(portfolioToDelete);
                    fetchPortfolios();
                    showToast('포트폴리오가 삭제되었습니다.', 'success');
                } catch (e) {
                    showToast('오류 발생', 'error');
                }
                closeDeleteModal();
            }
        });'''
html = html.replace(old_delete_func, new_delete_func)


# 5. Remove Volatility card and keep MDD only (Metrics Grid)
# Current has Volatility, then MDD. 
old_volatility = '''                <div class="metric-card" style="background: ${getGradientColor(metrics.volatility, metrics.benchmark_volatility, 'lower')};">
                    <div class="metric-label">변동성 (Volatility)</div>
                    <div class="metric-value" style="color: #333;">${metrics.volatility}%</div>
                    <div class="metric-description" style="font-size: 11px; color: #444;">
                        벤치마크: ${metrics.benchmark_volatility}%<br>
                        연간 표준편차. 낮을수록 안정적
                    </div>
                </div>'''
html = html.replace(old_volatility, '') # Just remove it entirely


# 6. Adjust getGradientColor and getTextColor logic for new theme
# Since the new metrics-card uses white text, we should adjust the getGradientColor to return solid colors matching the theme.
# Good: Emerald (#10b981), Bad: Rose (#f43f5e), Neutral: Indigo (#6366f1) or Blue (#3b82f6)
old_gradient_func = '''            function getGradientColor(value, benchmarkValue, betterCondition = 'higher') {
                const diff = value - benchmarkValue;
                const ratio = benchmarkValue !== 0 ? diff / Math.abs(benchmarkValue) : diff;

                // 최대 강도 제한 (예: 차이가 20% 이상일 때 최대 색상)
                const intensity = Math.min(Math.max(ratio * 5, -1), 1);

                let isBetter = false;
                if (betterCondition === 'higher') {
                    isBetter = diff >= 0;
                } else if (betterCondition === 'lower') {
                    isBetter = diff <= 0;
                }

                if (isBetter) {
                    // 초록색 (좋음) - 연한 초록 -> 진한 초록
                    const alpha = Math.abs(intensity);
                    const r = Math.floor(200 - alpha * 100); // 200 -> 100
                    const g = Math.floor(230 - alpha * 50);  // 230 -> 180
                    const b = Math.floor(200 - alpha * 100); // 200 -> 100
                    return `rgb(${r}, ${g}, ${b})`;
                } else {
                    // 빨간색 (나쁨) - 연한 빨강 -> 진한 빨강
                    const alpha = Math.abs(intensity);
                    const r = Math.floor(230 - alpha * 50);  // 230 -> 180
                    const g = Math.floor(200 - alpha * 100); // 200 -> 100
                    const b = Math.floor(200 - alpha * 100); // 200 -> 100
                    return `rgb(${r}, ${g}, ${b})`;
                }
            }'''

new_gradient_func = '''            function getGradientColor(value, benchmarkValue, betterCondition = 'higher') {
                const diff = value - benchmarkValue;
                let isBetter = false;
                if (betterCondition === 'higher') {
                    isBetter = diff >= 0;
                } else if (betterCondition === 'lower') {
                    isBetter = diff <= 0;
                }

                // Return modern solid colors instead of dynamic gradients for a cleaner premium look
                if (isBetter) {
                    return '#10b981'; // Emerald
                } else {
                    return '#f43f5e'; // Rose
                }
            }'''
html = html.replace(old_gradient_func, new_gradient_func)

# And remove getTextColor since it's hardcoded to white now in CSS.
# Also update the HTML metric cards that use getTextColor to just not use it.
html = re.sub(r'style="color: \$\{getTextColor\([^)]+\)\};"', '', html)
html = html.replace('style="color: #333;"', '')


with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("UI update script generated and applied.")
