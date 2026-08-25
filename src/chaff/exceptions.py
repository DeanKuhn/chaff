class ChaffError(Exception):
    pass


class FlowChangedError(ChaffError):
    pass


class UsernameConflictError(ChaffError):
    pass


class AccountSuspendedError(ChaffError):
    pass


class VerificationRequiredError(ChaffError):
    pass
