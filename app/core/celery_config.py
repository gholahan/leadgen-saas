task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

timezone = "UTC"
enable_utc = True

task_track_started = True
task_acks_late = True

worker_prefetch_multiplier = 1

result_expires = 3600