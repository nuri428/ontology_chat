import typer
from api.config import settings

app = typer.Typer(help="ontology_chat CLI")

@app.command()
def info():
    """프로젝트/환경 정보 출력"""
    typer.echo(f"ENV={settings.app_env} HOST={settings.app_host} PORT={settings.app_port}")

@app.command()
def hello(name: str = "world"):
    typer.echo(f"Hello, {name}!")

if __name__ == "__main__":
    app()
