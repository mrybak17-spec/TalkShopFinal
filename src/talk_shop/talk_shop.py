# ======================================================================================
#                                    INCLUDES
# ======================================================================================
"""A simple shop chatbot that answers product questions. - I would rather write those helping texts in Polish, but I will stick to the English"""
from lark import Lark, Token, Tree
from lark.exceptions import LarkError

import argparse
from dataclasses import dataclass
from pathlib import Path

from data_shop import (
    Product,
    prepare_db,
    add_product,
    retrieve_product_by_name,
    retrieve_all_products,
    update_product,
    delete_product,
    clear_db,
    statistics,
)


# ======================================================================================
#                                     grammar 
# ======================================================================================
def parse_args():
    """Odczytuje argumenty uruchomieniowe."""
    prs = argparse.ArgumentParser()

    prs.add_argument(
        "-g",
        "--grammar",
        required=True,
        help="Path to grammar file"
    )

    prs.add_argument(
        "--admin",
        action="store_true",
        help="Run in administrator mode"
    )

    return prs.parse_args()

# ======================================================================================
#                                     DATA MODEL
# ======================================================================================

def normalize_name(name: str) -> str:
    """Normalizuje identyfikator produktu z gramatyki."""
    return name.strip().replace("_", " ").casefold()


def find_product(item: str, eng) -> Product | None:
    """Wyszukuje produkt w bazie danych."""
    wanted = normalize_name(item)

    for product in retrieve_all_products(eng):
        if normalize_name(product.name) == wanted:
            return product

    return None

# ======================================================================================
#                                     NLP
# ======================================================================================


def print_tree(node: Tree | Token, depth: int = 0) -> None:
    """Print the parse tree with indentation."""
    if isinstance(node, Token):
        print(" " * depth + f"{node.type} = {node.value}")
        return
    print(" " * depth + node.data)
    for subtree in node.children:
        print_tree(subtree, depth + 1)



def process_query(query: str, grammar: str, eng) -> str:
    """Parse a user query and return the appropriate shop response."""
    try:
        parser = Lark(grammar, parser="earley")
        tree = parser.parse(query)
    except LarkError:
        return "Yyyyy... I dont understand"

    if not tree.children or not isinstance(tree.children[0], Tree):
        return "Yyyyy... I dont understand"

    query_node = tree.children[0]

    if query_node.data == "price_question":
        item = list(query_node.find_token("ITEM"))[0].value.lower()
        product = find_product(item, eng)

        if product is None:
            return f"{item} is not available in our shop"

        return f"The price of {item} is {product.price}"

    if query_node.data == "stock_question":
        item = list(query_node.find_token("ITEM"))[0].value.lower()
        pproduct = find_product(item, eng)

        if product is None:
            return f"{item} is not available in our shop"

        return f"The stock of {item} is {product.stock}"

    if query_node.data == "availability_question":
        item = list(query_node.find_token("ITEM"))[0].value.lower()
        product = find_product(item, eng)

        if product is None:
            return f"{item} is not available in our shop"

        if product.stock > 0:
            return (
                f"Yes, {item} is available. "
                f"We have {product.stock} in stock."
            )

        return f"Sorry, {item} is currently unavailable."

    return "Yyyyy... I dont understand"

def read_price() -> float:
    """Pobiera poprawną cenę."""
    while True:
        try:
            price = float(input("Podaj cenę: ").replace(",", "."))
            if price < 0:
                print("Cena nie może być ujemna.")
                continue
            return price
        except ValueError:
            print("Podaj poprawną liczbę, np. 149.99.")


def read_stock() -> int:
    """Pobiera poprawną liczbę sztuk."""
    while True:
        try:
            stock = int(input("Podaj stan magazynowy: "))
            if stock < 0:
                print("Stan magazynowy nie może być ujemny.")
                continue
            return stock
        except ValueError:
            print("Podaj liczbę całkowitą, np. 10.")


def print_products(eng) -> None:
    """Wyświetla wszystkie produkty."""
    products = retrieve_all_products(eng)

    if not products:
        print("Brak produktów w bazie.")
        return

    for product in products:
        print(
            f"Nazwa: {product.name} | "
            f"Cena: {product.price:.2f} | "
            f"Stan: {product.stock}"
        )

def admin_menu(eng) -> None:
    """Menu zarządzania produktami."""

    while True:
        print("\n===== MENU ADMINA =====")
        print("1 - Dodaj produkt")
        print("2 - Znajdź produkt")
        print("3 - Zmień produkt")
        print("4 - Usuń produkt")
        print("5 - Lista produktów")
        print("6 - Wyczyść bazę danych")
        print("7 - Statystyka")
        print("0 - Wyjdź")

        choice = input("Wybierz opcję: ").strip()

        # 1. Dodaj produkt
        if choice == "1":
            name = input("Podaj nazwę produktu: ").strip()

            if not name or len(name) > 100:
                print("Nazwa musi mieć od 1 do 100 znaków.")
                continue

            price = read_price()
            stock = read_stock()

            product = Product(
                name=name,
                price=price,
                stock=stock
            )

            if add_product(eng, product):
                print("Produkt został dodany.")
            else:
                print("Produkt o takiej nazwie już istnieje.")

        # 2. Znajdź produkt
        elif choice == "2":
            name = input("Podaj nazwę produktu: ").strip()

            products = retrieve_product_by_name(eng, name)

            if products:
                for product in products:
                    print(
                        f"{product.name} | "
                        f"Cena: {product.price:.2f} | "
                        f"Stan: {product.stock}"
                    )
            else:
                print("Nie znaleziono produktu.")

        # 3. Zmień produkt
        elif choice == "3":
            name = input(
                "Podaj nazwę produktu do zmiany: "
            ).strip()

            products = retrieve_product_by_name(eng, name)

            if not products:
                print("Nie znaleziono produktu.")
                continue

            if len(products) > 1:
                print("Znaleziono kilka produktów o tej nazwie.")
                print("Zmień nazwy produktów, aby były unikalne.")
                continue

            product = products[0]

            print(
                f"Aktualnie: {product.name}, "
                f"{product.price:.2f}, stan: {product.stock}"
            )

            new_name = input(
                "Nowa nazwa (Enter = bez zmian): "
            ).strip()

            if not new_name:
                new_name = product.name

            if len(new_name) > 100:
                print("Nazwa może mieć maksymalnie 100 znaków.")
                continue

            new_price_text = input(
                "Nowa cena (Enter = bez zmian): "
            ).strip()

            if new_price_text:
                try:
                    new_price = float(
                        new_price_text.replace(",", ".")
                    )
                    if new_price < 0:
                        print("Cena nie może być ujemna.")
                        continue
                except ValueError:
                    print("Niepoprawna cena.")
                    continue
            else:
                new_price = product.price

            new_stock_text = input(
                "Nowy stan (Enter = bez zmian): "
            ).strip()

            if new_stock_text:
                try:
                    new_stock = int(new_stock_text)
                    if new_stock < 0:
                        print("Stan nie może być ujemny.")
                        continue
                except ValueError:
                    print("Stan musi być liczbą całkowitą.")
                    continue
            else:
                new_stock = product.stock

            success = update_product(
                eng,
                product.name,
                new_name,
                new_price,
                new_stock
            )

            if success:
                print("Produkt został zmieniony.")
            else:
                print(
                    "Nie udało się zmienić produktu. "
                    "Sprawdź, czy nowa nazwa nie jest zajęta."
                )

        # 4. Usuń produkt
        elif choice == "4":
            name = input(
                "Podaj nazwę produktu do usunięcia: "
            ).strip()

            products = retrieve_product_by_name(eng, name)

            if not products:
                print("Nie znaleziono produktu.")
                continue

            if len(products) > 1:
                print(
                    "Znaleziono kilka produktów o tej nazwie. "
                    "Usuwanie przerwane."
                )
                continue

            confirm = input(
                f"Czy usunąć {products[0].name}? (tak/nie): "
            ).strip().lower()

            if confirm == "tak":
                if delete_product(eng, products[0].name):
                    print("Produkt został usunięty.")
                else:
                    print("Nie udało się usunąć produktu.")
            else:
                print("Anulowano usuwanie.")

        # 5. Lista produktów
        elif choice == "5":
            print_products(eng)

        # 6. Wyczyść bazę
        elif choice == "6":
            confirm = input(
                "To usunie WSZYSTKIE produkty. "
                "Wpisz TAK, aby potwierdzić: "
            ).strip()

            if confirm == "TAK":
                clear_db(eng)
                print("Baza produktów została wyczyszczona.")
            else:
                print("Anulowano czyszczenie.")
        
        elif choice == "7":
            products = retrieve_all_products(eng)
            statistics(eng, products)

        # Wyjście z menu
        elif choice == "0":
            print("Koniec pracy administratora.")
            break

        else:
            print("Niepoprawna opcja. Wybierz od 0 do 6.")

def main():
    """Uruchamia chat lub menu administratora."""
    args = parse_args()

    grammar = Path(args.grammar).read_text(encoding="utf-8")

    # Przygotowujemy bazę tylko raz.
    eng = prepare_db()

    if args.admin:
        admin_menu(eng)
        return

    print("How can i help?")

    while True:
        query = input().strip()

        if query.upper() == "END":
            print("Thanks for the chat my friend")
            break

        print(process_query(query, grammar, eng))


if __name__ == "__main__":
    main()