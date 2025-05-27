from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/charts")
def get_charts():
    # Return dummy chart data (can be replaced with real ML/DB logic)
    return [
        {
            "id": 1,
            "type": "bar",
            "title": "Monthly Data Overview (from Python)",
            "data": [
                {"name": "Jan", "uv": 410, "pv": 250, "amt": 250},
                {"name": "Feb", "uv": 310, "pv": 139, "amt": 221},
                {"name": "Mar", "uv": 210, "pv": 980, "amt": 229},
                {"name": "Apr", "uv": 288, "pv": 390, "amt": 200},
                {"name": "May", "uv": 199, "pv": 480, "amt": 218},
                {"name": "Jun", "uv": 249, "pv": 380, "amt": 250},
                {"name": "Jul", "uv": 359, "pv": 430, "amt": 210},
                {"name": "Aug", "uv": 410, "pv": 240, "amt": 240},
                {"name": "Sep", "uv": 310, "pv": 139, "amt": 221},
                {"name": "Oct", "uv": 210, "pv": 980, "amt": 229},
                {"name": "Nov", "uv": 288, "pv": 390, "amt": 200},
                {"name": "Dec", "uv": 199, "pv": 480, "amt": 218}
            ]
        },
        {
            "id": 2,
            "type": "line",
            "title": "Email Traffic by Month (from Python)",
            "data": [
                {"name": "Jan", "sent": 410, "received": 250},
                {"name": "Feb", "sent": 310, "received": 139},
                {"name": "Mar", "sent": 210, "received": 980},
                {"name": "Apr", "sent": 288, "received": 390},
                {"name": "May", "sent": 199, "received": 480},
                {"name": "Jun", "sent": 249, "received": 380},
                {"name": "Jul", "sent": 359, "received": 430},
                {"name": "Aug", "sent": 410, "received": 240},
                {"name": "Sep", "sent": 310, "received": 139},
                {"name": "Oct", "sent": 210, "received": 980},
                {"name": "Nov", "sent": 288, "received": 390},
                {"name": "Dec", "sent": 199, "received": 480}
            ]
        }
    ]