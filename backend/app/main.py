from fastapi import FastAPI


app = FastAPI(title="seismo-ionomap")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
