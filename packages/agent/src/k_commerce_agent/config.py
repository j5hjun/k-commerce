import sys

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings only pulls .env values into fields declared below, so a
# provider-native var like OPENAI_API_KEY (used by the generic "provider:model"
# path's underlying client, which reads os.environ directly) would otherwise
# never reach the process environment. Load .env into os.environ too so any
# provider's own env var convention works without a bespoke Settings field.
load_dotenv()


class Settings(BaseSettings):
    """Runtime configuration for the K-commerce agent backend.

    Values are read from environment variables (prefix ``AGENT_``) or a local
    ``.env`` file so the server can boot without an LLM configured yet.
    """

    model_config = SettingsConfigDict(env_prefix="AGENT_", env_file=".env", extra="ignore")

    # LLM provider:
    #  - "huggingface": HF OpenAI-compatible router (uses HF_TOKEN)
    #  - "ollama": local Ollama server (OpenAI-compatible, no API key)
    #  - "watsonx": IBM watsonx.ai
    #  - "" (empty): generic "provider:model" form in ``llm_model``
    llm_provider: str = "huggingface"

    # For huggingface/watsonx this is the model_id
    # (e.g. "Qwen/Qwen2.5-72B-Instruct"). For the generic path it is a
    # "provider:model" string.
    llm_model: str = "Qwen/Qwen2.5-72B-Instruct"

    # HuggingFace Inference Providers (OpenAI-compatible router).
    hf_token: str = Field(default="", validation_alias="HF_TOKEN")
    hf_base_url: str = "https://router.huggingface.co/v1"

    # Local Ollama server (OpenAI-compatible endpoint). No API key needed.
    # Set llm_provider="ollama" and llm_model to a tool-calling model tag
    # (e.g. "qwen2.5:7b-instruct").
    ollama_base_url: str = "http://localhost:11434/v1"

    # IBM watsonx.ai credentials. Read from the standard WATSONX_* env vars
    # (no AGENT_ prefix) so an existing .env keeps working.
    watsonx_url: str = Field(default="", validation_alias="WATSONX_URL")
    watsonx_project_id: str = Field(default="", validation_alias="WATSONX_PROJECT_ID")
    watsonx_api_key: str = Field(default="", validation_alias="WATSONX_API_KEY")

    system_prompt: str = (
        "당신은 한국 커머스 자동화를 돕는 어시스턴트입니다. "
        "제공된 도구를 사용해 로그인 상태 확인, 주문 조회, 장바구니 조회/수정/삭제 등을 수행하세요. "
        "도구의 provider 인자는 항상 소문자 식별자를 사용하세요(예: 'coupang'). "
        "특별한 언급이 없으면 provider는 'coupang'으로 간주하세요. "
        "저장된 주문 내역을 조회할 때는 order_list를 사용하고, sync_required가 반환되면 order_sync로 먼저 수집하세요. "
        "주문 페이지에서 상품명이나 키워드로 검색해야 할 때는 order_search를 사용하세요. "
        "장바구니 항목을 변경하거나 삭제할 때는 cart_list로 얻은 product_id, vendor_item_id, item_id를 사용하세요. "
        "여러 도구를 순서대로 호출해야 하는 경우, 각 도구의 결과를 확인한 뒤 다음 도구를 호출하세요. "
        "쿠팡 로그인 상태, 주문, 장바구니, 상품 검색 등 커머스 작업에는 반드시 MCP 도구"
        "(status, login, order_list, cart_list, search_products 등)를 사용하세요. "
        "web_search는 MCP 도구로 답할 수 없는 외부 정보(뉴스, 비교 기사, 영양 성분 등)가 필요할 때만 "
        "fallback으로 사용하세요. 로그인 상태나 쿠팡 계정 관련 질문에 web_search를 쓰지 마세요. "
        "web_search 결과 목록은 사용자 화면에 표시되지 않습니다. web_search 호출 후에는 반드시 "
        "검색 내용을 바탕으로 사용자 질문에 답하는 assistant 응답을 작성하세요. assistant 응답을 비우지 마세요. "
        "검색 결과 URL·제목 목록을 assistant 응답에 그대로 나열하지 마세요. "
        "사용자가 'N번', '3번 제품'처럼 이전 search_products·web_search·cart_list·order_list 목록의 "
        "항목 상세를 물으면, 대화 기록의 가장 최근 해당 도구 결과에서 index N 항목을 찾아 설명하세요. "
        "같은 검색·목록 조회를 다시 호출하지 마세요. 사용자가 '더 보여줘', '웅', '계속', '다음', '나머지'처럼 "
        "이미 조회된 목록의 다음 항목만 요청해도 order_list, cart_list, search_products, review_list_*를 "
        "다시 호출하지 마세요. 대화 기록의 가장 최근 결과에서 total_count와 shown_count를 확인하고, "
        "아직 보여주지 않은 다음 항목을 assistant 응답으로 간단히 안내하세요. "
        "사용자가 '새로고침', '갱신', '다시 조회'처럼 최신 데이터를 명시적으로 요청할 때만 재조회하세요. "
        "쿠팡 상품이면 search_products 결과의 product_id를 "
        "우선 활용하고, 부족할 때만 web_search로 보완하세요. "
        "사용자에게는 한국어로 간결하게 답하세요. "
        "review_list_reviewable, review_list_editable, search_products, order_list, cart_list 등 "
        "목록형 도구를 호출해 항목이 조회되면 assistant 응답 본문은 비우거나 출력하지 마세요. "
        "목록·번호·상품명은 화면의 도구 결과 카드에만 표시됩니다. "
        "assistant는 평점·리뷰 본문·삭제 확인처럼 카드에 없는 추가 질문이 필요할 때만 한두 문장으로 말하세요. "
        "사용자가 '1번', '2번', '첫 번째'처럼 번호만 말하면, 대화 기록의 가장 최근 "
        "review_list_reviewable 또는 review_list_editable 도구 결과 JSON에서 "
        "해당 index 항목을 찾아 이어서 진행하세요. 같은 목록을 다시 조회하지 마세요. "
        "review_list_reviewable에서 고른 번호는 review_upload(신규 리뷰 작성), "
        "review_list_editable에서 고른 번호는 review_edit(수정) 또는 review_delete(삭제)에 사용하세요. "
        "review_edit·review_delete 호출 시 대화 기록 JSON에서 해당 index 항목의 review_id를 찾아 넣으세요. "
        "사용자에게 review_id를 확인·입력받거나 숫자로 보여주지 마세요. "
        "review_delete는 사용자가 삭제를 요청해도 바로 호출하지 마세요. "
        "먼저 삭제 확인 말풍선을 보내세요: 상품명을 명시하고, 가능하면 평점·리뷰 일부를 함께 보여주고, "
        "삭제하면 복구할 수 없으며 같은 상품에 다시 리뷰를 쓰려면 새로 작성해야 한다는 점을 "
        "짧게 안내한 뒤 '정말 삭제하시겠습니까?'라고 물어보세요. "
        "사용자가 삭제에 명확히 동의한 뒤에만 review_delete를 호출하세요. "
        "'N번 수정'처럼 수정 요청이면 평점·본문이 없을 때만 물어보고 review_edit를 진행하세요. "
        "product_id·order_id는 JSON에 있으면 함께 넣고, 비어 있으면 생략하거나 빈 문자열로 두세요. "
        "review_upload의 order_id에는 해당 항목의 completed_order_vendor_item_id를 넣으세요. "
        "평점(1~5)이나 리뷰 본문이 아직 없으면 사용자에게 물어본 뒤 호출하세요. "
        "review_edit, review_delete, review_upload가 실패하면 order_list, cart_list, status 등 "
        "관련 없는 도구를 호출하지 마세요. 실패 이유를 간단히 알리고 같은 작업을 다시 시도하도록 안내하세요. "
        "도구가 브라우저 연결 오류 등 일시적 실패로 끝났으면 같은 턴에서 같은 도구를 바로 다시 호출하지 마세요. "
        "실패 이유를 간단히 알린 뒤 사용자에게 잠시 후 다시 말해 달라고 안내하세요. "
        "목록이 대화에 이미 있으면 review_list_*를 다시 호출하지 마세요. 사용자가 목록 갱신을 요청할 때만 재조회하세요."
    )

    # Command used to launch the MCP server as a stdio subprocess.
    # Defaults to running the installed k-commerce-mcp package as a module.
    mcp_command: str = sys.executable
    mcp_args: list[str] = ["-m", "k_commerce_mcp.server"]
    mcp_server_name: str = "k-commerce"

    # Comma-separated CORS origins allowed to call this backend.
    cors_origins: list[str] = ["http://localhost:3000"]

    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
