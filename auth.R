library(httr2)
library(jsonlite)
library(lubridate)

appkey <- readLines("52193434_appkey.txt", warn = FALSE)
secretkey <- readLines("52193434_secretkey.txt", warn = FALSE)
KIWOOM_HOST <- "https://api.kiwoom.com"   # 실전
TOKEN_FILE  <- "kiwoom_token.rds"

request_token <- function(appkey, secretkey) {
  
  req <- request(paste0(KIWOOM_HOST, "/oauth2/token")) |>
    req_method("POST") |>
    req_headers(
      "Content-Type" = "application/json;charset=UTF-8",
      "api-id"       = "AU10001"   
    ) |>
    req_body_json(list(
      grant_type = "client_credentials",
      appkey     = appkey,
      secretkey  = secretkey
    ))
  
  resp <- req_perform(req)
  body <- resp_body_json(resp, simplifyVector = TRUE)
  
  # 방어 코드
  if (is.null(body$token)) {
    stop("❌ access_token 없음:\n", toJSON(body, auto_unbox = TRUE, pretty = TRUE))
  }
  
  token <- list(
    access_token = body$token,
    token_type   = body$token_type,
    expires_dt   = ymd_hms(body$expires_dt)
  )
  
  saveRDS(token, TOKEN_FILE)
  token
}


#----------------------------------------------------------
# 토큰 가져오기 (있으면 재사용)
#----------------------------------------------------------
get_token <- function(appkey, secretkey) {
  
  if (file.exists(TOKEN_FILE)) {
    
    token <- tryCatch(readRDS(TOKEN_FILE),error = function(e) NULL)
    
    if (is.list(token) &&
        !is.null(token$access_token) &&
        !is.null(token$expires_at)) {
      
      if (Sys.time() < token$expires_at) {
        message("✅ 기존 토큰 사용")
        return(token$access_token)
      }
    }
  }
  message("🔄 새 토큰 발급 중...")
  res <- request_token(appkey, secretkey)
  return(res$access_token)
}

token <- get_token(appkey, secretkey)