from pipeline.config import cors_origins, validate_admin_settings

# Validate startup configuration before importing routes or constructing the app.
origins = cors_origins()
validate_admin_settings()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers.api import router
from backend.app.routers.explorer import router as explorer_router

app = FastAPI(title="Fire Activity Explorer", version="1.0.0", description="Sensor-separated NASA hotspot analytics. Observations are not wildfire incidents.")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET'], allow_headers=['Content-Type'])
app.include_router(router)
app.include_router(explorer_router)

@app.exception_handler(Exception)
async def unexpected_error(request, error):
    # Avoid serializing internal paths or credential-bearing exception messages.
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500,content={"detail":"Internal processing error; review data integrity and server configuration"})
