a = float(input("Podaj wartosc a: "))
b = float(input("Podaj wartosc b: "))

print(f"Suma a + b = {    a+b :.2f}")
print(f"Rownica a - b = { a-b :.2f}")
print(f"Iloczyn a * b = { a*b :.2f}")
print(f"Iloraz a / b = {  a/b :.2f}")

print(f"Liczba A jest { "mniejsza od" if a < b else "wieksza od" if a > b else "rowna"  } B")