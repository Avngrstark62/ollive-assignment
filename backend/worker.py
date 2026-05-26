import asyncio

from ingestion_service import ingest_inference_log
from rmq.consumer import start_inference_log_consumer


async def _handle_inference_log_event(message: dict) -> None:
    payload = message.get("payload")
    if not isinstance(payload, dict):
        print("[worker] Received invalid event payload.")
        raise ValueError("Invalid inference log event payload.")
    log_id = payload.get("id", "unknown")
    print(f"[worker] Received inference log event: id={log_id}")
    ingest_inference_log(payload)
    print(f"[worker] Inference log stored: id={log_id}")


async def run_worker() -> None:
    print("[worker] Starting inference log worker...")
    await start_inference_log_consumer(_handle_inference_log_event)


if __name__ == "__main__":
    asyncio.run(run_worker())
