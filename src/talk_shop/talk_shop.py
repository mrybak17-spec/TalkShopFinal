# ======================================================================================
#                                    INCLUDES
# ======================================================================================
"""A simple shop chatbot that answers product questions."""
from lark import Lark, Token, Tree
from lark.exceptions import LarkError

import argparse
from dataclasses import dataclass
from pathlib import Path



# ======================================================================================
#                                     grammar 
# ======================================================================================
def parse_args() -> str:
    """Parse command-line arguments and return the grammar path."""
    prs = argparse.ArgumentParser()
    prs.add_argument("-g", "--grammar", required=True, help="Path to grammar file")
    return prs.parse_args().grammar

# ======================================================================================
#                                     DATA MODEL
# ======================================================================================
@dataclass
class Product:
    """Products in the shop"""
    name: str
    price: float
    stock: int


products: dict[str, Product] = {
    "monorail": Product(name="Monorail", price=1449.99, stock=30),
    "hewlett_packard": Product(name="Hewlett Packard", price=1849.99, stock=23),
    "compaq": Product(name="COMPAQ", price=2399.99, stock=8),
}

def find_product(item: str) -> Product | None:
    """Find a product by its identifier."""
    return products.get(item.lower())

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



def process_query(query: str, grammar: str) -> str:
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
        product = find_product(item)

        if product is None:
            return f"{item} is not available in our shop"

        return f"The price of {item} is {product.price}"

    if query_node.data == "stock_question":
        item = list(query_node.find_token("ITEM"))[0].value.lower()
        product = find_product(item)

        if product is None:
            return f"{item} is not available in our shop"

        return f"The stock of {item} is {product.stock}"

    if query_node.data == "availability_question":
        item = list(query_node.find_token("ITEM"))[0].value.lower()
        product = find_product(item)

        if product is None:
            return f"{item} is not available in our shop"

        if product.stock > 0:
            return (
                f"Yes, {item} is available. "
                f"We have {product.stock} in stock."
            )

        return f"Sorry, {item} is currently unavailable."

    return "Yyyyy... I dont understand"



def main():
    """Run the shop chatbot interaction loop."""
    grammar_path = parse_args()
    grammar = Path(grammar_path).read_text(encoding="utf-8")
    print("How can i help?")
    while True:
        query = input().strip()
        if query.upper() == "END":
            print("Thanks for the chat bro")
            break
        print(process_query(query, grammar))


if __name__ == "__main__":
    main()
