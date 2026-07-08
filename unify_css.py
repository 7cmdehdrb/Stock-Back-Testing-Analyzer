import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Remove ALL <style> blocks
html_without_style = re.sub(r'<style>.*?</style>', '', html, flags=re.DOTALL)

# 2. Build the unified, highly optimized CSS
optimized_css = """<style>
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
            padding: 16px; /* Reduced from 20px for desktop */
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            color: #1e293b;
            margin-bottom: 24px;
            font-size: 2em;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .card {
            background: #ffffff;
            border-radius: 12px;
            padding: 24px; /* Reduced from 30px */
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
            margin-bottom: 16px;
        }

        label {
            display: block;
            margin-bottom: 6px;
            font-weight: 600;
            color: #475569;
            font-size: 13px;
        }

        /* -------------------------------------------------------------
           Inputs, Selects, Buttons unified heights and paddings
        ------------------------------------------------------------- */
        input[type="file"],
        input[type="date"],
        input[type="text"],
        input[type="number"],
        select {
            width: 100%;
            padding: 10px 12px;
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
            background: #2563eb;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
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
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
            border-left: 4px solid #ef4444;
            display: none;
            font-weight: 500;
        }

        .results {
            display: none;
        }

        /* -------------------------------------------------------------
           Table Layout
        ------------------------------------------------------------- */
        .input-table-container {
            margin-top: 12px;
            overflow-x: auto;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 4px; /* Slight inner padding for aesthetics */
            background: #f8fafc;
        }

        .input-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 4px;
        }

        .input-table th {
            background: #f1f5f9;
            padding: 10px 8px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
            font-weight: 600;
            font-size: 12px;
            color: #475569;
            text-transform: uppercase;
        }

        .input-table td {
            padding: 6px 4px; /* Minimized padding inside cells */
            border-bottom: 1px solid #f1f5f9;
        }

        .input-table tr:last-child td {
            border-bottom: none;
        }

        /* Unify inputs and buttons inside table */
        .input-table input[type="text"],
        .input-table input[type="number"],
        .input-table select,
        .country-toggle,
        .delete-row-btn {
            width: 100%;
            height: 38px; /* Strict uniform height */
            padding: 0 10px; /* Uniform horizontal padding */
            font-size: 14px;
            border-radius: 6px;
            border: 1px solid #cbd5e1;
            background-color: #ffffff;
            box-sizing: border-box;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
        }
        
        /* Specific overrides for buttons inside table */
        .country-toggle {
            cursor: pointer;
            font-weight: 600;
            border: 1px solid transparent; /* Replaces default border */
        }
        
        .delete-row-btn {
            background: #ef4444;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.2s;
        }
        .delete-row-btn:hover { background: #dc2626; }

        /* Action Buttons Container (Add Row / DCA) */
        .action-buttons-container {
            display: flex;
            gap: 10px;
            margin-top: 12px; /* Margin from table */
        }

        .add-row-btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0 16px;
            height: 42px; /* Distinct height from table rows but consistent across buttons */
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: all 0.2s ease;
            flex: 1;
        }
        .add-row-btn:hover { background: #2563eb; }

        .cash-inputs-grid {
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 12px;
        }

        .input-mode-toggle {
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
        }

        .mode-btn {
            flex: 1;
            padding: 10px;
            border: 2px solid #e2e8f0;
            background: #f8fafc;
            color: #64748b;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s ease;
        }

        .mode-btn.active {
            background: #eff6ff;
            color: #2563eb;
            border-color: #2563eb;
        }

        /* -------------------------------------------------------------
           Mobile Responsiveness (Crucial for space optimization)
        ------------------------------------------------------------- */
        @media (max-width: 768px) {
            body {
                padding: 10px; /* Minimized body padding */
            }
            .card {
                padding: 16px; /* Minimized card padding */
            }
            .navbar-content {
                padding: 12px 16px;
            }
        }

        @media (max-width: 480px) {
            body {
                padding: 0; /* No body padding on very small screens */
            }
            .card {
                padding: 12px;
                border-radius: 0; /* Remove border radius to maximize edge-to-edge */
                border-left: none;
                border-right: none;
            }
            .input-table th {
                padding: 8px 4px;
                font-size: 11px;
            }
            .input-table td {
                padding: 4px 2px;
            }
            
            /* Extremely compact table inputs for small screens */
            .input-table input[type="text"],
            .input-table input[type="number"],
            .country-toggle,
            .delete-row-btn {
                height: 34px; 
                padding: 0 4px;
                font-size: 12px;
            }

            .action-buttons-container {
                flex-direction: column !important;
            }
            .add-row-btn {
                height: 44px; /* Larger tap target on mobile */
            }
            .cash-inputs-grid {
                grid-template-columns: 1fr;
            }
            .input-mode-toggle {
                flex-direction: column !important;
            }
        }

        /* -------------------------------------------------------------
           Summary & Metrics
        ------------------------------------------------------------- */
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }

        .summary-item {
            background: #f8fafc;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #e2e8f0;
        }

        .summary-label {
            font-size: 11px;
            color: #64748b;
            margin-bottom: 6px;
            font-weight: 600;
        }

        .summary-value {
            font-size: 24px;
            font-weight: 700;
            color: #0f172a;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .metric-card {
            padding: 20px;
            border-radius: 12px;
            color: white;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .metric-label {
            font-size: 12px;
            opacity: 0.9;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .metric-value {
            font-size: 30px;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .chart-container {
            margin-top: 20px;
            height: 350px;
            background: #ffffff;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }

        .helper-text { font-size: 12px; color: #64748b; margin-top: 6px; }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }

        /* 네비게이션 바 스타일 */
        .navbar {
            background: #1e293b; 
            padding: 0; margin: 0;
        }
        .navbar-content {
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 24px; flex-wrap: wrap; gap: 12px;
        }
        .navbar-title { color: white; font-size: 20px; font-weight: 700; text-decoration: none; }
        .navbar-links { display: flex; gap: 8px; flex-wrap: wrap; }
        .navbar-link { color: #cbd5e1; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-weight: 600; font-size: 13px; }
        .navbar-link.active { color: white; background: #2563eb; }

        /* Toast Notification */
        #toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px; }
        .toast { min-width: 250px; background: white; padding: 12px 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 10px; border-left: 4px solid #3b82f6; opacity: 0; transform: translateX(100%); transition: all 0.3s; }
        .toast.show { opacity: 1; transform: translateX(0); }
        .toast.error { border-left-color: #ef4444; }
        .toast.success { border-left-color: #10b981; }

        /* Custom Modal */
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(4px); z-index: 10000; display: none; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.3s ease; }
        .modal-overlay.show { display: flex; opacity: 1; }
        .modal-content { background: white; padding: 24px; border-radius: 16px; max-width: 350px; width: 90%; text-align: center; }
        .modal-icon { font-size: 40px; margin-bottom: 12px; }
        .modal-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
        .modal-message { font-size: 13px; color: #64748b; margin-bottom: 20px; }
        .modal-actions { display: flex; gap: 10px; }
        .modal-btn { flex: 1; padding: 10px; border-radius: 8px; font-weight: 600; cursor: pointer; border: none; font-size: 13px; }
        .modal-btn-cancel { background: #f1f5f9; color: #475569; }
        .modal-btn-confirm { background: #ef4444; color: white; }
</style>"""

html_new = html_without_style.replace('<head>', '<head>\n' + optimized_css, 1)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_new)
print('Unified and highly optimized CSS injected successfully.')
