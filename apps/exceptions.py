class NotFoundError(Exception):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(f"{resource} not found: {identifier}")
        self.resource = resource
        self.identifier = identifier


class ConflictError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class ForbiddenError(Exception):
    def __init__(self, message: str = "权限不足"):
        super().__init__(message)


class UnauthorizedError(Exception):
    def __init__(self, message: str = "未认证或 token 已过期"):
        super().__init__(message)
