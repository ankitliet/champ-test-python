import yaml
from consumer.core.app.consumer import Consumer
queue_name = 'hcmp_orchestrator'
from datetime import datetime

from util.core.app.audit_log_transaction import insert_audit_log

if __name__ == "__main__":
    with open("dev.yml", "r") as f:
        config = yaml.safe_load(f)

    # Ex code to push audit transaction log
    # audit_log = AuditLogTransaction(config)
    # payload = {
    #     "task_id": "a10",
    #     "source": "ClassA",
    #     "event": "VMCreate",
    #     "status": "in_progress",
    #     "trace": "",
    #     "timestamp": datetime.utcnow()
    # }
    # audit_log.insert_audit_log(payload)

    # Ex code to use consumer to fetch message from the rmq
    consumer = Consumer(config.get('rmq'), queue_name)
    message = consumer.consumer_method()
    print("Message Body:")
    print(message)
