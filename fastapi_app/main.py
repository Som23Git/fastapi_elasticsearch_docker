import logging
import json
from fastapi import FastAPI, Request
from elasticsearch import Elasticsearch
from datetime import datetime
import os

app = FastAPI()

# Elasticsearch client (force compatibility header if needed)
es = Elasticsearch("http://elasticsearch:9200", headers={"Accept": "application/vnd.elasticsearch+json; compatible-with=8"})

# Ensure log directory exists
os.makedirs("logs", exist_ok=True)

# JSON formatter for all log handlers
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# Setup logger
logger = logging.getLogger("fastapi_logger")

logger.setLevel(logging.INFO)

# Console handler (stdout)
console_handler = logging.StreamHandler()
console_handler.setFormatter(JsonFormatter())
logger.addHandler(console_handler)

# File handler (logs/app.log)
file_handler = logging.FileHandler("logs/app.log")
file_handler.setFormatter(JsonFormatter())
logger.addHandler(file_handler)

# Elasticsearch handler
class ElasticsearchHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        try:
            es.index(index="fastapi-logs", document=json.loads(log_entry))
        except Exception as e:
            # Avoid crashing the app if Elasticsearch is down
            print(f"Elasticsearch logging failed: {e}")

es_handler = ElasticsearchHandler()
es_handler.setFormatter(JsonFormatter())
logger.addHandler(es_handler)

# FastAPI middleware to log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {"message": "Hello from FastAPI with logging"}

@app.get("/error")
def raise_error():
    try:
        1 / 0
    except Exception:
        logger.exception("An error occurred")
    return {"message": "Error logged to Elasticsearch and file"}