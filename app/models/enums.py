from enum import StrEnum


class JobStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class PushStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

