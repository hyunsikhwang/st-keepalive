# 파일명: visit_app.py
from playwright.sync_api import sync_playwright
import time
import os

def get_urls_from_file(filename="urls.txt"):
    """파일에서 URL 목록을 읽어옵니다."""
    url_list = []
    
    if not os.path.exists(filename):
        print(f"❌ [오류] '{filename}' 파일이 존재하지 않습니다.")
        return []

    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            # 공백 제거
            clean_line = line.strip()
            # 빈 줄이거나 #으로 시작하는 주석 라인은 무시
            if clean_line and not clean_line.startswith("#"):
                url_list.append(clean_line)
    
    return url_list

def run():
    # 1. 파일에서 URL 로드
    target_urls = get_urls_from_file()

    if not target_urls:
        print("점검할 URL이 없습니다. 스크립트를 종료합니다.")
        return

    print(f"📋 총 {len(target_urls)}개의 사이트가 로드되었습니다.\n")

    with sync_playwright() as p:
        # 브라우저 실행 (Headless 모드)
        browser = p.chromium.launch(headless=True)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        for idx, url in enumerate(target_urls, 1):
            print(f"--- [{idx}/{len(target_urls)}] 접속 시도: {url} ---")
            
            page = context.new_page()
            
            try:
                # 사이트 접속
                page.goto(url, timeout=60000)
                
                # 로딩 대기
                print("페이지 로딩 중... (15초 대기)")
                page.wait_for_timeout(15000) 

                # '앱 깨우기' 버튼 감지 및 클릭
                try:
                    wake_up_btn = page.get_by_role("button", name="Yes, get this app back up")
                    
                    if wake_up_btn.is_visible(timeout=5000):
                        print("🚨 'Sleep Mode' 감지됨! 깨우기 버튼을 클릭합니다.")
                        wake_up_btn.click()
                        print("버튼 클릭 완료. 앱 재실행 대기 (40초)...")
                        page.wait_for_timeout(40000) 
                    else:
                        print("✅ 앱이 이미 활성화되어 있습니다.")
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