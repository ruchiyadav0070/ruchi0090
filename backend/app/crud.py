from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas


LOW_STOCK_THRESHOLD = 5


def create_product(db: Session, product: schemas.ProductCreate):
    existing = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product SKU already exists."
        )

    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_products(db: Session):
    return db.query(models.Product).order_by(models.Product.id.desc()).all()


def get_product(db: Session, product_id: int):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


def update_product(db: Session, product_id: int, payload: schemas.ProductUpdate):
    product = get_product(db, product_id)

    if payload.sku and payload.sku != product.sku:
        sku_exists = db.query(models.Product).filter(models.Product.sku == payload.sku).first()
        if sku_exists:
            raise HTTPException(status_code=400, detail="Product SKU already exists.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int):
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully."}


def create_customer(db: Session, customer: schemas.CustomerCreate):
    existing = db.query(models.Customer).filter(models.Customer.email == customer.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Customer email already exists.")

    db_customer = models.Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


def get_customers(db: Session):
    return db.query(models.Customer).order_by(models.Customer.id.desc()).all()


def get_customer(db: Session, customer_id: int):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return customer


def delete_customer(db: Session, customer_id: int):
    customer = get_customer(db, customer_id)
    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted successfully."}


def create_order(db: Session, order: schemas.OrderCreate):
    customer = db.query(models.Customer).filter(models.Customer.id == order.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    if not order.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item.")

    products_map = {}
    total_amount = 0.0

    for item in order.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found.")

        if product.quantity_in_stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product '{product.name}'. Available: {product.quantity_in_stock}, requested: {item.quantity}."
            )

        products_map[item.product_id] = product
        total_amount += product.price * item.quantity

    db_order = models.Order(customer_id=order.customer_id, total_amount=total_amount)
    db.add(db_order)
    db.flush()

    for item in order.items:
        product = products_map[item.product_id]
        line_total = product.price * item.quantity

        db_item = models.OrderItem(
            order_id=db_order.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_price=product.price,
            line_total=line_total
        )
        db.add(db_item)
        product.quantity_in_stock -= item.quantity

    db.commit()
    db.refresh(db_order)
    return db_order


def get_orders(db: Session):
    return db.query(models.Order).order_by(models.Order.id.desc()).all()


def get_order(db: Session, order_id: int):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


def delete_order(db: Session, order_id: int):
    order = get_order(db, order_id)
    db.delete(order)
    db.commit()
    return {"message": "Order deleted successfully."}


def get_dashboard(db: Session):
    total_products = db.query(func.count(models.Product.id)).scalar() or 0
    total_customers = db.query(func.count(models.Customer.id)).scalar() or 0
    total_orders = db.query(func.count(models.Order.id)).scalar() or 0
    low_stock_products = db.query(models.Product).filter(models.Product.quantity_in_stock <= LOW_STOCK_THRESHOLD).all()

    return {
        "total_products": total_products,
        "total_customers": total_customers,
        "total_orders": total_orders,
        "low_stock_products": low_stock_products
    }