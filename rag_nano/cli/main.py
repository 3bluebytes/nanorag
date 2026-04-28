from __future__ import annotations

import typer
import uvicorn

from rag_nano.api.app import create_app
from rag_nano.config import Settings

app = typer.Typer()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8089, "--port"),
) -> None:
    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=host, port=port)


if __name__ == "__main__":
    app()
