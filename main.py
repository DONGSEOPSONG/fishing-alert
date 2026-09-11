import os
import time
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
    
    # 파란색 링크가 예쁘게 눌리도록 마크다운(Markdown) 형식 적용
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def check_zeus_seats():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    
    try:
        target_url = "https://www.ochzeus.com/index.php?mid=bk"
        driver.get(target_url)
        time.sleep(3)

        page_source = driver.page_source
        
        if "10월" in page_source and "2일" in page_source:
            if "예약하기" in page_source:
                # [링크 이름](주소) 형식으로 넣으면 텔레그램에서 누를 수 있는 파란색 링크가 돼요!
                msg = f"🎉 **[대박! 빈자리 발견]**\n\n오천항 제우스호 10월 2일 예약 가능 상태 포착!\n👉 [여기서 바로 예약하기]({target_url})"
            else:
                msg = f"🔍 **[예약 현황 확인]**\n\n10월 2일 날짜는 있지만 현재 예약 마감 상태입니다.\n🔗 [페이지 확인하기]({target_url})"
        else:
            msg = f"⏳ **[정보 대기중]**\n\n아직 10월 2일 정보가 없거나 확인이 필요합니다.\n🔗 [사이트 직접 가보기]({target_url})"

        send_telegram_message(msg)
        print("텔레그램 알림 전송 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_telegram_message(f"⚠️ [오류 발생] 낚시배 확인 중 에러가 났어요: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    check_zeus_seats()
