import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.onto_app_router import router as model_router

# Configure basic logging
logging.basicConfig(level=logging.DEBUG,
                 format='%(asctime)s - %(name)s - %(levelname)-2s [%(filename)s:%(lineno)d]  - %(message)s')

 
# Definition of origins
origins = ["*"]
app = FastAPI(debug=True)

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG)
app_logger = logging.getLogger("ontoui_app")
app_logger.setLevel(logging.DEBUG)



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
    logger.debug('Uvicorn ========= ciao ========= ')
    app_logger.info('Info ========= ciao ========= ')
    app_logger.debug('Debug ========= ciao ========= ')
    uvicorn.run( "main:app",port=8089, host='0.0.0.0', reload=True, log_level='debug')