import asyncio
import contextlib
from k_commerce_cli.services.base import BrowserSession, BrowserTab

COUPANG_HOME_URL = "https://www.coupang.com/"
COUPANG_LOGIN_LINK_SELECTOR = 'a[href*="login/login.pang"]'
COUPANG_MYCOUPANG_SELECTOR = (
    'a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]'
)


def deserialize_evaluate_result(value: object) -> object:
    """브라우저 evaluate 결과를 일반 Python 객체로 변환합니다."""
    if isinstance(value, dict) and "type" in value and "value" in value:
        typed = str(value["type"])
        inner = value["value"]
        if typed == "object":
            return {
                str(pair[0]): deserialize_evaluate_result(pair[1])
                for pair in inner
                if isinstance(pair, list) and len(pair) == 2
            }
        if typed == "array":
            return [deserialize_evaluate_result(item) for item in inner]
        if typed == "null":
            return None
        if typed in {"string", "number", "boolean"}:
            return inner
        return inner

    if isinstance(value, list):
        if value and all(
            isinstance(item, list) and len(item) == 2 and isinstance(item[0], str) for item in value
        ):
            return {item[0]: deserialize_evaluate_result(item[1]) for item in value}
        return [deserialize_evaluate_result(item) for item in value]

    if isinstance(value, dict):
        return {key: deserialize_evaluate_result(item) for key, item in value.items()}

    return value


class CoupangReviewBrowser:
    browser: object
    _browser_session: BrowserSession | None

    async def _close_browser_session(self) -> None:
        """열려 있는 브라우저 세션을 닫고 내부 참조를 정리합니다."""
        if self._browser_session is None:
            return

        try:
            await self.browser.close(self._browser_session)
        finally:
            self._browser_session = None

    async def _open_home(self, session: BrowserSession) -> None:
        """쿠팡 홈 화면을 엽니다."""
        await session.tab.get(COUPANG_HOME_URL)

    async def _is_logged_in(self, tab: BrowserTab) -> bool:
        """현재 탭이 쿠팡 로그인 상태인지 확인합니다."""
        page_state = await self._read_login_state(tab)
        page_url = str(page_state["url"])
        if "login.coupang.com" in page_url:
            return False

        if "my.coupang.com" in page_url:
            evaluate = getattr(tab, "evaluate", None)
            if callable(evaluate):
                try:
                    result = await evaluate(
                        """
                        (() => {
                          const bodyText = document.body?.innerText || '';
                          if (
                            bodyText.includes('로그인') &&
                            bodyText.includes('회원가입') &&
                            !bodyText.includes('마이쿠팡')
                          ) {
                            return false;
                          }
                          return !bodyText.includes('로그인이 필요');
                        })()
                        """
                    )
                    if isinstance(result, bool):
                        return result
                except Exception:
                    pass
            return True

        return (not page_state["has_login_link"]) and page_state["has_mycoupang_link"]

    async def _evaluate_json(self, tab: BrowserTab, script: str) -> object | None:
        """브라우저에서 JavaScript를 실행하고 JSON 형태 결과를 읽습니다."""
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return None

        try:
            result = await evaluate(script)
        except Exception:
            return None

        return deserialize_evaluate_result(result)

    async def _read_review_page_state(self, tab: BrowserTab) -> dict[str, object]:
        result = await self._evaluate_json(
            tab,
            """
            (() => ({
              url: window.location.href,
              body_text: document.body?.innerText || ''
            }))()
            """,
        )
        if not isinstance(result, dict):
            return {
                "read_failed": True,
                "url": "",
                "body_text": "",
            }

        return {
            "read_failed": False,
            "url": str(result.get("url", "")),
            "body_text": str(result.get("body_text", "")),
        }

    async def _is_review_login_screen(self, tab: BrowserTab) -> bool:
        """탭 속성이 아닌 실제 DOM 기준으로 로그인 화면인지 확인합니다."""
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const url = window.location.href;
              const bodyText = document.body?.innerText || '';
              if (url.includes('login.coupang.com') || url.includes('login/login.pang')) {
                return true;
              }
              if (bodyText.includes('로그인이 필요')) {
                return true;
              }
              const passwordInput = document.querySelector(
                'input[type="password"], #login-password, input[name="password"]'
              );
              return passwordInput !== null && url.includes('coupang.com');
            })()
            """,
        )
        return result is True

    async def _scroll_page(self, tab: BrowserTab) -> None:
        """현재 페이지와 내부 스크롤 영역을 아래로 내립니다."""
        evaluate = getattr(tab, "evaluate", None)
        if not callable(evaluate):
            return

        with contextlib.suppress(Exception):
            await evaluate(
                """
                (() => {
                  window.scrollBy(0, window.innerHeight);
                  window.scrollTo(0, document.documentElement.scrollHeight);
                  const containers = document.querySelectorAll(
                    '.my-review__wrote, [class*="wrote"], [class*="review-list"], main, [class*="scroll"]'
                  );
                  for (const container of containers) {
                    if (container.scrollHeight > container.clientHeight + 20) {
                      container.scrollTop = container.scrollHeight;
                    }
                  }
                })()
                """
            )

    async def _is_page_scrolled_to_bottom(self, tab: BrowserTab) -> bool:
        """윈도우와 내부 스크롤 영역이 하단에 도달했는지 확인합니다."""
        result = await self._evaluate_json(
            tab,
            """
            (() => {
              const nearBottom = (element, threshold = 80) =>
                element.scrollTop + element.clientHeight >= element.scrollHeight - threshold;
              const windowBottom =
                window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 80;
              const containers = Array.from(
                document.querySelectorAll(
                  '.my-review__wrote, [class*="wrote"], [class*="review-list"], main'
                )
              ).filter((element) => element.scrollHeight > element.clientHeight + 20);
              if (containers.length === 0) return windowBottom;
              return containers.every((element) => nearBottom(element));
            })()
            """,
        )
        return result is True

    async def _sleep_ms(self, timeout_ms: int) -> None:
        """밀리초 단위 대기 시간을 asyncio sleep으로 처리합니다."""
        await asyncio.sleep(timeout_ms / 1000)

    async def _safe_select(self, tab: BrowserTab, selector: str, timeout: int = 1):
        """선택자 조회를 브라우저 adapter에 위임합니다."""
        return await self.browser.select(tab, selector, timeout=timeout)

    def _active_tab(self, session: BrowserSession) -> BrowserTab:
        """브라우저 세션에서 쿠팡 페이지로 보이는 활성 탭을 고릅니다."""
        runtime = getattr(session, "browser", None)
        candidates: list[BrowserTab] = []
        if runtime is not None:
            tabs = getattr(runtime, "tabs", None)
            if isinstance(tabs, list):
                candidates.extend(reversed(tabs))

            main_tab = None
            try:
                main_tab = runtime.main_tab  # type: ignore[attr-defined]
            except (StopIteration, RuntimeError):
                main_tab = None
            if main_tab is not None:
                candidates.append(main_tab)
        candidates.append(session.tab)

        for candidate in candidates:
            if not hasattr(candidate, "select"):
                continue
            url = str(getattr(candidate, "url", ""))
            if "coupang.com" in url:
                return candidate

        for candidate in candidates:
            if not hasattr(candidate, "select"):
                continue
            url = str(getattr(candidate, "url", ""))
            if url.startswith(("https://", "http://", "about:blank")):
                return candidate

        for candidate in candidates:
            if hasattr(candidate, "select"):
                return candidate

        return session.tab

    async def _read_login_state(self, tab: BrowserTab) -> dict[str, object]:
        """현재 탭의 URL과 로그인/마이쿠팡 링크 존재 여부를 읽습니다."""
        evaluate = getattr(tab, "evaluate", None)
        if callable(evaluate):
            try:
                result = await evaluate(
                    """
                    (() => ({
                      url: window.location.href,
                      has_login_link: document.querySelector('a[href*="login/login.pang"]') !== null,
                      has_mycoupang_link:
                        document.querySelector('a[href*="mc/main"], a[href*="mc/mymain"], a[href*="mycoupang"], a[title*="마이쿠팡"]') !== null
                    }))()
                    """
                )
                if isinstance(result, dict):
                    return {
                        "url": str(result.get("url", "")),
                        "has_login_link": bool(result.get("has_login_link", False)),
                        "has_mycoupang_link": bool(result.get("has_mycoupang_link", False)),
                    }
            except Exception:
                pass

        page_url = getattr(tab, "url", "")
        login_link = await self._safe_select(tab, COUPANG_LOGIN_LINK_SELECTOR)
        my_coupang_link = await self._safe_select(tab, COUPANG_MYCOUPANG_SELECTOR)
        return {
            "url": page_url,
            "has_login_link": login_link is not None,
            "has_mycoupang_link": my_coupang_link is not None,
        }
