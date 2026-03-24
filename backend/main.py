from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import financial_router, search_router

app = FastAPI(
    title="SEC Financial Intelligence API",
    description="Query SEC financial statement data across Raw, JSON, and Fact Table storage approaches",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(financial_router.router, prefix="/financial", tags=["Financial Data"])
app.include_router(search_router.router, prefix="/search", tags=["Search"])

@app.get("/")
def root():
    return {"message": "SEC Financial Intelligence API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}