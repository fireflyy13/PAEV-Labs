import json
import random

from registration_bureau import RegistrationBureau
from election_commission import (
    ElectionCommission,
    canonical_vote_message,
    create_signature,
    generate_rsa_key_pair,
    rsa_encrypt_text
)


class Voter:
    def __init__(self, full_name):
        self.full_name = full_name
        self.keys = generate_rsa_key_pair()
        self.rn = None
        self.last_vote_id = None
        self.last_candidate = None

    @property
    def public_key(self):
        return self.keys.public_key

    def register(self, bureau):
        rn = bureau.register_voter(
            self.full_name,
            self.public_key
        )

        if rn is not None:
            self.rn = rn

        return rn

    def create_vote(
        self,
        candidate,
        commission_public_key,
        forced_id=None,
        forced_rn=None,
        wrong_signature=False,
        remember=True
    ):
        rn = self.rn if forced_rn is None else forced_rn

        if rn is None:
            raise ValueError("Виборець не має RN.")

        vote_id = (
            random.randint(10**10, 10**14)
            if forced_id is None
            else forced_id
        )

        message = canonical_vote_message(
            vote_id,
            rn,
            candidate
        )

        signature = create_signature(
            message,
            self.keys.private_key
        )

        if wrong_signature:
            signature = (signature + 1) % self.keys.n

        package = {
            "id": vote_id,
            "rn": rn,
            "candidate": candidate,
            "signature": signature
        }

        text = json.dumps(
            package,
            ensure_ascii=False,
            separators=(",", ":")
        )

        if remember:
            self.last_vote_id = vote_id
            self.last_candidate = candidate

        return (
            rsa_encrypt_text(
                text,
                commission_public_key
            ),
            vote_id
        )

    def verify_published_vote(self, published_ballots):
        if self.last_vote_id is None:
            print(f"{self.full_name}: немає збереженого ID голосу.")
            return False

        ballot = next(
            (
                item
                for item in published_ballots
                if item["id"] == self.last_vote_id
            ),
            None
        )

        if ballot is None:
            print(
                f"{self.full_name}: бюлетень з ID "
                f"{self.last_vote_id} не знайдено."
            )
            return False

        if ballot["candidate"] != self.last_candidate:
            print(
                f"{self.full_name}: опублікований бюлетень "
                "не відповідає зробленому вибору."
            )
            return False

        print(
            f"{self.full_name}: голос з ID "
            f"{self.last_vote_id} враховано правильно."
        )
        return True


def main():
    candidates = [
        "Кандидат 1",
        "Кандидат 2"
    ]

    voter_names = [
        "Іваненко Іван Іванович",
        "Петренко Петро Петрович",
        "Сидоренко Анна Олегівна",
        "Коваль Марія Сергіївна",
        "Бондаренко Олег Андрійович"
    ]

    voters = [
        Voter(name)
        for name in voter_names
    ]

    bureau = RegistrationBureau(voter_names)
    commission = ElectionCommission(candidates)

    commission.print_initial_data()

    print("\nРеєстрація виборців:")

    for voter in voters:
        voter.register(bureau)

    bureau.print_registered_voters()

    commission.load_registration_data(
        bureau.export_registration_data()
    )

    print("\nШтатне голосування:")

    encrypted_vote, first_id = voters[0].create_vote(
        "Кандидат 1",
        commission.public_key
    )
    commission.receive_vote(encrypted_vote)

    encrypted_vote, _ = voters[1].create_vote(
        "Кандидат 2",
        commission.public_key
    )
    commission.receive_vote(encrypted_vote)

    print("\nПеревірка повторного отримання RN:")
    voters[0].register(bureau)

    print("\nПеревірка невалідного RN:")

    encrypted_vote, _ = voters[2].create_vote(
        "Кандидат 1",
        commission.public_key,
        forced_rn=999999999999,
        remember=False
    )
    commission.receive_vote(encrypted_vote)

    print("\nПеревірка вже використаного RN:")

    encrypted_vote, _ = voters[0].create_vote(
        "Кандидат 2",
        commission.public_key,
        remember=False
    )
    commission.receive_vote(encrypted_vote)

    print("\nПеревірка повторного ID:")

    encrypted_vote, _ = voters[2].create_vote(
        "Кандидат 1",
        commission.public_key,
        forced_id=first_id,
        remember=False
    )
    commission.receive_vote(encrypted_vote)

    print("\nПеревірка неправильного ЕЦП:")

    encrypted_vote, _ = voters[2].create_vote(
        "Кандидат 1",
        commission.public_key,
        wrong_signature=True,
        remember=False
    )
    commission.receive_vote(encrypted_vote)

    print("\nКоректне голосування третього виборця:")

    encrypted_vote, _ = voters[2].create_vote(
        "Кандидат 1",
        commission.public_key
    )
    commission.receive_vote(encrypted_vote)

    print("\nКоректне голосування четвертого виборця:")

    encrypted_vote, _ = voters[3].create_vote(
        "Кандидат 2",
        commission.public_key
    )
    commission.receive_vote(encrypted_vote)

    print("\nКоректне голосування п'ятого виборця:")

    encrypted_vote, _ = voters[4].create_vote(
        "Кандидат 1",
        commission.public_key
    )
    commission.receive_vote(encrypted_vote)

    commission.publish_results()

    print("\nПеревірка виборцями власних голосів:")

    published_ballots = commission.get_published_ballots()

    for voter in voters:
        voter.verify_published_vote(
            published_ballots
        )

    print("\nПеревірка виявлення невідповідності:")

    fake_publication = [
        dict(ballot)
        for ballot in published_ballots
    ]

    for ballot in fake_publication:
        if ballot["id"] == voters[0].last_vote_id:
            ballot["candidate"] = "Кандидат 2"
            break

    voters[0].verify_published_vote(
        fake_publication
    )


if __name__ == "__main__":
    main()
