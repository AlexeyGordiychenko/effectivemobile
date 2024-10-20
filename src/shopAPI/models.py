from datetime import datetime
import enum
from typing import Any, Dict
from uuid import UUID
from pydantic import (
    AliasChoices,
    AliasPath,
    ConfigDict,
    field_serializer,
)
from sqlmodel import Field, Relationship, SQLModel, Column, Enum
from shopAPI.database import IdMixin


class ApiStatus(SQLModel):
    name: str = Field(...)
    version: str = Field(...)
    status: str = Field(...)
    message: str = Field(...)
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "ShopAPI",
                    "version": "1.0.0",
                    "status": "OK",
                    "message": "Visit /swagger for documentation.",
                },
            ]
        }
    )


class ResponseMessage(SQLModel):
    detail: str


def field_example(param: Any) -> Dict[str, Dict[str, Any]]:
    """
    Returns field example for swagger documentation

    It's a workaround for SQLModel bug,
    see https://github.com/tiangolo/sqlmodel/discussions/833
    """
    return {"schema_extra": {"json_schema_extra": {"example": param}}}


class ProductBase(SQLModel):
    name: str = Field(nullable=False, **field_example("Product"))
    description: str = Field(nullable=False, **field_example("A simple product"))
    price: float = Field(nullable=False, **field_example(128.99))
    amount: int = Field(nullable=False, **field_example(100))


class Product(IdMixin, ProductBase, table=True):
    __tablename__ = "product"
    order_items: list["OrderItem"] = Relationship(back_populates="product")


class ProductCreate(ProductBase):
    pass
    model_config = ConfigDict(extra="forbid")


class ProductUpdate(ProductBase):
    # TODO check examples with https://fastapi.tiangolo.com/tutorial/schema-extra-example/#body-with-examples
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Updated product",
                    "description": "A simple updated product",
                    "price": 256.99,
                    "amount": 200,
                }
            ]
        },
    )


class ProductResponse(ProductBase):
    id: UUID


class ProductResponseInOrderItem(ProductResponse):
    description: str = Field(exclude=True)
    amount: int = Field(exclude=True)


class OrderStatus(str, enum.Enum):
    created = "created"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    canceled = "canceled"


class OrderBase(SQLModel):
    pass


class Order(IdMixin, OrderBase, table=True):
    __tablename__ = "order"
    creation_date: datetime = Field(default_factory=datetime.now)
    status: OrderStatus = Field(
        default=OrderStatus.created, sa_column=Column(Enum(OrderStatus), nullable=False)
    )

    order_items: list["OrderItem"] = Relationship(
        sa_relationship_kwargs={"cascade": "all"}, back_populates="order"
    )

    def __init__(self, **kwargs):
        order_items = kwargs.pop("order_items", [])
        super().__init__(**kwargs)
        self.order_items = [OrderItem(**order_item) for order_item in order_items]


class OrderCreate(OrderBase):
    order_items: list["OrderItemCreate"] = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class OrderStatusUpdate(SQLModel):
    status: OrderStatus
    model_config = ConfigDict(extra="forbid")


class OrderResponse(OrderBase):
    id: UUID
    creation_date: datetime
    status: OrderStatus

    @field_serializer("creation_date", return_type=str, when_used="json")
    def serialize_creation_date(self, creation_date: datetime):
        return creation_date.strftime("%Y-%m-%d %H:%M:%S")


class OrderResponseWithItems(OrderResponse):
    order_items: list["OrderItemResponse"] | None = None


class OrderResponseWithItemsShort(OrderResponse):
    order_items: list["OrderItemResponseShort"] | None = None


class OrderItemBase(SQLModel):
    amount: int = Field(nullable=False, gt=0, **field_example(5))


class OrderItem(IdMixin, OrderItemBase, table=True):
    __tablename__ = "order_item"

    order_id: UUID | None = Field(foreign_key="order.id")
    order: Order | None = Relationship(back_populates="order_items")

    product_id: UUID | None = Field(foreign_key="product.id")
    product: Product | None = Relationship(back_populates="order_items")


class OrderItemCreate(OrderItemBase):
    product_id: UUID
    model_config = ConfigDict(extra="forbid")


class OrderItemResponse(OrderItemBase):
    product: ProductResponseInOrderItem


class OrderItemResponseShort(OrderItemBase):
    product_id: UUID = Field(
        schema_extra={
            "validation_alias": AliasChoices("product_id", AliasPath("product", "id"))
        }
    )
