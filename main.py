import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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

def remove_popups_aggressively(driver):
    script = """
    try {
        var selectors = [
            '.popup', '.layer_popup', '#popup', 'div[id*="popup"]', 
            '.modal', '.layer', '.dimmed', '.overlay', 
            'div[class*="popup"]', 'div[class*="modal"]', 'div[class*="layer"]'
        ];
        selectors.forEach(function(sel) {
            document.querySelectorAll(sel).forEach(function(el) {
                el.remove();
            });
        });
        document.body.style.overflow = 'auto';
        document.documentElement.style.overflow = 'auto';
    } catch(e) {}
    """
    try:
        driver.execute_script(script)
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
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(10)

    try:
        for site in sites:
            site_name = site["name"]
            url = site["url"]
            target_boats = site.get("target_boats", [])

            print(f"\n접속 중: {site_name}")
            
            try:
                driver.get(url)
            except Exception:
                print(f"⚠️ {site_name} 로딩 시간 초과 (수집 모드 진입)")

            time.sleep(3)
            remove_popups_aggressively(driver)

            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)

            try:
                month_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '10월') or contains(text(), '9월')]")
                if month_btns:
                    month_btns[0].click()
                    time.sleep(3)
            except Exception:
                pass

            # 📌 전체 페이지 소스 자체를 가져와서 배 이름과 날짜, 예약 가능 여부를 유연하게 통합 검사
            page_source = driver.page_source

            for date_str in target_dates:
                parts = date_str.replace("일", "").split("월")
                if len(parts) == 2:
                    m_val = parts[0].strip() + "월"
                    d_val = parts[1].strip()
                else:
                    m_val = ""
                    d_val = ""

                for boat in target_boats:
                    # 1단계: 날짜와 배 이름이 페이지 내에 모두 존재하는지 확인
                    date_found = (date_str in page_source) or (m_val and d_val and m_val in page_source and d_val in page_source)
                    
                    if date_found and boat in page_source:
                        # 2단계: 해당 배가 마감/완료/대기 상태인지 확인하기 위해, 텍스트 상에서 배 이름 주변이나 전체 소스 상태 파악
                        # (단순 무식하게 전체 소스에 "예약하기"가 있다고 돌리면 다른 배에 낚이므로, 
                        #  배 이름 근처에 "예약하기" 또는 "바로예약"이 명확히 살아있는지 체크)
                        
                        # 각 배별 고유 블록을 다시 정밀 탐색
                        blocks = driver.find_elements(By.XPATH, "//tr | //div[contains(@class, 'schedule') or contains(@class, 'item') or contains(@class, 'box') or contains(@class, 'list') or contains(@class, 'row') or contains(@class, 'ship') or contains(@class, 'schedule_box')]")
                        
                        found_real_slot = False
                        status_msg = "마감 또는 대기 상태"

                        for block in blocks:
                            try:
                                b_text = block.text
                                if boat in b_text:
                                    d_matched = (date_str in b_text) or (m_val and d_val and m_val in b_text and d_val in b_text)
                                    if d_matched:
                                        if any(kw in b_text for kw in ["대기하기", "예약마감", "마감", "예약완료", "예약 완료", "매진"]):
                                            status_msg = "마감 또는 대기 상태"
                                            break
                                        elif "예약하기" in b_text or "바로예약" in b_text:
                                            found_real_slot = True
                                            status_msg = "예약 가능"
                                            break
                            except Exception:
                                continue

                        if found_real_slot:
                            msg = f"🎉 **[진짜 빈자리 발견!]**\n\n선단: {site_name}\n배 이름: **{boat}**\n날짜: 📅 **{date_str}**\n👉 [바로 예약하기]({url})"
                            send_telegram_message(msg)
                            print(f" - {date_str} [{boat}]: 예약 가능 포착! (알람 발송)")
                        else:
                            print(f" - {date_str} [{boat}]: {status_msg}")
                    else:
                        print(f" - {date_str} [{boat}]: 날짜 또는 배 정보 없음")

                time.sleep(0.2)

        print("\n모든 검사 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"⚠️ [오류 발생] 낚시배 확인 중 에러: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_specific_boats()
