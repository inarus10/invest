import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import Optional, Tuple, Dict, Any, List

KIWOOM_HOST = "https://api.kiwoom.com"

def get_daily_price(token: str, code: str, today_str: str) -> pd.DataFrame:
    """
    키움 API(/api/dostk/mrkcond, ka10086)를 호출하여 
    최대 300영업일의 일별 종가를 수집합니다.
    """
    all_data = []
    next_key = ""
    headers = {
        "Authorization": f"Bearer {token}",
        "api-id": "ka10086",
        "cont-yn": "Y",
        "next-key": next_key,
        "Content-Type": "application/json;charset=UTF-8"
    }

    url = f"{KIWOOM_HOST}/api/dostk/mrkcond"

    for page in range(25):  # 20개씩 반환되므로 최대 25회(500영업일치) 반복
        headers["next-key"] = next_key
        payload = {
            "stk_cd": str(code),
            "qry_dt": str(today_str).replace("-", ""),
            "indc_tp": "0"
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"   ⚠️ API 응답 에러 ({code}): {resp.status_code} {resp.text}")
                break
            
            headers_resp = resp.headers
            next_key = headers_resp.get("next-key", "")
            cont_yn = headers_resp.get("cont-yn", "N")

            data = resp.json()
            daily_list = data.get("daly_stkpc", [])
            if not daily_list:
                break

            all_data.extend(daily_list)
            if len(all_data) >= 300 or cont_yn != "Y" or not next_key:
                break

            time.sleep(0.15)
        except Exception as e:
            print(f"   ❌ 통신 실패 ({code}): {e}")
            break

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    # 컬럼 표준화: date, open, high, low, close
    df['date'] = pd.to_datetime(df['date'].astype(str), format="%Y%m%d", errors='coerce')
    df['close'] = df['close_pric'].astype(str).str.replace(",", "").astype(float).abs()
    
    df = df.dropna(subset=['date']).sort_values(by='date', ascending=False).reset_index(drop=True)
    return df

def get_near_price(df: pd.DataFrame, target_date: pd.Timestamp) -> Optional[float]:
    """target_date 이하의 가장 최근 거래일 종가를 가져옵니다."""
    matched = df[df['date'] <= target_date]
    if matched.empty:
        return None
    return float(matched.iloc[0]['close'])

def calc_return_row(token: str, code: str, today_str: str) -> Optional[Dict[str, Any]]:
    """1종목에 대한 1M/3M/6M/1Y 수익률 및 M-Score 계산"""
    df = get_daily_price(token, code, today_str)
    if df.empty:
        return None

    target_dt = pd.to_datetime(today_str)
    
    p0 = get_near_price(df, target_dt)
    p1 = get_near_price(df, target_dt - relativedelta(months=1))
    p3 = get_near_price(df, target_dt - relativedelta(months=3))
    p6 = get_near_price(df, target_dt - relativedelta(months=6))
    p12 = get_near_price(df, target_dt - relativedelta(months=12))

    if p0 is None or p1 is None or p12 is None:
        print(f"   ⚠️ {code}: 1년치 데이터가 부족합니다 (수집된 행: {len(df)})")
        return None

    today_price = df.iloc[0]['close']

    r1 = round(((today_price / p1) - 1) * 100, 2)
    r3 = round(((today_price / p3) - 1) * 100, 2)
    r6 = round(((today_price / p6) - 1) * 100, 2)
    r12 = round(((today_price / p12) - 1) * 100, 2)
    
    m_score = round((12 * r1 + 4 * r3 + 2 * r6 + 1 * r12) / 4, 2)

    print(f"   ✅ {code}: 종가 {int(p0):,}원 | M_score {m_score:.2f}")

    return {
        "close": int(round(p0)),
        "1M": r1,
        "3M": r3,
        "6M": r6,
        "1Y": r12,
        "M_score": m_score
    }

def build_return_table(token: str, input_df: pd.DataFrame, today_str: str) -> pd.DataFrame:
    """전체 대상 종목에 대해 모멘텀 지표를 계산하여 데이터프레임으로 반환"""
    results = []
    for _, row in input_df.iterrows():
        meta = row.to_dict()
        code = str(meta.get("Code")).zfill(6)
        print(f"▶ 종목 분석: {meta.get('명칭')} ({code})")
        ret = calc_return_row(token, code, today_str)
        if ret is not None:
            combined = {**meta, **ret}
            results.append(combined)
        time.sleep(0.1)

    return pd.DataFrame(results)

def recommend_portfolio(
    accum_df: pd.DataFrame, 
    today_str: str, 
    total_amount: int = 100_000_000
) -> pd.DataFrame:
    """
    사용자 맞춤형 자산 배분 알고리즘:
    1. 총 투자금액: 기본 100,000,000원
    2. 수비자산 1위: 30% 배분
    3. 전체자산 M-score 순위 산출:
       - Top 4 안에 '200'(KIWOOM 200TR)과 '모멘텀주'(KODEX 모멘텀주)가 둘 다 들어가는 경우:
         -> 둘을 합쳐서 30% (각 15%씩 반반 분할)
         -> 나머지 순위들을 각각 20%씩 배분
       - 일반 케이스:
         -> 1순위: 30%, 2순위: 20%, 3순위: 20%
    """
    today_dt = pd.to_datetime(today_str)
    
    # 당일 데이터 추출
    curr_df = accum_df[pd.to_datetime(accum_df['Date']) == today_dt].copy()
    if curr_df.empty:
        # 가장 최근 날짜 사용
        latest_date = pd.to_datetime(accum_df['Date']).max()
        curr_df = accum_df[pd.to_datetime(accum_df['Date']) == latest_date].copy()
        today_dt = latest_date

    # 약 30일 전 기준 M-score 가져와서 delta_M 계산
    target_prev_dt = pd.to_datetime(today_dt) - pd.Timedelta(days=30)
    prev_records = accum_df[pd.to_datetime(accum_df['Date']) <= target_prev_dt].copy()
    
    prev_m_map = {}
    if not prev_records.empty:
        prev_records = prev_records.sort_values(by=['Code', 'Date'], ascending=[True, False])
        latest_prev = prev_records.drop_duplicates(subset=['Code'], keep='first')
        for _, row in latest_prev.iterrows():
            code_str = str(row['Code']).zfill(6)
            prev_m_map[code_str] = row['M_score']

    curr_df['Code'] = curr_df['Code'].astype(str).str.zfill(6)
    curr_df['prev_M'] = curr_df['Code'].map(prev_m_map)
    curr_df['delta_M'] = (curr_df['M_score'] - curr_df['prev_M']).round(2)
    curr_df['delta_M'] = curr_df['delta_M'].fillna(0.0)

    # 1. 수비자산 1위 선발 (비중 30%)
    defensive_df = curr_df[curr_df['분류'] == '수비자산'].sort_values(by='M_score', ascending=False)
    if defensive_df.empty:
        raise ValueError("수비자산 데이터가 없습니다.")
    top_defensive = defensive_df.iloc[0].to_dict()

    portfolio_items: List[Dict[str, Any]] = []
    selected_codes = set()

    # [분석 조건] 수비자산인데 모멘텀지수가 마이너스면 현금보유 권고
    if top_defensive['M_score'] < 0:
        cash_item = {
            '분류': '수비자산',
            '자산군': '현금성자산',
            '명칭': '현금 (예수금/CMA)',
            'Code': '-',
            'close': 1,
            'M_score': 0.0,
            'prev_M': 0.0,
            'delta_M': 0.0,
            '비중': 30,
            '배분구분': '수비자산 (현금보유 30%)'
        }
        portfolio_items.append(cash_item)
    else:
        top_defensive['비중'] = 30
        top_defensive['배분구분'] = '수비자산 1위 (30%)'
        portfolio_items.append(top_defensive)
        selected_codes.add(str(top_defensive['Code']))

    # 2. 전체 자산 M-score 순위 정렬
    all_sorted = curr_df.sort_values(by='M_score', ascending=False).reset_index(drop=True)

    # Top 4 종목 추출 (검사용)
    top4_df = all_sorted.head(4)
    
    # '200'과 '모멘텀주' 식별 헬퍼
    def is_200(row) -> bool:
        name = str(row['명칭'])
        code = str(row['Code'])
        return "200" in name or code == "294400"

    def is_momentum(row) -> bool:
        name = str(row['명칭'])
        code = str(row['Code'])
        return "모멘텀" in name or code == "275280"

    has_200_in_top4 = any(is_200(row) for _, row in top4_df.iterrows())
    has_mom_in_top4 = any(is_momentum(row) for _, row in top4_df.iterrows())
    if has_200_in_top4 and has_mom_in_top4:
        # [예외 규칙 발동!]
        # '200'과 '모멘텀주'를 각각 15%씩 배분하여 합쳐서 30%가 되게 함
        item_200 = all_sorted[all_sorted.apply(is_200, axis=1)].iloc[0].to_dict()
        item_mom = all_sorted[all_sorted.apply(is_momentum, axis=1)].iloc[0].to_dict()

        item_200['비중'] = 15
        item_200['배분구분'] = '한국대형주 묶음 (15%)'
        portfolio_items.append(item_200)
        selected_codes.add(str(item_200['Code']))

        item_mom['비중'] = 15
        item_mom['배분구분'] = '한국대형주 묶음 (15%)'
        portfolio_items.append(item_mom)
        selected_codes.add(str(item_mom['Code']))

        # 나머지 자산 중 순위 순서대로 20%씩 2개 종목 선발
        remaining_candidates = all_sorted[~all_sorted['Code'].isin(selected_codes)]
        for _, row in remaining_candidates.head(2).iterrows():
            item = row.to_dict()
            item['비중'] = 20
            item['배분구분'] = '상위 모멘텀 (20%)'
            portfolio_items.append(item)
            selected_codes.add(str(item['Code']))

    else:
        # [일반 규칙]
        # 전체 자산 중 수비 1위를 제외하고 상위 3개 종목을 30%, 20%, 20% 순으로 배분
        remaining_candidates = all_sorted[~all_sorted['Code'].isin(selected_codes)]
        weights = [30, 20, 20]
        for i, (_, row) in enumerate(remaining_candidates.head(3).iterrows()):
            w = weights[i]
            item = row.to_dict()
            item['비중'] = w
            item['배분구분'] = f'상위 모멘텀 {i+1}위 ({w}%)'
            portfolio_items.append(item)
            selected_codes.add(str(item['Code']))

    res_df = pd.DataFrame(portfolio_items)
    
    # 매수 금액 및 수량 계산
    res_df['금액'] = res_df['비중'].apply(lambda w: int(round(total_amount * (w / 100.0))))
    res_df['예상수량'] = res_df.apply(
        lambda r: int(r['금액'] // r['close']) if r['close'] > 0 else 0, 
        axis=1
    )

    columns_order = [
        '분류', '자산군', '명칭', 'Code', 'close', 'M_score', 'delta_M', 
        '비중', '금액', '예상수량', '배분구분'
    ]
    return res_df[[c for c in columns_order if c in res_df.columns]]
