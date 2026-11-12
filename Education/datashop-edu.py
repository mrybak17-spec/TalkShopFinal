# ======================================================================================
#                                    INCLUDES
# ======================================================================================
from __future__ import annotations
# Sprawia, że adnotacje typów są traktowane jak tekst i sprawdzane później.
# Jest to potrzebne, bo metoda to_model w klasie ProductModel zwraca
# "-> ProductModel", czyli odwołuje się do klasy, która jeszcze nie jest w pełni
# zdefiniowana. Bez tego importu wystąpiłby NameError.

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
# Biblioteka standardowa:
#   dataclass - dekorator do tworzenia prostych klas z danymi,
#   Path      - praca na ścieżkach (tworzenie folderu na bazę),
#   Sequence  - typ "dowolna sekwencja" (lista, krotka) do adnotacji.

from sqlalchemy import Engine, Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
# SQLAlchemy to biblioteka do pracy z bazami danych (ORM):
#   Engine          - obiekt zarządzający połączeniem z bazą,
#   Float, Integer, String - typy kolumn w tabeli,
#   create_engine   - tworzy silnik połączenia,
#   select          - buduje zapytania SELECT,
#   DeclarativeBase - klasa bazowa dla klas-tabel,
#   Mapped, mapped_column - opis kolumn w stylu SQLAlchemy 2.0,
#   Session         - sesja, czyli "rozmowa" z bazą (zbiera zmiany do commit).


# ======================================================================================
#                                     DATA MODEL
# ======================================================================================
@dataclass
class Product:
    name: str
    price: float
    stock: int
# Zwykły model danych w Pythonie, niezwiązany z bazą. Jeden obiekt = jeden produkt.
# @dataclass sam generuje konstruktor __init__, __repr__ (ładny wydruk) oraz
# __eq__ (porównywanie), na podstawie pól z adnotacjami typów.
# Użycie: Product(name="Monorail", price=1449.99, stock=30).


example_data: list[Product] = [
    Product(name="Monorail", price=1449.99, stock=30),
    Product(name="Hewlett Packard", price=1849.99, stock=23),
    Product(name="COMPAQ", price=2399.99, stock=8),
]
# Lista przykładowych produktów, służąca do wypełnienia pustej bazy
# (używa jej funkcja populate_db). Adnotacja list[Product] mówi, że to lista
# obiektów Product.


# =====================================================================================
#                                  DATABASE INTERFACE
# =====================================================================================
class DatabaseModel(DeclarativeBase):
    pass
# Klasa bazowa dla wszystkich tabel w tej bazie. DeclarativeBase z SQLAlchemy
# tworzy rejestr (DatabaseModel.metadata), w którym zbierają się wszystkie
# klasy-tabele dziedziczące po tej klasie. pass = nic więcej nie dodajemy.


class ProductModel(DatabaseModel):
    # Klasa odwzorowująca tabelę w bazie (technika ORM). Jeden obiekt
    # ProductModel = jeden wiersz tabeli.

    __tablename__ = "products"
    # Nazwa tabeli w bazie SQL.

    id: Mapped[int] = mapped_column(primary_key=True)
    # Kolumna id: liczba całkowita, klucz główny (unikalny identyfikator wiersza).
    # SQLite nadaje go automatycznie: 1, 2, 3...

    name: Mapped[str] = mapped_column(String(100))
    # Kolumna name: tekst do 100 znaków (VARCHAR(100)). Brak unique=True,
    # więc baza sama nie pilnuje unikalności nazw - robi to add_product.

    price: Mapped[float] = mapped_column(Float())
    # Kolumna price: liczba zmiennoprzecinkowa.

    stock: Mapped[int] = mapped_column(Integer())
    # Kolumna stock: liczba całkowita (stan magazynowy).

    @staticmethod
    def to_model(product: Product) -> ProductModel:
        return ProductModel(name=product.name, price=product.price, stock=product.stock)
    # Metoda statyczna (bez self): wywołuje się ją na klasie,
    # ProductModel.to_model(p). Zamienia zwykły Product na ProductModel
    # (wiersz bazy). Pole id pomija, bo nada je baza.

    def from_model(self) -> Product:
        return Product(name=self.name, price=self.price, stock=self.stock)
    # Zwykła metoda (ma self, czyli konkretny wiersz). Robi odwrotnie:
    # z wiersza bazy tworzy zwykły Product.
    # Po co dwie klasy? Reszta programu pracuje na prostym Product i nic nie
    # wie o SQLAlchemy. Konwersja odbywa się tylko na granicy z bazą.


def prepare_db() -> Engine:
    # Przygotowuje bazę i zwraca silnik połączenia (ten "eng" z reszty programu).

    Path("local").mkdir(parents=True, exist_ok=True)
    # Tworzy folder "local". parents=True tworzy też foldery nadrzędne,
    # exist_ok=True zapobiega błędowi, gdy folder już istnieje.
    # Baza SQLite to plik, więc folder musi istnieć wcześniej.

    engine = create_engine("sqlite:///local/demo.db")
    # Tworzy silnik. Napis to adres bazy: sqlite = typ bazy (plik na dysku,
    # bez osobnego serwera), local/demo.db = ścieżka do pliku. Jeśli pliku nie
    # ma, powstanie przy pierwszym połączeniu.

    DatabaseModel.metadata.create_all(engine)
    # Tworzy w bazie wszystkie tabele zdefiniowane przez klasy dziedziczące po
    # DatabaseModel (tu: products). Jeśli tabela już istnieje, nic nie robi
    # i nie kasuje danych.

    return engine
    # Zwraca silnik, którego używają pozostałe funkcje.


# ======================================================================================
#                                     OPERATIONS
# ======================================================================================
def populate_db(eng: Engine) -> None:
    # Wypełnia bazę przykładowymi danymi z example_data.

    with Session(eng) as session:
        # Otwiera sesję. "with" gwarantuje jej zamknięcie na końcu bloku,
        # nawet przy błędzie. Zmiany nie zapisują się same - trzeba commit().

        for product in example_data:
            session.add(ProductModel.to_model(product))
        # Dla każdego produktu z listy: zamienia Product na ProductModel
        # i dodaje do sesji. Wiersze czekają jeszcze w pamięci.

        session.commit()
        # Zatwierdza transakcję: wszystkie dodane wiersze trafiają do bazy.
        # Uwaga: funkcja nie sprawdza duplikatów, więc dwukrotne wywołanie
        # zdubluje dane. Nie jest też nigdzie wywoływana automatycznie.

def clear_db(eng: Engine)-> None:
    # Usuwa wszystkie produkty (opcja 6 w menu admina).

    with Session(eng) as session:
        session.query(ProductModel).delete(synchronize_session="fetch")
        # session.query(ProductModel) = "wszystkie wiersze tabeli products"
        # (starszy styl zapytań). .delete() usuwa je jednym poleceniem SQL.
        # synchronize_session="fetch" każe SQLAlchemy zaktualizować swój stan
        # dla obiektów już załadowanych do sesji. Tu sesja jest świeża,
        # więc to głównie formalność.

        session.commit()
        # Zatwierdza usunięcie. Bez tego zmiana zostałaby wycofana.

def add_product(eng: Engine, product: Product) -> bool:
    """Dodaje produkt. Nie pozwala na duplikaty nazw."""
    # Zwraca True (dodano) albo False (duplikat nazwy).

    with Session(eng) as session:
        existing = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(product.name)
            )
        ).first()
        # Od środka:
        #   select(ProductModel)  - zapytanie SELECT ... FROM products,
        #   .where(...)           - dodaje warunek,
        #   .ilike(...)           - porównanie bez rozróżniania wielkości liter
        #                           (i = insensitive), więc COMPAQ == compaq,
        #   session.scalars(...)  - wykonuje zapytanie i zwraca same obiekty
        #                           ProductModel,
        #   .first()              - pierwszy wynik albo None.
        # Uwaga: w LIKE znaki % i _ są wzorcami, więc nazwa "%" dopasuje wszystko.

        if existing is not None:
            return False
        # Produkt o takiej nazwie już istnieje -> False.
        # Menu pokazuje wtedy "Produkt o takiej nazwie już istnieje".

        session.add(ProductModel.to_model(product))
        session.commit()
        return True
        # Nazwa wolna: konwertuje, dodaje, zatwierdza i zwraca True.


def retrieve_product_by_name(
    eng: Engine, name: str
) -> list[Product]:
    """Wyszukuje produkty po nazwie, bez rozróżniania wielkości liter."""
    # Zwraca LISTĘ produktów (może być pusta albo mieć kilka elementów).

    with Session(eng) as session:
        products = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(name)
            )
        ).all()
        # Zapytanie jak w add_product, ale .all() zwraca WSZYSTKIE pasujące
        # wiersze, a nie tylko pierwszy.

        return [product.from_model() for product in products]
        # List comprehension: dla każdego ProductModel wywołuje from_model(),
        # więc na zewnątrz wychodzą zwykłe obiekty Product.
        # Konwersja musi się odbyć WEWNĄTRZ bloku with, póki sesja jest otwarta.


def retrieve_all_products(eng: Engine) -> list[Product]:
    """Zwraca wszystkie produkty."""
    with Session(eng) as session:
        products = session.scalars(
            select(ProductModel).order_by(ProductModel.id)
        ).all()
        # Pobiera wszystkie produkty bez warunku where. order_by(ProductModel.id)
        # sortuje je po id (czyli w kolejności dodawania), żeby wynik był
        # przewidywalny.

        return [product.from_model() for product in products]
        # Konwersja na zwykłe obiekty Product, jak wyżej.


def update_product(
    eng: Engine,
    name: str,
    new_name: str,
    new_price: float,
    new_stock: int
) -> bool:
    """Zmienia nazwę, cenę i stan produktu."""
    # name = AKTUALNA nazwa (po niej szukamy rekordu), new_* = nowe wartości.
    # Zwraca True/False.

    with Session(eng) as session:
        product = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(name)
            )
        ).first()
        # Szuka produktu po starej nazwie.

        if product is None:
            return False
        # Nie ma takiego produktu -> False.

        # Nie pozwalaj zmienić nazwy na nazwę innego produktu.
        duplicate = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(new_name),
                ProductModel.id != product.id
            )
        ).first()
        # Sprawdza, czy INNY produkt ma już nową nazwę. Warunek
        # ProductModel.id != product.id wyklucza samego edytowanego produktu,
        # dzięki czemu można zmienić tylko cenę, zostawiając nazwę. Dwa warunki
        # w .where(...) są łączone przez AND.

        if duplicate is not None:
            return False
        # Nowa nazwa zajęta przez inny produkt -> False.

        product.name = new_name
        product.price = new_price
        product.stock = new_stock
        # Zmienia pola obiektu. SQLAlchemy sam śledzi zmiany w obiektach
        # pobranych z sesji, więc commit() wygeneruje odpowiednie UPDATE.

        session.commit()
        return True
        # Zapisuje zmiany i zwraca True.


def delete_product(eng: Engine, name: str) -> bool:
    """Usuwa jeden produkt po nazwie."""
    with Session(eng) as session:
        product = session.scalars(
            select(ProductModel).where(
                ProductModel.name.ilike(name)
            )
        ).first()
        # Szuka produktu po nazwie (pierwszy pasujący albo None).

        if product is None:
            return False
        # Brak produktu -> False.

        session.delete(product)
        session.commit()
        return True
        # session.delete oznacza obiekt do usunięcia, a commit() wykonuje
        # faktyczne DELETE. Zwraca True.

def statistics(eng: Engine, products: Sequence[Product]) -> None:
    """Wyświetla statystyki dotyczące produktów w bazie danych."""
    # products = dowolna sekwencja obiektów Product. Funkcja tylko drukuje.
    # Parametr eng nie jest tu używany (można go usunąć razem z wywołaniem
    # w admin_menu).

    products_number = len(products)
    # Liczba produktów.

    global_worth = sum(product.price * product.stock for product in products)
    # Łączna wartość magazynu: cena * liczba sztuk dla każdego produktu,
    # wszystko zsumowane. To generator w sum(), bez tworzenia pośredniej listy.

    global_stock = sum(product.stock for product in products)
    # Łączna liczba sztuk wszystkich produktów.

    print(f"Liczba produktów w bazie: {products_number}")
    print(f"Łączna wartość magazynu: {global_worth:.2f}")
    print(f"Łączny stan magazynowy: {global_stock}")
    # Wypisuje wyniki; wartość z dwoma miejscami po przecinku (:.2f).

if __name__ == "__main__":
    eng = prepare_db()
    print("Baza danych jest gotowa.")
    # Przygotowuje bazę i wypisuje komunikat.

    for product in retrieve_all_products(eng):
        print(product)
    # Drukuje każdy produkt. Dataclass ma automatyczny __repr__, więc zobaczysz
    # np. Product(name='Monorail', price=1449.99, stock=30).
# Ten blok wykonuje się tylko przy bezpośrednim uruchomieniu pliku
# (python data_shop.py), a nie przy imporcie przez główny program.