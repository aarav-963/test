import os


bind = f"0.0.0.0:{int(os.environ.get('PORT', '10000'))}"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = 4
timeout = 120
accesslog = "-"
errorlog = "-"
