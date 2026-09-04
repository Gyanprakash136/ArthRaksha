from mcp.interfaces import RetryInterface
import asyncio

class RetryTool(RetryInterface):
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        
    def validate(self, payload: dict) -> bool:
        return "payment_id" in payload and "delay_hours" in payload

    def execute(self, payload: dict) -> dict:
        scheduled = self.trigger(payload["payment_id"], payload["delay_hours"])
        return {"success": True, "scheduled": scheduled}

    def trigger(self, payment_id: str, delay_hours: float) -> bool:
        # Instead of RabbitMQ/Kafka, use asyncio.Queue for demo
        try:
            self.queue.put_nowait({"payment_id": payment_id, "delay_hours": delay_hours})
            return True
        except Exception:
            return False
