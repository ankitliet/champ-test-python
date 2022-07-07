'''
# Will be defined
'''

# GENERATING LOGGER for `binder`
from logger import getlogger
from util.core.app.audit_log_transaction import insert_audit_log
from util.core.app.constants import TASK_STATUS

from util.core.app.cipher_keys import AESCipher, recr_dict
from util.core.app.models import Application as CallbackApplication

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
from typing import NamedTuple, Dict, Union, Awaitable, Tuple, List, Optional
from datetime import datetime
import socket
import traceback

from abstract.executor import AbstractExecutor
from concurrent.futures import ThreadPoolExecutor, as_completed





class ThreadParallelExecutor(AbstractExecutor):
    
    def __init__(self, **kwargs):
        self._session_factory=kwargs['session_factory']
        self._state_transition_log_service = kwargs['state_transition_log_service']
        self.hostname = kwargs['hostname']
        
        
    def add_audit_log(self, task_id: str, source: str, event: str, trace: str, status: str):
        payload = {
            "task_id": task_id,
            "source": source,
            "event": event,
            "trace": trace,
            "status": status
        }
        insert_audit_log(payload, session_factory=self._session_factory)
        
        
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
                    identifier=self.hostname
                )
            except Exception as excp:
                logger.debug('\n\n\n\n')
                logger.exception(excp)
                logger.warning(f'Cannot log transaction for plan[{plan_id}]')
                raise excp
        
    
    def __call__(self, plan_id, state: str, pstates: Dict, payload: Dict[str, str], autoinitiate: bool):
        with ThreadPoolExecutor(max_workers=len(pstates)) as exe:
            wait_for = []
            for st, val in pstates.items():
                if payload.get(f'{st}_flag') == None:
                    payload[f'{st}_flag'] = False
                if payload[f'{st}_flag'] == False:
                    fut = exe.submit(
                        val, state=st, payload=payload, autoinitiate=autoinitiate
                    )
                    fut.iden = st
                    fut.payl = payload
                    self.add_audit_log(
                        payload['task_id'], 'THREADER', 'ThreadStarted', st, TASK_STATUS.COMPLETED
                    )
                    self._insert_transition_log(plan_id, st, 'IN_PROGRESS', payload)
                    wait_for.append(fut)
                else:
                    self.add_audit_log(
                        payload['task_id'], 'THREADER', f'ThreadSkipped', st, TASK_STATUS.COMPLETED
                    )
            resp = {}
            flg = True
            for fut in as_completed(wait_for):
                try:
                    resp[fut.iden] = fut.result()
                    self._insert_transition_log(plan_id, fut.iden, 'SUCCESS', resp[fut.iden][1])
                    payload[f'{fut.iden}_flag'] = True
                except Exception as excp:
                    flg = False
                    resp[fut.iden] = traceback.format_list(traceback.extract_tb(tb=excp.__traceback__))
                    self._insert_transition_log(
                        plan_id, fut.iden, 'FAILED', fut.payl, 
                        kv_log={'exception':traceback.format_list(traceback.extract_tb(tb=excp.__traceback__))}
                    )
            if flg == False:
                raise Exception(resp.__repr__())
            return (payload, 'success',)