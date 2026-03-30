"""自定义异常"""


class GitSyncError(Exception):
    """基础异常类"""
    pass


class GitOperationError(GitSyncError):
    """Git 操作异常"""
    pass


class RepositoryNotFoundError(GitSyncError):
    """仓库未找到"""
    pass


class RepositoryExistsError(GitSyncError):
    """仓库已存在"""
    pass


class AuthenticationError(GitSyncError):
    """认证失败"""
    pass


class NetworkError(GitSyncError):
    """网络错误"""
    pass


class ConflictError(GitSyncError):
    """冲突错误"""
    pass


class ConfigurationError(GitSyncError):
    """配置错误"""
    pass


class ValidationError(GitSyncError):
    """验证错误"""
    pass
