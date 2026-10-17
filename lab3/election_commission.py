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


def modular_inverse(a, modulus):
    gcd, x, _ = extended_euclid(a, modulus)

    if gcd != 1:
        raise ValueError("Оберненого елемента не існує.")

    return x % modulus


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
        (
            value
            for value in (65537, 257, 17, 5, 3)
            if 1 < value < phi and math.gcd(value, phi) == 1
        ),
        None
    )

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


def quadratic_hash(message, n):
    h = 0

    for symbol in message:
        h = pow(h + ord(symbol), 2, n)

    return h


def create_signature(message, private_key):
    d, n = private_key
    h = quadratic_hash(message, n)
    return pow(h, d, n)


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
            raise ValueError(
                "Числове представлення символу повинне бути меншим за n."
            )

        encrypted.append(pow(m, e, n))

    return encrypted


def rsa_decrypt_text(encrypted, private_key):
    d, n = private_key
    return "".join(chr(pow(c, d, n)) for c in encrypted)


def canonical_vote_message(vote_id, rn, candidate):
    return f"ID={vote_id};RN={rn};Кандидат={candidate}"


class ElectionCommission:
    def __init__(self, candidates):
        self.candidates = list(candidates)
        self.keys = generate_rsa_key_pair()
        self.registered_rns = {}
        self.used_rns = set()
        self.used_ids = set()
        self.accepted_ballots = []

    @property
    def public_key(self):
        return self.keys.public_key

    def load_registration_data(self, registration_data):
        self.registered_rns = dict(registration_data)

        print("\nВК отримала від БР список RN та відкритих ключів.")
        print("Персональні дані виборців до ВК не передаються.")

    def print_initial_data(self):
        print("\nСписок кандидатів:")

        for index, candidate in enumerate(self.candidates, 1):
            print(f"{index}. {candidate}")

        print("\nВідкритий ключ ВК:")
        print(self.public_key)

    def receive_vote(self, encrypted_message):
        print("\nВК отримала зашифрований бюлетень.")

        try:
            text = rsa_decrypt_text(
                encrypted_message,
                self.keys.private_key
            )

            package = json.loads(text)

            vote_id = int(package["id"])
            rn = int(package["rn"])
            candidate = package["candidate"]
            signature = int(package["signature"])

        except (
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
            UnicodeError
        ):
            print("Розшифрування або структура повідомлення: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("Розшифрування повідомлення: успішно.")

        if rn not in self.registered_rns:
            print("Перевірка RN у списку: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("Перевірка RN у списку: пройдено.")

        if rn in self.used_rns:
            print("Перевірка повторного використання RN: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("Перевірка повторного використання RN: пройдено.")

        if candidate not in self.candidates:
            print("Перевірка кандидата: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        message = canonical_vote_message(
            vote_id,
            rn,
            candidate
        )

        public_key = self.registered_rns[rn]

        valid_signature, h, hc = verify_signature(
            message,
            signature,
            public_key
        )

        print(f"Перевірка ЕЦП: H = {h}, Hc = {hc}")

        if not valid_signature:
            print("ЕЦП виборця: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("ЕЦП виборця: пройдено.")

        if vote_id in self.used_ids:
            print("Перевірка унікальності ID: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("Перевірка унікальності ID: пройдено.")

        self.used_rns.add(rn)
        self.used_ids.add(vote_id)

        self.accepted_ballots.append({
            "id": vote_id,
            "candidate": candidate,
            "message": message,
            "signature": signature
        })

        print("RN позначено як використаний.")
        print("Бюлетень прийнято до підрахунку.")

        return True

    def get_results(self):
        results = {
            candidate: 0
            for candidate in self.candidates
        }

        for ballot in self.accepted_ballots:
            results[ballot["candidate"]] += 1

        return results

    def get_published_ballots(self):
        return [
            dict(ballot)
            for ballot in self.accepted_ballots
        ]

    def publish_results(self):
        results = self.get_results()

        print("\nКінцеві результати:")

        for candidate, votes in results.items():
            print(f"{candidate}: {votes} голос(и)")

        print("\nОпубліковані підписані бюлетені:")

        for ballot in self.accepted_ballots:
            print(
                f"ID={ballot['id']}; "
                f"кандидат={ballot['candidate']}; "
                f"ЕЦП={ballot['signature']}"
            )
