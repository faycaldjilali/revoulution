from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.rout import router

app = FastAPI(title="BOAMP Dashboard", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
