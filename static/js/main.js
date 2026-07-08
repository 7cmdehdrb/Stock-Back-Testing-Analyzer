const form = document.getElementById('analysisForm');
        const loading = document.getElementById('loading');
        const error = document.getElementById('error');
        const results = document.getElementById('results');
        const analyzeBtn = document.getElementById('analyzeBtn');

        // 날짜 기본값 설정 (오늘 날짜와 3년 전 1월 1일)
        const today = new Date();
        const twoYearsAgo = new Date(today.getFullYear() - 2, today.getMonth(), today.getDate()); // 0 = January, 1 = 1일
        const minDate = new Date(2000, 0, 1); // 2000년 1월 1일

        // 로컬 날짜를 YYYY-MM-DD 형식으로 변환 (UTC 문제 방지)
        function formatLocalDate(date) {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }

        console.log('Today:', formatLocalDate(today));
        console.log('Two years ago:', formatLocalDate(twoYearsAgo));

        document.getElementById('startDate').min = formatLocalDate(minDate);
        document.getElementById('startDate').max = formatLocalDate(today);
        document.getElementById('startDate').value = formatLocalDate(twoYearsAgo);

        // 기본 벤치마크 설정
        document.getElementById('benchmarkTicker').value = 'SPY';

        // 벤치마크 선택 변경 이벤트 리스너
        document.getElementById('benchmarkTicker').addEventListener('change', function () {
            const customBenchmarkGroup = document.getElementById('customBenchmarkGroup');
            const customBenchmarkTicker = document.getElementById('customBenchmarkTicker');

            if (this.value === 'CUSTOM') {
                customBenchmarkGroup.style.display = 'block';
                customBenchmarkTicker.required = true;
            } else {
                customBenchmarkGroup.style.display = 'none';
                customBenchmarkTicker.required = false;
                customBenchmarkTicker.value = ''; // 값 초기화
            }
        });

        // 입력 모드 버튼 이벤트 리스너
        document.getElementById('csvModeBtn').addEventListener('click', function () {
            openPortfolioModal();
        });
        document.getElementById('manualModeBtn').addEventListener('click', function () {
            switchInputMode('manual');
        });

        // CSV 파일 선택 시 자동 파싱
        document.getElementById('csvFile').addEventListener('change', async function (e) {
            const file = e.target.files[0];
            if (!file) return;

            console.log('📁 CSV file selected:', file.name);

            // 로딩 표시
            const csvSection = document.getElementById('csvUploadSection');
            const helperText = csvSection.querySelector('.helper-text');
            const originalHelperText = helperText.innerHTML;
            helperText.innerHTML = '<span style="color: #667eea;">⏳ CSV 파일을 분석하는 중...</span>';

            try {
                const formData = new FormData();
                formData.append('csv_file', file);

                const response = await fetch('/parse-csv', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'CSV 파일 파싱 실패');
                }

                console.log('✅ CSV parsed successfully:', data);

                // 수동 입력 모드로 전환
                switchInputMode('manual');

                // 기존 행 모두 삭제
                const tbody = document.getElementById('manualInputTableBody');
                tbody.innerHTML = '';

                // CSV 데이터로 행 채우기
                data.portfolio.forEach(item => {
                    const newRow = document.createElement('tr');
                    newRow.className = 'input-row';
                    newRow.innerHTML = `
                        <td><input type="text" class="ticker-input" placeholder="예: AAPL" value="${item.ticker}"></td>
                        <td><input type="number" class="quantity-input" placeholder="보유 주식 수 (예: 10)" min="0" step="any" value="${item.quantity}"></td>
                        <td>
                            <select class="country-input">
                                <option value="미국" ${item.country === '미국' ? 'selected' : ''}>미국</option>
                                <option value="한국" ${item.country === '한국' ? 'selected' : ''}>한국</option>
                            </select>
                        </td>
                        <td><button type="button" class="delete-row-btn" onclick="deleteRow(this)">삭제</button></td>
                    `;
                    tbody.appendChild(newRow);
                });

                // 최소 1개 행 보장
                if (tbody.children.length === 0) {
                    addRow();
                }

                // 현금 데이터 채우기
                if (data.cash) {
                    document.getElementById('cashKRW').value = data.cash.KRW || 0;
                    document.getElementById('cashUSD').value = data.cash.USD || 0;
                }

                // 성공 메시지
                helperText.innerHTML = '<span style="color: #22c55e;">✅ CSV 파일이 성공적으로 불러와졌습니다!</span>';
                setTimeout(() => {
                    helperText.innerHTML = originalHelperText;
                }, 3000);

                // 파일 입력 초기화
                e.target.value = '';

            } catch (error) {
                console.error('❌ Error parsing CSV:', error);
                helperText.innerHTML = `<span style="color: #ef4444;">❌ ${error.message}</span>`;
                setTimeout(() => {
                    helperText.innerHTML = originalHelperText;
                }, 5000);
            }
        });

        // 입력 모드 전역 변수 (기본값: manual, 항상 manual 모드 사용)
        let currentInputMode = 'manual';

        // 입력 모드 전환 (CSV 모드는 파일 선택 트리거로만 사용)
        function switchInputMode(mode) {
            console.log('Switching to mode:', mode);

            if (mode === 'csv') {
                // CSV 버튼 클릭 시 파일 선택 다이얼로그 열기
                document.getElementById('csvFile').click();
                // 항상 manual 모드 유지
                currentInputMode = 'manual';
            } else {
                currentInputMode = 'manual';
            }

            // 항상 manual 섹션만 표시
            document.getElementById('csvUploadSection').style.display = 'none';
            document.getElementById('manualInputSection').style.display = 'block';
            document.getElementById('csvFile').required = false;

            // 버튼 상태 업데이트
            document.getElementById('manualModeBtn').classList.add('active');
            document.getElementById('csvModeBtn').classList.remove('active');
        }

        // 행 추가
                function toggleCountry(btn) {
            if (btn.value === '미국') {
                btn.value = '한국';
                btn.innerText = '한국';
                btn.style.background = '#e2e8f0';
                btn.style.color = '#334155';
            } else {
                btn.value = '미국';
                btn.innerText = '미국';
                btn.style.background = '#eff6ff';
                btn.style.color = '#2563eb';
            }
        }

        function addRow(ticker = '', quantity = '', country = '미국') {
            const tbody = document.getElementById('manualInputTableBody');
            const newRow = document.createElement('tr');
            newRow.className = 'input-row';
            newRow.innerHTML = `
                <td><input type="text" class="ticker-input" placeholder="예: AAPL" value="${ticker}"></td>
                <td><input type="number" class="quantity-input" placeholder="보유 주식 수 (예: 10)" min="0" step="any" value="${quantity}"></td>
                <td>
                    <button type="button" class="country-input country-toggle" value="${country}" onclick="toggleCountry(this)" style="background: ${country === '미국' ? '#eff6ff' : '#e2e8f0'}; color: ${country === '미국' ? '#2563eb' : '#334155'}; font-weight: 600; cursor: pointer; padding: 8px 12px; font-size: 14px; height: 38px; border: 1px solid transparent; border-radius: 6px; width: 100%; transition: all 0.2s;">${country}</button>
                </td>
                <td><button type="button" class="delete-row-btn" onclick="deleteRow(this)">삭제</button></td>
            `;
            tbody.appendChild(newRow);
        }

        // 행 삭제
        function deleteRow(button) {
            const tbody = document.getElementById('manualInputTableBody');
            const rows = tbody.getElementsByClassName('input-row');

            // 최소 1개 행은 유지
            if (rows.length > 1) {
                button.closest('tr').remove();
            } else {
                showToast('최소 1개의 종목은 입력해야 합니다.');
            }
        }

        // 적립식 투자 행 추가
        function addDcaRow(ticker = '', quantity = '', country = '미국', frequency = 'monthly') {
            const dcaSection = document.getElementById('dcaSection');
            const tbody = document.getElementById('dcaInputTableBody');

            // 섹션이 숨겨져 있으면 표시
            if (dcaSection.style.display === 'none') {
                dcaSection.style.display = 'block';
            }

            const newRow = document.createElement('tr');
            newRow.className = 'dca-row';
            newRow.innerHTML = `
                <td><input type="text" class="dca-ticker-input" placeholder="예: AAPL" value="${ticker}"></td>
                <td><input type="number" class="dca-quantity-input" placeholder="금액" min="0.001" step="any" value="${quantity}"></td>
                <td>
                    <button type="button" class="dca-country-input country-toggle" value="${country}" onclick="toggleCountry(this)" style="background: ${country === '미국' ? '#eff6ff' : '#e2e8f0'}; color: ${country === '미국' ? '#2563eb' : '#334155'}; font-weight: 600; cursor: pointer; padding: 8px 12px; font-size: 14px; height: 38px; border: 1px solid transparent; border-radius: 6px; width: 100%; transition: all 0.2s;">${country}</button>
                </td>
                <td>
                    <select class="dca-frequency-input">
                        <option value="weekly" ${frequency === 'weekly' ? 'selected' : ''}>매주</option>
                        <option value="monthly" ${frequency === 'monthly' ? 'selected' : ''}>매월</option>
                        <option value="quarterly" ${frequency === 'quarterly' ? 'selected' : ''}>매분기</option>
                    </select>
                </td>
                <td><button type="button" class="delete-row-btn" onclick="deleteDcaRow(this)">삭제</button></td>
            `;
            tbody.appendChild(newRow);
        }

        // 적립식 투자 행 삭제
        function deleteDcaRow(button) {
            const tbody = document.getElementById('dcaInputTableBody');
            const dcaSection = document.getElementById('dcaSection');

            button.closest('tr').remove();

            // 모든 행이 삭제되면 섹션 숨기기
            const rows = tbody.getElementsByClassName('dca-row');
            if (rows.length === 0) {
                dcaSection.style.display = 'none';
            }
        }

        // 수동 입력 데이터를 CSV 형식으로 변환
        function convertManualInputToCSV() {
            const rows = document.querySelectorAll('#manualInputTableBody .input-row');
            const csvLines = ['티커,보유량,국가,분류'];

            let hasData = false;
            rows.forEach(row => {
                const ticker = row.querySelector('.ticker-input').value.trim();
                const quantity = row.querySelector('.quantity-input').value.trim();
                const country = row.querySelector('.country-input').value;

                if (ticker && quantity) {
                    hasData = true;
                    const assetClass = '주식';  // 모든 행은 주식으로 처리
                    csvLines.push(`${ticker},${quantity},${country},${assetClass}`);
                }
            });

            // 현금 추가
            const cashKRW = parseFloat(document.getElementById('cashKRW').value) || 0;
            const cashUSD = parseFloat(document.getElementById('cashUSD').value) || 0;

            if (cashKRW > 0) {
                hasData = true;
                csvLines.push(`KRW,${cashKRW},한국,현금`);
            }

            if (cashUSD > 0) {
                hasData = true;
                csvLines.push(`USD,${cashUSD},미국,현금`);
            }

            if (!hasData) {
                return null;
            }

            return csvLines.join('\n');
        }

        // 캐시 통계 로드
        async function loadCacheStats() {
            try {
                const response = await fetch('/api/cache-stats');
                if (response.ok) {
                    const data = await response.json();
                    const statsElement = document.getElementById('cacheStats');
                    statsElement.textContent = `${data.stock_prices}개 주가, ${data.exchange_rates}개 환율`;
                } else {
                    document.getElementById('cacheStats').textContent = '데이터 없음';
                }
            } catch (err) {
                console.error('캐시 통계 로드 오류:', err);
                document.getElementById('cacheStats').textContent = '오류 발생';
            }
        }

        // 페이지 로드 시 캐시 통계 가져오기
        loadCacheStats();

        // 저장된 포트폴리오 보기 처리
        window.addEventListener('DOMContentLoaded', function () {
            const urlParams = new URLSearchParams(window.location.search);
            console.log('URL params:', urlParams.toString());
            console.log('view param:', urlParams.get('view'));

            if (urlParams.get('view') === 'portfolio') {
                const portfolioData = sessionStorage.getItem('portfolioData');
                console.log('SessionStorage data:', portfolioData);

                if (portfolioData) {
                    try {
                        const data = JSON.parse(portfolioData);
                        console.log('Parsed data:', data);

                        // 폼 섹션 숨기기
                        const formCard = document.getElementById('analysisFormCard');
                        if (formCard) {
                            formCard.style.display = 'none';
                        }

                        // 포트폴리오 이름 및 소유자 표시
                        const portfolioNameSection = document.getElementById('portfolioNameSection');
                        const portfolioNameDisplay = document.getElementById('portfolioNameDisplay');
                        const portfolioOwnerDisplay = document.getElementById('portfolioOwnerDisplay');
                        const privacyNotice = document.getElementById('privacyNotice');

                        if (portfolioNameSection && portfolioNameDisplay) {
                            portfolioNameDisplay.textContent = data.name;
                            if (portfolioOwnerDisplay && data.owner_nickname) {
                                portfolioOwnerDisplay.textContent = data.owner_nickname;
                            } else if (portfolioOwnerDisplay) {
                                portfolioOwnerDisplay.textContent = '익명';
                            }

                            // 프라이버시 알림 설정
                            if (privacyNotice) {
                                if (data.is_owner) {
                                    // 소유자인 경우
                                    privacyNotice.style.background = '#d1ecf1';
                                    privacyNotice.style.color = '#0c5460';
                                    privacyNotice.innerHTML = '✅ <strong>내 포트폴리오:</strong> 모든 정보가 표시됩니다.';
                                } else {
                                    // 다른 사용자의 포트폴리오인 경우
                                    privacyNotice.style.background = '#fff3cd';
                                    privacyNotice.style.color = '#856404';
                                    privacyNotice.innerHTML = 'ℹ️ <strong>알림:</strong> 다른 사용자의 포트폴리오를 조회할 때는 프라이버시 보호를 위해 자산 가치가 표시되지 않습니다.';
                                }
                            }

                            portfolioNameSection.style.display = 'block';
                        }

                        // 결과 표시 - data에서 직접 필요한 필드 추출
                        // is_owner가 true면 정상 표시, false면 프라이버시 모드
                        displayResults({
                            metrics: data.metrics,
                            summary: data.summary,
                            holdings_table: data.holdings_table,
                            allocation_data: data.allocation_data,
                            chart_data: data.chart_data
                        }, !data.is_owner); // true = 프라이버시 모드 (다른 사용자), false = 정상 표시 (소유자)

                        // 결과 섹션 표시
                        const results = document.getElementById('results');
                        if (results) {
                            results.style.display = 'block';
                        }

                        // sessionStorage 정리
                        sessionStorage.removeItem('portfolioData');

                        // URL에서 view 파라미터 제거 (브라우저 히스토리 유지)
                        window.history.replaceState({}, document.title, window.location.pathname);

                    } catch (err) {
                        console.error('포트폴리오 데이터 로드 오류:', err);
                        console.error('Error stack:', err.stack);
                        showToast('포트폴리오 데이터를 불러오는 중 오류가 발생했습니다.');
                    }
                } else {
                    console.log('No portfolio data in sessionStorage');
                }
            }
        });

        let chart = null;
        let initialAllocationChart = null;
        let currentAllocationChart = null;

        // 분석 결과를 저장하기 위한 전역 변수
        let currentAnalysisData = null;

        // 보유 종목 데이터 및 정렬 상태
        let currentHoldings = [];
        let currentCurrency = 'USD';
        let isDetailView = false;
        let currentSortColumn = null;
        let currentSortDirection = 'asc';

        // 정렬 함수
        function sortHoldings(column) {
            // 같은 컬럼을 클릭하면 방향 전환, 다른 컬럼이면 오름차순으로 시작
            if (currentSortColumn === column) {
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortColumn = column;
                currentSortDirection = 'asc';
            }

            // 정렬
            const sorted = [...currentHoldings].sort((a, b) => {
                if (column === 'ticker') {
                    // 현금은 항상 맨 아래
                    const aIsCash = a.asset_class === '현금';
                    const bIsCash = b.asset_class === '현금';

                    if (aIsCash && !bIsCash) return 1;
                    if (!aIsCash && bIsCash) return -1;

                    // 둘 다 현금이거나 둘 다 일반 자산인 경우 티커로 비교
                    const comparison = a.ticker.localeCompare(b.ticker);
                    return currentSortDirection === 'asc' ? comparison : -comparison;
                } else if (column === 'weight') {
                    const comparison = a.weight - b.weight;
                    return currentSortDirection === 'asc' ? comparison : -comparison;
                }
                return 0;
            });

            // 테이블 다시 렌더링
            renderHoldingsTable(sorted, currentCurrency, isDetailView);

            // 헤더 스타일 업데이트
            updateSortHeaders();
        }

        // 정렬 헤더 스타일 업데이트
        function updateSortHeaders() {
            // 모든 헤더에서 정렬 클래스 제거
            document.querySelectorAll('.sortable-header').forEach(th => {
                th.classList.remove('sort-asc', 'sort-desc');
            });

            // 현재 정렬 컬럼에 클래스 추가
            if (currentSortColumn === 'ticker') {
                const tickerHeader = document.querySelector('.sortable-header[onclick*="ticker"]');
                if (tickerHeader) {
                    tickerHeader.classList.add(currentSortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
                }
            } else if (currentSortColumn === 'weight') {
                const weightHeader = document.querySelector('.sortable-header[onclick*="weight"]');
                if (weightHeader) {
                    weightHeader.classList.add(currentSortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
                }
            }
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            // 항상 수동 입력 모드로 처리 (CSV는 이미 파싱되어 폼에 채워져 있음)
            let csvContent = null;
            let fileToUpload = null;

            // 수동 입력 모드: CSV 생성
            csvContent = convertManualInputToCSV();
            if (!csvContent) {
                showToast('최소 1개의 종목을 입력해주세요.');
                return;
            }
            console.log('📝 Manual input CSV:', csvContent);

            // CSV를 Blob으로 변환하여 파일처럼 처리
            const blob = new Blob([csvContent], { type: 'text/csv' });
            fileToUpload = new File([blob], 'manual_input.csv', { type: 'text/csv' });

            // UI 초기화
            error.style.display = 'none';
            error.style.backgroundColor = ''; // 배경색 초기화
            error.style.color = ''; // 글자색 초기화
            error.style.borderLeft = ''; // 테두리 초기화
            results.style.display = 'none';
            loading.style.display = 'block';
            analyzeBtn.disabled = true;

            // AI 분석 캐시 초기화 (새로운 분석 시작)
            aiAnalysisResultCache = null;

            const formData = new FormData();
            formData.append('csv_file', fileToUpload);
            formData.append('start_date', document.getElementById('startDate').value);

            // 벤치마크 처리
            const benchmarkSelect = document.getElementById('benchmarkTicker').value;
            if (benchmarkSelect === 'CUSTOM') {
                const customTicker = document.getElementById('customBenchmarkTicker').value.trim();
                if (!customTicker) {
                    showToast('벤치마크 티커를 입력해주세요.');
                    loading.style.display = 'none';
                    analyzeBtn.disabled = false;
                    return;
                }
                formData.append('benchmark_ticker', customTicker);
            } else {
                formData.append('benchmark_ticker', benchmarkSelect);
            }

            formData.append('base_currency', document.getElementById('baseCurrency').value);

            // 적립식 투자 데이터 추가
            const dcaSectionVisible = document.getElementById('dcaSection').style.display !== 'none';
            const dcaData = [];
            if (dcaSectionVisible) {
                const dcaRows = document.querySelectorAll('#dcaInputTableBody .dca-row');
                dcaRows.forEach(row => {
                const ticker = row.querySelector('.dca-ticker-input').value.trim();
                const quantity = row.querySelector('.dca-quantity-input').value.trim();
                const country = row.querySelector('.dca-country-input').value;
                const frequency = row.querySelector('.dca-frequency-input').value;

                if (ticker && quantity) {
                    dcaData.push({
                        ticker: ticker,
                        quantity: parseFloat(quantity),
                        country: country,
                        frequency: frequency
                    });
                }
                });
            }

            if (dcaData.length > 0) {
                formData.append('dca_data', JSON.stringify(dcaData));
                console.log('📈 DCA data:', dcaData);
            }

            // FormData 내용 확인 (디버깅용)
            console.log('📤 Sending data:');
            for (let [key, value] of formData.entries()) {
                if (value instanceof File) {
                    console.log(`  ${key}: ${value.name} (${value.size} bytes)`);
                } else {
                    console.log(`  ${key}: ${value}`);
                }
            }

            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || '분석 중 오류가 발생했습니다.');
                }

                console.log('✅ Analysis completed successfully');

                // 경고 메시지 표시 (일부 티커 실패)
                if (data.warning) {
                    const warningDiv = document.getElementById('error');
                    warningDiv.textContent = data.warning;
                    warningDiv.style.display = 'block';
                    warningDiv.style.backgroundColor = '#fff3cd';
                    warningDiv.style.color = '#856404';
                    warningDiv.style.borderLeft = '4px solid #ffc107';
                }

                // 분석 결과 저장 (저장 버튼용)
                // DCA가 적용된 최종 포트폴리오 CSV 사용
                let csvContentForSave;
                if (data.final_portfolio_csv) {
                    // 백엔드에서 DCA가 적용된 최종 포트폴리오를 받음
                    csvContentForSave = data.final_portfolio_csv;
                    console.log('📊 Using final portfolio CSV (with DCA applied)');
                } else {
                    // 항상 수동 입력에서 생성된 CSV 사용
                    csvContentForSave = csvContent;
                }

                currentAnalysisData = {
                    csv_content: csvContentForSave,
                    start_date: document.getElementById('startDate').value,
                    benchmark_ticker: document.getElementById('benchmarkTicker').value,
                    base_currency: document.getElementById('baseCurrency').value,
                    ...data
                };

                displayResults(data);
                results.style.display = 'block';

                // 저장 섹션 표시
                document.getElementById('saveSection').style.display = 'block';
                document.getElementById('saveMessage').style.display = 'none';

                // AI 분석 버튼 표시
                // 로그인 상태에 따라 UI 업데이트


                // 항상 CSV 내보내기 버튼 표시 (수동 입력 모드)
                } catch (err) {
                console.error('❌ Error:', err);
                error.textContent = err.message;
                error.style.display = 'block';
            } finally {
                loading.style.display = 'none';
                analyzeBtn.disabled = false;
                // 분석 후 캐시 통계 업데이트
                loadCacheStats();
            }
        });

        function displayResults(data, isDetailViewMode = false) {
            const { metrics, chart_data, summary, allocation_data, holdings_table } = data;

            // 전역 변수에 저장
            currentHoldings = holdings_table;
            currentCurrency = summary.base_currency;
            isDetailView = isDetailViewMode;
            currentSortColumn = null; // 정렬 상태 초기화
            currentSortDirection = 'asc';

            // 통화 심볼 결정
            const currencySymbol = summary.base_currency === 'USD' ? '$' : '₩';
            const currencyName = summary.base_currency === 'USD' ? 'USD' : 'KRW';

            // 자산 가치 표시 함수 (상세 뷰에서는 숨김)
            const formatValue = (value) => {
                return isDetailViewMode ? '-' : formatCurrency(value, summary.base_currency);
            };

            // 요약 정보 표시
            const summaryGrid = document.getElementById('summaryGrid');
            summaryGrid.innerHTML = `
                <div class="summary-item">
                    <div class="summary-label">보유 종목 수</div>
                    <div class="summary-value">${summary.num_holdings}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">기준 통화</div>
                    <div class="summary-value">${currencyName}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">USD/KRW 환율</div>
                    <div class="summary-value">${summary.exchange_rate.toLocaleString()}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">시작 가치 (투자자산)</div>
                    <div class="summary-value">${formatValue(summary.initial_value)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">현재 가치 (투자자산)</div>
                    <div class="summary-value">${formatValue(summary.current_value)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">현금 보유액</div>
                    <div class="summary-value">${formatValue(summary.total_cash)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">총 자산 (현금포함)</div>
                    <div class="summary-value">${formatValue(summary.current_value_with_cash)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">수익률 (투자자산)</div>
                    <div class="summary-value ${summary.total_return >= 0 ? 'positive' : 'negative'}">
                        ${summary.total_return >= 0 ? '+' : ''}${summary.total_return}%
                    </div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">수익률 (현금포함)</div>
                    <div class="summary-value ${summary.total_return_with_cash >= 0 ? 'positive' : 'negative'}">
                        ${summary.total_return_with_cash >= 0 ? '+' : ''}${summary.total_return_with_cash}%
                    </div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">연평균 수익률 (CAGR)</div>
                    <div class="summary-value ${metrics.cagr >= 0 ? 'positive' : 'negative'}">
                        ${metrics.cagr >= 0 ? '+' : ''}${metrics.cagr}%
                    </div>
                </div>
            `;

            // 도넛 차트 생성
            createAllocationCharts(allocation_data, summary.base_currency);

            // 보유 종목 테이블 렌더링 (상세 뷰에서는 평가액 숨김)
            renderHoldingsTable(holdings_table, summary.base_currency, isDetailViewMode);

            // 정렬 헤더 초기화
            updateSortHeaders();

            // 그라데이션 색상 계산 함수
            function getGradientColor(value, benchmarkValue, isBetter) {
                // value가 benchmark보다 좋을수록 초록, 나쁠수록 빨강
                // isBetter: 'higher' (높을수록 좋음) 또는 'lower' (낮을수록 좋음)
                let diff = 0;
                if (isBetter === 'higher') {
                    diff = value - benchmarkValue;
                } else {
                    diff = benchmarkValue - value;
                }

                // 차이를 퍼센트로 변환 (벤치마크 대비)
                const percentDiff = benchmarkValue !== 0 ? (diff / Math.abs(benchmarkValue)) * 100 : diff * 100;

                // -50% ~ +50% 범위를 기준으로 색상 강도 계산
                const intensity = Math.max(-1, Math.min(1, percentDiff / 50));

                if (Math.abs(intensity) < 0.05) {
                    // 거의 같으면 매우 연한 회색
                    return 'rgb(245, 245, 245)';
                } else if (intensity > 0) {
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
            }

            // 배경색에 따른 텍스트 색상 결정 함수
            function getTextColor(value, benchmarkValue, isBetter) {
                // 모든 텍스트를 어두운 회색으로 통일
                return '#333';
            }

            // 성과 지표 표시
            const metricsGrid = document.getElementById('metricsGrid');
            metricsGrid.innerHTML = `
                <div class="metric-card" style="background: ${getGradientColor(metrics.sharpe_ratio, metrics.benchmark_sharpe_ratio, 'higher')};">
                    <div class="metric-label">샤프 비율 (Sharpe Ratio)</div>
                    <div class="metric-value" >${metrics.sharpe_ratio}</div>
                    <div class="metric-description" style="font-size: 11px; color: #475569;">
                        벤치마크: ${metrics.benchmark_sharpe_ratio}<br>
                        위험 대비 수익률. 높을수록 좋음
                    </div>
                </div>
                <div class="metric-card" style="background: ${getGradientColor(metrics.sortino_ratio, metrics.benchmark_sortino_ratio, 'higher')};">
                    <div class="metric-label">소티노 비율 (Sortino Ratio)</div>
                    <div class="metric-value" >${metrics.sortino_ratio}</div>
                    <div class="metric-description" style="font-size: 11px; color: #475569;">
                        벤치마크: ${metrics.benchmark_sortino_ratio}<br>
                        하방 위험 대비 수익률. 높을수록 좋음
                    </div>
                </div>
                <div class="metric-card" style="background: ${getGradientColor(metrics.alpha, 0, 'higher')};">
                    <div class="metric-label">알파 (Alpha)</div>
                    <div class="metric-value" >
                        ${metrics.alpha >= 0 ? '+' : ''}${metrics.alpha}%
                    </div>
                    <div class="metric-description" style="font-size: 11px; color: #475569;">
                        벤치마크: 0%<br>
                        벤치마크 대비 초과 수익률
                    </div>
                </div>
                <div class="metric-card" style="background: ${getGradientColor(Math.abs(metrics.beta - 1), 0, 'lower')};">
                    <div class="metric-label">베타 (Beta)</div>
                    <div class="metric-value" >${metrics.beta}</div>
                    <div class="metric-description" style="font-size: 11px; color: #475569;">
                        벤치마크: 1.0<br>
                        시장 민감도. 1.0 = 시장과 동일
                    </div>
                </div>
                <div class="metric-card" style="background: ${getGradientColor(metrics.cagr, metrics.benchmark_annual_return, 'higher')};">
                    <div class="metric-label">연평균 수익률 (CAGR)</div>
                    <div class="metric-value" >
                        ${metrics.cagr >= 0 ? '+' : ''}${metrics.cagr}%
                    </div>
                    <div class="metric-description" style="font-size: 11px; color: #475569;">
                        벤치마크: ${metrics.benchmark_annual_return >= 0 ? '+' : ''}${metrics.benchmark_annual_return}%<br>
                        연간 복리 수익률
                    </div>
                </div>

                <div class="metric-card" style="background: ${getGradientColor(metrics.mdd, metrics.benchmark_mdd, 'higher')};">
                    <div class="metric-label">최대 낙폭 (MDD)</div>
                    <div class="metric-value" >${metrics.mdd}%</div>
                    <div class="metric-description" style="font-size: 11px; color: #475569;">
                        벤치마크: ${metrics.benchmark_mdd}%<br>
                        최고점 대비 최대 하락폭. 0에 가까울수록 방어력이 좋음
                    </div>
                </div>
            `;

            // 차트 생성
            const benchmarkName = summary.benchmark_name || summary.benchmark;
            createChart(chart_data, benchmarkName);
        }

        function createChart(chartData, benchmark) {
            const ctx = document.getElementById('performanceChart').getContext('2d');

            if (chart) {
                chart.destroy();
            }

            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.dates,
                    datasets: [
                        {
                            label: '내 포트폴리오',
                            data: chartData.portfolio_cumulative,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 3,
                            tension: 0.1,
                            fill: true,
                            pointRadius: 1,
                            pointHoverRadius: 5
                        },
                        {
                            label: `벤치마크 (${benchmark})`,
                            data: chartData.benchmark_cumulative,
                            borderColor: '#f43f5e',
                            backgroundColor: 'rgba(244, 63, 94, 0.1)',
                            borderWidth: 3,
                            tension: 0.1,
                            fill: true,
                            pointRadius: 1,
                            pointHoverRadius: 5
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function (context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    const value = context.parsed.y;
                                    const percent = ((value - 1) * 100).toFixed(2);
                                    label += `${value.toFixed(4)} (${percent >= 0 ? '+' : ''}${percent}%)`;
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            ticks: {
                                callback: function (value) {
                                    return value.toFixed(2);
                                }
                            },
                            title: {
                                display: true,
                                text: '누적 수익 (1.0 = 시작점)',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            }
                        },
                        x: {
                            ticks: {
                                maxTicksLimit: 10
                            },
                            title: {
                                display: true,
                                text: '날짜',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            }
                        }
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                }
            });
        }

        function createAllocationCharts(allocationData, baseCurrency) {
            // 색상 팔레트
            const colors = [
                '#667eea', '#764ba2', '#f093fb', '#4facfe',
                '#43e97b', '#fa709a', '#fee140', '#30cfd0',
                '#a8edea', '#fed6e3', '#c471f5', '#ffecd2'
            ];

            // 시작 시점 도넛 차트
            const initialCtx = document.getElementById('initialAllocationChart').getContext('2d');
            if (initialAllocationChart) {
                initialAllocationChart.destroy();
            }

            initialAllocationChart = new Chart(initialCtx, {
                type: 'doughnut',
                data: {
                    labels: allocationData.initial.labels,
                    datasets: [{
                        data: allocationData.initial.values,
                        backgroundColor: colors.slice(0, allocationData.initial.labels.length),
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 10,
                                font: {
                                    size: 11
                                },
                                generateLabels: function (chart) {
                                    const data = chart.data;
                                    if (data.labels.length && data.datasets.length) {
                                        const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        return data.labels.map((label, i) => {
                                            const value = data.datasets[0].data[i];
                                            const percentage = ((value / total) * 100).toFixed(1);
                                            return {
                                                text: `${label}: ${percentage}%`,
                                                fillStyle: data.datasets[0].backgroundColor[i],
                                                hidden: false,
                                                index: i
                                            };
                                        });
                                    }
                                    return [];
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${formatCurrency(value, baseCurrency)} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });

            // 현재 시점 도넛 차트
            const currentCtx = document.getElementById('currentAllocationChart').getContext('2d');
            if (currentAllocationChart) {
                currentAllocationChart.destroy();
            }

            currentAllocationChart = new Chart(currentCtx, {
                type: 'doughnut',
                data: {
                    labels: allocationData.current.labels,
                    datasets: [{
                        data: allocationData.current.values,
                        backgroundColor: colors.slice(0, allocationData.current.labels.length),
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 10,
                                font: {
                                    size: 11
                                },
                                generateLabels: function (chart) {
                                    const data = chart.data;
                                    if (data.labels.length && data.datasets.length) {
                                        const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        return data.labels.map((label, i) => {
                                            const value = data.datasets[0].data[i];
                                            const percentage = ((value / total) * 100).toFixed(1);
                                            return {
                                                text: `${label}: ${percentage}%`,
                                                fillStyle: data.datasets[0].backgroundColor[i],
                                                hidden: false,
                                                index: i
                                            };
                                        });
                                    }
                                    return [];
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${formatCurrency(value, baseCurrency)} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }

        function renderHoldingsTable(holdings, currency, isDetailView = false) {
            const tbody = document.getElementById('holdingsTableBody');

            tbody.innerHTML = holdings.map(h => `
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px;"><strong>${h.ticker}</strong></td>
                    <td style="padding: 12px;">${h.name}</td>
                    <td style="padding: 12px; text-align: right;">${isDetailView ? '-' : (h.asset_class === '현금' ? '-' : h.quantity.toLocaleString())}</td>
                    <td style="padding: 12px; text-align: right;">${isDetailView ? '-' : formatCurrency(h.current_value, currency)}</td>
                    <td style="padding: 12px; text-align: right;"><strong>${h.weight}%</strong></td>
                </tr>
            `).join('');
        }

        function formatCurrency(value, currency = 'USD') {
            if (currency === 'KRW') {
                // 한국 원화
                if (value >= 100000000) {
                    return '₩' + (value / 100000000).toFixed(2) + '억';
                } else if (value >= 10000) {
                    return '₩' + (value / 10000).toFixed(0) + '만';
                }
                return '₩' + value.toLocaleString();
            } else {
                // 미국 달러
                if (value >= 1000000) {
                    return '$' + (value / 1000000).toFixed(2) + 'M';
                } else if (value >= 1000) {
                    return '$' + (value / 1000).toFixed(1) + 'K';
                }
                return '$' + value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            }
        }

        // 포트폴리오 저장 함수
        async function savePortfolio() {
            const nameInput = document.getElementById('portfolioName');
            const name = nameInput.value.trim();
            const saveBtn = document.getElementById('saveBtn');
            const saveMessage = document.getElementById('saveMessage');

            if (!name) {
                showToast('포트폴리오 이름을 입력해주세요.');
                nameInput.focus();
                return;
            }

            if (!currentAnalysisData) {
                showToast('분석 결과가 없습니다. 먼저 분석을 실행해주세요.');
                return;
            }

            try {
                saveBtn.disabled = true;
                saveBtn.textContent = '저장 중...';

                const payload = {
                    name: name,
                    csv_content: currentAnalysisData.csv_content,
                    start_date: currentAnalysisData.start_date,
                    benchmark_ticker: currentAnalysisData.benchmark_ticker,
                    base_currency: currentAnalysisData.base_currency
                };

                saveLocalPortfolio(payload);

                // 성공 메시지
                saveMessage.style.display = 'block';
                saveMessage.style.background = '#d4edda';
                saveMessage.style.color = '#155724';
                saveMessage.style.border = '1px solid #c3e6cb';
                saveMessage.textContent = `✅ 포트폴리오가 저장되었습니다!`;

                // 입력 필드 초기화
                nameInput.value = '';

            } catch (err) {
                console.error('❌ Save Error:', err);
                saveMessage.style.display = 'block';
                saveMessage.style.background = '#f8d7da';
                saveMessage.style.color = '#721c24';
                saveMessage.style.border = '1px solid #f5c6cb';
                saveMessage.textContent = `❌ ${err.message}`;
            } finally {
                saveBtn.disabled = false;
                saveBtn.textContent = '💾 저장하기';
            }
        }

        function openAIModal() {
            document.getElementById('aiAnalysisModal').style.display = 'block';
            // 모바일에서 배경 스크롤 방지
            document.body.style.overflow = 'hidden';
        }


    
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            
            let icon = 'ℹ️';
            if(type === 'error') icon = '❌';
            if(type === 'success') icon = '✅';
            
            toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
            container.appendChild(toast);
            
            // Trigger animation
            setTimeout(() => toast.classList.add('show'), 10);
            
            // Remove after 3 seconds
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

function showAnalyzeView() {
            document.getElementById('analysisFormCard').style.display = 'block';
            // 분석 결과가 있으면 다시 보여줌
            if (chart || currentAnalysisData) {
                document.getElementById('results').style.display = 'block';
            }
            document.getElementById('portfolioViewCard').style.display = 'none';
            document.getElementById('navAnalyze').classList.add('active');
            document.getElementById('navPortfolio').classList.remove('active');
        }

        function showPortfolioView() {
            document.getElementById('analysisFormCard').style.display = 'none';
            document.getElementById('results').style.display = 'none';
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
            const numId = Number(id);
            let portfolios = getLocalPortfolios();
            portfolios = portfolios.filter(p => Number(p.id) !== numId);
            localStorage.setItem(DB_KEY, JSON.stringify(portfolios));
        }

        async function fetchPortfolios() {
            try {
                const portfolios = getLocalPortfolios().sort((a, b) => b.id - a.id);
                const list = document.getElementById('portfolioList');
                if (portfolios.length > 0) {
                    list.innerHTML = portfolios.map(p => {
                        let assetsPreview = '';
                        try {
                            if (p.csv_content) {
                                const lines = p.csv_content.split('\n').filter(l => l.trim());
                                const items = [];
                                for(let i=1; i<lines.length; i++) {
                                    const parts = lines[i].split(',');
                                    if(parts.length >= 2) items.push(`${parts[0]}(${parts[1]})`);
                                }
                                if(items.length > 5) {
                                    assetsPreview = items.slice(0, 5).join(', ') + ` 외 ${items.length - 5}종목`;
                                } else {
                                    assetsPreview = items.join(', ');
                                }
                            }
                        } catch(e) {}
                        
                        // Fallback stringify for loadPortfolioData
                        const pStr = JSON.stringify(p).replace(/'/g, "&#39;");
                        
                        return `
                        <div style="background: white; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: space-between;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                                <div>
                                    <h3 style="color: #2d3748; margin: 0 0 5px 0; font-size: 1.2rem; font-weight: 700;">${p.name}</h3>
                                    <p style="font-size: 0.85em; color: #718096; margin: 0;">🗓 ${p.created_at}</p>
                                </div>
                            </div>
                            
                            <div style="background: #f8fafc; padding: 12px; border-radius: 8px; margin-bottom: 20px;">
                                <div style="font-size: 0.9em; color: #4a5568; margin-bottom: 8px;"><strong>💼 구성 종목:</strong></div>
                                <div style="font-size: 0.95em; color: #2b6cb0; word-break: break-all; line-height: 1.4;">
                                    ${assetsPreview || '종목 없음'}
                                </div>
                                <div style="font-size: 0.8em; color: #a0aec0; margin-top: 8px; border-top: 1px solid #e2e8f0; padding-top: 8px;">
                                    ${p.start_date ? '시작: ' + p.start_date + ' | ' : ''}벤치마크: ${p.benchmark_ticker || '없음'}
                                </div>
                            </div>

                            <div style="display: flex; gap: 8px; justify-content: flex-end; align-items: center; margin-top: 10px; border-top: 1px solid #edf2f7; padding-top: 15px;">
                                <button onclick='deletePortfolio(${p.id})' style="background: transparent; color: #e53e3e; padding: 8px 12px; height: 38px; border-radius: 6px; border: 1px solid #feb2b2; cursor: pointer; font-size: 0.85rem; font-weight: 600; white-space: nowrap; transition: all 0.2s;">
                                    삭제
                                </button>
                                <button onclick='loadPortfolioData(${pStr})' style="background: #3182ce; color: white; padding: 6px 16px; height: 38px; border-radius: 6px; border: none; cursor: pointer; font-size: 0.85rem; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(49, 130, 206, 0.2); transition: all 0.2s;">
                                    📥 불러오기
                                </button>
                            </div>
                        </div>
                    `;
                    }).join('');
                } else {
                    list.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 50px; background: #f8fafc; border-radius: 12px; color: #718096;">저장된 포트폴리오가 없습니다.</div>';
                }
            } catch (e) {
                document.getElementById('portfolioList').innerHTML = '<p style="color:red; text-align:center; grid-column: 1 / -1;">오류가 발생했습니다.</p>';
            }
        }

        async function loadPortfolioData(portfolio) {
            closePortfolioModal();
            
            // Populate config fields if they exist
            if (portfolio.start_date) document.getElementById('startDate').value = portfolio.start_date;
            if (portfolio.benchmark_ticker) document.getElementById('benchmarkTicker').value = portfolio.benchmark_ticker;
            if (portfolio.base_currency) document.getElementById('baseCurrency').value = portfolio.base_currency;
            
            // DCA 초기화 및 복원
            if (portfolio.dca_enabled && portfolio.dca_data && portfolio.dca_data.length > 0) {
                document.getElementById('dcaSection').style.display = 'block';
                document.getElementById('dcaInputTableBody').innerHTML = '';
                portfolio.dca_data.forEach(dca => {
                    addDcaRow(dca.ticker, dca.quantity, dca.country, dca.frequency);
                });
            } else {
                document.getElementById('dcaSection').style.display = 'none';
                document.getElementById('dcaInputTableBody').innerHTML = '';
            }

            const blob = new Blob([portfolio.csv_content], { type: 'text/csv' });
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

                document.getElementById('manualInputTableBody').innerHTML = '';

                data.portfolio.forEach(asset => {
                    addRow(asset.ticker, asset.quantity, asset.country);
                });

                document.getElementById('cashKRW').value = data.cash.KRW || 0;
                document.getElementById('cashUSD').value = data.cash.USD || 0;

                showToast('포트폴리오를 성공적으로 불러왔습니다!');
            } catch (e) {
                showToast('포트폴리오 로드 중 오류: ' + e.message, 'error');
            }
        }

        let portfolioToDelete = null;

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

        function confirmDelete() {
            if (portfolioToDelete !== null) {
                try {
                    deleteLocalPortfolio(portfolioToDelete);
                    fetchPortfolios();
                    showToast('포트폴리오가 삭제되었습니다.', 'success');
                } catch (e) {
                    showToast('오류 발생', 'error');
                }
                closeDeleteModal();
            }
        }

        async function savePortfolioToDB() {
            const name = document.getElementById('portfolioName').value.trim();
            if (!name) {
                showToast('포트폴리오 이름을 입력하세요.');
                return;
            }

            const csvContent = convertManualInputToCSV(); // existing function
            if (!csvContent) {
                showToast('포트폴리오 내용이 없습니다.');
                return;
            }

            const dcaRows = document.querySelectorAll('#dcaInputTableBody .dca-row');
            const dcaData = [];
            dcaRows.forEach(row => {
                const ticker = row.querySelector('.dca-ticker-input').value.trim();
                const quantity = row.querySelector('.dca-quantity-input').value.trim();
                const country = row.querySelector('.dca-country-input').value;
                const frequency = row.querySelector('.dca-frequency-input').value;
                if (ticker && quantity) {
                    dcaData.push({
                        ticker: ticker,
                        quantity: quantity,
                        country: country,
                        frequency: frequency
                    });
                }
            });
            
            // Check if DCA section is actually visible and has data
            const dcaSectionVisible = document.getElementById('dcaSection').style.display !== 'none';
            const dcaEnabled = dcaSectionVisible && dcaData.length > 0;

            const payload = {
                name: name,
                csv_content: csvContent,
                start_date: document.getElementById('startDate').value,
                benchmark_ticker: document.getElementById('benchmarkTicker').value,
                base_currency: document.getElementById('baseCurrency').value,
                dca_enabled: dcaEnabled,
                dca_data: dcaEnabled ? dcaData : []
            };

            try {
                saveLocalPortfolio(payload);
                showToast('저장되었습니다!');
            } catch (e) {
                showToast('저장 실패: ' + e.message, 'error');
            }
        }

    
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            
            let icon = 'ℹ️';
            if(type === 'error') icon = '❌';
            if(type === 'success') icon = '✅';
            
            toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
            container.appendChild(toast);
            
            // Trigger animation
            setTimeout(() => toast.classList.add('show'), 10);
            
            // Remove after 3 seconds
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

// 소수점 자리수 검증 로직 추가 (항상 최대 3자리까지 허용)
        document.addEventListener('input', function(e) {
            if (e.target.type === 'number') {
                const decimals = 3; // 최대 소수점 자리수 설정
                const valStr = e.target.value.toString();
                
                // 이전 커스텀 유효성 상태 초기화
                e.target.setCustomValidity('');
                e.target.style.borderColor = '#ddd';
                e.target.style.outline = '';
                
                if (valStr.includes('.')) {
                    const currentDecimals = valStr.split('.')[1].length;
                    if (currentDecimals > decimals) {
                        e.target.setCustomValidity(`소수점 ${decimals}자리까지만 입력 가능합니다.`);
                        e.target.reportValidity();
                        e.target.style.borderColor = '#ef4444';
                        e.target.style.outline = '1px solid #ef4444';
                    }
                }
            }
        });

// --- Custom Number Input Logic ---
// To prevent snapping and allow +- N (1) from current decimal value
document.addEventListener('keydown', function(e) {
    if (e.target.tagName.toLowerCase() === 'input' && e.target.type === 'number') {
        if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
            if (e.target.id === 'cashKRW') return; // Native behavior for KRW (step=1)
            
            e.preventDefault();
            let currentVal = parseFloat(e.target.value);
            if (isNaN(currentVal)) currentVal = 0;
            
            let step = 1;
            if (e.key === 'ArrowUp') currentVal += step;
            else if (e.key === 'ArrowDown') currentVal -= step;
            
            let min = parseFloat(e.target.getAttribute('min'));
            if (!isNaN(min) && currentVal < min) currentVal = min;
            
            currentVal = Math.round(currentVal * 1000) / 1000; // precision
            e.target.value = currentVal;
            e.target.dispatchEvent(new Event('input', { bubbles: true }));
            e.target.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }
});

document.addEventListener('wheel', function(e) {
    if (document.activeElement === e.target && e.target.tagName.toLowerCase() === 'input' && e.target.type === 'number') {
        if (e.target.id === 'cashKRW') return;
        e.preventDefault();
        let currentVal = parseFloat(e.target.value);
        if (isNaN(currentVal)) currentVal = 0;
        
        let step = 1;
        if (e.deltaY < 0) currentVal += step;
        else currentVal -= step;
        
        let min = parseFloat(e.target.getAttribute('min'));
        if (!isNaN(min) && currentVal < min) currentVal = min;
        
        currentVal = Math.round(currentVal * 1000) / 1000;
        e.target.value = currentVal;
        e.target.dispatchEvent(new Event('input', { bubbles: true }));
        e.target.dispatchEvent(new Event('change', { bubbles: true }));
    }
}, { passive: false });

document.addEventListener('focusin', function(e) {
    if (e.target.type === 'number') {
        e.target.dataset.oldValue = e.target.value;
    }
});
document.addEventListener('input', function(e) {
    if (e.target.type === 'number') {
        e.target.dataset.oldValue = e.target.value;
    }
});
