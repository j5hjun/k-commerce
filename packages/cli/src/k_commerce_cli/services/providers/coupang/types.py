from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from k_commerce_cli.services.types.provider import ProviderName


@dataclass(frozen=True)
class CoupangOrderSummary:
    totalOrders: int
    addedOrders: int
    updatedOrders: int
    deletedOrders: int

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoupangOrderSummary":
        return cls(
            totalOrders=int(payload["totalOrders"]),
            addedOrders=int(payload["addedOrders"]),
            updatedOrders=int(payload["updatedOrders"]),
            deletedOrders=int(payload["deletedOrders"]),
        )


@dataclass(frozen=True)
class CoupangOrderMeta:
    provider: ProviderName
    collectedAt: str
    years: list[str]
    failedPages: list[list[int | str]]
    refresh: bool
    summary: CoupangOrderSummary

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoupangOrderMeta":
        return cls(
            provider=ProviderName(str(payload["provider"])),
            collectedAt=str(payload["collectedAt"]),
            years=[str(year) for year in payload["years"]],
            failedPages=[[page[0], int(page[1])] for page in payload["failedPages"]],
            refresh=bool(payload["refresh"]),
            summary=CoupangOrderSummary.from_dict(payload["summary"]),
        )


@dataclass(frozen=True)
class CoupangOrderProduct:
    vendorItemId: int
    vendorItemName: str
    productName: str
    quantity: int
    unitPrice: int
    discountedUnitPrice: int
    combinedUnitPrice: int
    imagePath: str
    productUrl: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoupangOrderProduct":
        return cls(
            vendorItemId=int(payload["vendorItemId"]),
            vendorItemName=str(payload["vendorItemName"]),
            productName=str(payload["productName"]),
            quantity=int(payload["quantity"]),
            unitPrice=int(payload["unitPrice"]),
            discountedUnitPrice=int(payload["discountedUnitPrice"]),
            combinedUnitPrice=int(payload["combinedUnitPrice"]),
            imagePath=str(payload["imagePath"]),
            productUrl=str(payload.get("productUrl") or ""),
        )


@dataclass(frozen=True)
class CoupangDeliveryGroup:
    shipmentBoxId: str
    invoiceNumber: str
    invoiceStatus: str
    pddMessage: dict[str, str | None]
    productList: list[CoupangOrderProduct]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoupangDeliveryGroup":
        return cls(
            shipmentBoxId=str(payload["shipmentBoxId"]),
            invoiceNumber=str(payload["invoiceNumber"]),
            invoiceStatus=str(payload["invoiceStatus"]),
            pddMessage=dict(payload["pddMessage"]),
            productList=[
                CoupangOrderProduct.from_dict(product)
                for product in payload["productList"]
            ],
        )


@dataclass(frozen=True)
class CoupangOrderResult:
    provider: ProviderName
    orderId: int
    title: str
    orderedAt: int
    totalProductPrice: int
    deliveryGroupList: list[CoupangDeliveryGroup]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoupangOrderResult":
        return cls(
            provider=ProviderName(str(payload["provider"])),
            orderId=int(payload["orderId"]),
            title=str(payload["title"]),
            orderedAt=int(payload["orderedAt"]),
            totalProductPrice=int(payload["totalProductPrice"]),
            deliveryGroupList=[
                CoupangDeliveryGroup.from_dict(group)
                for group in payload["deliveryGroupList"]
            ],
        )


@dataclass(frozen=True)
class CoupangOrderList:
    meta: CoupangOrderMeta
    orders: list[CoupangOrderResult]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CoupangOrderList":
        return cls(
            meta=CoupangOrderMeta.from_dict(payload["meta"]),
            orders=[
                CoupangOrderResult.from_dict(order) for order in payload["orders"]
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CoupangOrderListResult:
    message: str
    payload: CoupangOrderList
    next_tools: tuple[str, ...] = ()
