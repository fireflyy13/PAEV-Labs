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
    p = generate_prime()
    q = generate_prime()

    while q == p:
        q = generate_prime()

    n = p * q
    phi = (p - 1) * (q - 1)

    e = next(
        (value for value in (65537, 257, 17, 5, 3)
         if 1 < value < phi and math.gcd(value, phi) == 1),
        None
    )

    if e is None:
        e = 3
        while e < phi and math.gcd(e, phi) != 1:
            e += 2

    d = modular_inverse(e, phi)
    return RSAKeyPair(p, q, n, phi, e, d)

def quadratic_hash(message, n):
    h = 0
    for symbol in message:
        h = pow(h + ord(symbol), 2, n)
    return h

def create_signature(message, private_key):
    d, n = private_key
    return pow(quadratic_hash(message, n), d, n)

def verify_signature(message, signature, public_key):
    e, n = public_key
    h = quadratic_hash(message, n)
    hc = pow(signature, e, n)
    return h == hc, h, hc

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
        self.keys = generate_rsa_key_pair()

    @property
    def public_key(self):
        return self.keys.public_key

    def form_signed_ballot(self, candidate):
        ballot = f"Виборець={self.full_name};Кандидат={candidate}"
        return {
            "voter": self.full_name,
            "candidate": candidate,
            "ballot": ballot,
            "signature": create_signature(ballot, self.keys.private_key)
        }

    def encrypt_ballot(self, package, commission_public_key):
        text = json.dumps(package, ensure_ascii=False, separators=(",", ":"))
        return rsa_encrypt_text(text, commission_public_key)

    def vote(self, candidate, commission_public_key):
        return self.encrypt_ballot(
            self.form_signed_ballot(candidate),
            commission_public_key
        )

class ElectionCommission:
    def __init__(self, candidates):
        self.candidates = list(candidates)
        self.keys = generate_rsa_key_pair()
        self.voters = {}
        self.voted = set()
        self.accepted_ballots = []

    @property
    def public_key(self):
        return self.keys.public_key

    def add_voter(self, voter):
        self.voters[voter.full_name] = voter.public_key

    def print_initial_data(self):
        print("\nСписок кандидатів:")

        for index, candidate in enumerate(self.candidates, 1):
            print(f"{index}. {candidate}")

        print("\nСписок допущених виборців та їх відкриті ключі:")

        for full_name, key in self.voters.items():
            print(f"{full_name}: відкритий ключ {key}")

        print("\nВідкритий ключ виборчої комісії:")
        print(self.public_key)

    def receive_ballot(self, sender_name, encrypted_ballot):
        print("\n" + "-" * 70)
        print(f"ВК отримала бюлетень. Відправник: {sender_name}")

        try:
            decrypted_text = rsa_decrypt_text(
                encrypted_ballot,
                self.keys.private_key
            )
            package = json.loads(decrypted_text)
            print("1. Розшифрування бюлетеня: УСПІШНО.")
        except (ValueError, json.JSONDecodeError, UnicodeError):
            print("1. Розшифрування бюлетеня: НЕ ПРОЙДЕНО.")
            print("Бюлетень ВІДХИЛЕНО.")
            return False

        if sender_name not in self.voters:
            print("2. Перевірка наявності у списку виборців: НЕ ПРОЙДЕНО.")
            print("Бюлетень ВІДХИЛЕНО.")
            return False

        print("2. Перевірка наявності у списку виборців: ПРОЙДЕНО.")

        if package.get("voter") != sender_name:
            print("3. Перевірка ЕЦП: НЕ ПРОЙДЕНО.")
            print("Причина: ПІБ у бюлетені не відповідає відправнику.")
            print("Бюлетень ВІДХИЛЕНО.")
            return False

        ballot = package["ballot"]
        signature = int(package["signature"])

        signature_ok, h, hc = verify_signature(
            ballot,
            signature,
            self.voters[sender_name]
        )

        print(f"3. Перевірка ЕЦП: H = {h}, Hc = {hc}")

        if not signature_ok:
            print("   ЕЦП: НЕ ПРОЙДЕНО.")
            print("Бюлетень ВІДХИЛЕНО.")
            return False

        print("   ЕЦП: ПРОЙДЕНО.")

        expected_ballot = (
            f"Виборець={package['voter']};"
            f"Кандидат={package['candidate']}"
        )

        if ballot != expected_ballot:
            print("Вміст пакета не відповідає підписаному бюлетеню.")
            print("Бюлетень ВІДХИЛЕНО.")
            return False

        if sender_name in self.voted:
            print("4. Перевірка повторного голосування: НЕ ПРОЙДЕНО.")
            print("Бюлетень ВІДХИЛЕНО.")
            return False

        print("4. Перевірка повторного голосування: ПРОЙДЕНО.")

        self.accepted_ballots.append({
            "voter": sender_name,
            "candidate": package["candidate"]
        })
        self.voted.add(sender_name)

        print("5. Бюлетень ПРИЙНЯТО до підрахунку.")
        print("6. У списку виборців встановлено позначку: ПРОГОЛОСУВАВ.")
        return True

    def publish_results(self):
        results = {candidate: 0 for candidate in self.candidates}
        invalid_ballots = 0

        for ballot in self.accepted_ballots:
            candidate = ballot["candidate"]

            if candidate in results:
                results[candidate] += 1
            else:
                invalid_ballots += 1

        print("\nЗАГАЛЬНІ РЕЗУЛЬТАТИ ГОЛОСУВАННЯ")

        for candidate, votes in results.items():
            print(f"{candidate}: {votes} голос(и)")

        if invalid_ballots:
            print(f"Некоректні бюлетені: {invalid_ballots}")

        maximum = max(results.values())
        winners = [
            candidate
            for candidate, votes in results.items()
            if votes == maximum
        ]

        if len(winners) > 1:
            print("Результат: РІВНОМІРНИЙ РОЗПОДІЛ ГОЛОСІВ (НІЧИЯ).")
        else:
            print(f"Переможець: {winners[0]}")

def main():
    candidates = ["Кандидат 1", "Кандидат 2"]
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

    print("ПОЗИТИВНІ СЦЕНАРІЇ ПЕРЕВІРОК:")

    normal_votes = [
        (voters[0], "Кандидат 1"),
        (voters[1], "Кандидат 2"),
        (voters[2], "Кандидат 1"),
        (voters[3], "Кандидат 2")
    ]

    for voter, candidate in normal_votes:
        encrypted_ballot = voter.vote(candidate, commission.public_key)

        print(
            f"\nЗашифрований бюлетень {voter.full_name}: "
            f"{encrypted_ballot[:8]} ... "
            f"(усього блоків: {len(encrypted_ballot)})"
        )

        commission.receive_ballot(voter.full_name, encrypted_ballot)

    print("\nНЕГАТИВНІ СЦЕНАРІЇ ПЕРЕВІРОК:")
    print("\nНЕГАТИВНИЙ СЦЕНАРІЙ: ЗМІНА ПІДПИСАНОГО БЮЛЕТЕНЯ")

    fifth_voter = voters[4]
    tampered_package = fifth_voter.form_signed_ballot("Кандидат 1")
    tampered_package["candidate"] = "Кандидат 2"
    tampered_package["ballot"] = (
        f"Виборець={fifth_voter.full_name};Кандидат=Кандидат 2"
    )

    tampered_encrypted = fifth_voter.encrypt_ballot(
        tampered_package,
        commission.public_key
    )

    commission.receive_ballot(fifth_voter.full_name, tampered_encrypted)

    print("\n")
    print("НЕГАТИВНИЙ СЦЕНАРІЙ: ВИБОРЕЦЬ ВІДСУТНІЙ У СПИСКУ")

    unknown_voter = Voter("Невідомий Виборець")
    unknown_ballot = unknown_voter.vote("Кандидат 1", commission.public_key)

    commission.receive_ballot(unknown_voter.full_name, unknown_ballot)

    print("\n")
    print("НЕГАТИВНИЙ СЦЕНАРІЙ: ПОВТОРНЕ ГОЛОСУВАННЯ")

    repeated_ballot = voters[0].vote("Кандидат 2", commission.public_key)
    commission.receive_ballot(voters[0].full_name, repeated_ballot)

    commission.publish_results()

if __name__ == "__main__":
    main()