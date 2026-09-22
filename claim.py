"""Unity Asset Store 'Publisher of the Week' 무료 에셋을 내 계정에 자동으로 담는다.

사용법:
  python claim.py --login     # 최초 1회: 브라우저가 뜨면 직접 로그인
  python claim.py             # 이번 주 무료 에셋 담기 (헤드리스)
  python claim.py --headed    # 브라우저를 보면서 실행
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PwTimeout
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PROFILE = ROOT / "profile"
LOGS = ROOT / "logs"
STATE = ROOT / "state.json"
AUTH = ROOT / "auth.json"  # 로그인 쿠키 (세션 쿠키라 브라우저를 닫으면 사라지므로 따로 보관)
SALE_URL = "https://assetstore.unity.com/publisher-sale"
STORE = "https://assetstore.unity.com"

LOGS.mkdir(exist_ok=True)
_log = open(LOGS / "run.log", "a", encoding="utf-8")


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    _log.write(line + "\n")
    _log.flush()


def notify(title, body):
    """Windows 토스트 알림. 실패해도 조용히 넘어간다 (로그가 주 채널)."""
    ps = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t = $x.GetElementsByTagName('text'); $t.Item(0).AppendChild($x.CreateTextNode('{title}')) | Out-Null; $t.Item(1).AppendChild($x.CreateTextNode('{body}')) | Out-Null
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Unity Free Asset').Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=15, capture_output=True)
    except Exception as e:  # noqa: BLE001
        log(f"notify failed: {e}")


def fail(page, msg, code=1):
    shot = LOGS / f"fail-{datetime.now():%Y%m%d-%H%M%S}.png"
    try:
        page.screenshot(path=str(shot), full_page=True)
        log(f"screenshot: {shot}")
        # 다음 디버깅을 위해 화면의 버튼/입력창 목록도 남긴다
        for el in page.locator("button, input, a[role=button]").all()[:80]:
            t = (el.inner_text() or "").strip().replace("\n", " ")[:40]
            log(f"  ctl: {el.evaluate('e=>e.tagName')} {t!r} ph={el.get_attribute('placeholder')} aria={el.get_attribute('aria-label')} data-test={el.get_attribute('data-test')}")
    except Exception:  # noqa: BLE001
        pass
    log(f"FAIL: {msg}")
    notify("Unity 무료 에셋 실패", msg)
    sys.exit(code)


def load_state():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"claimed": []}


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def dismiss_cookies(page):
    try:
        page.locator("#onetrust-accept-btn-handler").click(timeout=3000)
    except PwTimeout:
        pass


def launch(p, headed):
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE), channel="chrome", headless=not headed, locale="en-US", viewport={"width": 1400, "height": 900}
    )
    if AUTH.exists():
        ctx.add_cookies(json.loads(AUTH.read_text(encoding="utf-8"))["cookies"])
    return ctx


def do_login(p):
    """장바구니 → Checkout 을 눌러 로그인 페이지로 간 뒤, 로그인 끝나고 스토어로 돌아올 때까지 기다린다.
    Google 로그인처럼 탭이 바뀌거나 닫혀도 견디도록 페이지가 아니라 컨텍스트 전체를 폴링한다."""
    ctx = launch(p, headed=True)
    page = ctx.pages[0]
    dismiss_cookies(page)
    url, _, _ = find_this_weeks_gift(page)
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    dismiss_cookies(page)
    open_cart_and_checkout(page)
    if "login.unity.com" not in page.url:
        log(f"로그인 페이지로 넘어가지 않았습니다 (현재: {page.url}). 이미 로그인된 것으로 보고 세션을 저장합니다.")
        ctx.storage_state(path=str(AUTH))
    else:
        log("브라우저에서 Unity 계정으로 로그인하세요. 로그인이 끝나 스토어로 돌아오면 자동으로 저장됩니다 (최대 30분).")
        deadline = time.time() + 1800
        while time.time() < deadline:
            try:
                pages = ctx.pages
                if not pages:
                    break
                if any(pg.url.startswith(STORE) for pg in pages):
                    pages[0].wait_for_timeout(5000)
                    ctx.storage_state(path=str(AUTH))
                    break
                # time.sleep 이 아니라 Playwright 호출로 기다려야 URL 변경 이벤트가 반영된다
                pages[0].wait_for_timeout(1000)
            except Exception:  # noqa: BLE001  (창이 닫힘)
                break
    try:
        ctx.close()
    except Exception:  # noqa: BLE001
        pass

    # 저장된 세션이 실제로 유효한지 헤드리스로 확인
    ctx = launch(p, headed=False)
    page = ctx.pages[0]
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    dismiss_cookies(page)
    open_cart_and_checkout(page)
    ok = "login.unity.com" not in page.url
    ctx.close()
    if ok:
        log("로그인 세션 저장 완료. 이제 `python claim.py --headed` 로 첫 실행을 해보세요.")
    else:
        log("로그인이 끝나지 않았거나 세션이 저장되지 않았습니다. `python claim.py --login` 을 다시 실행하세요.")
        sys.exit(1)


def open_cart_and_checkout(page):
    # 상단의 메인 버튼만 누른다 ("Add to Cart" 또는 이미 담겨 있으면 "View In Cart"). 관련 에셋의 버튼은 건드리지 않는다.
    before = page.url
    page.locator("[data-test=product-detail-add-to-cart-button]").first.click(timeout=30_000)
    page.locator("[data-test=checkout-button]").first.click(timeout=30_000)
    # 로그인 페이지 또는 체크아웃 페이지로 실제로 넘어갈 때까지 기다린다 (몇 초 걸림)
    try:
        page.wait_for_url(lambda u: u != before, timeout=30_000)
    except PwTimeout:
        pass
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)


def is_owned(page):
    """에셋 페이지의 메인 버튼이 'Open in Unity'면 이미 보유. 버튼이 렌더링될 때까지 기다린다."""
    btn = page.locator("[data-test=product-detail-add-to-cart-button]").first
    btn.wait_for(timeout=30_000)
    return bool(re.search("open in unity", btn.inner_text(), re.I))


def find_this_weeks_gift(page):
    page.goto(SALE_URL, wait_until="domcontentloaded", timeout=60_000)
    link = page.get_by_role("link", name=re.compile("free gift", re.I)).first
    link.wait_for(timeout=30_000)
    href = link.get_attribute("href")
    text = page.inner_text("body")
    m = re.search(r"coupon code\s+([A-Z0-9]+)", text, re.I)
    if not href or not m:
        fail(page, "세일 페이지에서 무료 에셋 링크 또는 쿠폰 코드를 찾지 못했습니다.")
    name = href.rstrip("/").split("/")[-1]
    return STORE + href, m.group(1), name


def do_claim(p, headed):
    state = load_state()
    ctx = launch(p, headed)
    page = ctx.pages[0]
    dismiss_cookies(page)

    url, coupon, name = find_this_weeks_gift(page)
    log(f"이번 주 무료 에셋: {name} / 쿠폰: {coupon}")
    if name in state["claimed"]:
        log("이미 담은 에셋입니다. 종료.")
        ctx.close()
        return

    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    dismiss_cookies(page)
    if is_owned(page):
        log("이미 보유 중인 에셋입니다. 기록만 남기고 종료.")
        state["claimed"].append(name)
        save_state(state)
        ctx.close()
        return

    open_cart_and_checkout(page)

    if "login.unity.com" in page.url:
        fail(page, "로그인 세션이 만료됐습니다. `python claim.py --login` 을 다시 실행하세요.", code=2)
    log(f"체크아웃 페이지: {page.url}")

    # 쿠폰 입력 (모바일용/데스크톱용 입력창이 둘이라 보이는 쪽만)
    page.locator(".summary-coupon input[type=text]:visible").first.fill(coupon, timeout=15_000)
    page.locator(".summary-coupon button:visible").first.click()
    page.wait_for_timeout(5000)

    # 안전장치: 총액이 0이 아니면 절대 결제 버튼을 누르지 않는다
    body = page.inner_text("body")
    total = re.search(r"To pay now\s*\n\s*\$?\s*([\d.,]+)", body)
    if not total or float(total.group(1).replace(",", "")) != 0.0:
        fail(page, f"쿠폰 적용 후 총액이 0이 아닙니다 (읽은 값: {total.group(1) if total else '없음'}). 결제하지 않고 중단.")

    # EULA 동의 체크 (숨겨진 체크박스라 라벨을 클릭)
    eula_checked = lambda: page.evaluate("() => [...document.querySelectorAll('input[name=term]')].some(e => e.checked)")  # noqa: E731
    if not eula_checked():
        page.locator("label[for=order_terms]:visible").first.click()
        page.wait_for_timeout(500)
    if not eula_checked():
        fail(page, "EULA 동의 체크가 되지 않았습니다.")

    page.get_by_role("button", name="Pay now").first.click(timeout=15_000)
    page.wait_for_timeout(10_000)
    log(f"결제 버튼 클릭 후 페이지: {page.url}")

    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    if not is_owned(page):
        fail(page, "결제 후에도 에셋 페이지에 'Open in Unity'가 보이지 않습니다. 실제로 담겼는지 확인 필요.")

    state["claimed"].append(name)
    save_state(state)
    log(f"성공: {name} 을(를) 내 에셋에 담았습니다.")
    notify("Unity 무료 에셋", f"{name} 담기 완료")
    ctx.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true", help="브라우저를 열어 직접 로그인 (최초 1회)")
    ap.add_argument("--headed", action="store_true", help="브라우저를 보면서 실행")
    a = ap.parse_args()
    with sync_playwright() as p:
        if a.login:
            do_login(p)
        else:
            do_claim(p, a.headed)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        log(f"UNEXPECTED: {e!r}")
        notify("Unity 무료 에셋 오류", str(e)[:150])
        sys.exit(1)
