import os
import requests
from bs4 import BeautifulSoup

# 내가 감시하고 싶은 사이트 목록
my_favorite_sites = [
    {
        "name": "낚시배 사이트 이름",
        "url": "https://www.ochzeus.com" 
    }
]

target_date = "10월 2일"  # 찾고 싶은 날짜

def send_telegram_message(text):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def check_seats():
    for site in my_favorite_sites:
        try:
            response = requests.get(site["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text()

            # 사이트 글자에 내가 찾는 날짜가 포함되어 있는지 확인
            if target_date in page_text:
                msg = f"[빈자리 알림] {site['name']}에 {target_date} 예약 페이지가 열렸거나 자리가 있습니다!\n확인하기: {site['url']}"
                send_telegram_message(msg)
                print(msg)
            else:
                print(f"{target_date} 발견 안 됨: {site['name']}")
        except Exception as e:
            print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_seats()
