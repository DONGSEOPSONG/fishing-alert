import os
import time
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
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def check_zeus_seats():
    options = Options()
    options.add_argument("--headless")  # 화면 없이 백그라운드 실행
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    
    try:
        # 1. 제우스호 예약 페이지 접속
        driver.get("https://www.ochzeus.com/index.php?mid=bk")
        time.sleep(3)

        # 2. 10월과 2일 버튼 클릭 (사이트 구조에 따라 수정 필요할 수 있음)
        # 예시: 10월 버튼이나 달력 날짜 '2'를 찾는 코드
        # (실제 사이트 버튼 속성에 맞춰 클릭 명령 수행)
        
        # 임시로 페이지 전체 텍스트에서 '10월'과 '2일' 상태 확인
        page_source = driver.page_source
        
        if "10월" in page_source and "2일" in page_source:
            # '예약하기' 또는 '마감' 버튼 상태 확인
            if "예약하기" in page_source:
                msg = "[대박] 오천항 제우스호 10월 2일 빈자리(예약 가능)가 포착되었습니다!"
            else:
                msg = "[확인] 10월 2일 날짜는 보이지만 현재 '예약마감' 상태이거나 빈자리가 없습니다."
        else:
            msg = "[확인] 아직 10월 2일 예약 창이 오픈되지 않았거나 정보를 찾을 수 없습니다."

        send_telegram_message(msg)
        print(msg)

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"[오류] 낚시배 확인 중 에러 발생: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_zeus_seats()
