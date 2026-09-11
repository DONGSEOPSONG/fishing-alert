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
    # 넉넉하게 15초 타임아웃 설정
    driver.set_page_load_timeout(15)

    try:
        for site in sites:
            site_name = site["name"]
            url = site["url"]
            target_boats = site.get("target_boats", [])

            print(f"접속 중: {site_name}")
            
            try:
                driver.get(url)
            except Exception:
                print(f"⚠️ {site_name} 페이지 로딩 타임아웃 발생 (계속 진행)")

            # 페이지가 렌더링되도록 충분히 대기
            time.sleep(4)
            remove_popups_aggressively(driver)

            # 스크롤을 살짝 내려서 지연 로딩되는 콘텐츠 유도
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)

            # 월 선택 버튼(10월 등)이 있으면 클릭 시도
            try:
                month_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '10월') or contains(text(), '9월')]")
                if month_btns:
                    month_btns[0].click()
                    time.sleep(3)
            except Exception:
                pass

            # 페이지 내에서 스케줄이나 텍스트를 담고 있는 요소들을 폭넓게 수집
            elements = driver.find_elements(By.XPATH, "//tr | //li | //div[contains(@class, 'schedule') or contains(@class, 'item') or contains(@class, 'box') or contains(@class, 'list')]")
            
            # 만약 요소를 못 찾았다면 body 전체 텍스트 활용을 위한 예비 조치
            page_source = driver.page_source

            for date_str in target_dates:
                parts = date_str.replace("일", "").split("월")
                if len(parts) == 2:
                    m_val = parts[0].strip()
                    d_val = parts[1].strip()
                else:
                    m_val = ""
                    d_val = ""

                for boat in target_boats:
                    found_real_slot = False
                    status_msg = "마감 또는 정보 없음"

                    for el in elements:
                        try:
                            text = el.text
                            date_matched = (date_str in text) or (m_val and d_val and m_val in text and d_val in text)
                            
                            if date_matched and boat in text:
                                if "예약하기" in text:
                                    found_real_slot = True
                                    status_msg = "예약하기 가능"
                                    break
                                elif "대기하기" in text:
                                    status_msg = "대기하기 상태"
                                    break
                                else:
                                    status_msg = "마감 상태"
                        except Exception:
                            continue

                    # 만약 요소를 못 찾았거나 세밀한 매칭 안에서 못 찾았을 때 전체 소스 fallback 검사
                    if not found_real_slot and status_msg == "마감 또는 정보 없음":
                        if date_str in page_source and boat in page_source:
                            if "예약하기" in page_source:
                                # 주의: 전체 소스 검색이므로 해당 날짜/배 근처인지 한 번 더 확인 필요하지만 
                                # 일단 가독성을 위해 상태 분기
                                pass

                    if found_real_slot:
                        msg = f"🎉 **[진짜 빈자리 발견!]**\n\n선단: {site_name}\n배 이름: **{boat}**\n날짜: 📅 **{date_str}**\n👉 [바로 예약하기]({url})"
                        send_telegram_message(msg)
                        print(f" - {date_str} [{boat}]: 예약하기 포착 (알람 발송)")
                    else:
                        print(f" - {date_str} [{boat}]: {status_msg}")

                time.sleep(0.3)

        print("모든 검사 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"⚠️ [오류 발생] 낚시배 확인 중 에러: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_specific_boats()
