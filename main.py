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
                    m_val = parts[0].strip() # 예: "11"
                    d_val = parts[1].strip() # 예: "16"
                else:
                    continue

                # 📌 1단계: 원하는 월(예: 11월) 텍스트가 달력에 보일 때까지 다음 달 버튼을 누르거나 해당 월 버튼 직접 클릭
                month_found = False
                for _ in range(3): # 최대 3번까지 다음 달로 넘기며 탐색
                    try:
                        month_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{m_val}월')]")
                        for el in month_elements:
                            if len(el.text.strip()) <= 10:
                                month_found = True
                                break
                        if month_found:
                            break
                        
                        # 월이 안 보이면 다음 달 화살표(> 또는 next) 클릭 시도
                        next_btns = driver.find_elements(By.XPATH, "//a[contains(@class, 'next') or contains(@class, 'fc-next-button') or contains(text(), '>') or contains(text(), '다음')]")
                        if next_btns:
                            next_btns[0].click()
                            time.sleep(2)
                    except Exception:
                        break

                # 📌 2단계: 해당 일자(일) 숫자 버튼 클릭
                clicked_date = False
                try:
                    day_elements = driver.find_elements(By.XPATH, f"//*[text()='{d_val}' or text()='{d_val}일']")
                    for el in day_elements:
                        parent_tag = el.tag_name.lower()
                        if parent_tag in ['a', 'span', 'li', 'button', 'div', 'td'] and len(el.text.strip()) <= 3:
                            el.click()
                            time.sleep(3)
                            clicked_date = True
                            break
                except Exception:
                    pass

                if not clicked_date:
                    print(f" - {date_str} [{site_name}]: 해당 일자 버튼 클릭 실패")
                    continue

                # 📌 3단계: 표의 각 행(<tr>)을 수집하여 예약 상태 정밀 분석
                rows = driver.find_elements(By.TAG_NAME, "tr")

                for boat in target_boats:
                    found_real_slot = False
                    status_msg = "마감 또는 정보 없음"

                    for row in rows:
                        try:
                            row_text = row.text
                            if boat in row_text:
                                # 예약완료, 마감, 대기 키워드가 있으면 차단
                                if any(kw in row_text for kw in ["예약완료", "예약 완료", "대기하기", "예약마감", "마감", "매진"]):
                                    status_msg = "마감 / 예약완료 상태"
                                    break
                                
                                # 예약 가능 상태 확인 ("예약하기", "바로예약", 또는 잔여석 "명")
                                if "예약하기" in row_text or "바로예약" in row_text or ("명" in row_text and "입금자" not in row_text):
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
