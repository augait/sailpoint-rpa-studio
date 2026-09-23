import socket
from uuid import uuid4

from rq import Worker
from rq.serializers import JSONSerializer

from backend.app.core.queue import connection, queue


def main():
    worker = Worker(
        [queue()],
        connection=connection(),
        serializer=JSONSerializer,
        name=f"{socket.gethostname()}-{uuid4().hex[:6]}",
    )
    worker.work()


if __name__ == "__main__":
    main()
