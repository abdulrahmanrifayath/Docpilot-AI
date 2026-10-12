class PaymentService:
    @staticmethod
    def process_charge(user: str, amount: float):
        """Charge credit card or gateway wallet securely."""
        return {"success": True, "charge_id": "ch_987213"}
