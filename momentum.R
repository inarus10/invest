library(httr2)
library(jsonlite)
library(dplyr)
library(lubridate)
library(magrittr)
library(tibble)

KIWOOM_HOST <- "https://api.kiwoom.com"

# --------------------------------------------------
# 1. 일별 종가 조회
# --------------------------------------------------
get_daily_price <- function(token, code, today) {
  all_data <- list()
  next_key <-""
  
  repeat{
  req <- request(paste0(KIWOOM_HOST, "/api/dostk/mrkcond")) %>%
    req_method("POST") %>%
    req_headers(
      Authorization = paste("Bearer", token),
      "api-id" = "ka10086", 
      "cont-yn" = "Y",
      "next-key"=next_key
    ) %>%
    req_body_json(list(
      stk_cd  = code,
      qry_dt  = today,
      indc_tp = "0"
    ))
  
  resp <- req_perform(req)
  if (is.null(resp)) break
  
  # 응답 헤더에서 다음 페이지 정보 추출
  next_key <- resp_header(resp, "next-key") %||% ""
  cont_yn  <- resp_header(resp, "cont-yn") %||% "N"
  
  
  #body에서 데이터 추출
  api_body <- resp %>% resp_body_json()
  daily_list <- api_body$daly_stkpc
  
  if (is.null(daily_list) || length(daily_list) == 0) break
  
  #데이터 모으기기
  all_data <- c(all_data, daily_list)
  
  #종료조건
  if(length(all_data)>=300) break
  Sys.sleep(0.15)
  }
 
  # 리스트 데이터를 행 단위로 합쳐서 데이터프레임 변환
  df <- bind_rows(all_data) %>% 
    transmute(
      # date가 리스트나 숫자로 오해받지 않게 강제로 캐릭터화
      date  = ymd(as.character(date)),            
      open  = as.numeric(as.character(open_pric)),
      high  = as.numeric(as.character(high_pric)),
      low   = as.numeric(as.character(low_pric)),
      close = abs(as.numeric(as.character(close_pric)))
    ) %>%
    filter(!is.na(date)) %>% 
    arrange(desc(date))
  
  return(df)
} 


# --------------------------------------------------
# 2. 기준일 이전 가장 가까운 거래일 종가
# --------------------------------------------------
get_near_price <- function(df, target_date) {
  res<-df %>%
    filter(date <= target_date) %>%
    slice(1) %>%
    pull(close)
  if (length(res)==0) return(NULL)
  return(res)
}

# --------------------------------------------------
# 3. 종목 1개: 1M/3M/6M/1Y + M score 계산
#    M score = (12*1M + 4*3M + 2*6M + 1*12M) / 4
# --------------------------------------------------
calc_return_row <- function(token, code) {
    prices <- get_daily_price(token     = token,
                              code      = code,
                              today = today)
  
  today_price <- prices %>% slice(1) %>% pull(close) 
  
  # get_near_price를 써서 휴장일을 피해 정확한 과거 종가를 가져옵니다.
  p0  <- get_near_price(prices, ymd(today))
  p1  <- get_near_price(prices, ymd(today) %m-% months(1))
  p3  <- get_near_price(prices, ymd(today) %m-% months(3))
  p6  <- get_near_price(prices, ymd(today) %m-% months(6))
  p12 <- get_near_price(prices, ymd(today) %m-% months(12))
  
  # [중요] 만약 상장한지 얼마 안 되어 12개월 전 가격(p12)이 NULL이면 에러 방지
   if (is.null(p1) || is.null(p12)) {
    message(paste("   ⚠️", code, ": 1년치 데이터가 부족합니다 (현재", nrow(prices), "행)"))
    return(NULL)
  }
  
  
  # 3. 수익률 계산
  r1  <- (today_price / p1  - 1) * 100
  r3  <- (today_price / p3  - 1) * 100
  r6  <- (today_price / p6  - 1) * 100
  r12 <- (today_price / p12 - 1) * 100
  
  message(paste("   ✅", code, ": 계산 성공"))
 
  tibble(
    close = round(p0, 0),
    `1M` = round(r1,  2),
    `3M` = round(r3,  2),
    `6M` = round(r6,  2),
    `1Y` = round(r12, 2),
    M_score = round((12*r1 + 4*r3 + 2*r6 + 1*r12) / 4, 2)
      )
}

# --------------------------------------------------
# 4. 입력 메타 테이블 → 최종 결과 테이블
# --------------------------------------------------
build_return_table <- function(token, input_df) {
  
  rows <- lapply(seq_len(nrow(input_df)), function(i) {
    meta <- as.tibble(input_df[i, ])
    returns <- calc_return_row(token = token,
                               code  = meta$Code
                               )
    if(is.null(returns)) return(NULL)
    bind_cols(meta, returns)
  })
  
  bind_rows(rows)
}


# --------------------------------------------------
# 5. 포트폴리오 추천 함수
# --------------------------------------------------
library(gt)
recommend_portfolio <- function(total_amount, balancing_vector) {
    target_date <- ymd(today) - days(30)
    
    nearest_df <- accum_final_df %>%
    filter(Date <= target_date) %>%
    group_by(Code) %>%
    slice_max(Date, n = 1, with_ties = FALSE) %>%
    ungroup() %>%
    select(Code, prev_M = M_score)
    
    res <- accum_final_df %>% filter(Date == ymd(today)) %>%
      left_join(nearest_df, by = "Code") %>%
      mutate(delta_M = M_score - prev_M) %>%
      arrange(desc(M_score)) %>%
      head(length(balancing_vector)) %>%
      mutate(
      비중 = balancing_vector,
      금액 = round(total_amount * (balancing_vector / 100), 0)
    ) %>%
    select(분류, 자산군, 명칭, Code, M_score,delta_M, 비중,금액)
  
    formatted_table <- res %>% gt() %>%
      tab_header(
        title = md("🚀 모멘텀 기반 포트폴리오 추천 🚀"),
        subtitle = paste0("분석 기준일: ", today, " | 총 투자금액: ", format(total_amount, big.mark=",",scientific = FALSE), "원")
      ) %>%fmt(
        columns = 비중,
        fns = function(x) paste0(x, "%")
      ) %>%
      # 나머지 포맷팅
      fmt_currency(columns = 금액, currency = "KRW", decimals = 0) %>%
      fmt_number(columns = M_score,decimals = 1 ) %>%
      text_transform(
        locations = cells_body(columns = delta_M),
        fn = function(x){
          num <- as.numeric(x)
          ifelse(
            num > 0,
            paste0("▲ ", sprintf("%.1f", num)),
            ifelse(
              num < 0,
              paste0("▼ ", sprintf("%.1f", abs(num))),
              "0.0"
            )
          )
        }
      ) %>%
      data_color(
        columns = M_score,
        fn = scales::col_numeric(palette = c("#ffffff", "#ffcccc"), domain = NULL)
      ) %>%
      tab_options(
        table.width = px(750),
        column_labels.background.color = "#f8f9fa",
        column_labels.font.weight = "bold"
      )
    
    return(formatted_table)
}
