from redis import Redis
from rq import Queue
from rq.serializers import JSONSerializer

from backend.app.core.config import settings


def connection() -> Redis:
    return Redis.from_url(settings().redis_url, socket_connect_timeout=3, socket_timeout=5)


def queue() -> Queue:
    return Queue(settings().queue_name, connection=connection(), serializer=JSONSerializer)
