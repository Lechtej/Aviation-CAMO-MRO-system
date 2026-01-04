"""Worker skeleton (v0.2.1)

Purpose:
- keep the container alive
- provide a placeholder entrypoint for future Celery app and ERP jobs

In v0.3+:
- configure Celery app
- add integration tasks with retry/idempotency
"""

import time

def main():
    print("worker skeleton: running (no tasks configured yet)")
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
