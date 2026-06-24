"""
쿠팡 자동 로그인 — 이 파일 하나만 수정/실행하면 됩니다.

1. 아래 EMAIL, PASSWORD 상수를 본인 계정으로 변경
2. 실행:

  
   uv sync
   uv run python packages/cli/src/k_commerce_cli/providers/coupang/login_auto.py
   install nodriver 해야함
"""

from __future__ import annotations

import asyncio
import random

import nodriver as uc

# uv sync
# uv run python packages/cli/src/k_commerce_cli/providers/coupang/login_auto.py

# ── 여기에 로그인 정보 입력 ──────────────────────────────────
EMAIL = "쿠팡아이디"
PASSWORD = "쿠팡비밀번호"
# ────────────────────────────────────────────────────────────

COUPANG_LOGIN_URL = "https://login.coupang.com/login/login.pang"

EMAIL_SELECTOR = 'input[name="email"], input#login-email-input'
PASSWORD_SELECTOR = 'input[name="password"], input#login-password-input'
SUBMIT_SELECTOR = 'button[type="submit"], .login__button'


async def human_type(element, text: str) -> None:
    await element.click()
    await asyncio.sleep(random.uniform(0.2, 0.5))
    for char in text:
        await element.send_keys(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def wait_for_selector(tab, selector: str, timeout: float = 20.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        element = await tab.select(selector)
        if element is not None:
            return element
        await asyncio.sleep(0.3)
    raise TimeoutError(f"요소를 찾지 못했습니다: {selector}")


async def page_looks_denied(tab) -> bool:
    body = await tab.get_content()
    lowered = body.lower()
    return (
        "access denied" in lowered
        or "you don't have permission" in lowered
        or "errors.edgesuite.net" in lowered
    )


async def page_looks_logged_in(tab) -> bool:
    url = tab.target.url or ""
    if "login.coupang.com" in url:
        return False
    if await page_looks_denied(tab):
        return False

    body = await tab.get_content()
    has_login = "login.coupang.com" in body
    has_my = "마이쿠팡" in body or "mycoupang" in body or "mc/main" in body
    return not has_login and has_my


async def run() -> int:
    if EMAIL == "your@email.com" or PASSWORD == "your-password":
        print("EMAIL, PASSWORD 상수를 본인 계정으로 바꿔주세요.")
        return 1

    print("Chrome 실행 중...")
    browser = await uc.start(headless=False)

    try:
        print("로그인 페이지 이동...")
        tab = await browser.get(COUPANG_LOGIN_URL)
        await tab.sleep(random.uniform(1.5, 2.5))

        if await page_looks_denied(tab):
            print("Access Denied — 쿠팡이 접근을 차단했습니다.")
            return 1

        print("이메일 입력...")
        email_input = await wait_for_selector(tab, EMAIL_SELECTOR)
        await human_type(email_input, EMAIL)

        print("비밀번호 입력...")
        password_input = await wait_for_selector(tab, PASSWORD_SELECTOR)
        await human_type(password_input, PASSWORD)

        print("로그인 버튼 클릭...")
        submit = await wait_for_selector(tab, SUBMIT_SELECTOR)
        await asyncio.sleep(random.uniform(0.3, 0.8))
        await submit.click()

        print("로그인 처리 대기...")
        for _ in range(60):
            await tab.sleep(1)
            if await page_looks_logged_in(tab):
                print("쿠팡 로그인 성공")
                await tab.sleep(3)
                return 0
            if await page_looks_denied(tab):
                print("Access Denied — 로그인 후 쿠팡이 접근을 차단했습니다.")
                return 1

        print("쿠팡 로그인 실패 (시간 초과 또는 추가 인증 필요)")
        await tab.sleep(5)
        return 1
    finally:
        browser.stop()


def main() -> int:
    return uc.loop().run_until_complete(run())


if __name__ == "__main__":
    raise SystemExit(main())
