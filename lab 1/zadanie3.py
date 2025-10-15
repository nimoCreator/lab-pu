
def process(set1: set[str], set2: set[str]):
    """
    Funkcja dokonuje analizy czesci wpolnej, sumy i roznic dwoch zbiorow sringow
    """
    print("\nProdukty wspólne:", set1.intersection(set2))
    print("Produkty unikalne dla osoby 1:", set1.difference(set2))
    print("Produkty unikalne dla osoby 2:", set2.difference(set1))
    print("Pełna lista produktów:", set1.union(set2))

def getList() -> list[str]:
    """
    Funkcja pobiera od uzytkownika wartosci stringowe oddzielane przecinkami i je zwraca

    :return: Wprowadzona przez uzytkownika lista stringow
    """
    return input("Podaj listę zakupów osoby, rozdzielając produkty przecinkiem: ").split(',')

# main:
try:
    set1 = set([produkt.strip().lower() for produkt in getList()])
    set2 = set([produkt.strip().lower() for produkt in getList()])
    process(set1, set2)
    
except ValueError as e:
    print(f"Wystapil wyjatek: {e}")