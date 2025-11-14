import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product as ProductSchema, Order as OrderSchema

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------- Utils -----------------------------

def serialize_mongo(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc["_id"])  # expose as id
        del doc["_id"]
    # Convert nested ObjectIds if any
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc


# ----------------------------- Basic -----------------------------

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# ----------------------------- Products -----------------------------

@app.get("/api/products")
def list_products(
    category: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200)
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    filter_query = {}
    if category:
        filter_query["category"] = category
    if q:
        filter_query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"brand": {"$regex": q, "$options": "i"}},
        ]

    docs = get_documents("product", filter_query, limit)
    return [serialize_mongo(d) for d in docs]


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_mongo(doc)


@app.post("/api/products/seed")
def seed_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # If already have products, skip
    existing = db["product"].count_documents({})
    if existing > 0:
        return {"message": "Products already exist", "count": existing}

    samples: List[ProductSchema] = [
        ProductSchema(
            title="Boys Cotton T-Shirt",
            description="Soft cotton tee for everyday comfort",
            price_bdt=450,
            category="Boys",
            brand="Kiddo",
            sizes=["2-3Y", "4-5Y", "6-7Y"],
            colors=["Blue", "Red"],
            images=["https://images.unsplash.com/photo-1601050690597-9c33a4ee5ad5?w=800&q=80"],
            in_stock=True,
            stock_qty=50,
            age_range="2-7Y",
            rating=4.5,
        ),
        ProductSchema(
            title="Girls Floral Dress",
            description="Lightweight floral print dress, perfect for summer",
            price_bdt=1250,
            category="Girls",
            brand="MiniBloom",
            sizes=["2-3Y", "3-4Y", "5-6Y", "7-8Y"],
            colors=["Pink", "Yellow"],
            images=["https://images.unsplash.com/photo-1520975922117-9ce8bdb000a6?w=800&q=80"],
            in_stock=True,
            stock_qty=20,
            age_range="2-8Y",
            rating=4.8,
        ),
        ProductSchema(
            title="Baby Romper Set",
            description="Organic cotton romper set for newborns",
            price_bdt=990,
            category="Baby",
            brand="TinyCare",
            sizes=["0-3M", "3-6M", "6-9M"],
            colors=["Mint", "Cream"],
            images=["https://images.unsplash.com/photo-1619177097999-89c3b1edbba9?w=800&q=80"],
            in_stock=True,
            stock_qty=30,
            age_range="0-9M",
            rating=4.6,
        ),
        ProductSchema(
            title="Kids Hooded Jacket",
            description="Warm fleece-lined jacket for winter",
            price_bdt=1850,
            category="Winter Wear",
            brand="Warmy",
            sizes=["3-4Y", "5-6Y", "7-8Y", "9-10Y"],
            colors=["Navy", "Grey"],
            images=["https://images.unsplash.com/photo-1520975922117-9ce8bdb000a6?w=800&q=80"],
            in_stock=True,
            stock_qty=15,
            age_range="3-10Y",
            rating=4.7,
        ),
    ]

    inserted = 0
    for p in samples:
        create_document("product", p)
        inserted += 1

    return {"message": "Seeded sample products", "inserted": inserted}


# ----------------------------- Orders -----------------------------

class OrderResponse(BaseModel):
    order_id: str
    status: str
    total_bdt: float

@app.post("/api/orders", response_model=OrderResponse)
def create_order(order: OrderSchema):
    """Create an order. Totals will be recalculated server-side."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Recalculate totals
    subtotal = sum(item.price_bdt * item.quantity for item in order.items)
    # Simple flat delivery fee inside BD
    delivery_fee = 80.0
    total = subtotal + delivery_fee

    # Create a copy with corrected totals
    order_dict = order.model_dump()
    order_dict["subtotal_bdt"] = round(subtotal, 2)
    order_dict["delivery_fee_bdt"] = delivery_fee
    order_dict["total_bdt"] = round(total, 2)

    order_id = create_document("order", order_dict)
    return OrderResponse(order_id=order_id, status="received", total_bdt=round(total, 2))


# ----------------------------- Schema (optional helper) -----------------------------

@app.get("/schema")
def get_schema_overview():
    return {
        "collections": ["user", "product", "order"],
        "notes": "Collections are created dynamically on first insert.",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
