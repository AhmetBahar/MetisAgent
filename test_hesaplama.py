def topla(a, b):
    return a + b

def cikar(a, b):
    return a - b

def carpma(a, b):
    return a * b

def bolme(a, b):
    if b == 0:
        return "Sıfıra bölme hatası!"
    return a / b

print("Toplama: 5 + 3 =", topla(5, 3))
print("Çıkarma: 10 - 4 =", cikar(10, 4))
print("Çarpma: 6 * 7 =", carpma(6, 7))
print("Bölme: 8 / 2 =", bolme(8, 2))
print("Bölme hatası kontrolü: 5 / 0 =", bolme(5, 0))