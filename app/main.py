from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers import lectures

app = FastAPI(
    title="Adaptive AI Exam Portal",
    description="An AI-driven examination portal with adaptive testing and proctoring",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# include routers
app.include_router(lectures.router, prefix="/lectures", tags=["lectures"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main landing page."""
    try:
        with open("templates/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Welcome to Adaptive AI Exam Portal</h1><p>Frontend coming soon...</p>")

@app.get("/exam", response_class=HTMLResponse)
async def exam_page():
    """Serve the exam taking page."""
    try:
        with open("templates/exam.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Exam Page</h1><p>Frontend coming soon...</p>")

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page():
    """Serve the analytics dashboard page."""
    try:
        with open("templates/analytics.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Analytics Dashboard</h1><p>Frontend coming soon...</p>")

@app.get("/results", response_class=HTMLResponse)
async def results_page():
    """Serve the results page."""
    try:
        with open("templates/results.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Results Page</h1><p>Frontend coming soon...</p>")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Adaptive AI Exam Portal is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
