import json
import math
import random
from dataclasses import dataclass

# допоміжні функції для RSA

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
    """
    Розширений алгоритм Евкліда.

    Повертає gcd, x, y, для яких:
    a*x + b*y = gcd(a, b)
    """
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
    """
    Знаходження числа d, оберненого до e
    за модулем phi.
    """
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
    """
    Генерація ключів RSA:

    1. Вибираються прості p та q.
    2. n = p * q.
    3. phi(n) = (p - 1)(q - 1).
    4. Вибирається непарне e,
       взаємно просте з phi(n).
    5. d = e^(-1) mod phi(n).
    """
    p = generate_prime()
    q = generate_prime()

    while q == p:
        q = generate_prime()

    n = p * q
    phi = (p - 1) * (q - 1)

    preferred_e = [65537, 257, 17, 5, 3]
    e = None

    for value in preferred_e:
        if 1 < value < phi and math.gcd(value, phi) == 1:
            e = value
            break

    if e is None:
        e = 3

        while e < phi and math.gcd(e, phi) != 1:
            e += 2

    d = modular_inverse(e, phi)

    return RSAKeyPair(
        p=p,
        q=q,
        n=n,
        phi=phi,
        e=e,
        d=d
    )


# ============================================================
# 2. Хешування, ЕЦП, шифрування і розшифрування
# ============================================================

def quadratic_hash(message, n):
    """
    Спрощена хеш-функція квадратичної згортки
    з методичних вказівок:

    H0 = 0
    Hi = (Hi-1 + Mi)^2 mod n

    Mi — числове представлення символу.
    """
    h = 0

    for symbol in message:
        m = ord(symbol)
        h = pow(h + m, 2, n)

    return h


def create_signature(message, private_key):
    """
    Формування ЕЦП:

    ЕЦП = H^d mod n
    """
    d, n = private_key

    h = quadratic_hash(message, n)
    signature = pow(h, d, n)

    return signature


def verify_signature(message, signature, public_key):
    """
    Перевірка ЕЦП.

    Обчислюємо:
    H  — хеш отриманого повідомлення;
    Hc = ЕЦП^e mod n.

    Якщо H == Hc, підпис правильний.
    """
    e, n = public_key

    h = quadratic_hash(message, n)
    hc = pow(signature, e, n)

    return h == hc, h, hc


def rsa_encrypt_text(text, public_key):
    """
    Шифрування RSA:

    c = m^e mod n

    Повідомлення шифрується посимвольно.
    """
    e, n = public_key

    encrypted = []

    for symbol in text:
        m = ord(symbol)

        if m >= n:
            raise ValueError(
                "Числове представлення символу повинно бути меншим за n."
            )

        c = pow(m, e, n)

        encrypted.append(c)

    return encrypted


def rsa_decrypt_text(encrypted, private_key):
    """
    Розшифрування RSA:

    m = c^d mod n
    """
    d, n = private_key

    symbols = []

    for c in encrypted:
        m = pow(c, d, n)

        symbols.append(chr(m))

    return "".join(symbols)


# ============================================================
# 3. Виборець
# ============================================================

class Voter:
    def __init__(self, full_name):
        self.full_name = full_name

        # Кожен виборець самостійно генерує
        # власну пару ключів RSA для ЕЦП.
        self.keys = generate_rsa_key_pair()

    @property
    def public_key(self):
        return self.keys.public_key

    def form_signed_ballot(self, candidate):
        """
        1. Виборець формує бюлетень.
        2. Бюлетень хешується.
        3. Хеш підписується закритим ключем виборця.
        """
        ballot = (
            f"Виборець={self.full_name};"
            f"Кандидат={candidate}"
        )

        signature = create_signature(
            ballot,
            self.keys.private_key
        )

        package = {
            "voter": self.full_name,
            "candidate": candidate,
            "ballot": ballot,
            "signature": signature
        }

        return package

    def encrypt_ballot(self, package, commission_public_key):
        """
        Підписаний бюлетень шифрується
        відкритим ключем ВК.
        """
        package_text = json.dumps(
            package,
            ensure_ascii=False,
            separators=(",", ":")
        )

        encrypted = rsa_encrypt_text(
            package_text,
            commission_public_key
        )

        return encrypted

    def vote(self, candidate, commission_public_key):
        package = self.form_signed_ballot(candidate)

        return self.encrypt_ballot(
            package,
            commission_public_key
        )


# ============================================================
# 4. Виборча комісія
# ============================================================

class ElectionCommission:
    def __init__(self, candidates):

        # ВК формує список кандидатів.
        self.candidates = list(candidates)

        # ВК формує власну пару ключів RSA
        # для шифрування бюлетенів.
        self.keys = generate_rsa_key_pair()

        # ПІБ виборця -> його відкритий ключ.
        self.voters = {}

        # Множина виборців, які вже проголосували.
        self.voted = set()

        # Прийняті бюлетені.
        self.accepted_ballots = []

    @property
    def public_key(self):
        return self.keys.public_key

    def add_voter(self, voter):
        """
        ВК додає виборця до списку разом
        з його відкритим ключем ЕЦП.
        """
        self.voters[voter.full_name] = voter.public_key

    def print_initial_data(self):
        print("=" * 70)
        print("СПИСОК КАНДИДАТІВ")
        print("=" * 70)

        for index, candidate in enumerate(
            self.candidates,
            start=1
        ):
            print(f"{index}. {candidate}")

        print("\n" + "=" * 70)
        print(
            "СПИСОК ДОПУЩЕНИХ ВИБОРЦІВ "
            "ТА ЇХ ВІДКРИТІ КЛЮЧІ"
        )
        print("=" * 70)

        for full_name, key in self.voters.items():
            print(
                f"{full_name}: "
                f"відкритий ключ {key}"
            )

        print("\n" + "=" * 70)
        print("ВІДКРИТИЙ КЛЮЧ ВИБОРЧОЇ КОМІСІЇ")
        print("=" * 70)

        print(self.public_key)

    def receive_ballot(
        self,
        sender_name,
        encrypted_ballot
    ):
        """
        Обробка бюлетеня ВК:

        1. Розшифрування.
        2. Перевірка наявності виборця у списку.
        3. Перевірка ЕЦП.
        4. Перевірка повторного голосування.
        5. Прийняття або відхилення.
        6. Фіксація факту голосування.
        """

        print("\n" + "-" * 70)

        print(
            f"ВК отримала бюлетень. "
            f"Відправник: {sender_name}"
        )

        # ----------------------------------------------------
        # 1. Розшифрування бюлетеня
        # ----------------------------------------------------

        try:
            decrypted_text = rsa_decrypt_text(
                encrypted_ballot,
                self.keys.private_key
            )

            package = json.loads(decrypted_text)

            print(
                "1. Розшифрування бюлетеня: "
                "УСПІШНО."
            )

        except (
            ValueError,
            json.JSONDecodeError,
            UnicodeError
        ):
            print(
                "1. Розшифрування бюлетеня: "
                "НЕ ПРОЙДЕНО."
            )

            print("Бюлетень ВІДХИЛЕНО.")

            return False

        # ----------------------------------------------------
        # 2. Перевірка наявності виборця у списку
        # ----------------------------------------------------

        if sender_name not in self.voters:

            print(
                "2. Перевірка наявності "
                "у списку виборців: НЕ ПРОЙДЕНО."
            )

            print("Бюлетень ВІДХИЛЕНО.")

            return False

        print(
            "2. Перевірка наявності "
            "у списку виборців: ПРОЙДЕНО."
        )

        # ПІБ усередині бюлетеня також повинен
        # відповідати відправнику.

        if package.get("voter") != sender_name:

            print("3. Перевірка ЕЦП: НЕ ПРОЙДЕНО.")

            print(
                "Причина: ПІБ у бюлетені "
                "не відповідає відправнику."
            )

            print("Бюлетень ВІДХИЛЕНО.")

            return False

        # ----------------------------------------------------
        # 3. Перевірка ЕЦП
        # ----------------------------------------------------

        ballot = package["ballot"]
        signature = int(package["signature"])

        signature_ok, h, hc = verify_signature(
            ballot,
            signature,
            self.voters[sender_name]
        )

        print(
            f"3. Перевірка ЕЦП: "
            f"H = {h}, Hc = {hc}"
        )

        if not signature_ok:

            print("   ЕЦП: НЕ ПРОЙДЕНО.")

            print("Бюлетень ВІДХИЛЕНО.")

            return False

        print("   ЕЦП: ПРОЙДЕНО.")

        # Перевіряємо відповідність окремих
        # полів підписаному бюлетеню.

        expected_ballot = (
            f"Виборець={package['voter']};"
            f"Кандидат={package['candidate']}"
        )

        if ballot != expected_ballot:

            print(
                "   Вміст пакета не відповідає "
                "підписаному бюлетеню."
            )

            print("Бюлетень ВІДХИЛЕНО.")

            return False

        # ----------------------------------------------------
        # 4. Перевірка повторного голосування
        # ----------------------------------------------------

        if sender_name in self.voted:

            print(
                "4. Перевірка повторного "
                "голосування: НЕ ПРОЙДЕНО."
            )

            print("Бюлетень ВІДХИЛЕНО.")

            return False

        print(
            "4. Перевірка повторного "
            "голосування: ПРОЙДЕНО."
        )

        # ----------------------------------------------------
        # 5. Прийняття бюлетеня
        # ----------------------------------------------------

        self.accepted_ballots.append(
            {
                "voter": sender_name,
                "candidate": package["candidate"]
            }
        )

        # ----------------------------------------------------
        # 6. Фіксація факту голосування
        # ----------------------------------------------------

        self.voted.add(sender_name)

        print(
            "5. Бюлетень ПРИЙНЯТО "
            "до підрахунку."
        )

        print(
            "6. У списку виборців встановлено "
            "позначку: ПРОГОЛОСУВАВ."
        )

        return True

    def publish_results(self):
        """
        Підрахунок прийнятих голосів
        та публікація результатів.
        """

        results = {
            candidate: 0
            for candidate in self.candidates
        }

        invalid_ballots = 0

        for ballot in self.accepted_ballots:

            candidate = ballot["candidate"]

            if candidate in results:
                results[candidate] += 1

            else:
                invalid_ballots += 1

        print("\n" + "=" * 70)
        print("ЗАГАЛЬНІ РЕЗУЛЬТАТИ ГОЛОСУВАННЯ")
        print("=" * 70)

        for candidate, votes in results.items():

            print(
                f"{candidate}: "
                f"{votes} голос(и)"
            )

        if invalid_ballots > 0:

            print(
                f"Некоректні бюлетені: "
                f"{invalid_ballots}"
            )

        maximum = max(results.values())

        winners = [
            candidate
            for candidate, votes in results.items()
            if votes == maximum
        ]

        # Урахування рівномірного розподілу голосів.

        if len(winners) > 1:

            print(
                "Результат: РІВНОМІРНИЙ "
                "РОЗПОДІЛ ГОЛОСІВ (НІЧИЯ)."
            )

        else:

            print(
                f"Переможець: {winners[0]}"
            )


# ============================================================
# 5. Демонстрація протоколу
# ============================================================

def main():

    # За умовою лабораторної — 2 кандидати.

    candidates = [
        "Кандидат 1",
        "Кандидат 2"
    ]

    commission = ElectionCommission(candidates)

    # За умовою лабораторної — 5 виборців.

    voters = [
        Voter("Іваненко Іван Іванович"),
        Voter("Петренко Петро Петрович"),
        Voter("Сидоренко Анна Олегівна"),
        Voter("Коваль Марія Сергіївна"),
        Voter("Бондаренко Олег Андрійович")
    ]

    # ВК формує список виборців:
    # ПІБ + відкритий ключ ЕЦП.

    for voter in voters:
        commission.add_voter(voter)

    # Виведення списків та відкритого ключа ВК.

    commission.print_initial_data()

    # ========================================================
    # ПОЗИТИВНІ СЦЕНАРІЇ
    # ========================================================

    print("\n\n" + "#" * 70)
    print("ПОЗИТИВНІ СЦЕНАРІЇ ПЕРЕВІРОК")
    print("#" * 70)

    normal_votes = [
        (voters[0], "Кандидат 1"),
        (voters[1], "Кандидат 2"),
        (voters[2], "Кандидат 1"),
        (voters[3], "Кандидат 2")
    ]

    for voter, candidate in normal_votes:

        encrypted_ballot = voter.vote(
            candidate,
            commission.public_key
        )

        print(
            f"\nЗашифрований бюлетень "
            f"{voter.full_name}: "
            f"{encrypted_ballot[:8]} ... "
            f"(усього блоків: "
            f"{len(encrypted_ballot)})"
        )

        commission.receive_ballot(
            voter.full_name,
            encrypted_ballot
        )

    # ========================================================
    # НЕГАТИВНИЙ СЦЕНАРІЙ №1
    # ЗМІНА ПІДПИСАНОГО БЮЛЕТЕНЯ
    # ========================================================

    print("\n\n" + "#" * 70)

    print(
        "НЕГАТИВНИЙ СЦЕНАРІЙ: "
        "ЗМІНА ПІДПИСАНОГО БЮЛЕТЕНЯ"
    )

    print("#" * 70)

    fifth_voter = voters[4]

    # Спочатку виборець правильно підписує голос
    # за Кандидата 1.

    tampered_package = (
        fifth_voter.form_signed_ballot(
            "Кандидат 1"
        )
    )

    # Після формування ЕЦП змінюємо голос
    # на Кандидата 2, але старий підпис залишаємо.

    tampered_package["candidate"] = "Кандидат 2"

    tampered_package["ballot"] = (
        f"Виборець={fifth_voter.full_name};"
        f"Кандидат=Кандидат 2"
    )

    tampered_encrypted = (
        fifth_voter.encrypt_ballot(
            tampered_package,
            commission.public_key
        )
    )

    commission.receive_ballot(
        fifth_voter.full_name,
        tampered_encrypted
    )

    # ========================================================
    # НЕГАТИВНИЙ СЦЕНАРІЙ №2
    # ВИБОРЕЦЬ ВІДСУТНІЙ У СПИСКУ
    # ========================================================

    print("\n\n" + "#" * 70)

    print(
        "НЕГАТИВНИЙ СЦЕНАРІЙ: "
        "ВИБОРЕЦЬ ВІДСУТНІЙ У СПИСКУ"
    )

    print("#" * 70)

    unknown_voter = Voter(
        "Невідомий Виборець"
    )

    unknown_ballot = unknown_voter.vote(
        "Кандидат 1",
        commission.public_key
    )

    commission.receive_ballot(
        unknown_voter.full_name,
        unknown_ballot
    )

    # ========================================================
    # НЕГАТИВНИЙ СЦЕНАРІЙ №3
    # ПОВТОРНЕ ГОЛОСУВАННЯ
    # ========================================================

    print("\n\n" + "#" * 70)

    print(
        "НЕГАТИВНИЙ СЦЕНАРІЙ: "
        "ПОВТОРНЕ ГОЛОСУВАННЯ"
    )

    print("#" * 70)

    repeated_ballot = voters[0].vote(
        "Кандидат 2",
        commission.public_key
    )

    commission.receive_ballot(
        voters[0].full_name,
        repeated_ballot
    )

    # ========================================================
    # ПІДРАХУНОК
    # ========================================================

    commission.publish_results()


if __name__ == "__main__":
    main()