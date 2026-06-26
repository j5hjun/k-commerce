import json
from pathlib import Path

import pytest

from ._helpers import invoke_order_list, provider_paths, require_smoke_enabled

pytestmark = pytest.mark.smoke


def test_coupang_order_list_with_cache_smoke(tmp_path: Path) -> None:
    require_smoke_enabled()
    root_dir = tmp_path
    paths = provider_paths(root_dir)
    paths.base_dir.mkdir(parents=True, exist_ok=True)
    paths.orders_path.write_text(
        json.dumps(
            {
                "orders": [
                    {
                        "order_date": "2026. 6. 26",
                        "title": "로켓프레시 사과",
                        "quantity": 2,
                        "status": "배송완료",
"product_url": "https://www.coupang.com/placeholder"
,
                    },
                    {
                        "order_date": "2026. 6. 25",
                        "title": "생수 2L",
                        "quantity": 1,
                        "status": "배송중",
"product_url": "https://www.coupang.com/placeholder"
,
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = invoke_order_list(root_dir)

    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "상품: 로켓프레시 사과 | 수량: 2 | 상태: 배송완료",
        "상품: 생수 2L | 수량: 1 | 상태: 배송중",
    ]
    assert json.loads(paths.orders_path.read_text(encoding="utf-8")) == {
        "orders": [
            {
                "order_date": "2026. 6. 26",
                "title": "로켓프레시 사과",
                "quantity": 2,
                "status": "배송완료",
"product_url": "https://www.coupang.com/placeholder"
,
            },
            {
                "order_date": "2026. 6. 25",
                "title": "생수 2L",
                "quantity": 1,
                "status": "배송중",
"product_url": "https://www.coupang.com/placeholder"
,
            },
        ]
    }
