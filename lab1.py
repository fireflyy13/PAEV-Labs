import json
import math
import random
from dataclasses import dataclass

def is_prime(number): 
    if number < 2:
        return False
    for i in range(2, number):
        if number % i == 0:
            return False
    return True

def generate_prime(left=1000, right=5000):
    while True:
        number = random.randint(left, right)
        if number % 2 == 0:
            number += 1

        while number <= right:
            if is_prime(number):
                return number
            number += 2

def extended_euclid(a, b):
    # використовуємо розширений алгоритм Евкліда, щоб 
    # знайти найбільший спільний ділник чисел a i b,
    #  а також коефіцієнтів x та y
    # a*x + b*y = НСД(a, b)
    r0, r1 = a, b
    x0, x1 = 1, 0
    y0, y1 = 0, 1

    while r1 != 0:
        q = r0 // r1
        r0, r1 = r1, r0 - q * r1
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1

    return r0, x0, y0

def modular_inverse(e, phi):
    gcd, x, _ = extended_euclid(e, phi)
    if gcd != 1:
        raise ValueError("Оберненого елемента не існує.")
    return x % phi

@dataclass
class RSAKeyPair:
    p: int
    q: int
    n: int
    phi: int
    e: int
    d: int

    @property
    def public_key(self):
        return self.e, self.n

    @property
    def private_key(self):
        return self.d, self.n

def generate_rsa_key_pair():
    p = generate_prime() # процедура генерації ключів починається
    # з того, що ми обираємо просто числа p та q (різні)
    q = generate_prime()

    while q == p:
        q = generate_prime()

    n = p * q # обраховуємо добуток цих чисел
    phi = (p - 1) * (q - 1) # обраховуємо функцію Ейлера

    e = next(
        (value for value in (65537, 257, 17, 5, 3)
         if 1 < value < phi and math.gcd(value, phi) == 1),
        None
    ) # обираємо непарне число e, взаємно просте з функцією Ейлера в діапазоні від 1 до фі

    if e is None:
        e = 3
        while e < phi and math.gcd(e, phi) != 1:
            e += 2

    d = modular_inverse(e, phi) # число d - це обернене за модулем фі до e 
    return RSAKeyPair(p, q, n, phi, e, d)

def quadratic_hash(message, n): # хешуємо повідомлення. тут ми використовуємо спрощену хеш-функцію
    # квадратичної згортки
    h = 0
    for symbol in message:
        h = pow(h + ord(symbol), 2, n)
    return h

def create_signature(message, private_key):
    d, n = private_key # закритий ключ
    return pow(quadratic_hash(message, n), d, n) # формуємо ЕЦП

def verify_signature(message, signature, public_key): # перевіряємо підпис
    e, n = public_key # відкритий ключ
    h = quadratic_hash(message, n)
    hc = pow(signature, e, n)
    return h == hc, h, hc # для перевірки порівнюємо H та Hc

def rsa_encrypt_text(text, public_key):
    e, n = public_key
    encrypted = []

    for symbol in text:
        m = ord(symbol)
        if m >= n:
            raise ValueError("Числове представлення символу повинне бути меншим за n.")
        encrypted.append(pow(m, e, n))

    return encrypted

def rsa_decrypt_text(encrypted, private_key):
    d, n = private_key
    return "".join(chr(pow(c, d, n)) for c in encrypted)

class Voter:
    def __init__(self, full_name):
        self.full_name = full_name
        self.keys = generate_rsa_key_pair() # кожен виборець самостійно генерує власну пару ключів

    @property
    def public_key(self):
        return self.keys.public_key

    def form_signed_ballot(self, candidate):  # формування виборцем бюлетеня
        ballot = f"Виборець={self.full_name};Кандидат={candidate}"
        return {
            "voter": self.full_name,
            "candidate": candidate,
            "ballot": ballot,
            "signature": create_signature(ballot, self.keys.private_key) # підписання бюлетеня
        }

    def encrypt_ballot(self, package, commission_public_key):
        text = json.dumps(package, ensure_ascii=False, separators=(",", ":")) # шифрування бюлетеня власним ключем ВК
        return rsa_encrypt_text(text, commission_public_key)

    def vote(self, candidate, commission_public_key):
        return self.encrypt_ballot(
            self.form_signed_ballot(candidate), # підписання та шифрування бюлетеня
            commission_public_key
        )

class ElectionCommission:
    def __init__(self, candidates):
        self.candidates = list(candidates)
        self.keys = generate_rsa_key_pair() # генерація пари ключів
        self.voters = {}
        self.voted = set()
        self.accepted_ballots = []

    @property
    def public_key(self):
        return self.keys.public_key

    def add_voter(self, voter):
        self.voters[voter.full_name] = voter.public_key

    def print_initial_data(self): # формування списку виборців із ПІБ та відкритим ключем
        print("\nСписок кандидатів:")

        for index, candidate in enumerate(self.candidates, 1):
            print(f"{index}. {candidate}")

        print("\nСписок допущених виборців та їх відкриті ключі:")

        for full_name, key in self.voters.items():
            print(f"{full_name}: відкритий ключ {key}")

        print("\nВідкритий ключ виборчої комісії:") # публікація відкритого ключа
        print(self.public_key)

    def receive_ballot(self, sender_name, encrypted_ballot): 
        print(f"\nВК отримала бюлетень. Відправник: {sender_name}")

        try:
            decrypted_text = rsa_decrypt_text( # розшифрування бюлетеня власним закритим ключем ВК
                encrypted_ballot,
                self.keys.private_key
            )
            package = json.loads(decrypted_text)
            print("1. Розшифрування бюлетеня: успішно.")
        except (ValueError, json.JSONDecodeError, UnicodeError):
            print("1. Розшифрування бюлетеня: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        if sender_name not in self.voters: # перевірка наявності виборців у списку
            print("2. Перевірка наявності у списку виборців: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("2. Перевірка наявності у списку виборців: пройдено.")

        if package.get("voter") != sender_name:
            print("3. Перевірка ЕЦП: не пройдено.")
            print("Причина: ПІБ у бюлетені не відповідає відправнику.")
            print("Бюлетень відхилено.")
            return False

        ballot = package["ballot"]
        signature = int(package["signature"])

        signature_ok, h, hc = verify_signature( # перевірка ЕЦП відкритим ключем виборця
            ballot,
            signature,
            self.voters[sender_name]
        )

        print(f"3. Перевірка ЕЦП: H = {h}, Hc = {hc}")

        if not signature_ok:
            print("ЕЦП: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("ЕЦП: пройдено.")

        expected_ballot = (
            f"Виборець={package['voter']};"
            f"Кандидат={package['candidate']}"
        )

        if ballot != expected_ballot:
            print("Вміст пакета не відповідає підписаному бюлетеню.")
            print("Бюлетень відхилено.")
            return False

        if sender_name in self.voted: # перевірка, чи виборец не голосував раніше
            print("4. Перевірка повторного голосування: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("4. Перевірка повторного голосування: пройдено.")

        self.accepted_ballots.append({
            "voter": sender_name,
            "candidate": package["candidate"] # прийняття виборця відповідно до перевірок 
        })
        self.voted.add(sender_name)

        print("5. Бюлетень прийнято до підрахунку.") # фіксація факту голосування виборця 
        print("6. У списку виборців встановлено позначку: проголосував.")
        return True

    def publish_results(self):
        results = {candidate: 0 for candidate in self.candidates} # підрахунок прийнятих голосів

        for ballot in self.accepted_ballots:
            candidate = ballot["candidate"]
            if candidate in results:
                results[candidate] += 1

        print("\nРЕЗУЛЬТАТИ ГОЛОСУВАННЯ:")

        for candidate, votes in results.items(): # публікація результатів голосування 
            print(f"{candidate}: {votes} голос(и)")

        maximum = max(results.values())
        winners = [
            candidate
            for candidate, votes in results.items()
            if votes == maximum
        ]

        if len(winners) > 1:
            print("Результат: нічия. Потрібне повторне голосування.")
        else:
            print(f"Переможець: {winners[0]}")

def main():
    candidates = ["Кандидат 1", "Кандидат 2"] # формування списку кандидатів
    commission = ElectionCommission(candidates)

    voters = [
        Voter("Іваненко Іван Іванович"),
        Voter("Петренко Петро Петрович"),
        Voter("Сидоренко Анна Олегівна"),
        Voter("Коваль Марія Сергіївна"),
        Voter("Бондаренко Олег Андрійович")
    ]

    for voter in voters:
        commission.add_voter(voter)

    commission.print_initial_data()

    print("\nШТАТНЕ ГОЛОСУВАННЯ:")

    normal_votes = [
        (voters[0], "Кандидат 1"),
        (voters[1], "Кандидат 2"),
        (voters[2], "Кандидат 1")
    ]

    for voter, candidate in normal_votes:
        encrypted_ballot = voter.vote(candidate, commission.public_key)
        print(
            f"\nЗашифрований бюлетень {voter.full_name}: "
            f"{encrypted_ballot[:8]} ... "
            f"(усього блоків: {len(encrypted_ballot)})"
        )
        commission.receive_ballot(voter.full_name, encrypted_ballot)

    commission.publish_results()

    print("\nТЕСТУВАННЯ:")

    print("\nПОВТОРНЕ ГОЛОСУВАННЯ:")
    repeated_ballot = voters[0].vote("Кандидат 2", commission.public_key)
    commission.receive_ballot(voters[0].full_name, repeated_ballot)

    print("\nНезареєстрований виборець:")
    unknown_voter = Voter("Невідомий Виборець")
    unknown_ballot = unknown_voter.vote("Кандидат 1", commission.public_key)
    commission.receive_ballot(unknown_voter.full_name, unknown_ballot)

    print("\nПошкоджений бюлетень:")
    fourth_voter = voters[3]
    tampered_package = fourth_voter.form_signed_ballot("Кандидат 1")
    tampered_package["candidate"] = "Кандидат 2"
    tampered_package["ballot"] = (
        f"Виборець={fourth_voter.full_name};Кандидат=Кандидат 2"
    )
    tampered_encrypted = fourth_voter.encrypt_ballot(
        tampered_package,
        commission.public_key
    )
    commission.receive_ballot(fourth_voter.full_name, tampered_encrypted)

    print("\nПеревірка на нічию:")
    fifth_ballot = voters[4].vote("Кандидат 2", commission.public_key)
    commission.receive_ballot(voters[4].full_name, fifth_ballot)

    commission.publish_results()

if __name__ == "__main__":
    main()