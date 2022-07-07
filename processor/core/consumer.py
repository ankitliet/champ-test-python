from logger import getlogger
logger = getlogger(__file__)
import pika



def _rabbit_gen(host: str, port, username, password, queue: str):
    logger.info(f'Creating `rabbit_generator` for host[{host}] | queue[{queue}]...')
    credentials = pika.PlainCredentials(username, password)
    parameters = pika.ConnectionParameters(
        host,
       port,
       '/',
       credentials,
       heartbeat=0
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    #channel.queue_declare(queue=queue)
    while True:
        result = channel.basic_get(queue=queue, auto_ack=False)
        #logger.debug(f'rabbit[{channel}] replied[{result}]')
        if result[0]:
            #logger.info(f'rabbit[{channel}] pushed task[{result[2]}]')
            _ack_flag = yield result[2]
            if _ack_flag == True:
                #logger.debug(f'Acknowledge rabbit[{channel}] task with `delivery_tag[{result[0].delivery_tag}]`')
                channel.basic_ack(result[0].delivery_tag)
            else:
                #logger.debug(f'Negative acknowledge rabbit[{channel}] task with `delivery_tag[{result[0].delivery_tag}]`')
                channel.basic_nack(result[0].delivery_tag)
        else:
            _ack_flag = yield None