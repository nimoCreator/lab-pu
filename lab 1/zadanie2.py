from typing import List
from typeguard import typechecked

@typechecked
def process(dane: List[float]) -> dict[str, float]:
    """
    Funkcja oblicza sume, srednia i liczbe dodatnich wartosci w podanej liscie liczb.

    :param dane: Lista liczb
    :return: Slownik zawierajacy sume, srednia i liczbe dodatnich liczb
    """
    if not dane:
        raise ValueError("Lista nie może być pusta.")
    
    suma = sum(dane)  
    srednia = suma / len(dane)  
    liczba_dodatnich = len(list(filter(lambda x: x > 0, dane))) 

    return {
        'suma': suma,
        'srednia': srednia,
        'liczba_dodatnich': liczba_dodatnich
    }









@typechecked
def inputs() -> List[float]:
    """
    Funkcja poiera od uzytkownika liste liczb

    :return: Lista liczb zmiennoprzecinkowych
    """
    dane_wejscie = input("Podaj liczby oddzielone spacjami: ")
    dane = list(map(float, dane_wejscie.split())) 
    return dane
       





# main:   
try:
    while(True):
        try:
            dane = inputs()
            break
        except ValueError as ex:
            print(f"Błąd wrpowadzanych danych: {ex}]\n spróbuj ponownie")

    wyniki = process(dane)
    
    print(f"Suma: {wyniki['suma']}")
    print(f"Średnia: {wyniki['srednia']}")
    print(f"Liczba dodatnich wartości: {wyniki['liczba_dodatnich']}")

except ValueError as e:
    print(f"Błąd: {e}")
