from fastapi import FastAPI

app = FastAPI()
@app.get("/")
async def root():
    return {"mensaje": "¡Bienvenido a la API con FastAPI!"}


