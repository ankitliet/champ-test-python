import yaml
import json
import os
import asyncio
import aio_pika.exceptions
from datetime import datetime
from aio_pika import connect_robust
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS

class Consumer:
    def __init__(self, config=None, queue_name=None, session=None):
        if config:
            self.server = config['server']
            self.port = config['port']
            self.virtual_host = config['virtual_host']
            self.user = config['user']
            self.password = config['password']
            self.exchange = config.get('exchange', 'direct')
        else:
            config_file = os.path.join(os.environ['BASEDIR'],
                                       'configurations',
                                       f'{os.environ["EXECFILE"]}.yml')
            # config_file = "dev.yml"
            if not os.path.exists(config_file):
                config_file = os.path.join(os.environ['BASEDIR'],
                                           'core', 'core', 'settings',
                                           f'{os.environ["EXECFILE"]}.yml')
            try:
                with open(config_file, "r") as f:
                    config = yaml.safe_load(f)
            except Exception as ex:
                raise Exception("Config file not found:%s" % str(ex))
            config = config.get('rmq')
        if not config:
            raise Exception("Configuration not found")
        if queue_name:
            self.queue = queue_name
        else:
            self.queue = config.get('queue', 'hcmp_orchestrator')
        self.rmq_connection_str = f"amqp://{self.user}:" \
                                       f"{self.password}@{self.server}:" \
                                       f"{self.port}/"
        self.session_factory = session

    async def get_message(self, loop):
        try:
            payload = {
                "task_id": "",
                "source":  self.__class__.__name__,
                "event": f"ReceiveMessage from queue[{self.queue}]",
                "timestamp": datetime.utcnow(),
                "status": TASK_STATUS.FAILED,
                "trace": ""
            }
            print("Consumer get_message 1")
            connection = await connect_robust(
                self.rmq_connection_str, loop=loop
            )
            # Creating channel
            channel = await connection.channel()
            # Declaring exchange
            exchange = await channel.declare_exchange(self.exchange, auto_delete=False,
                                                      durable=True)
            # Declaring queue
            queue = await channel.declare_queue(self.queue, auto_delete=False,
                                                durable=True)
            # Binding queue
            #try:
            print("Consumer get_message 2")
            await queue.bind(exchange, self.queue)
            print("Consumer get_message 3")
            # except Exception as ex:
            #     payload.update({
            #         "task_id": "consumer_error",
            #         "status": TASK_STATUS.FAILED,
            #         "trace": "Message Failed",
            #     })
            #     insert_audit_log(payload, session_factory=self.session_factory)
            try:
                # Fetch the single message from the queue
                print("Consumer get_message 4")
                incoming_message = await queue.get(timeout=60)
                print("Consumer get_message 5")
                # Acknowledge the message
                await incoming_message.ack()
                await queue.unbind(exchange, self.queue)

                # Add an entry to the audit log
                data = json.loads(incoming_message.body.decode('utf-8'))
                task_id = data.get('Payload').get('task_id')
                payload.update({
                    "task_id": task_id,
                    "status": TASK_STATUS.COMPLETED,
                    "trace": "Message Delivered",
                })
                message = incoming_message.body
                insert_audit_log(payload, session_factory=self.session_factory)
            except aio_pika.exceptions.QueueEmpty as ex:
                # return none in case queue is empty
                message = None
                #payload.update({"trace": "Queue is empty"})
                print("Consumer get_message 6")
            except Exception as ex:
                print("Consumer get_message 7")
                payload.update({"trace": str(ex)})
                insert_audit_log(payload, session_factory=self.session_factory)
                raise Exception("%s" % str(ex))
            # finally:
            #     insert_audit_log(payload, session_factory=self.session_factory)
            return message
        finally:
            #print("close the connection")
            await connection.close()

    def consumer_method(self):
       loop = asyncio.get_event_loop()
       return loop.run_until_complete(self.get_message(loop))
