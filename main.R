input_df <- read.csv("input_df.csv", fileEncoding = "CP949", colClasses = "character")
#today = format(Sys.Date(), "%Y%m%d")
today = "20260831"
source("auth.R")
source("momentum.R")

final_df <- build_return_table(token, input_df)
#final_df <- accum_final_df[accum_final_df$Date== as.Date("2026-02-28"),]

#누적데이터 만들기
accum_final_df <- readRDS("accum_final_df.rds")
accum_final_df <- final_df %>% mutate(Date=ymd(today)) %>% bind_rows(accum_final_df)
saveRDS(accum_final_df,"accum_final_df.rds")
#일부 데이터 삭제하기
#accum_final_df <- accum_final_df[accum_final_df$Date != as.Date("2026-07-31"),]

#투자 총 금액과 원하는 배분 비율 입력
Total <- c(0000000000000)
balancing <- c(10,20,0,0,20,20,0,30,0,0,0,0,0)

recommend <- recommend_portfolio(Total, balancing)
print(recommend)




#그래프로 분석
target_stocks <- c("KODEX 미국러셀2000(H)","KODEX 미국S&P500", "ACE KRX금현물", "KODEX MSCI선진국","KIWOOM 200TR","ACE 코스닥150", "RISE 미국나스닥100","TIGER 미국달러단기채권액티브", "ACE 미국30년국채액티브")
library(ggplot2)
p <- accum_final_df %>% filter(Date>="2025-07-01") %>%
 filter(명칭 %in% target_stocks) %>%
 ggplot(aes(x = Date, y = M_score, color = 명칭, group = 명칭, linetype = 분류)) +
        geom_line(linewidth = 1) +
        geom_point(size = 2) +
        labs(title = "주요 종목별 M-score 추이",
              subtitle = format(Sys.Date(), "%Y%m%d"),
              x = "날짜",
              y = "M-score",
              color = "종목명") +
        scale_x_date(date_breaks = "3 month",date_labels = "%y.%m") +
       theme_minimal() +
       theme(legend.position = "bottom",
              title = element_text(face = "bold", size = 14),
              axis.title = element_text(size = 10))
print(p)
