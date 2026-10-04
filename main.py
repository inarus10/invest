import os
import sys
import argparse
import calendar
import webbrowser
from datetime import datetime, date, timedelta
import pandas as pd

import auth
import momentum
import report_generator

ACCUM_FILE = "accum_final_df.csv"
INPUT_FILE = "input_df.csv"

def is_rebalance_day(target_date: date) -> bool:
    """
    매달 15일 또는 마지막 날인지 검사
    """
    if target_date.day == 15:
        return True
    
    # 내일이 1일이면 오늘이 마지막 날
    tomorrow = target_date + timedelta(days=1)
    if tomorrow.day == 1:
        return True
    
    return False

def update_database(accum_df: pd.DataFrame, new_rows_df: pd.DataFrame, target_date_str: str) -> pd.DataFrame:
    """
    누적 데이터베이스에 신규 수집된 데이터를 병합하고 중복 제거 후 저장
    """
    new_rows_df = new_rows_df.copy()
    new_rows_df['Date'] = target_date_str

    # 기존 데이터에서 해당 날짜 데이터가 이미 있으면 갱신을 위해 제거
    cleaned_df = accum_df[accum_df['Date'] != target_date_str].copy()
    updated_df = pd.concat([new_rows_df, cleaned_df], ignore_index=True)
    
    # 날짜 최신순 정렬
    updated_df['Date_dt'] = pd.to_datetime(updated_df['Date'])
    updated_df = updated_df.sort_values(by=['Date_dt', 'M_score'], ascending=[False, False]).drop(columns=['Date_dt'])

    # CSV 저장 (utf-8-sig로 한글 및 엑셀 호환 보장)
    updated_df.to_csv(ACCUM_FILE, index=False, encoding='utf-8-sig')
    print(f"💾 누적 데이터 저장 완료 ({ACCUM_FILE}, 총 {len(updated_df)}행)")
    return updated_df

def run_rebalance_pipeline(target_date_str: str, total_amount: int = 100_000_000, force: bool = False, report_only: bool = False, open_browser: bool = False):
    """
    지정된 날짜 기준 키움 API 주가 수집 -> M-score 계산 -> 누적 DB 갱신 -> 리포트 생성
    """
    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date()

    if not force and not is_rebalance_day(target_dt):
        print(f"ℹ️ {target_date_str}은 15일이나 말일이 아닙니다. (강제 실행하려면 --force 사용)")
        return

    print(f"==================================================")
    print(f"🚀 모멘텀 포트폴리오 파이프라인 시작 (기준일: {target_date_str})")
    print(f"==================================================")

    if os.path.exists(ACCUM_FILE):
        accum_df = pd.read_csv(ACCUM_FILE, encoding='utf-8-sig', dtype={'Code': str})
    else:
        accum_df = pd.DataFrame()

    if not report_only:
        # 1. 키움 API 토큰 획득
        token = auth.get_token()

        # 2. 관심 자산 목록 로드
        if not os.path.exists(INPUT_FILE):
            raise FileNotFoundError(f"{INPUT_FILE} 파일을 찾을 수 없습니다.")
        input_df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig', dtype={'Code': str})

        # 3. 주가 수집 및 모멘텀 지표 계산
        print(f"\n📡 키움 API 주가 데이터 수집 및 M-score 계산 중...")
        today_api_str = target_date_str.replace("-", "")
        return_df = momentum.build_return_table(token, input_df, today_api_str)

        if return_df.empty:
            print("❌ 데이터 수집 실패: 수집된 종목이 없습니다.")
            return

        # 4. 누적 DB 업데이트
        accum_df = update_database(accum_df, return_df, target_date_str)
    else:
        print(f"⚡ 로컬 누적 데이터({ACCUM_FILE})를 기반으로 리포트를 즉시 생성합니다.")

    # 5. 사용자 맞춤형 포트폴리오 추천 산출
    print(f"\n🎯 포트폴리오 추천 및 자산 배분 비중 계산...")
    rec_df = momentum.recommend_portfolio(accum_df, target_date_str, total_amount=total_amount)
    
    print("\n--- [추천 포트폴리오 요약] ---")
    cols_to_print = [c for c in ['배분구분', '명칭', 'Code', 'close', 'M_score', 'delta_M', '비중', '금액', '예상수량'] if c in rec_df.columns]
    print(rec_df[cols_to_print].to_string(index=False))

    # 6. 인터랙티브 HTML 대시보드 리포트 생성
    print(f"\n📑 인터랙티브 HTML 대시보드 리포트 생성 중...")
    report_file = report_generator.generate_html_report(
        accum_df=accum_df,
        portfolio_df=rec_df,
        target_date=target_date_str,
        total_amount=total_amount
    )

    print(f"\n✨ 모든 작업 완료! 리포트 파일: {report_file}")
    if open_browser and os.path.exists(report_file):
        try:
            webbrowser.open(f"file:///{os.path.abspath(report_file)}")
        except Exception:
            pass
    return report_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="키움 API 기반 모멘텀 포트폴리오 자동화")
    parser.add_argument("--date", type=str, help="분석 기준일 (YYYY-MM-DD), 미입력시 오늘 날짜")
    parser.add_argument("--amount", type=int, default=100_000_000, help="총 투자금액 (원, 기본 1억)")
    parser.add_argument("--force", action="store_true", help="15일/말일이 아니어도 강제 실행")
    parser.add_argument("--fill-september", action="store_true", help="9월 15일 및 9월 30일 데이터 연속 수집")
    parser.add_argument("--report-only", action="store_true", help="API 호출 없이 로컬 DB 기반으로 리포트만 재생성")
    parser.add_argument("--open", action="store_true", help="완료 후 기본 웹브라우저로 리포트 자동 열기")

    args = parser.parse_args()

    if args.fill_september:
        print("📥 9월 누락 데이터(2026-09-15, 2026-09-30) 연속 수집을 시작합니다...")
        run_rebalance_pipeline("2026-09-15", total_amount=args.amount, force=True)
        run_rebalance_pipeline("2026-09-30", total_amount=args.amount, force=True, open_browser=args.open)
    else:
        target = args.date if args.date else datetime.now().strftime("%Y-%m-%d")
        run_rebalance_pipeline(target, total_amount=args.amount, force=args.force, report_only=args.report_only, open_browser=args.open)
