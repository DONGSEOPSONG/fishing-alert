import os
import requests
from bs4 import BeautifulSoup

# 오천항 제우스호 예약 페이지
my_favorite_sites = [
    {
        "name": "오천항 제우스호",
        "url": "https://www.ochzeus.com/index.php?mid=bk" 
    }
]

target_date = "10월 2일"  # 확인하고 싶은 날짜 (사이트 표기에 따라 "10/2" 등으로 변경 가능)

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
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(site["url"], headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"접속 실패: {site['name']}")
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text()

            # 지정한 날짜가 페이지 내에 있는지 확인
            if target_date in page_text:
                msg = f"[예약 페이지 감지] {site['name']}에서 '{target_date}' 관련 글자가 확인되었습니다!\n링크: {site['url']}"
                send_telegram_message(msg)
                print(msg)
            else:
                print(f"'{target_date}' 정보 없음: {site['name']}")
                
        except Exception as e:
            print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_seats()
