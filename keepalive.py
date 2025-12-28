import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError


DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)

# Streamlit Cloud sleep 페이지의 버튼 텍스트(영문/한글 일부 변형 대비)
WAKE_TEXT_RE = re.compile(
    r"(Yes,\s*)?get this app back up|wake.*app|앱.*(깨우|다시)|다시.*(켜|시작)",
    re.IGNORECASE,
)

# "정상 렌더링"을 대략 확인할 때 쓸 후보 셀렉터들(버전/테마 차이를 감안해 복수)
READY_SELECTORS = [
    "div[data-testid='stAppViewContainer']",
    "div[data-testid='stApp']",
    "div.stApp",
    "section.main",
]


def _stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _slug(url: str) -> str:
    p = urlparse(url)
    host = (p.hostname or "unknown").replace(".", "_")
    return host


def _parse_urls() -> list[str]:
    raw = os.getenv("STREAMLIT_URLS", "").strip()
    if raw:
        parts = re.split(r"[\n,]+", raw)
        urls = [p.strip() for p in parts if p.strip()]
    else:
        # 하위호환: 단일 URL
        single = os.getenv("STREAMLIT_URL", "").strip()
        urls = [single] if single else []

    if not urls:
        raise RuntimeError("환경변수 STREAMLIT_URLS(또는 STREAMLIT_URL)가 비어 있습니다.")
    return urls


def _url_candidates(base: str) -> list[str]:
    base = base.strip()
    if not base:
        return []
    base_no_slash = base.rstrip("/")
    return [
        base,  # 원본
        base_no_slash + "/?embed=true",  # 보조 시도
    ]


def _wake_if_needed(page) -> None:
    # 1) Sleep(ZZZ) 페이지면 깨우기 버튼/링크 클릭 시도
    try:
        wake_btn = page.get_by_role("button", name=WAKE_TEXT_RE)
        if wake_btn.count() > 0 and wake_btn.first.is_visible():
            wake_btn.first.click()
            return
    except Exception:
        pass

    try:
        wake_link = page.get_by_role("link", name=WAKE_TEXT_RE)
        if wake_link.count() > 0 and wake_link.first.is_visible():
            wake_link.first.click()
            return
    except Exception:
        pass


def _wait_until_ready(page, timeout_ms: int = 300_000) -> bool:
    # 2) 앱이 완전히 살아날 때까지 대기 (최대 5분)
    for sel in READY_SELECTORS:
        try:
            page.wait_for_selector(sel, timeout=timeout_ms)
            return True
        except PWTimeoutError:
            continue
    return False


def _save_debug(page, site_tag: str, stage: str) -> None:
    tag = f"{_stamp()}_{site_tag}_{stage}"
    try:
        page.screenshot(path=str(DEBUG_DIR / f"{tag}.png"), full_page=True)
    except Exception:
        pass


def keepalive_one(page, url: str) -> None:
    site_tag = _slug(url)

    last_err = None
    used_url = None
    for candidate in _url_candidates(url):
        try:
            page.goto(candidate, wait_until="domcontentloaded", timeout=60_000)
            used_url = candidate
            break
        except Exception as e:
            last_err = e

    if not used_url:
        raise RuntimeError(f"[{site_tag}] URL 접속 실패: {last_err!r}")

    _save_debug(page, site_tag, "after_goto")

    # 깨우기 필요 시 클릭
    _wake_if_needed(page)

    # 완전 기동 대기
    ready = _wait_until_ready(page, timeout_ms=300_000)
    _save_debug(page, site_tag, "final")

    if not ready:
        raise RuntimeError(f"[{site_tag}] 5분 내 정상 렌더링 전환 실패. used_url={used_url}")


def main() -> None:
    urls = _parse_urls()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(30_000)

        failures: list[str] = []

        for url in urls:
            try:
                keepalive_one(page, url)
                # 사이트 간 짧은 휴지(과도한 동시성/부하 회피)
                time.sleep(3)
            except Exception as e:
                failures.append(f"{url} -> {e!r}")

        browser.close()

        if failures:
            # 여러 개 중 일부 실패해도 워크플로는 실패로 처리하여 알림/로그 확인 가능하게 함
            raise RuntimeError("KEEPALIVE 실패 항목:\n" + "\n".join(failures))


if __name__ == "__main__":
    main()
