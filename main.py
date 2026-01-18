from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import connect_db, disconnect_db
from routers import auth, groups, expenses, receipts


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="ChiaTien API",
    description="Expense sharing backend with PaddleOCR receipt scanning",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(groups.router, prefix="/api/groups", tags=["groups"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["expenses"])
app.include_router(receipts.router, prefix="/api/receipts", tags=["receipts"])


@app.get("/")
async def root():
    return {"message": "ChiaTien API is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
