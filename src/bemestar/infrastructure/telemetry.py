from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "bemestar_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram("bemestar_http_request_duration_seconds", "HTTP request latency", ["path"])
INGESTION_RECEIVED = Counter(
    "bemestar_ingestion_received_total", "HAE ingestion requests", ["stream"]
)
INGESTION_PROCESSED = Counter(
    "bemestar_ingestion_processed_total", "Processed HAE ingestion requests", ["status"]
)
INGESTION_PENDING = Gauge("bemestar_ingestion_pending", "Pending ingestion jobs")
