import teksty 

text = input("Podaj tekst do analizy: ")

liczba_słów = teksty.CountWords(text)
unikalne = teksty.UniqueWords(text)

print(f"Liczba słów w tekście: {liczba_słów}")
print(f"Liczba unikalnych słów: {len(unikalne)}")
print(f"Unikalne słowa: {unikalne}")

word = input("Podaj słowo do sprawdzenia, czy występuje w tekście: ")

print(f"Tekst { "nie" if not teksty.doesContain(text, word) else "" } zawiera podanego slowa")

