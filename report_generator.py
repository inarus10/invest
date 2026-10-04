import os
import json
import pandas as pd
from datetime import datetime

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>모멘텀 포트폴리오 리밸런싱 리포트 ({{ target_date }})</title>
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-page: #f8fafc;
            --bg-card: #ffffff;
            --text-main: #0f172a;
            --text-sub: #64748b;
            --border: #e2e8f0;
            --border-dark: #0f172a;
            --up-red: #dc2626;
            --down-blue: #2563eb;
            --gray-light: #f1f5f9;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Segoe UI", Roboto, sans-serif; }
        body { background-color: var(--bg-page); color: var(--text-main); padding: 28px 20px; line-height: 1.5; }
        .container { max-width: 1200px; margin: 0 auto; }

        header { margin-bottom: 24px; border-bottom: 2px solid var(--text-main); padding-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-end; }
        h1 { font-size: 26px; font-weight: 800; color: var(--text-main); letter-spacing: -0.5px; }
        .header-meta { font-size: 14px; color: var(--text-sub); margin-top: 4px; }

        /* 블랙 & 화이트 톤의 깔끔한 컨트롤 패널 */
        .control-panel {
            background: #ffffff;
            color: var(--text-main);
            padding: 20px 24px;
            border-radius: 10px;
            margin-bottom: 24px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }
        .control-group { display: flex; flex-direction: column; gap: 6px; }
        .control-label { font-size: 12px; color: var(--text-sub); font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
        .input-wrapper { display: flex; align-items: center; gap: 8px; }
        .input-amount {
            background: #ffffff;
            border: 1.5px solid #cbd5e1;
            color: var(--text-main);
            font-size: 20px;
            font-weight: 800;
            padding: 6px 14px;
            border-radius: 6px;
            width: 220px;
            outline: none;
            text-align: right;
            transition: border-color 0.2s;
        }
        .input-amount:focus { border-color: var(--text-main); }
        .unit-text { font-size: 16px; font-weight: 700; color: var(--text-main); }
        
        .btn-reset {
            background: #ffffff;
            color: var(--text-main);
            border: 1.5px solid #cbd5e1;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-reset:hover { background: #0f172a; color: #ffffff; border-color: #0f172a; }

        .card {
            background: var(--bg-card);
            border-radius: 10px;
            padding: 24px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            margin-bottom: 24px;
            width: 100%;
        }
        .card-title {
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            letter-spacing: -0.3px;
        }
        .weight-sum-badge {
            font-size: 13px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
        }
        .weight-ok { background: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1; }
        .weight-warn { background: #fee2e2; color: #991b1b; border: 1px solid #f87171; }

        /* Full Width Table */
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
        th { background: #f8fafc; color: #334155; font-weight: 700; padding: 12px 14px; border-bottom: 2px solid var(--border); }
        td { padding: 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }
        tr:hover { background: #f8fafc; }

        .weight-input {
            width: 65px;
            padding: 6px 8px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            text-align: right;
            font-weight: 700;
            font-size: 14px;
            color: var(--text-main);
        }
        .weight-input:focus { outline: none; border-color: var(--text-main); }

        .delta-up { color: var(--up-red); font-weight: 700; }
        .delta-down { color: var(--down-blue); font-weight: 700; }
        .delta-neutral { color: var(--text-sub); }

        .category-badge {
            font-size: 12px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            background: #f1f5f9;
            color: #475569;
            display: inline-block;
        }

        .briefing-box {
            background: #ffffff;
            border: 1px solid var(--border);
            border-left: 4px solid var(--text-main);
            padding: 18px 22px;
            border-radius: 6px;
            margin-bottom: 24px;
        }
        .briefing-title { font-weight: 800; font-size: 15px; color: var(--text-main); margin-bottom: 6px; }
        .briefing-text { font-size: 14px; color: #334155; line-height: 1.6; }

        /* 기간 필터 버튼 */
        .filter-group { display: flex; gap: 6px; }
        .btn-filter {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            color: #475569;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s;
        }
        .btn-filter.active {
            background: #0f172a;
            color: #ffffff;
            border-color: #0f172a;
        }
        .btn-filter:hover:not(.active) { background: #f1f5f9; }

        .rank-table th, .rank-table td { font-size: 13px; padding: 10px 12px; }
    </style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>📊 포트폴리오 모멘텀 리밸런싱 대시보드</h1>
            <div class="header-meta">분석 기준일: <strong>{{ target_date }}</strong> | 전략: 1M/3M/6M/12M 가중 모멘텀 배분</div>
        </div>
    </header>

    <!-- 블랙앤화이트 톤 컨트롤 패널 -->
    <div class="control-panel">
        <div class="control-group">
            <span class="control-label">총 투자 금액 (실시간 수정 가능)</span>
            <div class="input-wrapper">
                <input type="text" id="totalAmountInput" class="input-amount" value="{{ "{:,}".format(total_amount) }}" oninput="updatePortfolio()">
                <span class="unit-text">원</span>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap: 16px;">
            <div class="control-group" style="text-align: right;">
                <span class="control-label">배분 비중 합계</span>
                <span id="weightSumBadge" class="weight-sum-badge weight-ok">100% (정상)</span>
            </div>
            <button class="btn-reset" onclick="resetToDefaultWeights()">기본 비중으로 초기화</button>
        </div>
    </div>

    <!-- AI 마켓 브리핑 -->
    <div class="briefing-box">
        <div class="briefing-title">💡 포트폴리오 진단 및 모멘텀 분석</div>
        <div class="briefing-text">{{ ai_commentary }}</div>
    </div>

    <!-- 전체 폭을 활용하는 추천 포트폴리오 배분 카드 -->
    <div class="card">
        <div class="card-title">
            <span>🎯 추천 포트폴리오 배분</span>
            <span style="font-size: 13px; color: var(--text-sub); font-weight: normal;">* 비중을 직접 변경하면 매수금액과 수량이 실시간으로 재계산됩니다.</span>
        </div>
        <table>
            <thead>
                <tr>
                    <th style="width: 160px;">구분</th>
                    <th style="width: 120px;">자산군</th>
                    <th>종목명 (코드)</th>
                    <th style="text-align: right; width: 120px;">현재가</th>
                    <th style="text-align: right; width: 100px;">M-Score</th>
                    <th style="text-align: center; width: 100px;">전월대비</th>
                    <th style="text-align: center; width: 110px;">비중(%)</th>
                    <th style="text-align: right; width: 160px;">매수금액</th>
                    <th style="text-align: right; width: 120px;">예상수량</th>
                </tr>
            </thead>
            <tbody id="portfolioTableBody">
                <!-- 자바스크립트로 동적 렌더링 -->
            </tbody>
        </table>
    </div>

    <!-- M-Score 시계열 추이 차트 (기간 필터 및 y축 자동 스케일링) -->
    <div class="card">
        <div class="card-title">
            <span>📉 주요 종목별 M-Score 시계열 추이 <span style="font-size: 13px; font-weight: normal; color: var(--text-sub); margin-left: 8px;">(수비자산: 점선)</span></span>
            <div class="filter-group">
                <button class="btn-filter" onclick="setTrendPeriod('3M')">3개월</button>
                <button class="btn-filter" onclick="setTrendPeriod('6M')">6개월</button>
                <button class="btn-filter active" id="btn-1Y" onclick="setTrendPeriod('1Y')">1년</button>
                <button class="btn-filter" onclick="setTrendPeriod('ALL')">전체</button>
            </div>
        </div>
        <div style="height: 420px;">
            <canvas id="trendChart"></canvas>
        </div>
    </div>

    <!-- 전체 종목 모멘텀 랭킹 카드 -->
    <div class="card">
        <div class="card-title">
            <span>📈 전체 관심자산 모멘텀 스코어 랭킹 (기준일: {{ target_date }})</span>
        </div>
        <table class="rank-table">
            <thead>
                <tr>
                    <th style="text-align: center; width: 60px;">순위</th>
                    <th style="width: 90px;">분류</th>
                    <th style="width: 110px;">자산군</th>
                    <th>종목명</th>
                    <th style="width: 80px;">코드</th>
                    <th style="text-align: right; width: 100px;">종가</th>
                    <th style="text-align: right; width: 90px;">1M</th>
                    <th style="text-align: right; width: 90px;">3M</th>
                    <th style="text-align: right; width: 90px;">6M</th>
                    <th style="text-align: right; width: 90px;">1Y</th>
                    <th style="text-align: right; width: 110px; background: #0f172a; color: #ffffff;">M-Score</th>
                </tr>
            </thead>
            <tbody>
                {% for row in all_ranks %}
                <tr>
                    <td style="text-align: center; font-weight: 700;">{{ loop.index }}</td>
                    <td><span class="category-badge">{{ row.분류 }}</span></td>
                    <td>{{ row.자산군 }}</td>
                    <td><strong>{{ row.명칭 }}</strong></td>
                    <td style="color: var(--text-sub); font-family: monospace;">{{ row.Code }}</td>
                    <td style="text-align: right;">{{ "{:,}".format(row.close) }}원</td>
                    <td style="text-align: right; color: {{ '#dc2626' if row['1M']>0 else '#2563eb' }}; font-weight: 600;">{{ "{:+.2f}".format(row['1M']) }}%</td>
                    <td style="text-align: right; color: {{ '#dc2626' if row['3M']>0 else '#2563eb' }}; font-weight: 600;">{{ "{:+.2f}".format(row['3M']) }}%</td>
                    <td style="text-align: right; color: {{ '#dc2626' if row['6M']>0 else '#2563eb' }}; font-weight: 600;">{{ "{:+.2f}".format(row['6M']) }}%</td>
                    <td style="text-align: right; color: {{ '#dc2626' if row['1Y']>0 else '#2563eb' }}; font-weight: 600;">{{ "{:+.2f}".format(row['1Y']) }}%</td>
                    <td style="text-align: right; font-weight: 800; font-size: 15px; background: #f8fafc; color: #0f172a;">{{ "{:.2f}".format(row.M_score) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<script>
    // 포트폴리오 데이터
    const rawPortfolio = {{ portfolio_json | safe }};
    const defaultPortfolio = JSON.parse(JSON.stringify(rawPortfolio));
    let currentPortfolio = JSON.parse(JSON.stringify(rawPortfolio));

    // 시계열 전체 데이터
    const fullTrendData = {{ trend_json | safe }};
    let trendChartInstance = null;
    let currentPeriod = '1Y';

    function formatNumber(num) {
        return num.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ",");
    }

    function parseAmount(str) {
        return parseInt(str.replace(/[^0-9]/g, ""), 10) || 0;
    }

    function renderTable() {
        const tbody = document.getElementById("portfolioTableBody");
        tbody.innerHTML = "";
        const totalAmount = parseAmount(document.getElementById("totalAmountInput").value);

        currentPortfolio.forEach((item, index) => {
            const tr = document.createElement("tr");

            const isCash = item.Code === '-' || item.자산군 === '현금성자산';

            const deltaHtml = isCash ? `<span class="delta-neutral">-</span>`
                : item.delta_M > 0 
                ? `<span class="delta-up">▲ ${item.delta_M.toFixed(1)}</span>`
                : item.delta_M < 0 
                ? `<span class="delta-down">▼ ${Math.abs(item.delta_M).toFixed(1)}</span>`
                : `<span class="delta-neutral">-</span>`;

            const calcAmount = Math.round(totalAmount * (item.비중 / 100));
            const calcQty = isCash ? '-' : (item.close > 0 ? formatNumber(Math.floor(calcAmount / item.close)) + '주' : '0주');
            const priceDisplay = isCash ? '-' : formatNumber(item.close) + '원';
            const mScoreDisplay = isCash ? '-' : item.M_score.toFixed(1);

            tr.innerHTML = `
                <td><span class="category-badge">${item.배분구분}</span></td>
                <td>${item.자산군}</td>
                <td><strong>${item.명칭}</strong> ${item.Code !== '-' ? `<span style="font-size:12px; color:#94a3b8;">(${item.Code})</span>` : ''}</td>
                <td style="text-align: right;">${priceDisplay}</td>
                <td style="text-align: right; font-weight:700;">${mScoreDisplay}</td>
                <td style="text-align: center;">${deltaHtml}</td>
                <td style="text-align: center;">
                    <input type="number" class="weight-input" min="0" max="100" value="${item.비중}" onchange="onWeightChange(${index}, this.value)">
                </td>
                <td style="text-align: right; font-weight:800; color:#0f172a;">${formatNumber(calcAmount)}원</td>
                <td style="text-align: right; font-weight:600; color:#475569;">${calcQty}</td>
            `;
            tbody.appendChild(tr);
        });

        updateWeightSum();
    }

    function onWeightChange(index, newWeight) {
        currentPortfolio[index].비중 = parseFloat(newWeight) || 0;
        renderTable();
    }

    function updateWeightSum() {
        const sum = currentPortfolio.reduce((acc, cur) => acc + cur.비중, 0);
        const badge = document.getElementById("weightSumBadge");
        if (Math.abs(sum - 100) < 0.01) {
            badge.className = "weight-sum-badge weight-ok";
            badge.innerText = `100% (정상)`;
        } else {
            badge.className = "weight-sum-badge weight-warn";
            badge.innerText = `합계: ${sum}% (100% 필요)`;
        }
    }

    function updatePortfolio() {
        const input = document.getElementById("totalAmountInput");
        const val = parseAmount(input.value);
        input.value = formatNumber(val);
        renderTable();
    }

    function resetToDefaultWeights() {
        currentPortfolio = JSON.parse(JSON.stringify(defaultPortfolio));
        renderTable();
    }

    // 시계열 기간 필터 및 y축 자동 스케일링
    function setTrendPeriod(period) {
        currentPeriod = period;

        // 버튼 활성화 토글
        document.querySelectorAll('.btn-filter').forEach(btn => {
            btn.classList.remove('active');
            if (btn.innerText === (period === '3M' ? '3개월' : period === '6M' ? '6개월' : period === '1Y' ? '1년' : '전체')) {
                btn.classList.add('active');
            }
        });

        if (!fullTrendData || !fullTrendData.dates) return;

        const totalPoints = fullTrendData.dates.length;
        let startIndex = 0;

        // 월 2회 기준: 3M=6포인트, 6M=12포인트, 1Y=24포인트
        if (period === '3M') startIndex = Math.max(0, totalPoints - 6);
        else if (period === '6M') startIndex = Math.max(0, totalPoints - 12);
        else if (period === '1Y') startIndex = Math.max(0, totalPoints - 24);
        else if (period === 'ALL') startIndex = 0;

        const filteredDates = fullTrendData.dates.slice(startIndex);

        let minVal = Infinity;
        let maxVal = -Infinity;

        const updatedDatasets = fullTrendData.series.map((s, idx) => {
            const slicedData = s.data.slice(startIndex);
            slicedData.forEach(v => {
                if (v !== null && v !== undefined) {
                    if (v < minVal) minVal = v;
                    if (v > maxVal) maxVal = v;
                }
            });

            const colors = [
                '#0f172a', '#2563eb', '#059669', '#d97706', '#dc2626', 
                '#7c3aed', '#0891b2', '#be185d', '#475569', '#0d9488', 
                '#ea580c', '#6366f1'
            ];
            const isDefensive = s.isDefensive || s.category === '수비자산';
            return {
                label: s.name + (isDefensive ? ' (수비)' : ''),
                data: slicedData,
                borderColor: colors[idx % colors.length],
                backgroundColor: 'transparent',
                borderDash: isDefensive ? [6, 4] : [], // 수비자산은 점선 처리
                borderWidth: isDefensive ? 2.5 : 2,
                tension: 0.25,
                pointRadius: slicedData.length > 30 ? 2 : 3
            };
        });

        // y축 auto-scaling: 상하 10% 여유
        if (minVal === Infinity) minVal = -50;
        if (maxVal === -Infinity) maxVal = 50;
        const padding = Math.max(5, (maxVal - minVal) * 0.1);
        const yMin = Math.floor(minVal - padding);
        const yMax = Math.ceil(maxVal + padding);

        if (trendChartInstance) {
            trendChartInstance.data.labels = filteredDates;
            trendChartInstance.data.datasets = updatedDatasets;
            trendChartInstance.options.scales.y.min = yMin;
            trendChartInstance.options.scales.y.max = yMax;
            trendChartInstance.update();
        } else {
            const ctx = document.getElementById('trendChart').getContext('2d');
            trendChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: filteredDates,
                    datasets: updatedDatasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        y: {
                            min: yMin,
                            max: yMax,
                            title: { display: true, text: 'M-Score', font: { weight: 'bold' } },
                            grid: { color: '#f1f5f9' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 12 } } },
                        tooltip: { padding: 10 }
                    }
                }
            });
        }
    }

    window.onload = function() {
        renderTable();
        setTrendPeriod('1Y');
    };
</script>
</body>
</html>
"""

def generate_html_report(
    accum_df: pd.DataFrame, 
    portfolio_df: pd.DataFrame, 
    target_date: str, 
    total_amount: int = 100_000_000,
    output_filename: str = None
) -> str:
    from jinja2 import Template

    # 1. 당일 전체 랭킹
    target_dt = pd.to_datetime(target_date)
    curr_df = accum_df[pd.to_datetime(accum_df['Date']) == target_dt].copy()
    if curr_df.empty:
        latest_date = pd.to_datetime(accum_df['Date']).max()
        curr_df = accum_df[pd.to_datetime(accum_df['Date']) == latest_date].copy()
    
    all_ranks = curr_df.sort_values(by='M_score', ascending=False).to_dict(orient='records')

    # 2. AI 코멘터리 생성
    top1 = all_ranks[0] if all_ranks else None
    cash_holding = any(r['Code'] == '-' or '현금' in str(r['명칭']) for r in portfolio_df.to_dict(orient='records'))
    
    ai_commentary = f"기준일({target_date}) 전체 자산군 중 1위는 <strong>{top1['명칭']}</strong>(M-Score: {top1['M_score']:.1f})입니다. "
    if cash_holding:
        ai_commentary += "<strong>[수비자산 현금보유 원칙 적용]</strong> 모든 수비자산(채권/달러 등)의 모멘텀 지수가 마이너스를 기록함에 따라 채권 매수 대신 <strong>현금(예수금/CMA) 30% 보유</strong>를 권고합니다. "
    else:
        def_top = portfolio_df[portfolio_df['분류'] == '수비자산'].iloc[0] if not portfolio_df.empty else None
        if def_top:
            ai_commentary += f"수비자산 중에서는 <strong>{def_top['명칭']}</strong>(M-Score: {def_top['M_score']:.1f})이 양호한 모멘텀으로 30% 배정되었습니다. "

    is_split_applied = any("15%" in str(b) for b in portfolio_df['배분구분'])
    if is_split_applied:
        ai_commentary += "공격자산 부문에서는 코스피 200과 한국 모멘텀 팩터가 동시에 상위권에 올랐으나, 한국 시장 편중 리스크를 분산하기 위해 각각 15%씩 균등 분할 배분되었습니다."
    else:
        ai_commentary += "상위 모멘텀 자산군을 중심으로 분산 투자하여 추세를 반영했습니다."

    # 3. 전체 시계열 트렌드 데이터 (전체 날짜 전달 -> 프론트에서 3M/6M/1Y/ALL 슬라이싱 및 Auto-scaling)
    sub_df = accum_df.copy()
    sub_df['DateStr'] = pd.to_datetime(sub_df['Date']).dt.strftime('%y.%m.%d')
    dates = sorted(sub_df['DateStr'].unique().tolist())

    # 기본 추천 포트폴리오 종목들 (현금 제외)
    target_stocks = [r['명칭'] for r in portfolio_df.to_dict(orient='records') if r['Code'] != '-']

    # 사용자 필수 지정 비교 종목: S&P, 코스닥, 금, 달러단기채
    mandatory_stocks = [
        'KODEX 미국S&P500', 
        'ACE 코스닥150', 
        'ACE KRX금현물', 
        'TIGER 미국달러단기채권액티브'
    ]
    for s in mandatory_stocks:
        if s not in target_stocks and s in sub_df['명칭'].values:
            target_stocks.append(s)

    # 추가로 전체 상위 랭킹 종목들도 여유 시 포함
    for r in all_ranks[:5]:
        if r['명칭'] not in target_stocks and r['명칭'] in sub_df['명칭'].values:
            target_stocks.append(r['명칭'])

    # 종목별 분류(공격자산 / 수비자산) 매핑
    category_map = dict(zip(sub_df['명칭'], sub_df['분류']))

    series_list = []
    for stock_name in target_stocks:
        stk_data = sub_df[sub_df['명칭'] == stock_name].sort_values(by='Date')
        m_map = dict(zip(stk_data['DateStr'], stk_data['M_score']))
        data_points = [round(m_map.get(d, 0), 2) if d in m_map else None for d in dates]
        cat = category_map.get(stock_name, "공격자산")
        is_defensive = (cat == '수비자산')
        series_list.append({
            "name": stock_name,
            "category": cat,
            "isDefensive": is_defensive,
            "data": data_points
        })

    trend_json = json.dumps({"dates": dates, "series": series_list}, ensure_ascii=False)
    portfolio_json = json.dumps(portfolio_df.to_dict(orient='records'), ensure_ascii=False)

    template = Template(HTML_TEMPLATE)
    rendered_html = template.render(
        target_date=target_date,
        total_amount=total_amount,
        ai_commentary=ai_commentary,
        portfolio_json=portfolio_json,
        all_ranks=all_ranks,
        trend_json=trend_json
    )

    if not output_filename:
        output_filename = f"report_{target_date.replace('-', '')}.html"
    
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    # GitHub Pages용 최신 index.html 동시 갱신
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)

    print(f"✅ 개선된 HTML 대시보드 리포트 생성 완료: {os.path.abspath(output_filename)} (index.html 동기화)")
    return output_filename
