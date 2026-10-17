import random

from central_election_commission import (
    CentralElectionCommission,
    create_signature,
    generate_rsa_key_pair,
    rsa_encrypt_number,
    signature_message
)
from election_commission_1 import ElectionCommission1
from election_commission_2 import ElectionCommission2


class Voter:
    def __init__(self, full_name):
        self.full_name = full_name
        self.keys = generate_rsa_key_pair()
        self.last_vote = None

    @property
    def public_key(self):
        return self.keys.public_key

    def split_candidate_id(self, candidate_id):
        factor_pairs = []

        for factor_1 in range(2, candidate_id):
            if candidate_id % factor_1 == 0:
                factor_2 = candidate_id // factor_1

                if factor_2 > 1:
                    factor_pairs.append(
                        (factor_1, factor_2)
                    )

        if not factor_pairs:
            raise ValueError(
                "ID кандидата не має придатних нетривіальних множників."
            )

        return random.choice(factor_pairs)

    def create_vote_messages(
        self,
        candidate,
        candidate_ids,
        central_public_key,
        forced_id=None,
        wrong_signature_for=None
    ):
        if candidate not in candidate_ids:
            raise ValueError("Невідомий кандидат.")

        candidate_id = candidate_ids[candidate]

        factor_1, factor_2 = self.split_candidate_id(
            candidate_id
        )

        voter_id = (
            random.randint(10**10, 10**14)
            if forced_id is None
            else forced_id
        )

        encrypted_part_1 = rsa_encrypt_number(
            factor_1,
            central_public_key
        )

        encrypted_part_2 = rsa_encrypt_number(
            factor_2,
            central_public_key
        )

        message_1 = signature_message(
            voter_id,
            encrypted_part_1
        )

        message_2 = signature_message(
            voter_id,
            encrypted_part_2
        )

        signature_1 = create_signature(
            message_1,
            self.keys.private_key
        )

        signature_2 = create_signature(
            message_2,
            self.keys.private_key
        )

        if wrong_signature_for == 1:
            signature_1 = (
                signature_1 + 1
            ) % self.keys.n

        if wrong_signature_for == 2:
            signature_2 = (
                signature_2 + 1
            ) % self.keys.n

        self.last_vote = {
            "id": voter_id,
            "candidate": candidate,
            "candidate_id": candidate_id,
            "factor_1": factor_1,
            "factor_2": factor_2,
            "encrypted_part_1": encrypted_part_1,
            "encrypted_part_2": encrypted_part_2
        }

        return (
            {
                "full_name": self.full_name,
                "id": voter_id,
                "encrypted_part": encrypted_part_1,
                "signature": signature_1
            },
            {
                "full_name": self.full_name,
                "id": voter_id,
                "encrypted_part": encrypted_part_2,
                "signature": signature_2
            }
        )

    def verify_commission_publications(
        self,
        publication_1,
        publication_2
    ):
        if self.last_vote is None:
            print(f"{self.full_name}: немає збереженого голосу.")
            return False

        voter_id = self.last_vote["id"]

        item_1 = next(
            (
                item
                for item in publication_1
                if item["id"] == voter_id
            ),
            None
        )

        item_2 = next(
            (
                item
                for item in publication_2
                if item["id"] == voter_id
            ),
            None
        )

        if item_1 is None or item_2 is None:
            print(
                f"{self.full_name}: одна з ВК не опублікувала "
                "частину бюлетеня."
            )
            return False

        correct_1 = (
            item_1["encrypted_part"]
            == self.last_vote["encrypted_part_1"]
        )

        correct_2 = (
            item_2["encrypted_part"]
            == self.last_vote["encrypted_part_2"]
        )

        if not correct_1:
            print(
                f"{self.full_name}: ВК-1 опублікувала "
                "не ту зашифровану частину."
            )
            return False

        if not correct_2:
            print(
                f"{self.full_name}: ВК-2 опублікувала "
                "не ту зашифровану частину."
            )
            return False

        print(
            f"{self.full_name}: обидві ВК опублікували "
            "правильні зашифровані частини."
        )
        return True

    def verify_central_publication(
        self,
        published_ballots
    ):
        if self.last_vote is None:
            print(f"{self.full_name}: немає збереженого голосу.")
            return False

        voter_id = self.last_vote["id"]

        ballot = next(
            (
                item
                for item in published_ballots
                if item["id"] == voter_id
            ),
            None
        )

        if ballot is None:
            print(
                f"{self.full_name}: відновлений бюлетень "
                "не знайдено серед результатів."
            )
            return False

        if ballot["candidate_id"] != self.last_vote["candidate_id"]:
            print(
                f"{self.full_name}: ЦВК опублікувала "
                "неправильно відновлений бюлетень."
            )
            return False

        print(
            f"{self.full_name}: ЦВК правильно відновила "
            f"голос за {self.last_vote['candidate']}."
        )
        return True


def send_vote(voter, candidate, central, commission_1, commission_2):
    message_1, message_2 = voter.create_vote_messages(
        candidate,
        central.candidate_ids,
        central.public_key
    )

    accepted_1 = commission_1.receive_message(
        message_1["full_name"],
        message_1["id"],
        message_1["encrypted_part"],
        message_1["signature"]
    )

    accepted_2 = commission_2.receive_message(
        message_2["full_name"],
        message_2["id"],
        message_2["encrypted_part"],
        message_2["signature"]
    )

    return accepted_1 and accepted_2


def main():
    candidates = [
        "Кандидат 1",
        "Кандидат 2"
    ]

    voters = [
        Voter("Іваненко Іван Іванович"),
        Voter("Петренко Петро Петрович"),
        Voter("Сидоренко Анна Олегівна"),
        Voter("Коваль Марія Сергіївна"),
        Voter("Бондаренко Олег Андрійович")
    ]

    central = CentralElectionCommission(
        candidates
    )

    commission_1 = ElectionCommission1()
    commission_2 = ElectionCommission2()

    for voter in voters:
        central.register_voter(
            voter.full_name,
            voter.public_key
        )

    central.print_initial_data()

    registry = central.export_voter_registry()

    commission_1.load_voter_registry(
        registry
    )

    commission_2.load_voter_registry(
        registry
    )

    print("\nШтатне голосування:")

    send_vote(
        voters[0],
        "Кандидат 1",
        central,
        commission_1,
        commission_2
    )

    send_vote(
        voters[1],
        "Кандидат 2",
        central,
        commission_1,
        commission_2
    )

    send_vote(
        voters[2],
        "Кандидат 1",
        central,
        commission_1,
        commission_2
    )

    send_vote(
        voters[3],
        "Кандидат 2",
        central,
        commission_1,
        commission_2
    )

    send_vote(
        voters[4],
        "Кандидат 1",
        central,
        commission_1,
        commission_2
    )

    publication_1 = commission_1.publish_data()
    publication_2 = commission_2.publish_data()

    print("\nПеревірка правильного об'єднання частин:")

    central.process_publications(
        publication_1,
        publication_2
    )

    central.publish_results()

    print("\nПеревірка виборцями публікацій ВК-1 та ВК-2:")

    for voter in voters:
        voter.verify_commission_publications(
            publication_1,
            publication_2
        )

    print("\nПеревірка виборцями відновлених бюлетенів ЦВК:")

    published_ballots = central.get_published_ballots()

    for voter in voters:
        voter.verify_central_publication(
            published_ballots
        )

    print("\nПеревірка незареєстрованого виборця:")

    unknown = Voter("Невідомий Виборець")

    message_1, _ = unknown.create_vote_messages(
        "Кандидат 1",
        central.candidate_ids,
        central.public_key
    )

    commission_1.receive_message(
        message_1["full_name"],
        message_1["id"],
        message_1["encrypted_part"],
        message_1["signature"]
    )

    print("\nПеревірка неправильного ЕЦП:")

    test_voter = Voter("Тестовий Виборець")
    central.register_voter(
        test_voter.full_name,
        test_voter.public_key
    )

    updated_registry = central.export_voter_registry()

    test_commission_1 = ElectionCommission1()
    test_commission_1.load_voter_registry(
        updated_registry
    )

    bad_message, _ = test_voter.create_vote_messages(
        "Кандидат 1",
        central.candidate_ids,
        central.public_key,
        wrong_signature_for=1
    )

    test_commission_1.receive_message(
        bad_message["full_name"],
        bad_message["id"],
        bad_message["encrypted_part"],
        bad_message["signature"]
    )

    print("\nПеревірка зміни однієї частини бюлетеня:")

    tampered_publication_1 = [
        dict(item)
        for item in publication_1
    ]

    target_id = voters[0].last_vote["id"]

    for item in tampered_publication_1:
        if item["id"] == target_id:
            item["encrypted_part"] = rsa_encrypt_number(
                7,
                central.public_key
            )
            break

    central.process_publications(
        tampered_publication_1,
        publication_2
    )

    voters[0].verify_commission_publications(
        tampered_publication_1,
        publication_2
    )

    print("\nПовторне відновлення коректних результатів:")

    central.process_publications(
        publication_1,
        publication_2
    )

    central.publish_results()


if __name__ == "__main__":
    main()
