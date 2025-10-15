
import string

def CountWords(text: str) -> int:
    """
    Liczy slowa w tekscie podanym jako parametr.
    
    :param text: Tekst w ktorym beda liczone slowa 
    :return: Ilosc slow w tekscie
    """
    wordCount = text.split()
    return len(wordCount)



def UniqueWords(text: str) -> set[str]:
    """
    Zbiera unikalne slowa w tekscie podanym jako parametr.
    
    :param text: Tekst z ktorego pobierane beda unikalne slowa 
    :return: Set unikalnych slow w tekscie
    """    
    text = text.lower()
    for znak in string.punctuation:
        text = text.replace(znak, '')
    slowa = text.split()
    return set(slowa)



def doesContain(text: str, word: str) -> bool:
    """
    Sprawdza czy podany tekst zawiera podane slowo

    :param text: Tekst w ktorym bedzie szukane slowo
    :param word: Slowo ktore bedzie szukane w tekscie

    :return: Infomracja czy slowo wystepuje w tekscie
    """
    for znak in string.punctuation:
        text = text.replace(znak, '')
    return word.lower() in text.lower().split()
