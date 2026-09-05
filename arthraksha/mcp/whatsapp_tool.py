from mcp.interfaces import WhatsAppInterface

class WhatsAppTool(WhatsAppInterface):
    def validate(self, payload: dict) -> bool:
        return "phone" in payload and "message" in payload

    def execute(self, payload: dict) -> dict:
        return {"success": self.send(payload["phone"], payload["message"])}

    def send(self, phone: str, message: str) -> bool:
        print(f"\n[WHATSAPP DISPATCH]\nTo: {phone}\nMessage: {message}\n")
        return True
