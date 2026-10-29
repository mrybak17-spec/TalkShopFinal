# =====================================================================================
#                                    INCLUDES
# =====================================================================================
from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy import String, Float, Integer, create_engine, select
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

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

def retrieve_product_by_name(eng: Engine, name: str) -> list[Product]:
    prods: list[Product] = []
    with Session(eng) as session:
        products: Sequence[ProductModel] = session.scalars(
            select(ProductModel).where(ProductModel.name == name)
        ).all()
        for product in products:
            prods.append(product.from_model())
    return prods

def main() -> None:
    eng = prepare_db()
    clear_db(eng)
    populate_db(eng)
    prods = retrieve_product_by_name(eng, "Monorail")
    for prod in prods:
        print(prod)


if __name__ == "__main__":
    main()
