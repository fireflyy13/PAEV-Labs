from central_election_commission import (
    signature_message,
    verify_signature
)


class ElectionCommission2:
    def __init__(self):
        self.voters = {}
        self.received_voters = set()
        self.used_ids = set()
        self.accepted_messages = []

    def load_voter_registry(self, voter_registry):
        self.voters = dict(voter_registry)
        print("ВК-2 отримала від ЦВК список виборців та відкритих ключів.")

    def receive_message(
        self,
        full_name,
        voter_id,
        encrypted_part,
        signature
    ):
        print(f"\nВК-2 отримала повідомлення від: {full_name}")

        if full_name not in self.voters:
            print("Перевірка виборця у списку: не пройдено.")
            print("Повідомлення відхилено.")
            return False

        print("Перевірка виборця у списку: пройдено.")

        if full_name in self.received_voters:
            print("Перевірка повторного надсилання: не пройдено.")
            print("Повідомлення відхилено.")
            return False

        message = signature_message(
            voter_id,
            encrypted_part
        )

        valid, h, hc = verify_signature(
            message,
            signature,
            self.voters[full_name]
        )

        print(f"Перевірка ЕЦП: H = {h}, Hc = {hc}")

        if not valid:
            print("ЕЦП виборця: не пройдено.")
            print("Повідомлення відхилено.")
            return False

        print("ЕЦП виборця: пройдено.")

        if voter_id in self.used_ids:
            print("Перевірка унікальності ID: не пройдено.")
            print("Повідомлення відхилено.")
            return False

        print("Перевірка унікальності ID: пройдено.")

        self.received_voters.add(full_name)
        self.used_ids.add(voter_id)

        self.accepted_messages.append({
            "id": voter_id,
            "encrypted_part": encrypted_part
        })

        print("Зашифровану частину бюлетеня збережено.")
        return True

    def publish_data(self):
        return [
            dict(item)
            for item in self.accepted_messages
        ]

    def replace_published_part(self, voter_id, new_encrypted_part):
        for item in self.accepted_messages:
            if item["id"] == voter_id:
                item["encrypted_part"] = new_encrypted_part
                return True

        return False
