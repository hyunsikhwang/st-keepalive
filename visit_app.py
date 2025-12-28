# 파일명: visit_app.py
from playwright.sync_api import sync_playwright
import time

def run():
    # 관리할 사이트 목록
    target_urls = [
        "https://naverblog.streamlit.app/",
        "https://yt-shot.streamlit.app/",
        "https://yt-thumb.streamlit.app/"
    ]

    with sync_playwright() as p:
        # 브라우저 실행 (Headless 모드)
        browser = p.chromium.launch(headless=True)
        
        # 봇 탐지 회피를 위한 User-Agent 설정
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        print(f"총 {len(target_urls)}개의 사이트 점검을 시작합니다.\n")

        for idx, url in enumerate(target_urls, 1):
            print(f"--- [{idx}/{len(target_urls)}] 접속 시도: {url} ---")
            
            page = context.new_page()
            
            try:
                # 1. 사이트 접속 (타임아웃 60초)
                page.goto(url, timeout=60000)
                
                # 2. 로딩 대기
                print("페이지 로딩 중... (15초 대기)")
                page.wait_for_timeout(15000) 

                # 3. '앱 깨우기' 버튼 감지 및 클릭 로직
                try:
                    wake_up_btn = page.get_by_role("button", name="Yes, get this app back up")
                    
                    if wake_up_btn.is_visible(timeout=5000):
                        print("🚨 'Sleep Mode' 감지됨! 깨우기 버튼을 클릭합니다.")
                        wake_up_btn.click()
                        print("버튼 클릭 완료. 앱이 재실행될 때까지 40초 대기합니다.")
                        page.wait_for_timeout(40000) # 재부팅은 시간이 더 걸리므로 넉넉히 대기
                    else:
                        print("✅ 앱이 이미 활성화되어 있습니다.")
                        # 활성 상태라도 확실한 세션 유지를 위해 약간 더 머무름
                        page.wait_for_timeout(5000) 

                except Exception:
                    print("버튼 탐색 중 예외 발생 (활성 상태로 간주)")

                print(f"현재 페이지 제목: {page.title()}")
                print(f"[{url}] 점검 완료.\n")

            except Exception as e:
                print(f"❌ [{url}] 접속 중 에러 발생: {e}\n")
            
            finally:
                page.close()

        browser.close()
        print("모든 작업이 종료되었습니다.")

if __name__ == "__main__":
    run()