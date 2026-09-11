import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[알림] {text}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def check_all_combinations():
    if not os.path.exists("config.json"):
        print("config.json 파일이 없습니다.")
        return

    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    sites = config.get("sites", [])
    target_dates = config.get("target_dates", [])

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        # 배 사이트별로 접속
        for site in sites:
            name = site["name"]
            url = site["url"]

            print(f"접속 중: {name}")
            driver.get(url)
            time.sleep(3)

            page_source = driver.page_source

            # 등록된 모든 날짜를 각각 검사
            for date in target_dates:
                print(f" - 검사 날짜: {date}")
                
                if date in page_source:
                    if "예약하기" in page_source:
                        msg = f"🎉 **[대박! 빈자리 발견]**\n\n**{name}**\n📅 **{date}** 예약 가능 상태 포착!\n👉 [바로 예약하기]({url})"
                        send_telegram_message(msg)
                    else:
                        print(f"   -> {date}: 날짜는 있으나 마감 상태")
                else:
                    print(f"   -> {date}: 정보 없음")

                time.sleep(1)

        print("모든 검사 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"⚠️ [오류 발생] 낚시배 확인 중 에러: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_all_combinations()
