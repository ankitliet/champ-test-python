'''
# Will be defined
'''

# GENERATING LOGGER for `binder`
from logger import getlogger
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS

from util.core.app.cipher_keys import AESCipher, recr_dict
from util.core.app.models import Application as CallbackApplication, DBConfigModel

logger = getlogger(__file__)


'''
# Will be defined
'''
import importlib
import os
import time
import queue
import json
import inspect
import concurrent.futures
from typing import NamedTuple, Dict, Union, Awaitable, Tuple, List, Optional
from datetime import datetime
import socket
import traceback

from abstract.engine import AbstractEngine
from abstract.executor import AbstractExecutor
from abstract.handler import AbstractHandler
from exceptions import *
from .operation.services import CommonService
from .consumer import _rabbit_gen
from concurrent.futures import Future, Executor
from .threader import ThreadParallelExecutor





CALLBACK_OP = 'callback'
CALLBACK_CLASS = {
    "class": "CallBackops",
	"failure": "EndExecution",
	"success": "EndExecution"
}

class DummyEngine(Executor):
    """
    The class is needed to skip state in case condition to execute
    specific state is not matched
    """

    def __init__(self, **kwargs):
        self._logger = logger.getlogger(self.__class__.__name__)
        self.task_id = "NA"

    def __call__(self, state: str, payload: Dict[str, str], autoinitiate: bool):
        self.task_id = payload.get('task_id', 'NA')
        self._logger.info("Dummy engine call:%s" % payload, {'task_id': self.task_id})
        return (payload, 'skipped',)


class Engine(AbstractEngine):
    '''
    # Will be defined!
    '''
    class Config(NamedTuple):
        '''
        : Will be defined!
        '''
        service_name: str='ENGINE'
        auto_init: bool=True
        auto_initiate: bool=False
        cache_maxsize: int=10
        handlers: List=None
        hostname: str='::'.join([socket.gethostname(), socket.gethostbyname(socket.gethostname())])
        rabbit_listner: dict = None
        retrycount: int=None
        
            
    _buffer: Dict[str, Dict]=NotImplemented
    _cache: queue.Queue=NotImplemented
    _handlers: Dict[str, Union[Dict, str, int, bytes]]=NotImplemented
    _futures: int=NotImplemented
    
    
    def __init__(self, **kwargs):
        '''
        # Will be defined
        '''
        super(Engine, self).__init__(**kwargs)
        self._logger = logger.getlogger(self.__class__.__name__)
        self._conf = self.Config(**kwargs.get(self.__class__.__name__, {}))
        if self._conf.auto_init == True:
            self._logger.debug(f'auto initiating `init`...')
            self.init(
                executor=kwargs['executor'],
                state_transition_log_service=kwargs['state_transition_log_service'],
                session_factory=kwargs['session_factory'],
                request_service=kwargs['request_service'],
                rabbit_listner=kwargs['rabbit_listner'],
                conf=self._conf._asdict()
            )
        if self._conf.auto_initiate == True:
            self._logger.debug(f'auto initiating `initiate`...')
            self.initiate()
        #self._set_no_proxy(kwargs.get('session_factory'))

    def _set_no_proxy(self, session_factory):
        self._logger.debug('Set No proxy...')
        if session_factory:
            try:
                with session_factory() as session:
                    proxy_urls = session.query(
                        DBConfigModel).where(
                        DBConfigModel.key.__eq__('no_proxy_urls')).one()
                    self._logger.debug(proxy_urls.value)
                    if proxy_urls.value:
                        existing_urls = os.environ.get('no_proxy')
                        if existing_urls:
                            final_urls = existing_urls
                            existing_urls_list = existing_urls.split(",")
                            proxy_urls_list = proxy_urls.value.split(",")
                            for url in proxy_urls_list:
                                if url not in existing_urls_list:
                                    final_urls += ",%s" % url
                        else:
                            final_urls = proxy_urls.value
                        print("Proxy urls are:%s" % final_urls)
                        os.environ['no_proxy'] = final_urls
            except Exception as ex:
                self._logger.debug("Exception:%s" % str(ex))
        else:
            self._logger.debug("No db connection available")

            
    def _insert_transition_log(
        self, plan_id: str, current_state: str, current_status: str, payload: Dict={}, kv_log: Dict[str, str]={}
    ) -> None:
        if current_state.lower() != 'callback':
            try:
                self._state_transition_log_service.insert(
                    plan_id=plan_id,
                    current_state=current_state,
                    current_status=current_status,
                    payload=payload,
                    kv_log=json.dumps(kv_log),
                    identifier=self._conf.hostname
                )
            except Exception as excp:
                self._logger.exception(excp)
                self._logger.warning(f'Cannot log transaction for plan[{plan_id}]')
            
            
    def add_audit_log(self, task_id: str, source: str, event: str, trace: str, status: str):
        payload = {
            "task_id": task_id,
            "source": source,
            "event": event,
            "trace": trace,
            "status": status
        }
        insert_audit_log(payload, session_factory=self._session_factory)
            
            
    def _update_request_status(self, task_id: str, status: str) -> None:
        try:
            self._request_service.update(
                iden_filters={'task_id': task_id},
                status=status,
                modified_by='PROCESSOR'
            )
        except Exception as excp:
            self._logger.exception(excp)
            self._logger.warning(f'Cannot update request transaction for plan[{task_id}]')
        
        
    @staticmethod
    def load_handler_module(handler_module_path: str):
        try:
            logger.debug(f'loading handler[package[core.handler] | module[{handler_module_path.lower()}]]...')
            return importlib.import_module(f'.{handler_module_path.lower()}', package='core.handler')
        except (ModuleNotFoundError, ImportError, SyntaxError,) as excp:
            raise HandlerImportException from excp
        
        
    @classmethod
    def _load_handler(cls, handler_path: str):
        try:
            _mod = cls.load_handler_module(handler_path)
            _handler_cls = getattr(_mod, handler_path)
            logger.debug(f'loaded handler class[{_handler_cls}]')
            return _handler_cls
        except AttributeError as excp:
            raise InvalidHandlerClassException() from excp
    
    
    def load_handler(self, handler: str):
        try:
            _loaded_handler = self._handlers[handler]
            self._logger.debug(f'fetched handler[handler_name[{handler}] | handler_class[{_loaded_handler}]]')
        except KeyError as excp:
            _loaded_handler = self._load_handler(handler_path=handler)
            self._handlers[handler] = _loaded_handler
            self._logger.debug(f'fetched handler[handler_name[{handler}] | handler_class[{_loaded_handler}]]')
        return _loaded_handler
    
    
    def initiate_handler(self, handler):
        try:
            return handler()
        except Exception as excp:
            raise HanlderInstantiateException(excp.__repr__()) from excp
            
                
    def init(
        self, executor: AbstractExecutor, state_transition_log_service: CommonService, session_factory,
        request_service: CommonService, rabbit_listner, conf: Dict[str, str]
    ) -> None:
        try:
            self._logger.debug(f'init engine...')
            self._executor = executor
            self._state_transition_log_service = state_transition_log_service
            self._request_service = request_service
            self._rabbit_listner = rabbit_listner
            self._session_factory=session_factory
            self._identifier = socket.gethostname()
            self._buffer = {}
            self._handlers = {}
            self._futures = 0
            assert isinstance(conf['cache_maxsize'], int), f'Invalid `cache.maxsize[{conf["cache_maxsize"]}] instance!'
            self._cache = queue.Queue(maxsize=conf['cache_maxsize'])
        except Exception as excp:
            raise excp
        
        
    def _executor_callback(self, _future):
        self._futures -= 1
        if _future.cancelled():
            self._logger.debug(f'plan[{_future._planid}] with execution_index[{_future._execution_index}] has been cancelled!')
            self._cache.put(('cancelled', _future._planid,))
        elif _future.done():
            error = _future.exception()
            if error:
                self._logger.debug(f'plan[{_future._planid}] with execution_index[{_future._execution_index}] has returned exception[{error}]')
                self._cache.put(('exception', _future._planid, _future._execution_index, error,))
            else:
                result = _future.result()
                self._logger.debug(f'plan[{_future._planid}] with execution_index[{_future._execution_index}] has been sucessfully executed!')
                self._cache.put(('result', _future._planid, _future._execution_index, result))


    def _execute(self, _planid: str, handler: Tuple[str, Dict[str, str]], _payload: Union[Dict[str, str], str, int, bytes]) -> Awaitable:
        try:
            conditional_params = handler[1].get('conditional_params')
            if not conditional_params:
                self._logger.debug("No conditional parameters defined for this state")
                conditional_status = True
            else:
                conditional_status = self.condition_verification(conditional_params, _payload)
            if conditional_status:
                self._logger.debug(f'executing plan[{_planid}]...')
                _handler = self.load_handler(handler[1]['class'])
                self._logger.debug(f'Instantiating hander[{_handler}] class!')
                _handler = self.initiate_handler(_handler)
                self._insert_transition_log(_planid, handler[0], 'IN_PROGRESS', _payload)
                with self._session_factory() as session:
                    try:
                        key, iv = session.query(CallbackApplication).with_entities(
                            CallbackApplication.encryption_key, CallbackApplication.encryption_iv
                        ).filter(CallbackApplication.source == _payload.get('source')).one()
                        _cipher = AESCipher(key, iv)
                        _tmp = recr_dict(_payload, _cipher.decrypt)
                    except Exception as ex:
                        self._logger.debug("Key decryption failed:%s" % str(ex))
                        _tmp = _payload
                self._logger.debug(f'submitting [state[{_handler}] | handler[{handler[0]}]] to executor')
                _future = self._executor.submit(_handler, state=handler[0], payload=_tmp, autoinitiate=True)
                _future._planid = _planid
                _future._execution_index = handler[0]
                self._logger.debug(f'adding future callback[{self._executor}] on future[{_future}]')
                _future.add_done_callback(self._executor_callback)
                return _future
            else:
                _handler = DummyEngine()
                self._insert_transition_log(_planid, handler[0], 'SKIPPED', _payload)
                _future = self._executor.submit(_handler, state=handler[0], payload=_payload, autoinitiate=True)
                _future._planid = _planid
                _future._execution_index = handler[0]
                _future.cancelled()
                _future.add_done_callback(self._executor_callback)
                self._logger.debug('Condition for the state is not satisfied:%s, %s, %s' %
                                   (handler[0], handler[1], _payload))
                return _future
        except KeyError as excp:
            self._logger.exception(excp)
            raise InvalidStateTransitionKeyException(excp.__str__()) from excp
        except concurrent.futures.BrokenExecutor as excp:
            self._logger.exception(excp)
            self._insert_transition_log(
                _planid, handler[0], 'FAILED', _payload, 
                kv_log={'exception':traceback.format_list(traceback.extract_tb(tb=excp.__traceback__))}
            )
            raise ExecutorBrokenException from excp
            
            
    def _parallelexecute(self, _planid: str, handler: Tuple[str, Dict[str, str]], _payload: Union[Dict[str, str], str, int, bytes]) -> Awaitable:
        try:
            conditional_params = handler[1].get('conditional_params')
            if not conditional_params:
                self._logger.debug("No conditional parameters defined for this state")
                conditional_status = True
            else:
                conditional_status = self.condition_verification(conditional_params, _payload)
            if conditional_status:
                self._logger.debug(f'executing plan[{_planid}]...')
                lhds = {}
                tpe = ThreadParallelExecutor(
                    session_factory=self._session_factory, state_transition_log_service=self._state_transition_log_service,
                    hostname=self._conf.hostname
                )
                for st, val in handler[1]['parallel_tasks'].items():
                    _handler = self.load_handler(val['class'])
                    self._logger.debug(f'Instantiating hander[{st}] class!')
                    _handler = self.initiate_handler(_handler)
                    lhds[st] = _handler
                self._insert_transition_log(_planid, handler[0], 'IN_PROGRESS', _payload)
                with self._session_factory() as session:
                    try:
                        key, iv = session.query(CallbackApplication).with_entities(
                            CallbackApplication.encryption_key, CallbackApplication.encryption_iv
                        ).filter(CallbackApplication.source == _payload.get('source')).one()
                        _cipher = AESCipher(key, iv)
                        _tmp = recr_dict(_payload, _cipher.decrypt)
                    except Exception as ex:
                        self._logger.debug("Key decryption failed:%s" % str(ex))
                        _tmp = _payload
                self._logger.debug(f'submitting [state[{_handler}] | handler[{handler[0]}]] to parallel thread executor')
                _future = self._executor.submit(
                    tpe, plan_id=_planid, state=handler[0], pstates=lhds, payload=_tmp, autoinitiate=True
                )
                _future._planid = _planid
                _future._execution_index = handler[0]
                self._logger.debug(f'adding future callback[{self._executor}] on future[{_future}]')
                _future.add_done_callback(self._executor_callback)
                return _future
            else:
                _handler = DummyEngine()
                self._insert_transition_log(_planid, handler[0], 'SKIPPED', _payload)
                _future = self._executor.submit(_handler, state=handler[0], payload=_payload, autoinitiate=True)
                _future._planid = _planid
                _future._execution_index = handler[0]
                _future.cancelled()
                _future.add_done_callback(self._executor_callback)
                self._logger.debug('Condition for the state is not satisfied:%s, %s, %s' %
                                   (handler[0], handler[1], _payload))
                return _future
        except KeyError as excp:
            self._logger.exception(excp)
            raise InvalidStateTransitionKeyException(excp.__str__()) from excp
        except concurrent.futures.BrokenExecutor as excp:
            self._logger.exception(excp)
            self._insert_transition_log(
                _planid, handler[0], 'FAILED', _payload, 
                kv_log={'exception':traceback.format_list(traceback.extract_tb(tb=excp.__traceback__))}
            )
            raise ExecutorBrokenException from excp
            
            
            

    def compare_values(self, actual_value, conditional_value, operator):
        if operator == "eq":
            return actual_value == conditional_value
        elif operator == "gt":
            return actual_value > conditional_value
        elif operator == "lt":
            return actual_value < conditional_value
        elif operator == "gte":
            return actual_value >= conditional_value
        elif operator == "lte":
            return actual_value <= conditional_value
        elif operator == "neq":
            return actual_value != conditional_value

        
    def and_conditions_check(self, and_condition, payload):
        key = and_condition.get('key')
        value = and_condition.get('value')
        operator = and_condition.get('operator')
        self._logger.info("Key:%s, value:%s, operator:%s" % (key, value, operator))
        conditional_flag = []
        if "." in key:
            key_map = key.split(".")[0]
            key = key.split(".")[1]
            map_data = payload.get(key_map)
            if isinstance(map_data, list):
                for single_map in map_data:
                    payload_value = single_map.get(key, None)
                    conditional_flag.append(
                        self.compare_values(payload_value, value, operator))
            elif isinstance(map_data, dict):
                payload_value = map_data.get(key, None)
                conditional_flag.append(
                    self.compare_values(payload_value, value, operator))
        else:
            payload_value = payload.get(key, None)
            self._logger.debug("Payload value is:%s" % payload_value)
            if payload_value is not None:
                conditional_flag.append(
                    self.compare_values(payload_value, value, operator))
            else:
                conditional_flag.append(False)
        print(conditional_flag)
        output = True
        for each_op in conditional_flag:
            output = output and each_op
        return output

    def condition_verification(self, conditional_params, payload) -> None:
        self._logger.info("Verify the conditions:%s %s" % (conditional_params, payload))
        output = True
        and_conditions = conditional_params.get('AND')
        or_conditions = conditional_params.get('OR')
        conditional_flag = []
        for and_condition in and_conditions:
            self._logger.info("And condition:%s" % and_condition)
            conditional_flag.append(self.and_conditions_check(and_condition,
                                                              payload.get('parameters')))
        for each_op in conditional_flag:
            output = output and each_op
        return output
        
    def execute(self, _plan: Dict[str, Union[Dict, str]]) -> None:
        try:
            self._logger.debug(f'executing new plan[{_plan["PlanId"]}]')
            self.add_audit_log(
                _plan["PlanId"], 'PROCESSOR', 'initiate', _plan["PlanId"], TASK_STATUS.COMPLETED
            )
            new_handler = _plan['LastExecutionIndex']
            _new_handler = _plan['StateTransition'].get(new_handler, NotImplemented)
            if not 'retrycount' in _new_handler:
                if self.get_resource_destroy_flag(payload=_plan['Payload']):
                    _new_handler['retrycount'] = _plan.get('retrycount', self._conf.retrycount)
                else:
                    _new_handler['retrycount'] = 0
            if _new_handler == NotImplemented:
                raise InvalidLastExecutionIndexException(new_handler)
            assert _plan['PlanId'] not in self._buffer, f'plan[{_plan["PlanId"]}] already in execution! may be the plan has been sent twice!'
            self._buffer[_plan['PlanId']] = _plan
            self._update_request_status(task_id=_plan["PlanId"], status='IN_PROGRESS')
            if 'parallel_tasks' in _plan['StateTransition'][new_handler]:
                _future = self._parallelexecute(
                    _planid=_plan['PlanId'],
                    handler=(new_handler, _new_handler,),
                    _payload=_plan['Payload']
                )
            else:
                _future = self._execute(
                    _planid=_plan['PlanId'],
                    handler=(new_handler, _new_handler,),
                    _payload=_plan['Payload']
                )
            self._futures += 1
        except KeyError as excp:
            self._logger.exception(excp)
            raise PlanKeyMissingException(excp.__str__()) from excp
        except AssertionError as excp:
            self._logger.exception(excp)
            self.add_audit_log(
                _plan['PlanId'],  'PROCESSOR', 'execute',
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            raise DuplicatePlanIDException(_plan['PlanId']) from excp
        except Exception as excp:
            self._logger.exception(excp)
            self.add_audit_log(
                _plan['PlanId'],  'PROCESSOR', 'execute',
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            self._excp_cleanup(_planid=_plan['PlanId'])
            raise excp
            
    def _excp_cleanup(self, _planid: str) -> None:
        self._logger.debug(f'exceptional clean_up for plan[{_planid}]...')
        try:
            _plan = self._buffer.pop(_planid, None)
            if _plan:
                payload = _plan.get('Payload')
            else:
                payload=''
            self._update_request_status(task_id=_planid, status='FAILED')
            _new_handler = (CALLBACK_OP, CALLBACK_CLASS)
            self._execute(_planid=_planid, handler=_new_handler, _payload=payload)
            self.add_audit_log(
                _planid,  'PROCESSOR', '_excp_cleanup', '', TASK_STATUS.COMPLETED
            )
        except Exception as excp:
            raise excp

    def get_resource_destroy_flag(self, payload):
        self._logger.debug(f'Check Destroy flag...', {'task_id': payload.get('task_id')})
        destory_failed_flag = True
        try:
            with self._session_factory() as session:
                app_info = session.query(
                    CallbackApplication).where(
                    CallbackApplication.is_active.__eq__(True)).where(
                    CallbackApplication.source.__eq__(payload.get('source'))).one()
                print(app_info.channel)
                if app_info.channel.get('provisioning'):
                    destory_failed_flag = app_info.channel.get('provisioning').get(
                        'destrory_failed_transaction', True)
            return destory_failed_flag
        except Exception as ex:
            self._logger.debug("Exception:%s" % str(ex), {'task_id': self.task_id})
            return destory_failed_flag
            
    def _cleanup(self, _planid: str):
        self._logger.debug(f'clean_up for plan[{_planid}]...')
        try:
            self._logger.debug("Buffer is:%s" % self._buffer)
            payload = self._buffer.get(_planid).get('Payload')
            self._buffer.pop(_planid, None)
            self._update_request_status(task_id=_planid, status=TASK_STATUS.COMPLETED)
            _new_handler = (CALLBACK_OP, CALLBACK_CLASS)
            self._execute(_planid=_planid, handler=_new_handler, _payload=payload)
            self.add_audit_log(
                _planid,  'PROCESSOR', '_cleanup', '', TASK_STATUS.COMPLETED
            )
        except Exception as excp:
            raise excp
            
            
    def _process_cache(self, _cache_resp: Tuple[str, str, Tuple[str, Union[Dict, str, int, bytes]]]) -> None:
        self._logger.debug(f'processing cache...')
        self._logger.debug("Cache response is:%s" % str(_cache_resp))
        try:
            if _cache_resp[0] == 'result' and _cache_resp[2] != "callback":
                _result = _cache_resp[3]
                if _result[1] == 'skipped':
                    self._insert_transition_log(_cache_resp[1], _cache_resp[2],
                                                'SKIPPED', _result[0], kv_log={'trigger':_result[1]})
                    next_status = 'success'
                else:
                    self._insert_transition_log(_cache_resp[1], _cache_resp[2],
                                                'SUCCESS', _result[0], kv_log={'trigger': _result[1]})
                    next_status = _result[1]
                assert isinstance(_result, tuple), f'Invalid result fetched from handler!'
                _plan = self._buffer[_cache_resp[1]]
                _plan['Payload'] = _result[0]
                _new_handler = _plan['StateTransition'][_cache_resp[2]][next_status]
                if not 'retrycount' in _plan['StateTransition'][_new_handler]:
                    if self.get_resource_destroy_flag(payload=_result[0]):
                        _plan['StateTransition'][_new_handler]['retrycount'] = \
                            _plan.get('retrycount', self._conf.retrycount)
                    else:
                        _plan['StateTransition'][_new_handler]['retrycount'] = 0
                _new_handler = (_new_handler, _plan['StateTransition'][_new_handler])
                _plan['LastExecutionIndex'] = _new_handler[0]
                if _new_handler[0] == 'EndExecution':
                    self._insert_transition_log(_cache_resp[1], _new_handler[0], 'SUCCESS', _result[0])
                    self.add_audit_log(
                        _cache_resp[1],  'PROCESSOR', 'execute', '', TASK_STATUS.COMPLETED
                    )
                    self._logger.info(f'plan[{_cache_resp[1]}] has been sucessfully completed!')
                    self._cleanup(_cache_resp[1])
                else:
                    if 'parallel_tasks' in _plan['StateTransition'][_new_handler[0]]:
                        _future = self._parallelexecute(
                            _planid=_cache_resp[1],
                            handler=_new_handler,
                            _payload=_result[0]
                        )
                    else:
                        _future = self._execute(
                            _planid=_cache_resp[1],
                            handler=_new_handler,
                            _payload=_result[0]
                        )
            elif _cache_resp[0] == 'exception' and _cache_resp[2] != "callback":
                self._logger.warning(f'plan[{_cache_resp[1]}] has failed due to exception[{_cache_resp[3]}]!')
                self._insert_transition_log(
                    _cache_resp[1], _cache_resp[2], 'FAILED', self._buffer[_cache_resp[1]]['Payload'],
                    kv_log={'traceback': _cache_resp[3].__repr__()}
                )
                self.add_audit_log(
                        _cache_resp[1],  'PROCESSOR', 'execute', _cache_resp[3].__repr__(), TASK_STATUS.FAILED
                    )
                _sttmp = self._buffer[_cache_resp[1]]['StateTransition'][self._buffer[_cache_resp[1]]['LastExecutionIndex']]
                if _sttmp['retrycount'] > 0:
                    _sttmp['retrycount'] -= 1
                    self.add_audit_log(
                        _cache_resp[1],  'PROCESSOR', 'retry', 
                        f'{self._buffer[_cache_resp[1]]["LastExecutionIndex"]}[{_sttmp["retrycount"]}]',
                        TASK_STATUS.COMPLETED
                    )
                    if self._buffer[_cache_resp[1]]['LastExecutionIndex'] == 'parallel_tasks':
                        _future = self._parallelexecute(
                            _planid=_cache_resp[1], 
                            handler=(
                                self._buffer[_cache_resp[1]]['LastExecutionIndex'], 
                                self._buffer[_cache_resp[1]]['StateTransition'][self._buffer[_cache_resp[1]]['LastExecutionIndex']],
                            ),
                        _payload=self._buffer[_cache_resp[1]]['Payload']
                        )
                    else:
                        _future = self._execute(
                            _planid=_cache_resp[1], 
                            handler=(
                                self._buffer[_cache_resp[1]]['LastExecutionIndex'], 
                                self._buffer[_cache_resp[1]]['StateTransition'][self._buffer[_cache_resp[1]]['LastExecutionIndex']],
                            ),
                            _payload=self._buffer[_cache_resp[1]]['Payload']
                        )
                else:
                    self._excp_cleanup(_planid=_cache_resp[1])
        except TypeError as excp:
            self._logger.warning(f'Unable to process response for [plan[{_cache_resp[1]}] | state[{_cache_resp[2]}]]')
            self._insert_transition_log(
                _cache_resp[1], _cache_resp[2], 'EXECUTED', 'FAILED', 
                kv_log={'traceback': traceback.format_list(traceback.extract_tb(tb=excp.__traceback__))}
            )
            self.add_audit_log(
                _cache_resp[1],  'PROCESSOR', 'processor_callback', 
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            self._excp_cleanup(_planid=_cache_resp[1])
            raise InvalidHandlerResponseException from excp
        except (InvalidStateTransitionKeyException, KeyError, ) as excp:
            self._logger.warning(f'Unable to execute plan[{_plan}]')
            self._insert_transition_log(
                _cache_resp[1], 'UNDEFINED', 'FAILED', excp.__repr__(), 
                kv_log={'traceback': excp.__repr__()}
            )
            self.add_audit_log(
                _plan['PlanId'],  'PROCESSOR', 'processor_callback', 
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            self._excp_cleanup(_planid=_plan['PlanId'])
            raise InvalidPlanException from excp
        except (HandlerImportException, InvalidHandlerClassException, HanlderInstantiateException, ) as excp:
            self._logger.warning(f'Unable to execute plan[{_plan}]')
            self._insert_transition_log(
                _cache_resp[1], _new_handler[0], 'FAILED', excp.__repr__(), 
                kv_log={'traceback': traceback.format_list(traceback.extract_tb(tb=excp.__traceback__))}
            )
            self.add_audit_log(
                _plan['PlanId'],  'PROCESSOR', 'processor_callback', 
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            self._excp_cleanup(_planid=_plan['PlanId'])
            raise HandlerException from excp
        except Exception as excp:
            self.add_audit_log(
                _plan.get('PlanId'),  'PROCESSOR', 'processor_callback', 
                traceback.format_list(traceback.extract_tb(tb=excp.__traceback__)), TASK_STATUS.FAILED
            )
            self._excp_cleanup(_planid=_plan['PlanId'])
            raise excp
        
                
    
    def _fetch_cache(self) -> Optional[Tuple[str, str, str, Tuple[str, Dict[str, str]]]]:
        try:
            return self._cache.get_nowait()
        except queue.Empty:
            return None
        
        
    def process_listner(self, _plan):
        try:
            _plan = json.loads(_plan)
            self.execute(_plan)
        except (json.JSONDecodeError, DuplicatePlanIDException, PlanKeyMissingException) as excp:
            self._logger.warning(f'Unable to execute plan[{_plan}]')
            raise InvalidPlanException from excp
        except (InvalidStateTransitionKeyException, HandlerImportException, InvalidHandlerClassException, HanlderInstantiateException, ) as excp:
            self._logger.warning(f'Unable to execute plan[{_plan}]')
            self._insert_transition_log(
                    _plan['PlanId'], _plan['LastExecutionIndex'], 'Failed', 
                    kv_log={'traceback': traceback.format_list(traceback.extract_tb(tb=excp.__traceback__))}
                )
            self._excp_cleanup(_planid=_plan['PlanId'])
            raise HandlerException from excp
        
        
    def _initiate(self) -> None:
        yielder = _rabbit_gen(
            host=self._conf.rabbit_listner['server'], 
            port=self._conf.rabbit_listner['port'],
            username=self._conf.rabbit_listner['user'],
            password=self._conf.rabbit_listner['password'],
            queue=os.environ.get('RABBITQUEUENAME')
        )
        while True:
            time.sleep(0.6)
            try:
                _cache_resp = self._fetch_cache()
                if not _cache_resp == None:
                    self._process_cache(_cache_resp=_cache_resp)
                    continue
                else:
                    if self._futures <= self._executor._max_workers:
                        _plan = next(yielder)
                        if _plan == None:
                            yielder.send(False)
                            time.sleep(5)
                        else:
                            yielder.send(True)
                            self.process_listner(_plan=_plan)
            except (InvalidPlanException, InvalidHandlerResponseException, HandlerException) as excp:
                self._logger.exception(excp)
            except StopIteration as excp:
                yielder = _rabbit_gen(
                    host=self._conf.rabbit_listner['server'], 
                    port=self._conf.rabbit_listner['port'],
                    username=self._conf.rabbit_listner['user'],
                    password=self._conf.rabbit_listner['password'],
                    queue=os.environ.get('RABBITQUEUENAME')
                )
            except KeyboardInterrupt as excp:
                raise KeyboardInterrupt from excp
            except Exception as excp:
                self._logger.exception(excp)
                
                
    def _initiate_shutdown(self):
        self._logger.debug(f'shutting down executor[{self._executor}]')
        self._executor.shutdown()
        while True:
            try:
                _cache_resp = self._fetch_cache()
                if not _cache_resp == None:
                    self._process_cache(_cache_resp=_cache_resp)
                    continue
                else:
                    self._logger.debug(f'cache_store empty!')
                    break
            except Exception as excp:
                self._logger.exception(excp)
                self._logger.warning('worker stopped drastically!!!!!!!!!!!!!!!!!!')
                raise excp
        self._logger.debug(f'worker has gracefully stopped!')                    
                
                
    def initiate(self):
        try:
            self._logger.info('Starting the worker...')
            self._initiate()
        except KeyboardInterrupt as excp:
            self._logger.warning('Stopping the worker gracefully...')
            self._initiate_shutdown()
