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

def close_popups(driver):
    try:
        driver.execute_script("""
            var popups = document.querySelectorAll('.popup, .layer_popup, #popup, div[id*="popup"]');
            popups.forEach(function(popup) {
                popup.style.display = 'none';
            });
        """)
    except Exception:
        pass

def check_specific_boats():
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
    
    # 📌 페이지 로딩 최대 대기 시간을 10초로 제한 (무한 대기 방지)
    driver.set_page_load_timeout(10)

    try:
        for site in sites:
            site_name = site["name"]
            url = site["url"]
            target_boats = site.get("target_boats", [])

            print(f"접속 중: {site_name}")
            
            try:
                driver.get(url)
            except Exception:
                print(f"⚠️ {site_name} 로딩 시간이 길어져서 강제로 다음 단계를 진행합니다.")

            time.sleep(2)
            close_popups(driver)

            page_source = driver.page_source

            for date in target_dates:
                if date in page_source:
                    for boat in target_boats:
                        if boat in page_source:
                            if "예약하기" in page_source:
                                msg = f"🎉 **[원하던 배 빈자리 발견!]**\n\n선단: {site_name}\n배 이름: **{boat}**\n날짜: 📅 **{date}**\n👉 [바로 예약하기]({url})"
                                send_telegram_message(msg)
                            else:
                                print(f" - {date} [{boat}]: 마감 상태")
                        else:
                            print(f" - {date}: '{boat}' 정보 없음")
                else:
                    print(f" - {date}: 날짜 정보 없음")

                time.sleep(0.5)

        print("모든 검사 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"⚠️ [오류 발생] 낚시배 확인 중 에러: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_specific_boats()
