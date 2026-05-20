import os

host=os.getenv("host", "localhost")
name=os.getenv("name", "job_tracker")
user=os.getenv("user", "postgres")
password=os.getenv("password", "postgres")