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

    try:
        for site in sites:
            site_name = site["name"]
            url = site["url"]
            target_boats = site.get("target_boats", [])

            print(f"접속 중: {site_name}")
            
            try:
                driver.get(url)
                # 📌 페이지 본문이 나타날 때까지 최대 10초 대기
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except Exception:
                print(f"⚠️ {site_name} 로딩 지연 발생")

            # 팝업 닫고 자바스크립트가 데이터를 완전히 그릴 수 있도록 4초 대기
            time.sleep(4)
            close_popups(driver)

            # 월 선택 버튼 클릭 시도
            try:
                month_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '10월') or contains(text(), '9월')]")
                if month_btns:
                    month_btns[0].click()
                    time.sleep(3) # 클릭 후 달력 로딩 대기
                    print(f" -> {site_name} 월 버튼 클릭 완료")
            except Exception:
                pass

            page_source = driver.page_source

            for date_str in target_dates:
                parts = date_str.replace("일", "").split("월")
                if len(parts) == 2:
                    m_part = parts[0].strip() + "월"
                    d_part = parts[1].strip()
                    date_found = (m_part in page_source) and (d_part in page_source)
                else:
                    date_found = date_str in page_source

                if date_found:
                    for boat in target_boats:
                        if boat in page_source:
                            if "예약하기" in page_source:
                                msg = f"🎉 **[진짜 빈자리 발견!]**\n\n선단: {site_name}\n배 이름: **{boat}**\n날짜: 📅 **{date_str}**\n👉 [바로 예약하기]({url})"
                                send_telegram_message(msg)
                                print(f" - {date_str} [{boat}]: 예약하기 포착!")
                            elif "대기하기" in page_source:
                                print(f" - {date_str} [{boat}]: 대기하기 상태")
                            else:
                                print(f" - {date_str} [{boat}]: 마감 상태")
                        else:
                            print(f" - {date_str}: '{boat}' 정보 없음")
                else:
                    print(f" - {date_str}: 날짜 정보 없음")

                time.sleep(0.5)

        print("모든 검사 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"⚠️ [오류 발생] 낚시배 확인 중 에러: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_specific_boats()
