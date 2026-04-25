import sys
sys.path.insert(0, 'C:/Users/Abhay/OneDrive/Desktop/Programs/Projects/Arceux/server')

import uvicorn

uvicorn.run(
    "api:app",
    host="127.0.0.1",
    port=8000,
    log_level="info",
    access_log=False
)