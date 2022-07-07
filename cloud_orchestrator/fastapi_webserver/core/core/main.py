# FAST API IMPORTS
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_versioning import VersionedFastAPI
from starlette.middleware.sessions import SessionMiddleware
from core.app import api
from .routers import router
from .container import Container
from .utils import PrometheusMiddleware, metrics, setting_otlp
import logging

container = Container()
container.config.from_yaml(os.path.join(
    os.environ['BASEDIR'],
    'core', 'core', 'settings',
    f'{os.environ["EXECFILE"]}.yml'
))
container.wire(packages=[api])

tags_metadata = [
    {
        "name": "Jenkins",
        "description": "Operations with jenkins.",
    },

    {
        "name": "Orchestrator APIs",
        "description": "Post and execute jenkins tasks"
    },
    {
        "name": "Dashboard APIs",
        "description": "For handling data"
    }
]

# REGISTERING ROUTER TO APP
app = FastAPI(
    title=container.config.server.name(),
    description="Orchestrator APIs!",
    version="1.0.0",
    openapi_tags=tags_metadata
)

app.include_router(router, prefix='')
app = VersionedFastAPI(
    app,
    openapi_tags=tags_metadata,
    enable_latest=True
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in container.config.server.backend_cors_orgins()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key="!secret")


@app.get("/")
def main():
    return {"Am I working ??": "Ofcourse, Yes!!"}


def custom_openapi():
    openapi_schema = get_openapi(
        title="Orchestrator APIs!",
        version="1.0.0",
        description="This is a very custom Orchestrator OpenAPI schema",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

#OTLP_ENABLE = os.environ.get("OTLP_ENABLE", True)
#if OTLP_ENABLE:
#    print("OTLP_ENABLE is enabled!")
#    APP_NAME = os.environ.get("APP_NAME", "CHAMP")
#    EXPOSE_PORT = os.environ.get("EXPOSE_PORT", 8082)
#    OTLP_GRPC_ENDPOINT = os.environ.get("OTLP_GRPC_ENDPOINT", "http://tempo:14250")

    # Setting metrics middleware
#    app.add_middleware(PrometheusMiddleware, app_name=APP_NAME, filter_unhandled_paths=True)
#    app.add_route("/metrics", metrics)

    # Setting OpenTelemetry exporter
#    setting_otlp(app, APP_NAME, OTLP_GRPC_ENDPOINT)


#class EndpointFilter(logging.Filter):
    # Uvicorn endpoint access log filter
#    def filter(self, record: logging.LogRecord) -> bool:
#        return record.getMessage().find("GET /metrics") == -1


# Filter out /endpoint
#logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
