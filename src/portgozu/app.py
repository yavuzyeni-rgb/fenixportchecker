from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import Engine
from .paths import static_dir

STATIC = static_dir()
engine = Engine()

app = FastAPI(title="FenixPortChecker", version="0.1.1")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class ScanBody(BaseModel):
    adapter: str = ""
    demo: bool = False
    seconds: float = Field(default=4.0, ge=0.5, le=12.0)


class ListenBody(BaseModel):
    adapter: str = ""
    demo: bool = False
    on: bool = True


class SnmpBody(BaseModel):
    host: str
    community: str = "public"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/state")
def state() -> dict:
    if not engine.adapters and not engine.demo:
        engine.refresh_adapters()
    return engine.snapshot()


@app.post("/api/adapters")
def adapters() -> dict:
    engine.refresh_adapters(force=True)
    return engine.snapshot()


@app.post("/api/scan")
def scan(body: ScanBody) -> dict:
    return engine.scan(body.adapter, body.demo, body.seconds)


@app.post("/api/listen")
def listen(body: ListenBody) -> dict:
    if body.on:
        return engine.start_listen(body.adapter, body.demo)
    engine.stop_listen()
    return engine.snapshot()


@app.post("/api/snmp")
def snmp(body: SnmpBody) -> dict:
    host = body.host.strip()
    if not host:
        raise HTTPException(400, "SNMP adresi gerekli")
    return engine.query_snmp(host, body.community)
