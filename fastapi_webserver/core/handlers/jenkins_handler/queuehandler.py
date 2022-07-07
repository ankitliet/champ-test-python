import json
import pika


# GLOBAL VARIABLES
#release = f'-{os.environ.get("EXECFILE", "dev")}' if os.environ.get("EXECFILE", "dev") != 'dev' else ''


class ConnectionPool:
    ...
    
#     __conn__ = None

#     def __init__(self,server,port,virtual_host,user,password):
#         """ Constructor.
#         """
#         if ConnectionPool.__conn__ is None or ConnectionPool.__conn__.is_closed:
#             credentials = pika.PlainCredentials(user, password)
#             parameters = pika.ConnectionParameters(server,
#                                                    port,
#                                                    virtual_host,
#                                                    credentials)
#             ConnectionPool.__conn__ = pika.BlockingConnection(parameters)
#         else:
#             raise Exception("You cannot create another ConnectionPool class")

#     @staticmethod
#     def get_instance(server,port,virtual_host,user,password):
#         """ Static method to fetch the current instance.
#         """
#         if ConnectionPool.__conn__ is None or ConnectionPool.__conn__.is_closed:
#             ConnectionPool(server,port,virtual_host,user,password)
#         return ConnectionPool.__conn__


# class MessageQueue:

#     def __init__(self, config):
#         self.server = config['server']
#         self.port = config['port']
#         self.virtual_host = config['virtual_host']
#         self.user = config['user']
#         self.password = config['password']
#         self.queue = config['queue']
#         self.exchange = config['exchange']
        
        

#     def insert_task(self,body,queue):
#         try:
#             queue_name = self.queue
#             connection = ConnectionPool.get_instance(self.server,self.port,self.virtual_host,self.user,self.password)
#             channel = connection.channel()
#             channel.queue_declare(queue=queue_name,durable=True)
#             channel.basic_publish(exchange=self.exchange,
#                                   routing_key=queue_name,
#                                   body=str(body))
#             connection.close()

#             return {"message":"Request Added to Queue"}
#         except Exception as ex:
#             return {"error" : str(ex)}
        
        
        
        
        
        
class MessageQueue:
    
    def __init__(self, config):
        self._username = config['user']
        self._password = config['password']
        self._server = config['server']
        self._port = config['port']
        self._queue = config['queue']
        self._exchange = config['exchange']
        self._connection = self.get_connection(
                    username=self._username, password=self._password, host=self._server, port=self._port
                )
        
        
    def get_connection(self, username, password, host, port):
        credentials = pika.PlainCredentials(username, password)
        parameters = pika.ConnectionParameters(host,
                                       port,
                                       '/',
                                       credentials,
                                       heartbeat=0
                                              )
        connection = pika.BlockingConnection(parameters)
        return connection
        
        
    def insert_task(self, body, queue_name, exchange_key, **kwargs):
        count = 3
        while count > 0:
            try:
                channel = self._connection.channel()
                channel.basic_publish(exchange=exchange_key,
                                      routing_key=queue_name,
                                      body=str(body))
                channel.close()
                msg = {"message":"Request Added to Queue"}
                break
            except Exception as ex:
                print(ex)
                self._connection = self.get_connection(
                    username=self._username, password=self._password, host=self._server, port=self._port
                )
                msg = {"error" : str(ex)}
                count -= 1
        return msg
    