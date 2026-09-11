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

def remove_popups(driver):
    script = """
    try {
        var selectors = ['.popup', '.layer_popup', '#popup', 'div[id*="popup"]', '.modal', '.layer', '.dimmed', '.overlay'];
        selectors.forEach(function(sel) {
            document.querySelectorAll(sel).forEach(function(el) { el.remove(); });
        });
        document.body.style.overflow = 'auto';
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

    try:
        for site in sites:
            site_name = site["name"]
            url = site["url"]
            target_boats = site.get("target_boats", [])

            print(f"\n접속 중: {site_name}")
            
            try:
                driver.get(url)
            except Exception:
                print(f"⚠️ {site_name} 로딩 지연 (진행)")

            time.sleep(5)
            remove_popups(driver)
            driver.execute_script("window.scrollTo(0, 700);")
            time.sleep(2)

            # 월 선택 버튼 클릭 시도 (10월, 9월 등)
            try:
                month_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '10월') or contains(text(), '9월')]")
                if month_btns:
                    month_btns[0].click()
                    time.sleep(3)
            except Exception:
                pass

            # 각 배나 일정별로 격리된 컨테이너 블록 수집
            blocks = driver.find_elements(By.XPATH, "//tr | //li | //div[contains(@class, 'schedule') or contains(@class, 'item') or contains(@class, 'box') or contains(@class, 'list') or contains(@class, 'row') or contains(@class, 'ship')]")

            for date_str in target_dates:
                parts = date_str.replace("일", "").split("월")
                m_val = parts[0].strip() if len(parts) == 2 else ""
                d_val = parts[1].strip() if len(parts) == 2 else ""

                for boat in target_boats:
                    found_real_slot = False
                    status_msg = "마감 또는 정보 없음"

                    for block in blocks:
                        try:
                            text = block.text
                            # 1. 블록 안에 배 이름과 날짜가 동시에 포함되어 있는지 확인
                            has_date = (date_str in text) or (m_val and d_val and m_val in text and d_val in text)
                            
                            if has_date and boat in text:
                                # 2. 마감, 완료, 대기 문구가 있으면 확실히 제외
                                if any(kw in text for kw in ["대기하기", "예약마감", "마감", "예약완료", "예약 완료", "매진"]):
                                    status_msg = "마감/대기 상태"
                                    break
                                # 3. 명확하게 예약 가능한 버튼이 있을 때만 인정
                                elif "예약하기" in text or "바로예약" in text:
                                    found_real_slot = True
                                    status_msg = "예약 가능"
                                    break
                        except Exception:
                            continue

                    if found_real_slot:
                        msg = f"🎉 **[진짜 빈자리 발견!]**\n\n선단: {site_name}\n배 이름: **{boat}**\n날짜: 📅 **{date_str}**\n👉 [바로 예약하기]({url})"
                        send_telegram_message(msg)
                        print(f" - {date_str} [{boat}]: 예약 가능! (알림 발송)")
                    else:
                        print(f" - {date_str} [{boat}]: {status_msg}")

                time.sleep(0.2)

        print("\n모든 검사 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"⚠️ [오류 발생] 에러: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_specific_boats()
