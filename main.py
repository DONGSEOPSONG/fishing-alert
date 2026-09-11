import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    """사이트 접속 시 뜨는 팝업창을 자동으로 닫는 함수"""
    try:
        # 흔히 쓰이는 팝업 닫기 버튼들 (오늘 하루 그만 보기, 닫기 등)
        close_selectors = [
            "button.close", 
            ".pop_close", 
            "input[value*='닫기']", 
            "a.close",
            ".popup-close",
            "button:contains('닫기')"
        ]
        
        # 팝업이 뜰 시간을 잠깐 기다림
        time.sleep(1)
        
        # 자바스크립트로 화면에 보이는 팝업 요소들을 강제로 숨기거나 닫기 버튼 클릭 시도
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

    try:
        for site in sites:
            site_name = site["name"]
            url = site["url"]
            target_boats = site.get("target_boats", [])

            print(f"접속 중: {site_name}")
            driver.get(url)
            time.sleep(3)

            # 접속하자마자 팝업창 닫기 실행!
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
                                print(f" - {date} [{boat}]: 날짜와 배 이름은 있으나 마감 상태")
                        else:
                            print(f" - {date}: 해당 페이지에 '{boat}' 정보 없음")
                else:
                    print(f" - {date}: 날짜 정보 없음")

                time.sleep(1)

        print("모든 검사 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"⚠️ [오류 발생] 낚시배 확인 중 에러: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_specific_boats()
