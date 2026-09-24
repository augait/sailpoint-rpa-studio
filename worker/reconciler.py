import signal
import time

from backend.app.services.outbox_service import dispatch_pending


running = True


def stop(*_):
    global running
    running = False


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print("[RECONCILER] started", flush=True)

    while running:
        try:
            result = dispatch_pending(limit=100)

            if result["selected"]:
                print(
                    "[RECONCILER] "
                    f"selected={result['selected']} "
                    f"sent={result['sent']} "
                    f"failed={result['failed']}",
                    flush=True,
                )

        except Exception as exc:
            print(
                f"[RECONCILER ERROR] {type(exc).__name__}",
                flush=True,
            )

        time.sleep(5)

    print("[RECONCILER] stopped", flush=True)


if __name__ == "__main__":
    main()
