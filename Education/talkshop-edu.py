# ======================================================================================
#                                    INCLUDES
# ======================================================================================
"""A simple shop chatbot that answers product questions. - I would rather write those helping texts in Polish, but I will stick to the English"""
# Docstring modułu: opis całego pliku. Nie wpływa na działanie programu.

from lark import Lark, Token, Tree
from lark.exceptions import LarkError
# Z biblioteki Lark importujemy:
#   Lark      - klasa parsera (zamienia tekst na drzewo wg gramatyki),
#   Token     - liść drzewa (konkretny kawałek tekstu, np. nazwa produktu),
#   Tree      - węzeł drzewa (reguła gramatyki z listą dzieci),
#   LarkError - bazowy wyjątek Lark, łapiemy go przy błędach parsowania.

import argparse
from dataclasses import dataclass
from pathlib import Path
# Moduły biblioteki standardowej:
#   argparse  - odczyt argumentów z wiersza poleceń (-g, --admin),
#   dataclass - import nieużywany w tym pliku (można usunąć),
#   Path      - wygodna praca na ścieżkach i plikach.

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
# Import z Twojego modułu data_shop (warstwa bazy danych):
#   Product                  - klasa modelu produktu (name, price, stock),
#   prepare_db               - tworzy połączenie/bazę i zwraca obiekt eng,
#   add_product              - dodaje produkt, zwraca True/False,
#   retrieve_product_by_name - zwraca listę produktów o danej nazwie,
#   retrieve_all_products    - zwraca listę wszystkich produktów,
#   update_product           - zmienia produkt, zwraca True/False,
#   delete_product           - usuwa produkt, zwraca True/False,
#   clear_db                 - usuwa wszystkie produkty,
#   statistics               - wyświetla statystyki produktów.


# ======================================================================================
#                                     grammar
# ======================================================================================
def parse_args():
    """Odczytuje argumenty uruchomieniowe."""
    prs = argparse.ArgumentParser()
    # Tworzy parser argumentów terminala. Automatycznie dodaje też -h/--help.

    prs.add_argument(
        "-g",
        "--grammar",
        required=True,
        help="Path to grammar file"
    )
    # Rejestruje argument -g / --grammar (ścieżka do pliku gramatyki).
    # required=True: bez niego program zakończy się błędem.
    # Wartość będzie dostępna jako args.grammar (tekst).

    prs.add_argument(
        "--admin",
        action="store_true",
        help="Run in administrator mode"
    )
    # Rejestruje flagę --admin. action="store_true" oznacza, że flaga nie
    # przyjmuje wartości: podana -> args.admin == True, niepodana -> False.

    return prs.parse_args()
    # Odczytuje faktyczne argumenty z terminala (sys.argv), sprawdza je i zwraca
    # obiekt Namespace z polami grammar i admin.


# ======================================================================================
#                                     DATA MODEL
# ======================================================================================

def normalize_name(name: str) -> str:
    """Normalizuje identyfikator produktu z gramatyki."""
    return name.strip().replace("_", " ").casefold()
    # Trzy kroki po kolei:
    #   .strip()    - usuwa białe znaki z początku i końca,
    #   .replace()  - zamienia podkreślniki na spacje (Green_Tea -> Green Tea),
    #   .casefold() - zamienia na małe litery (agresywniej niż .lower()).
    # Dzięki temu "  Green_Tea " i "green tea" dają ten sam wynik: "green tea".


def find_product(item: str, eng) -> Product | None:
    """Wyszukuje produkt w bazie danych."""
    # item - szukana nazwa, eng - połączenie z bazą.
    # Zwraca obiekt Product albo None (zapis "X | None" działa od Pythona 3.10).

    wanted = normalize_name(item)
    # Normalizujemy szukaną nazwę raz, przed pętlą.

    for product in retrieve_all_products(eng):
        if normalize_name(product.name) == wanted:
            return product
    # Pobiera wszystkie produkty i porównuje znormalizowane nazwy.
    # Przy pierwszej zgodności od razu zwraca produkt i kończy funkcję.

    return None
    # Pętla nic nie znalazła -> "nie ma takiego produktu".


# ======================================================================================
#                                     NLP
# ======================================================================================


def print_tree(node: Tree | Token, depth: int = 0) -> None:
    """Print the parse tree with indentation."""
    # Funkcja rekurencyjna (wywołuje samą siebie), wypisuje drzewo z wcięciami.
    # node - Tree albo Token, depth - aktualna głębokość (liczba spacji wcięcia).

    if isinstance(node, Token):
        print(" " * depth + f"{node.type} = {node.value}")
        return
    # Jeśli to token (liść): wypisuje "TYP = wartość", np. "ITEM = apple".
    # return to warunek stopu rekurencji - token nie ma dzieci.

    print(" " * depth + node.data)
    # Jeśli to Tree: wypisuje nazwę reguły (np. price_question).

    for subtree in node.children:
        print_tree(subtree, depth + 1)
    # Dla każdego dziecka wywołuje się ponownie z głębokością o 1 większą,
    # więc dzieci są wcięte głębiej niż rodzic.



def process_query(query: str, grammar: str, eng) -> str:
    """Parse a user query and return the appropriate shop response."""
    # query - tekst od użytkownika, grammar - treść gramatyki Lark,
    # eng - połączenie z bazą. Zwraca gotową odpowiedź jako tekst.

    try:
        parser = Lark(grammar, parser="earley")
        tree = parser.parse(query)
    except LarkError:
        return "Yyyyy... I dont understand"
    # Buduje parser Earley (radzi sobie z niejednoznacznymi gramatykami)
    # i parsuje zapytanie na drzewo. Jeśli tekst nie pasuje do gramatyki,
    # Lark rzuca LarkError, a my zwracamy komunikat o niezrozumieniu.
    # Uwaga: parser budowany przy każdym zapytaniu jest wolny - lepiej
    # utworzyć go raz (np. w main) i przekazywać dalej.

    if not tree.children or not isinstance(tree.children[0], Tree):
        return "Yyyyy... I dont understand"
    # Dodatkowe zabezpieczenie: drzewo musi mieć dzieci, a pierwsze dziecko
    # musi być poddrzewem (Tree), a nie samym tokenem.

    query_node = tree.children[0]
    # Węzeł konkretnego zapytania (np. price_question). Jego .data to nazwa reguły.

    if query_node.data == "price_question":
        # Gałąź: pytanie o cenę.

        item = list(query_node.find_token("ITEM"))[0].value.lower()
        # Od środka: find_token("ITEM") zwraca generator tokenów typu ITEM,
        # list() robi z niego listę, [0] bierze pierwszy, .value to jego tekst,
        # .lower() zamienia na małe litery. Wynik: nazwa produktu, np. "apple".

        product = find_product(item, eng)
        # Szuka produktu w bazie: Product albo None.

        if product is None:
            return f"{item} is not available in our shop"
        # Nie znaleziono -> odpowiedź, że sklep tego nie ma.

        return f"The price of {item} is {product.price}"
        # Znaleziono -> zwraca cenę.

    if query_node.data == "stock_question":
        # Gałąź: pytanie o stan magazynowy.

        item = list(query_node.find_token("ITEM"))[0].value.lower()
        product = find_product(item, eng)
        # Tak samo jak wyżej: wyciągnięcie nazwy i wyszukanie produktu.

        if product is None:
            return f"{item} is not available in our shop"
        # Brak produktu -> komunikat.

        return f"The stock of {item} is {product.stock}"
        # Zwraca liczbę sztuk w magazynie.

    if query_node.data == "availability_question":
        # Gałąź: pytanie, czy produkt jest dostępny.

        item = list(query_node.find_token("ITEM"))[0].value.lower()
        product = find_product(item, eng)
        # Wyciągnięcie nazwy i wyszukanie produktu.

        if product is None:
            return f"{item} is not available in our shop"
        # Brak produktu -> komunikat.

        if product.stock > 0:
            return (
                f"Yes, {item} is available. "
                f"We have {product.stock} in stock."
            )
        # Stan > 0 -> odpowiedź twierdząca z liczbą sztuk.
        # Dwa f-stringi w nawiasie Python skleja w jeden tekst.

        return f"Sorry, {item} is currently unavailable."
        # Stan == 0 -> produkt chwilowo niedostępny.

    return "Yyyyy... I dont understand"
    # Żadna z trzech reguł nie pasuje -> komunikat domyślny.

def read_price() -> float:
    """Pobiera poprawną cenę."""
    # Pyta użytkownika o cenę do skutku, aż poda poprawną wartość.

    while True:
        # Nieskończona pętla; wychodzi z niej tylko return.

        try:
            price = float(input("Podaj cenę: ").replace(",", "."))
            # input() pobiera tekst, .replace zamienia przecinek na kropkę
            # (149,99 -> 149.99), float() zamienia tekst na liczbę.
            # Gdy się nie da (np. "abc"), rzuca ValueError.

            if price < 0:
                print("Cena nie może być ujemna.")
                continue
            # Ujemna cena -> komunikat; continue zaczyna pętlę od nowa.

            return price
            # Cena poprawna -> zwraca ją i kończy funkcję.

        except ValueError:
            print("Podaj poprawną liczbę, np. 149.99.")
            # Zły format -> podpowiedź i ponowne pytanie.


def read_stock() -> int:
    """Pobiera poprawną liczbę sztuk."""
    # Tak samo jak read_price, ale dla liczby całkowitej.

    while True:
        try:
            stock = int(input("Podaj stan magazynowy: "))
            # int() akceptuje "10", ale odrzuca "10.5" i "abc" (ValueError).
            # Nie ma tu replace, bo ułamki nie są potrzebne.

            if stock < 0:
                print("Stan magazynowy nie może być ujemny.")
                continue
            # Ujemny stan -> komunikat i ponowne pytanie.

            return stock
            # Poprawna wartość -> zwraca i kończy.

        except ValueError:
            print("Podaj liczbę całkowitą, np. 10.")
            # Zły format -> podpowiedź i ponowne pytanie.


def print_products(eng) -> None:
    """Wyświetla wszystkie produkty."""
    # Tylko drukuje, nic nie zwraca.

    products = retrieve_all_products(eng)
    # Pobiera listę wszystkich produktów z bazy.

    if not products:
        print("Brak produktów w bazie.")
        return
    # Pusta lista jest "fałszywa", więc not products == True.
    # return kończy funkcję wcześniej (early return).

    for product in products:
        print(
            f"Nazwa: {product.name} | "
            f"Cena: {product.price:.2f} | "
            f"Stan: {product.stock}"
        )
    # Dla każdego produktu wypisuje jedną linię. {product.price:.2f} formatuje
    # cenę do dwóch miejsc po przecinku (5 -> 5.00).

def admin_menu(eng) -> None:
    """Menu zarządzania produktami."""
    # Wyświetla menu w pętli i wykonuje wybraną operację na bazie.

    while True:
        # Pętla działa, dopóki użytkownik nie wybierze opcji 0 (break).

        print("\n===== MENU ADMINA =====")
        print("1 - Dodaj produkt")
        print("2 - Znajdź produkt")
        print("3 - Zmień produkt")
        print("4 - Usuń produkt")
        print("5 - Lista produktów")
        print("6 - Wyczyść bazę danych")
        print("7 - Statystyka")
        print("0 - Wyjdź")
        # Wypisuje opcje. \n na początku daje pustą linię odstępu.

        choice = input("Wybierz opcję: ").strip()
        # Pobiera wybór jako TEKST (dlatego niżej porównujemy z "1", "2"...).

        # 1. Dodaj produkt
        if choice == "1":
            name = input("Podaj nazwę produktu: ").strip()
            # Pobiera nazwę nowego produktu.

            if not name or len(name) > 100:
                print("Nazwa musi mieć od 1 do 100 znaków.")
                continue
            # Odrzuca pustą nazwę lub dłuższą niż 100 znaków.
            # continue wraca na początek pętli while (do menu).

            price = read_price()
            stock = read_stock()
            # Pytają do skutku o poprawną cenę i stan magazynowy.

            product = Product(
                name=name,
                price=price,
                stock=stock
            )
            # Tworzy obiekt produktu z podanych danych.

            if add_product(eng, product):
                print("Produkt został dodany.")
            else:
                print("Produkt o takiej nazwie już istnieje.")
            # add_product zwraca True/False; False = nazwa jest już zajęta.

        # 2. Znajdź produkt
        elif choice == "2":
            name = input("Podaj nazwę produktu: ").strip()
            # Pobiera szukaną nazwę.

            products = retrieve_product_by_name(eng, name)
            # Pobiera z bazy listę produktów o tej nazwie.

            if products:
                for product in products:
                    print(
                        f"{product.name} | "
                        f"Cena: {product.price:.2f} | "
                        f"Stan: {product.stock}"
                    )
            else:
                print("Nie znaleziono produktu.")
            # Niepusta lista -> wypisuje każdy produkt. Pusta -> komunikat.

        # 3. Zmień produkt
        elif choice == "3":
            name = input(
                "Podaj nazwę produktu do zmiany: "
            ).strip()
            # Pobiera nazwę produktu, który chcemy zmienić.

            products = retrieve_product_by_name(eng, name)
            # Szuka go w bazie.

            if not products:
                print("Nie znaleziono produktu.")
                continue
            # Brak wyników -> komunikat i powrót do menu.

            if len(products) > 1:
                print("Znaleziono kilka produktów o tej nazwie.")
                print("Zmień nazwy produktów, aby były unikalne.")
                continue
            # Kilka wyników -> nie wiadomo, który zmienić, więc przerywamy.

            product = products[0]
            # Jedyny znaleziony produkt.

            print(
                f"Aktualnie: {product.name}, "
                f"{product.price:.2f}, stan: {product.stock}"
            )
            # Pokazuje aktualne dane, żeby użytkownik wiedział, co zmienia.

            new_name = input(
                "Nowa nazwa (Enter = bez zmian): "
            ).strip()
            # Pobiera nową nazwę. Pusty wpis (Enter) oznacza "bez zmian".

            if not new_name:
                new_name = product.name
            # Pusty wpis -> zostaje stara nazwa.

            if len(new_name) > 100:
                print("Nazwa może mieć maksymalnie 100 znaków.")
                continue
            # Limit długości nazwy, tak jak przy dodawaniu.

            new_price_text = input(
                "Nowa cena (Enter = bez zmian): "
            ).strip()
            # Cena pobrana jako tekst, żeby dało się rozpoznać pusty wpis.

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
            # Coś wpisano -> zamiana przecinka na kropkę, konwersja na float,
            # odrzucenie wartości ujemnych i błędnych formatów (continue wraca
            # do menu). Nic nie wpisano -> zostaje stara cena.
            # Ręczna walidacja jest tu potrzebna, bo read_price() nie pozwala
            # na pusty wpis.

            new_stock_text = input(
                "Nowy stan (Enter = bez zmian): "
            ).strip()
            # Stan magazynowy też jako tekst (pusty wpis = bez zmian).

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
            # Ta sama logika co przy cenie, ale z int() zamiast float().

            success = update_product(
                eng,
                product.name,
                new_name,
                new_price,
                new_stock
            )
            # Zapisuje zmiany. Przekazuje STARĄ nazwę (żeby wiedzieć, który
            # rekord zmienić) oraz nowe wartości. Zwraca True/False.

            if success:
                print("Produkt został zmieniony.")
            else:
                print(
                    "Nie udało się zmienić produktu. "
                    "Sprawdź, czy nowa nazwa nie jest zajęta."
                )
            # False zwykle oznacza, że nowa nazwa jest już używana.

        # 4. Usuń produkt
        elif choice == "4":
            name = input(
                "Podaj nazwę produktu do usunięcia: "
            ).strip()
            # Pobiera nazwę produktu do usunięcia.

            products = retrieve_product_by_name(eng, name)
            # Szuka go w bazie.

            if not products:
                print("Nie znaleziono produktu.")
                continue
            # Brak wyników -> powrót do menu.

            if len(products) > 1:
                print(
                    "Znaleziono kilka produktów o tej nazwie. "
                    "Usuwanie przerwane."
                )
                continue
            # Kilka wyników -> dla bezpieczeństwa nic nie usuwamy.

            confirm = input(
                f"Czy usunąć {products[0].name}? (tak/nie): "
            ).strip().lower()
            # Prosi o potwierdzenie. .lower() sprawia, że TAK, Tak i tak
            # są równoważne.

            if confirm == "tak":
                if delete_product(eng, products[0].name):
                    print("Produkt został usunięty.")
                else:
                    print("Nie udało się usunąć produktu.")
            else:
                print("Anulowano usuwanie.")
            # Usuwa tylko po potwierdzeniu "tak". Każda inna odpowiedź anuluje.

        # 5. Lista produktów
        elif choice == "5":
            print_products(eng)
            # Wywołuje funkcję wypisującą wszystkie produkty.

        # 6. Wyczyść bazę
        elif choice == "6":
            confirm = input(
                "To usunie WSZYSTKIE produkty. "
                "Wpisz TAK, aby potwierdzić: "
            ).strip()
            # Ostrzejsze potwierdzenie: bez .lower(), więc trzeba wpisać
            # dokładnie TAK wielkimi literami (operacja jest nieodwracalna).

            if confirm == "TAK":
                clear_db(eng)
                print("Baza produktów została wyczyszczona.")
            else:
                print("Anulowano czyszczenie.")
            # Czyści bazę tylko przy dokładnym potwierdzeniu.

        elif choice == "7":
            products = retrieve_all_products(eng)
            statistics(eng, products)
            # Pobiera wszystkie produkty i przekazuje je do funkcji statistics
            # (zdefiniowanej w data_shop), która wypisuje statystyki.

        # Wyjście z menu
        elif choice == "0":
            print("Koniec pracy administratora.")
            break
            # break wychodzi z pętli while, więc funkcja się kończy.

        else:
            print("Niepoprawna opcja. Wybierz od 0 do 7.")
            # Każdy inny wpis -> komunikat. (Poprawiono z "0 do 6" na "0 do 7",
            # bo istnieje opcja 7.)

def main():
    """Uruchamia chat lub menu administratora."""

    args = parse_args()
    # Odczytuje argumenty z terminala: args.grammar i args.admin.

    grammar = Path(args.grammar).read_text(encoding="utf-8")
    # Path(...) tworzy obiekt ścieżki, .read_text() wczytuje cały plik jako
    # tekst. Wynik to treść gramatyki, którą dostaje process_query.

    # Przygotowujemy bazę tylko raz.
    eng = prepare_db()
    # Tworzy połączenie z bazą (i ewentualnie tabele) i zwraca eng.

    if args.admin:
        admin_menu(eng)
        return
    # Tryb admina (--admin): pokazuje menu, a return kończy main,
    # więc tryb czatu się nie uruchomi.

    print("How can i help?")
    # Tryb czatu: powitanie.

    while True:
        query = input().strip()
        # Czyta zapytanie użytkownika w nieskończonej pętli.

        if query.upper() == "END":
            print("Thanks for the chat my friend")
            break
        # Wpisanie "end" (w dowolnej wielkości liter) kończy rozmowę.

        print(process_query(query, grammar, eng))
        # Przekazuje zapytanie do parsera i drukuje odpowiedź sklepu.


if __name__ == "__main__":
    main()
# __name__ == "__main__" jest prawdą tylko przy bezpośrednim uruchomieniu pliku
# (python program.py). Przy imporcie jako moduł main() się nie wykona.