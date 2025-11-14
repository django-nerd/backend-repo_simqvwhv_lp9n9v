"""
Database Schemas for Kids Fashion E-commerce (Bangladesh)

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------
# USER (optional minimal for order contact)
# ----------------------------------------------------------------------------
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Address")
    is_active: bool = Field(True, description="Whether user is active")

# ----------------------------------------------------------------------------
# PRODUCT (kids fashion specific)
# ----------------------------------------------------------------------------
class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price_bdt: float = Field(..., ge=0, description="Price in Bangladeshi Taka")
    category: Literal[
        "Boys", "Girls", "Baby", "Eid Collection", "Winter Wear", "School Wear", "Accessories"
    ] = Field(..., description="Product category")
    brand: Optional[str] = Field(None, description="Brand name")
    sizes: List[str] = Field(default_factory=list, description="Available sizes (e.g., 0-3M, 2-3Y, S, M)")
    colors: List[str] = Field(default_factory=list, description="Available colors")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    in_stock: bool = Field(True, description="Whether product is in stock")
    stock_qty: int = Field(0, ge=0, description="Available quantity")
    age_range: Optional[str] = Field(None, description="Age range like 0-3M, 2-5Y, 6-12Y")
    rating: Optional[float] = Field(0.0, ge=0, le=5, description="Average rating")

# ----------------------------------------------------------------------------
# ORDER
# ----------------------------------------------------------------------------
class OrderItem(BaseModel):
    product_id: str
    title: str
    price_bdt: float
    quantity: int = Field(1, ge=1)
    size: Optional[str] = None
    color: Optional[str] = None
    image: Optional[str] = None

class ShippingAddress(BaseModel):
    name: str
    phone: str
    address_line: str
    city: str = "Dhaka"
    area: Optional[str] = None
    notes: Optional[str] = None

class PaymentInfo(BaseModel):
    method: Literal["COD", "bKash", "Nagad"] = "COD"
    status: Literal["pending", "paid", "failed"] = "pending"
    transaction_id: Optional[str] = None

class Order(BaseModel):
    items: List[OrderItem]
    shipping: ShippingAddress
    subtotal_bdt: float = 0.0
    delivery_fee_bdt: float = 0.0
    total_bdt: float = 0.0
    payment: PaymentInfo = PaymentInfo()
    status: Literal["pending", "processing", "shipped", "delivered", "cancelled"] = "pending"
