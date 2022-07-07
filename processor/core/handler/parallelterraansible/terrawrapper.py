import logging
logger = logging.getLogger(__name__)


import shlex, subprocess
from copy import deepcopy
from functools import partial
from .exceptions import *


FLAGVALUE = 'flagvalue'





class TerraformWrapper(object):
    __methods__: dict=dict(
        init=['terraform', 'init'],
        create_workspace=['terraform', 'workspace', 'new'],
        set_workspace=['terraform', 'workspace', 'select'],
        plan=['terraform', 'plan'],
        apply=['terraform', 'apply'],
        output=['terraform', 'output']
    )

    
    def __init__(self, global_opts: dict=dict(), globaltimeout: int=None, cwd=None):
        logger.warning(f'global_opts[{global_opts}]')
        self.gopts = []
        for op, val in global_opts.items():
            if val == FLAGVALUE:
                self.gopts.append(op)
            else:
                self.gopts.append(f'{op}={val}')
        logger.warning(f'self.gopts[{self.gopts}]')
        self.globaltimeout = globaltimeout
        
        
    def __getattr__(self, name: str):
        if name in self.__methods__.keys():
            return partial(self.invoke, cmd=deepcopy(self.__methods__)[name])
        else:
            return self.__getattribute__(name)
        
        
    def _invoke(
        self, cmd, timeout=None, suppress: bool=False, bufsize=-1, executable=None, stdin=None, stdout=None, 
        stderr=None, preexec_fn=None, close_fds=True, shell=False, cwd=None, env=None, universal_newlines=None, 
        startupinfo=None, creationflags=0, restore_signals=True, start_new_session=False, pass_fds=(), *, 
        encoding=None, errors=None, text=None
    ):
        if isinstance(cmd, str):
            cmd = args = shlex.split(cmd)
        if stdin == None:
            stdin=subprocess.PIPE
        if stdout == None:
            stdout=subprocess.PIPE
        if stderr == None:
            stderr=subprocess.PIPE
        try:
            cmd = ' '.join(cmd)
            cmd = shlex.split(cmd)
            logger.warning(f'CMD -> [{cmd}]')
            proc = subprocess.Popen(
                cmd, bufsize=bufsize, executable=executable, stdin=stdin, stdout=stdout, stderr=stderr, 
                preexec_fn=preexec_fn, close_fds=close_fds, shell=shell, cwd=cwd, env=env, 
                universal_newlines=universal_newlines, startupinfo=startupinfo, creationflags=creationflags, 
                restore_signals=restore_signals, start_new_session=start_new_session, pass_fds=pass_fds, 
                encoding=encoding, errors=errors, text=text
            )
            stdout_value, stderr_value = proc.communicate(timeout=timeout)
            if suppress == False:
                if proc.returncode != 0:
                    raise TerraformFailedException(f'\nSTDOUT -> [{stdout_value}] \nSTDERR -> [{stderr_value}]')
            return proc.returncode, stdout_value.decode(), stderr_value.decode()
        except subprocess.TimeoutExpired as excp:
            proc.kill()
            stdout_value, stderr_value = proc.communicate()
            raise TerraformTimoutException(f'\nSTDOUT -> [{stdout_value}] \nSTDERR -> [{stderr_value}]') from excp
            
            
    def p__opts(self, cmd, opts):
        for op, val in opts.items():
            if val == FLAGVALUE:
                cmd.append(op)
            elif isinstance(val, dict):
                for key, value in val.items():
                    cmd.append(f'{op}={key}={value}')
            else:
                cmd.append(f'{op}={val}')
        return cmd
    
    
    def invoke(self, cmd: list, opts: dict=dict(), cwd=None, timeout=None, suppress: bool=False):
        cmd = self.p__opts(cmd=cmd, opts=opts)
        cmd[1:1] = deepcopy(self.gopts)
        timeout = timeout or self.globaltimeout
        return self._invoke(cmd=cmd, timeout=timeout, suppress=suppress)