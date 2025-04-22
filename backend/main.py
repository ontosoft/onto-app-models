import uvicorn
import logging
from fastapi import FastAPI
from config.settings import Settings, get_settings
from fastapi.middleware.cors import CORSMiddleware
from routers.onto_app_router import router as model_router


settings: Settings = get_settings()

# Configure basic logging
app_logger = logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO,
                 format='%(asctime)s - %(name)s - %(levelname)-2s [%(filename)s:%(lineno)d]  - %(message)s')

 
# Definition of origins
origins = ["*"]
app = FastAPI(debug=settings.DEBUG, title=settings.APP_NAME, version="0.1.0")   


# add CORS middleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(model_router)

if __name__ == "__main__":
    app_logger.info('Info ========= ciao ========= ')
    uvicorn.run( "main:app",port=8089, host='0.0.0.0', reload=False, log_level='debug')