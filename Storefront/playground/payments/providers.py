from abc import ABC, abstractmethod

class PaymentProvider(ABC):
    @abstractmethod
    def charge(self, order):
        pass


class MockPaymentProvider(PaymentProvider):
    def charge(self, order):
        return {
            "payment_id": f"MOCK-{order.id}",
            "status": "success"
        }
