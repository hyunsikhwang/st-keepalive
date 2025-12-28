import os
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError


TARGET_URL = os.getenv("STREAMLIT_URL", "https://naverblog.streamlit.app/").strip()
# 일부 환경에서 리다이렉트/임베드 이슈가 있을 수 있어 보조 URL도 함께 시도
URL_CANDIDATES = [
    TARGET_URL,
    TARGET_URL.rstrip("/") + "/?embed=true",
]

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)

# Streamlit Cloud sleep 페이지의 버튼 텍스트(공식 문서에 언급된 문구) + 일부 변형 대비
WAKE_TEXT_RE = re.compile(
    r"(Yes,\s*)?get this app back up|wake.*app|앱.*(깨우|다시)|다시.*(켜|시작)",
    re.IGNORECASE,
)

# 앱이 “정상 렌더링” 되었음을 대략적으로 확인할 때 쓸 후보 셀렉터들(버전/테마 차이를 감안해 복수로)
READY_SELECTORS = [
    "div[data-testid='stAppViewContainer']",
    "div[data-testid='stApp']",
    "div.stApp",
    "section.main",
]


def _stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(30_000)

        last_err = None
        for url in URL_CANDIDATES:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                current_url = url
                break
            except Exception as e:
                last_err = e
        else:
            raise RuntimeError(f"URL 접속 실패: {last_err!r}")

        # 1) Sleep(ZZZ) 페이지면 깨우기 버튼 클릭
        try:
            wake_btn = page.get_by_role("button", name=WAKE_TEXT_RE)
            if wake_btn.count() > 0 and wake_btn.first.is_visible():
                wake_btn.first.click()
            else:
                # 혹시 button이 아니라 link로 잡히는 경우 대비
                wake_link = page.get_by_role("link", name=WAKE_TEXT_RE)
                if wake_link.count() > 0 and wake_link.first.is_visible():
                    wake_link.first.click()
        except Exception:
            # 버튼 탐지 실패는 “이미 깨어있음”일 수 있으므로 치명 오류로 보지 않음
            pass

        # 2) 앱이 완전히 살아날 때까지 대기 (최대 5분)
        ready = False
        last_timeout = None
        for sel in READY_SELECTORS:
            try:
                page.wait_for_selector(sel, timeout=300_000)  # 5분
                ready = True
                break
            except PWTimeoutError as e:
                last_timeout = e

        # 디버그 산출물 저장
        tag = _stamp()
        try:
            page.screenshot(path=str(DEBUG_DIR / f"{tag}_final.png"), full_page=True)
        except Exception:
            pass

        if not ready:
            raise RuntimeError(
                f"앱이 5분 내 정상 렌더링 상태로 전환되지 않았습니다. url={current_url} err={last_timeout!r}"
            )

        browser.close()


if __name__ == "__main__":
    main()
