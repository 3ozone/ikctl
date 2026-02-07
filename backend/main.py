""" Archivo principal de la aplicación FastAPI para ikctl API."""
from fastapi import FastAPI

app = FastAPI(
    title="ikctl API",
    description="API REST para gestionar servidores remotos e instalar aplicaciones mediante SSH",
    version="1.0.0"
)


@app.get("/")
def read_root():
    """Endpoint de prueba"""
    return {"message": "Hello World"}


@app.get("/health")
def health_check():
    """Endpoint de health check"""
    return {"status": "ok"}
