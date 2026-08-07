from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(status.HTTP_404_NOT_FOUND, f"{resource} not found")


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)


class ConflictError(AppException):
    def __init__(self, detail: str = "Conflict"):
        super().__init__(status.HTTP_409_CONFLICT, detail)


class BadRequestError(AppException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)
