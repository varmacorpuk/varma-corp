import uvicorn

from varma.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("varma.kernel.app:app", host=settings.api_host, port=settings.api_port, reload=False)
