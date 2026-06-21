class JobError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class JobRetryError(JobError):
    pass


class JobCancelError(JobError):
    pass
