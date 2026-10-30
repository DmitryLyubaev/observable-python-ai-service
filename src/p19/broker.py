import os

from celery import Celery

app = Celery("p19", broker=os.environ.get("P19_REDIS_URL", "redis://redis:6379/0"))
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    task_ignore_result=True,
    task_acks_late=False,
    worker_prefetch_multiplier=1,
    task_publish_retry=False,
    broker_connection_timeout=3,
    broker_transport_options={
        "socket_connect_timeout": 3,
        "socket_timeout": 3,
        "retry_on_timeout": False,
    },
    task_default_queue="p19",
    task_soft_time_limit=35,
    task_time_limit=40,
)


def publish(job_id, context):
    app.send_task("p19.investigate", args=[job_id], headers={"p19_trace": context}, retry=False)
