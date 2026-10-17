import random


class RegistrationBureau:
    def __init__(self, allowed_voters):
        self.allowed_voters = set(allowed_voters)
        self.registered_voters = {}
        self.used_rns = set()

    def generate_unique_rn(self):
        while True:
            rn = random.randint(10**8, 10**12)
            if rn not in self.used_rns:
                self.used_rns.add(rn)
                return rn

    def register_voter(self, full_name, public_key):
        print(f"\nЗапит на реєстрацію: {full_name}")

        if full_name not in self.allowed_voters:
            print("Перевірка права на участь у голосуванні: не пройдено.")
            print("У реєстрації відмовлено.")
            return None

        print("Перевірка права на участь у голосуванні: пройдено.")

        if full_name in self.registered_voters:
            print("Перевірка повторної реєстрації: не пройдено.")
            print("Повторний RN не видається.")
            return None

        print("Перевірка повторної реєстрації: пройдено.")

        rn = self.generate_unique_rn()

        self.registered_voters[full_name] = {
            "rn": rn,
            "public_key": public_key
        }

        print(f"БР видало виборцю RN: {rn}")
        return rn

    def export_registration_data(self):
        return {
            data["rn"]: data["public_key"]
            for data in self.registered_voters.values()
        }

    def print_registered_voters(self):
        print("\nЗареєстровані виборці у БР:")
        for full_name, data in self.registered_voters.items():
            print(f"{full_name}: RN={data['rn']}")
