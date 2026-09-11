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
            driver.execute_script("window.scrollTo(0, 400);")
            time.sleep(2)

            for date_str in target_dates:
                parts = date_str.replace("일", "").split("월")
                if len(parts) == 2:
                    m_val = parts[0].strip()
                    d_val = parts[1].strip()
                else:
                    continue

                # 1단계: 월 버튼 클릭
                try:
                    month_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{m_val}')]")
                    for el in month_elements:
                        if "월" in el.text and len(el.text) <= 5:
                            el.click()
                            time.sleep(2)
                            break
                except Exception:
                    pass

                # 2단계: 날짜(일자) 버튼 클릭
                try:
                    day_elements = driver.find_elements(By.XPATH, f"//*[text()='{d_val}' or text()='{d_val}일']")
                    for el in day_elements:
                        if el.tag_name.lower() in ['a', 'span', 'li', 'button', 'div'] and len(el.text.strip()) <= 3:
                            el.click()
                            time.sleep(3)
                            break
                except Exception:
                    pass

                # 3단계: 표의 각 행(<tr>)을 수집하여 배별 상태 정밀 분석
                rows = driver.find_elements(By.TAG_NAME, "tr")

                for boat in target_boats:
                    found_real_slot = False
                    status_msg = "마감 또는 정보 없음"

                    for row in rows:
                        try:
                            row_text = row.text
                            # 해당 행에 찾으려는 배 이름이 포함되어 있는지 확인
                            if boat in row_text:
                                # 예약완료나 마감, 대기 키워드가 행에 있으면 마감 처리
                                if any(kw in row_text for kw in ["예약완료", "예약 완료", "대기하기", "예약마감", "마감", "매진"]):
                                    status_msg = "마감 / 예약완료 상태"
                                    break
                                # "예약하기", "바로예약", 혹은 잔여석 숫자가 표시된 경우(예: "20명") 빈자리로 인정
                                elif "예약하기" in row_text or "바로예약" in row_text or "명" in row_text:
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

                time.sleep(0.3)

        print("\n모든 검사 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"⚠️ [오류 발생] 에러: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_specific_boats()
