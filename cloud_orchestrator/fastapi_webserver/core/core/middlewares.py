from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, Request, Header
from starlette.responses import Response, JSONResponse

from uuid import uuid4 as uuid

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime



Base = declarative_base()


class TracebackHelperModel(Base):
    __tablename__ = "tracebacks"

    trace_id = Column(String(255), primary_key=True)
    method = Column(String(100), nullable=False)
    headers = Column(Text)
    query_params = Column(Text)
    path_params = Column(Text)
    client_address = Column(Text)
    cookies = Column(Text)
    body = Column(Text)
    traceback = Column(Text)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    def _asdict(self):
        return dict(trace_id=self.trace_id,
                    method=self.method,
                    headers=self.headers,
                    query_params=self.query_params,
                    path_params=self.path_params,
                    client_address=self.client_address,
                    cookies=self.cookies,
                    request_data=self.request_data,
                    traceback = self.traceback,
                    timestamp=self.timestamp.strftime("%m/%d/%Y, %H:%M:%S"))

                    
                    
                    
                    
class TracebackHelper(BaseHTTPMiddleware):
    def __init__(self, app, container):
        super().__init__(app)
        self.app = app
        self.session_factory = container.db.provided.session()

    async def dispatch(self, request:Request, call_next):
        try:
            response = await call_next(request)
            if not str(response.status_code).startswith('2'):
                raise Exception(response)
        except Exception as excp:
            uid = uuid()
            with self.session_factory() as session:
                _exception = TracebackHelperModel(
                    trace_id=uid.hex,
                    method=request.method,
                    headers=request.headers,
                    query_params = request.query_params,
                    path_params = request.path_params,
                    client_address = request.client.host,
                    cookies = request.cookies,
                    body=await request.body(),
                    traceback=repr(excp)
                )
                session.add(_exception)
                session.commit()       
                    
            response.headers["Traceback-ID"] = uid.hex
        return response