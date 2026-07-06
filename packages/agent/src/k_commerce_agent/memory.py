from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock


CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "생수": ("생수", "물", "탄산수"),
    "음료": ("커피", "음료", "탄산", "주스", "차", "티백"),
    "간식": ("과자", "간식", "초콜릿", "사탕", "젤리"),
    "건강식품": ("영양제", "비타민", "오메가", "단백질", "프로틴"),
    "육아용품": ("기저귀", "분유", "물티슈", "젖병", "아기", "유아"),
    "반려동물": ("사료", "간식캔", "고양이", "강아지", "반려"),
    "주방용품": ("프라이팬", "냄비", "도마", "주방", "키친"),
    "생활용품": ("휴지", "세제", "샴푸", "린스", "칫솔", "칫약"),
    "캠핑": ("캠핑", "랜턴", "테이블", "버너", "텐트", "침낭"),
    "전자기기": ("이어폰", "키보드", "마우스", "충전기", "모니터", "노트북"),
}

NEGATIVE_PATTERNS = ("제외", "싫", "말고", "빼고", "안", "비추")
PRICE_PATTERNS = {
    "lowest_price": ("최저가", "가장 싼", "싸게", "저렴", "가격 낮"),
    "value": ("가성비", "가격 대비", "합리적"),
    "premium": ("좋은 거", "프리미엄", "고급", "브랜드"),
}
DELIVERY_PATTERNS = {
    "rocket": ("로켓", "오늘", "내일", "빠른 배송", "새벽"),
    "flexible": ("배송 상관없", "천천히", "느려도"),
}
INTENT_PATTERNS = {
    "recommendation": ("추천", "비교", "골라", "뭐 사", "살만", "재구매"),
    "cart": ("장바구니",),
    "orders": ("주문", "구매내역", "샀던"),
}
TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣]{2,}")


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _extract_categories(text: str) -> list[str]:
    return [
        category
        for category, patterns in CATEGORY_PATTERNS.items()
        if _contains_any(text, patterns)
    ]


def _extract_keywords(text: str) -> list[str]:
    return [
        token
        for token in TOKEN_PATTERN.findall(text)
        if token not in {"추천", "비교", "장바구니", "주문목록", "쿠팡", "상품"}
    ]


def _detect_preference(text: str, patterns: dict[str, tuple[str, ...]]) -> str | None:
    for label, keys in patterns.items():
        if _contains_any(text, keys):
            return label
    return None


def _detect_negative_terms(text: str) -> list[str]:
    if not _contains_any(text, NEGATIVE_PATTERNS):
        return []
    return _extract_keywords(text)[:5]


def _detect_intent(text: str) -> str:
    for intent, patterns in INTENT_PATTERNS.items():
        if _contains_any(text, patterns):
            return intent
    return "chat"


@dataclass
class SessionMemory:
    session_id: str
    user_messages: list[str] = field(default_factory=list)
    recent_queries: list[str] = field(default_factory=list)
    preferred_categories: list[str] = field(default_factory=list)
    avoided_keywords: list[str] = field(default_factory=list)
    recent_recommendations: list[str] = field(default_factory=list)
    price_preference: str | None = None
    delivery_preference: str | None = None
    last_intent: str = "chat"

    def ingest_user_message(self, message: str) -> None:
        text = message.strip()
        if not text:
            return

        self.user_messages = (self.user_messages + [text])[-12:]
        self.recent_queries = (self.recent_queries + _extract_keywords(text))[-24:]
        self.recent_recommendations = self.recent_recommendations[-6:]

        categories = list(dict.fromkeys(self.preferred_categories + _extract_categories(text)))
        self.preferred_categories = categories[-6:]

        negatives = list(dict.fromkeys(self.avoided_keywords + _detect_negative_terms(text)))
        self.avoided_keywords = negatives[-8:]

        price_preference = _detect_preference(text, PRICE_PATTERNS)
        if price_preference:
            self.price_preference = price_preference

        delivery_preference = _detect_preference(text, DELIVERY_PATTERNS)
        if delivery_preference:
            self.delivery_preference = delivery_preference

        self.last_intent = _detect_intent(text)

    def note_recommendations(self, product_names: list[str]) -> None:
        self.recent_recommendations = product_names[:5]

    def to_prompt_block(self) -> str:
        if not any(
            [
                self.user_messages,
                self.preferred_categories,
                self.avoided_keywords,
                self.price_preference,
                self.delivery_preference,
            ]
        ):
            return ""

        lines = ["[사용자 쇼핑 메모리]"]
        if self.preferred_categories:
            lines.append(f"- 선호 카테고리: {', '.join(self.preferred_categories)}")
        if self.avoided_keywords:
            lines.append(f"- 피하고 싶은 키워드: {', '.join(self.avoided_keywords)}")
        if self.price_preference:
            lines.append(f"- 가격 성향: {self.price_preference}")
        if self.delivery_preference:
            lines.append(f"- 배송 성향: {self.delivery_preference}")
        if self.recent_queries:
            lines.append(f"- 최근 관심 키워드: {', '.join(self.recent_queries[-6:])}")
        if self.recent_recommendations:
            lines.append(f"- 최근 추천 상품: {', '.join(self.recent_recommendations[:3])}")
        lines.append("- 메모리를 반영해 추천/비교 이유를 답변에 포함하세요.")
        return "\n".join(lines)


class SessionMemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self._sessions: dict[str, SessionMemory] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self._sessions = {
                    session_id: SessionMemory(**payload)
                    for session_id, payload in raw.items()
                }
            self._loaded = True

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            session_id: asdict(memory)
            for session_id, memory in self._sessions.items()
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, session_id: str) -> SessionMemory:
        self._ensure_loaded()
        with self._lock:
            memory = self._sessions.get(session_id)
            if memory is None:
                memory = SessionMemory(session_id=session_id)
                self._sessions[session_id] = memory
                self._persist()
            return memory

    def ingest_history(self, session_id: str, messages: list[str]) -> SessionMemory:
        memory = self.get(session_id)
        with self._lock:
            dedupe_window = set(memory.user_messages)
            for message in messages:
                if message.strip() and message not in dedupe_window:
                    memory.ingest_user_message(message)
            self._persist()
        return memory

    def note_recommendations(self, session_id: str, product_names: list[str]) -> None:
        memory = self.get(session_id)
        with self._lock:
            memory.note_recommendations(product_names)
            self._persist()


def category_counter(texts: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        counter.update(_extract_categories(text))
    return counter
