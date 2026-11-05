# =====================================================================================
#                                    INCLUDES
# =====================================================================================
from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy import String, Float, Integer, create_engine, select
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from pathlib import Path
from collections.abc import Sequence


# =====================================================================================
#                                     DATA MODEL
# =====================================================================================
@dataclass
class Product:
    name: str
    price: float
    stock: int


example_data: list[Product] = [
    Product(name="Monorail", price=1449.99, stock=30),
    Product(name="Hewlett Packard", price=1849.99, stock=23),
    Product(name="COMPAQ", price=2399.99, stock=8),
]


# =====================================================================================
#                                  DATABASE INTERFACE
# =====================================================================================
class DatabaseModel(DeclarativeBase):
    pass


class ProductModel(DatabaseModel):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Float())
    stock: Mapped[int] = mapped_column(Integer())

    @staticmethod
    def to_model(product: Product) -> ProductModel:
        return ProductModel(name=product.name, price=product.price, stock=product.stock)

    def from_model(self) -> Product:
        return Product(name=self.name, price=self.price, stock=self.stock)


def prepare_db() -> Engine:
    Path("local").mkdir(parents=True, exist_ok=True)

    engine = create_engine("sqlite:///local/demo.db")
    DatabaseModel.metadata.create_all(engine)

    return engine


def populate_db(eng: Engine) -> None:
    with Session(eng) as session:
        for product in example_data:
            session.add(ProductModel.to_model(product))
        session.commit()

def clear_db(eng: Engine)-> None:
    with Session(eng) as session:
        session.query(ProductModel).delete(synchronize_session="fetch")
        session.commit()

def add_product(eng: Engine, product: Product) -> bool:
    """Dodaje produkt. Nie pozwala na duplikaty nazw."""
    with Session(eng) as session:
        existing = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(product.name)
            )
        ).first()

        if existing is not None:
            return False

        session.add(ProductModel.to_model(product))
        session.commit()
        return True


def retrieve_product_by_name(
    eng: Engine, name: str
) -> list[Product]:
    """Wyszukuje produkty po nazwie, bez rozróżniania wielkości liter."""
    with Session(eng) as session:
        products = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(name)
            )
        ).all()

        return [product.from_model() for product in products]


def retrieve_all_products(eng: Engine) -> list[Product]:
    """Zwraca wszystkie produkty."""
    with Session(eng) as session:
        products = session.scalars(
            select(ProductModel).order_by(ProductModel.id)
        ).all()

        return [product.from_model() for product in products]


def update_product(
    eng: Engine,
    name: str,
    new_name: str,
    new_price: float,
    new_stock: int
) -> bool:
    """Zmienia nazwę, cenę i stan produktu."""
    with Session(eng) as session:
        product = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(name)
            )
        ).first()

        if product is None:
            return False

        # Nie pozwalaj zmienić nazwy na nazwę innego produktu.
        duplicate = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(new_name),
                ProductModel.id != product.id
            )
        ).first()

        if duplicate is not None:
            return False

        product.name = new_name
        product.price = new_price
        product.stock = new_stock

        session.commit()
        return True


def delete_product(eng: Engine, name: str) -> bool:
    """Usuwa jeden produkt po nazwie."""
    with Session(eng) as session:
        product = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(name)
            )
        ).first()

        if product is None:
            return False

        session.delete(product)
        session.commit()
        return True

def statistics(eng: Engine, products: Sequence[Product]) -> None:
    """Wyświetla statystyki dotyczące produktów w bazie danych."""
    products_number = len(products)
    global_worth = sum(product.price * product.stock for product in products)
    global_stock = sum(product.stock for product in products)

    print(f"Liczba produktów w bazie: {products_number}")
    print(f"Łączna wartość magazynu: {global_worth:.2f}")
    print(f"Łączny stan magazynowy: {global_stock}")

if __name__ == "__main__":
    eng = prepare_db()
    print("Baza danych jest gotowa.")

    for product in retrieve_all_products(eng):
        print(product)
