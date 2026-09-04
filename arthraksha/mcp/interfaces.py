from abc import ABC, abstractmethod

class MCPToolInterface(ABC):
    @abstractmethod
    def execute(self, payload: dict) -> dict:
        pass

    @abstractmethod
    def validate(self, payload: dict) -> bool:
        pass

class EmailInterface(MCPToolInterface):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> bool:
        pass

class PaymentLinkInterface(MCPToolInterface):
    @abstractmethod
    def generate(self, payment_id: str, amount: int, customer_id: str) -> str:
        pass

class RetryInterface(MCPToolInterface):
    @abstractmethod
    def trigger(self, payment_id: str, delay_hours: float) -> bool:
        pass

class AuditInterface(MCPToolInterface):
    @abstractmethod
    def log(self, entry: dict) -> bool:
        pass

class WhatsAppInterface(MCPToolInterface):
    @abstractmethod
    def send(self, phone: str, message: str) -> bool:
        pass
