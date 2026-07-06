import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from k_commerce_agent.config import settings
from k_commerce_agent.mcp_client import ensure_default_mcp_server
from k_commerce_agent.routes.chat import router
from k_commerce_agent.routes.mcp import router as mcp_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_default_mcp_server()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="K-Commerce Agent", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(mcp_router)
    return app


app = create_app()


def main() -> None:
    uvicorn.run(
        "k_commerce_agent.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
