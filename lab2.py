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


def generate_blinding_factor(n):
    while True:
        r = random.randint(2, n - 1)
        if math.gcd(r, n) == 1:
            return r


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


def make_ballot(ballot_id, candidate):
    return f"ID={ballot_id};Кандидат={candidate}"


def parse_ballot(ballot):
    id_part, candidate_part = ballot.split(";", 1)
    ballot_id = int(id_part.split("=", 1)[1])
    candidate = candidate_part.split("=", 1)[1]
    return ballot_id, candidate


class Voter:
    def __init__(self, full_name):
        self.full_name = full_name
        self.ballot_sets = []
        self.signed_set_index = None

    def prepare_ballot_sets(self, candidates, commission_public_key):
        e, n = commission_public_key
        self.ballot_sets = []
        used_ids = set()

        for _ in range(10):
            ballot_id = random.randint(10**10, 10**14)

            while ballot_id in used_ids:
                ballot_id = random.randint(10**10, 10**14)

            used_ids.add(ballot_id)
            items = []

            for candidate in candidates:
                ballot = make_ballot(ballot_id, candidate)
                h = quadratic_hash(ballot, n)
                r = generate_blinding_factor(n)
                masked_hash = (h * pow(r, e, n)) % n

                items.append({
                    "candidate": candidate,
                    "ballot": ballot,
                    "r": r,
                    "masked_hash": masked_hash
                })

            self.ballot_sets.append({
                "id": ballot_id,
                "items": items
            })

        return [
            [item["masked_hash"] for item in ballot_set["items"]]
            for ballot_set in self.ballot_sets
        ]

    def reveal_sets(self, indices):
        return {
            index: [
                {"ballot": item["ballot"], "r": item["r"]}
                for item in self.ballot_sets[index]["items"]
            ]
            for index in indices
        }

    def receive_blind_signatures(self, hidden_index, blind_signatures, commission_public_key):
        _, n = commission_public_key
        items = self.ballot_sets[hidden_index]["items"]

        for item, blind_signature in zip(items, blind_signatures):
            r_inverse = modular_inverse(item["r"], n)
            item["signature"] = (blind_signature * r_inverse) % n

        self.signed_set_index = hidden_index

    def create_vote(self, candidate, commission_public_key):
        if self.signed_set_index is None:
            raise ValueError("Виборець не має підписаного набору.")

        items = self.ballot_sets[self.signed_set_index]["items"]
        item = next(item for item in items if item["candidate"] == candidate)

        package = {
            "ballot": item["ballot"],
            "signature": item["signature"]
        }

        text = json.dumps(package, ensure_ascii=False, separators=(",", ":"))
        return rsa_encrypt_text(text, commission_public_key)

    def create_tampered_vote(self, signed_candidate, changed_candidate, commission_public_key):
        items = self.ballot_sets[self.signed_set_index]["items"]
        item = next(item for item in items if item["candidate"] == signed_candidate)
        ballot_id, _ = parse_ballot(item["ballot"])

        package = {
            "ballot": make_ballot(ballot_id, changed_candidate),
            "signature": item["signature"]
        }

        text = json.dumps(package, ensure_ascii=False, separators=(",", ":"))
        return rsa_encrypt_text(text, commission_public_key)


class ElectionCommission:
    def __init__(self, candidates, voters):
        self.candidates = list(candidates)
        self.voters = set(voters)
        self.keys = generate_rsa_key_pair()
        self.issued_voters = set()
        self.used_ids = set()
        self.accepted_ballots = []

    @property
    def public_key(self):
        return self.keys.public_key

    def print_initial_data(self):
        print("\nСписок кандидатів:")
        for index, candidate in enumerate(self.candidates, 1):
            print(f"{index}. {candidate}")

        print("\nСписок виборців:")
        for voter in sorted(self.voters):
            print(voter)

        print("\nВідкритий ключ виборчої комісії:")
        print(self.public_key)

    def choose_sets_for_check(self, voter_name, masked_sets):
        print(f"\nЗапит на підписаний набір від: {voter_name}")

        if voter_name not in self.voters:
            print("Перевірка виборця: не пройдено.")
            print("У підписанні відмовлено.")
            return None

        print("Перевірка виборця: пройдено.")

        if voter_name in self.issued_voters:
            print("Перевірка повторного отримання набору: не пройдено.")
            print("У підписанні відмовлено.")
            return None

        print("Перевірка повторного отримання набору: пройдено.")

        if len(masked_sets) != 10 or any(
            len(ballot_set) != len(self.candidates)
            for ballot_set in masked_sets
        ):
            print("Перевірка кількості наборів: не пройдено.")
            print("У підписанні відмовлено.")
            return None

        opened_indices = sorted(random.sample(range(10), 9))
        hidden_index = next(
            index for index in range(10)
            if index not in opened_indices
        )

        print(f"ВК обрала для розкриття набори: {[i + 1 for i in opened_indices]}")
        print(f"Нерозкритим залишився набір: {hidden_index + 1}")

        return opened_indices, hidden_index

    def verify_opened_sets_and_sign(
        self,
        voter_name,
        masked_sets,
        opened_indices,
        hidden_index,
        revealed_sets
    ):
        e, n = self.public_key
        d, _ = self.keys.private_key

        for index in opened_indices:
            revealed = revealed_sets.get(index)

            if revealed is None or len(revealed) != len(self.candidates):
                print(f"Набір {index + 1}: некоректний.")
                print("У підписанні відмовлено.")
                return None

            ids = []
            candidates = []

            for position, item in enumerate(revealed):
                try:
                    ballot_id, candidate = parse_ballot(item["ballot"])
                    r = item["r"]
                except (ValueError, KeyError, IndexError):
                    print(f"Набір {index + 1}: некоректний.")
                    print("У підписанні відмовлено.")
                    return None

                if not 1 < r < n or math.gcd(r, n) != 1:
                    print(f"Набір {index + 1}: некоректний множник маскування.")
                    print("У підписанні відмовлено.")
                    return None

                h = quadratic_hash(item["ballot"], n)
                expected_masked_hash = (h * pow(r, e, n)) % n

                if expected_masked_hash != masked_sets[index][position]:
                    print(f"Набір {index + 1}: замаскований хеш не відповідає бюлетеню.")
                    print("У підписанні відмовлено.")
                    return None

                ids.append(ballot_id)
                candidates.append(candidate)

            if len(set(ids)) != 1 or sorted(candidates) != sorted(self.candidates):
                print(f"Набір {index + 1}: сформовано неправильно.")
                print("У підписанні відмовлено.")
                return None

        print("Перевірка 9 розкритих наборів: пройдено.")

        blind_signatures = [
            pow(masked_hash, d, n)
            for masked_hash in masked_sets[hidden_index]
        ]

        self.issued_voters.add(voter_name)
        print("ВК підписала замасковані хеші нерозкритого набору.")

        return blind_signatures

    def receive_vote(self, encrypted_message):
        print("\nВК отримала анонімний бюлетень.")

        try:
            text = rsa_decrypt_text(
                encrypted_message,
                self.keys.private_key
            )
            package = json.loads(text)
            ballot = package["ballot"]
            signature = int(package["signature"])
            ballot_id, candidate = parse_ballot(ballot)
        except (ValueError, KeyError, json.JSONDecodeError, UnicodeError):
            print("Розшифрування або структура бюлетеня: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("Розшифрування бюлетеня: успішно.")

        if candidate not in self.candidates:
            print("Перевірка кандидата: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        e, n = self.public_key
        h = quadratic_hash(ballot, n)
        hc = pow(signature, e, n)

        print(f"Перевірка підпису ВК: H = {h}, Hc = {hc}")

        if h != hc:
            print("Підпис ВК: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("Підпис ВК: пройдено.")

        if ballot_id in self.used_ids:
            print("Перевірка унікальності ID: не пройдено.")
            print("Бюлетень відхилено.")
            return False

        print("Перевірка унікальності ID: пройдено.")

        self.used_ids.add(ballot_id)
        self.accepted_ballots.append({
            "id": ballot_id,
            "candidate": candidate,
            "ballot": ballot,
            "signature": signature
        })

        print("Бюлетень прийнято до підрахунку.")
        return True

    def publish_results(self):
        results = {candidate: 0 for candidate in self.candidates}

        for ballot in self.accepted_ballots:
            results[ballot["candidate"]] += 1

        print("\nКінцеві результати:")
        for candidate, votes in results.items():
            print(f"{candidate}: {votes} голос(и)")

        print("\nОпубліковані підписані бюлетені:")
        for ballot in self.accepted_ballots:
            print(
                f"ID={ballot['id']}; "
                f"кандидат={ballot['candidate']}; "
                f"підпис ВК={ballot['signature']}"
            )

def issue_signed_set(voter, commission):
    if voter.full_name in commission.issued_voters:
        print(f"Запит на підписаний набір від: {voter.full_name}")
        print("Перевірка виборця: пройдено.")
        print("Перевірка повторного отримання набору: не пройдено.")
        print("У підписанні відмовлено.")
        return False

    masked_sets = voter.prepare_ballot_sets(
        commission.candidates,
        commission.public_key
    )

    selection = commission.choose_sets_for_check(
        voter.full_name,
        masked_sets
    )

    if selection is None:
        return False

    opened_indices, hidden_index = selection
    revealed_sets = voter.reveal_sets(opened_indices)

    blind_signatures = commission.verify_opened_sets_and_sign(
        voter.full_name,
        masked_sets,
        opened_indices,
        hidden_index,
        revealed_sets
    )

    if blind_signatures is None:
        return False

    voter.receive_blind_signatures(
        hidden_index,
        blind_signatures,
        commission.public_key
    )

    print("Виборець зняв маскування з підписів.")
    return True

def main():
    candidates = ["Кандидат 1", "Кандидат 2"]

    voters = [
        Voter("Іваненко Іван Іванович"),
        Voter("Петренко Петро Петрович"),
        Voter("Сидоренко Анна Олегівна"),
        Voter("Коваль Марія Сергіївна"),
        Voter("Бондаренко Олег Андрійович")
    ]

    commission = ElectionCommission(
        candidates,
        [voter.full_name for voter in voters]
    )

    commission.print_initial_data()

    print("\nШтатне голосування:")

    issue_signed_set(voters[0], commission)
    commission.receive_vote(
        voters[0].create_vote("Кандидат 1", commission.public_key)
    )

    issue_signed_set(voters[1], commission)

    print("\nПеревірка неправильного підпису:")
    commission.receive_vote(
        voters[1].create_tampered_vote(
            "Кандидат 1",
            "Кандидат 2",
            commission.public_key
        )
    )

    commission.receive_vote(
        voters[1].create_vote("Кандидат 2", commission.public_key)
    )

    issue_signed_set(voters[2], commission)
    commission.receive_vote(
        voters[2].create_vote("Кандидат 1", commission.public_key)
    )

    print("\nПеревірка декількох бюлетенів з одного набору:")
    commission.receive_vote(
        voters[0].create_vote("Кандидат 2", commission.public_key)
    )

    print("\nПеревірка повторного отримання підписаного набору:")
    repeated_sets = voters[0].prepare_ballot_sets(
        candidates,
        commission.public_key
    )
    commission.choose_sets_for_check(
        voters[0].full_name,
        repeated_sets
    )

    print("\nПеревірка незареєстрованого виборця:")
    unknown_voter = Voter("Невідомий Виборець")
    unknown_sets = unknown_voter.prepare_ballot_sets(
        candidates,
        commission.public_key
    )
    commission.choose_sets_for_check(
        unknown_voter.full_name,
        unknown_sets
    )

    print("\nПеревірка некоректно сформованого розкритого набору:")
    masked_sets = voters[3].prepare_ballot_sets(
        candidates,
        commission.public_key
    )

    selection = commission.choose_sets_for_check(
        voters[3].full_name,
        masked_sets
    )

    opened_indices, hidden_index = selection
    revealed_sets = voters[3].reveal_sets(opened_indices)
    bad_index = opened_indices[0]
    ballot_id, _ = parse_ballot(revealed_sets[bad_index][0]["ballot"])

    revealed_sets[bad_index][0]["ballot"] = make_ballot(
        ballot_id,
        "Кандидат 2"
    )

    commission.verify_opened_sets_and_sign(
        voters[3].full_name,
        masked_sets,
        opened_indices,
        hidden_index,
        revealed_sets
    )

    print("\nПовторна коректна спроба четвертого виборця:")
    issue_signed_set(voters[3], commission)
    commission.receive_vote(
        voters[3].create_vote("Кандидат 2", commission.public_key)
    )

    issue_signed_set(voters[4], commission)
    commission.receive_vote(
        voters[4].create_vote("Кандидат 1", commission.public_key)
    )

    commission.publish_results()


if __name__ == "__main__":
    main()
