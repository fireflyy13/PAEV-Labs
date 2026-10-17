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


def rsa_encrypt_number(number, public_key):
    e, n = public_key

    if number < 0 or number >= n:
        raise ValueError("Число для RSA повинне бути в межах від 0 до n - 1.")

    return pow(number, e, n)


def rsa_decrypt_number(ciphertext, private_key):
    d, n = private_key
    return pow(ciphertext, d, n)


def signature_message(voter_id, encrypted_part):
    return f"ID={voter_id};EncryptedPart={encrypted_part}"


class CentralElectionCommission:
    def __init__(self, candidates):
        self.candidates = list(candidates)

        if len(self.candidates) != 2:
            raise ValueError("У лабораторній роботі передбачено 2 кандидати.")

        self.candidate_ids = {
            self.candidates[0]: 12,
            self.candidates[1]: 24
        }

        self.id_to_candidate = {
            candidate_id: candidate
            for candidate, candidate_id in self.candidate_ids.items()
        }

        self.voters = {}
        self.keys = generate_rsa_key_pair()
        self.accepted_ballots = []
        self.rejected_ballots = []

    @property
    def public_key(self):
        return self.keys.public_key

    def register_voter(self, full_name, public_key):
        self.voters[full_name] = public_key

    def export_voter_registry(self):
        return dict(self.voters)

    def print_initial_data(self):
        print("\nСписок кандидатів та їх ID:")

        for candidate in self.candidates:
            print(f"{candidate}: ID={self.candidate_ids[candidate]}")

        print("\nЗареєстровані виборці:")

        for full_name in self.voters:
            print(full_name)

        print("\nВідкритий ключ ЦВК:")
        print(self.public_key)

    def combine_encrypted_parts(self, encrypted_part_1, encrypted_part_2):
        _, n = self.public_key
        return (encrypted_part_1 * encrypted_part_2) % n

    def process_publications(self, publication_1, publication_2):
        self.accepted_ballots = []
        self.rejected_ballots = []

        data_1 = {
            item["id"]: item["encrypted_part"]
            for item in publication_1
        }

        data_2 = {
            item["id"]: item["encrypted_part"]
            for item in publication_2
        }

        all_ids = sorted(
            set(data_1.keys()) | set(data_2.keys())
        )

        print("\nЦВК об'єднує опубліковані частини бюлетенів.")

        for voter_id in all_ids:
            if voter_id not in data_1 or voter_id not in data_2:
                print(
                    f"ID={voter_id}: відсутня одна з частин бюлетеня. "
                    "Бюлетень відхилено."
                )

                self.rejected_ballots.append({
                    "id": voter_id,
                    "reason": "Відсутня одна з частин."
                })
                continue

            combined_ciphertext = self.combine_encrypted_parts(
                data_1[voter_id],
                data_2[voter_id]
            )

            restored_candidate_id = rsa_decrypt_number(
                combined_ciphertext,
                self.keys.private_key
            )

            print(
                f"ID={voter_id}: після об'єднання та розшифрування "
                f"отримано ID кандидата {restored_candidate_id}."
            )

            if restored_candidate_id not in self.id_to_candidate:
                print("Отримане значення не належить жодному кандидату.")
                print("Бюлетень відхилено.")

                self.rejected_ballots.append({
                    "id": voter_id,
                    "restored_candidate_id": restored_candidate_id,
                    "reason": "Некоректний ID кандидата."
                })
                continue

            candidate = self.id_to_candidate[restored_candidate_id]

            self.accepted_ballots.append({
                "id": voter_id,
                "candidate_id": restored_candidate_id,
                "candidate": candidate
            })

            print(f"Бюлетень прийнято: {candidate}.")

        return list(self.accepted_ballots)

    def get_results(self):
        results = {
            candidate: 0
            for candidate in self.candidates
        }

        for ballot in self.accepted_ballots:
            results[ballot["candidate"]] += 1

        return results

    def publish_results(self):
        results = self.get_results()

        print("\nКінцеві результати:")

        for candidate, votes in results.items():
            print(f"{candidate}: {votes} голос(и)")

        print("\nОпубліковані відновлені бюлетені:")

        for ballot in self.accepted_ballots:
            print(
                f"ID={ballot['id']}; "
                f"ID кандидата={ballot['candidate_id']}; "
                f"кандидат={ballot['candidate']}"
            )

        if self.rejected_ballots:
            print("\nВідхилені бюлетені:")

            for ballot in self.rejected_ballots:
                print(
                    f"ID={ballot['id']}; "
                    f"причина={ballot['reason']}"
                )

    def get_published_ballots(self):
        return [
            dict(ballot)
            for ballot in self.accepted_ballots
        ]
