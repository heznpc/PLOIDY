"""Exception hierarchy for Ploidy.

All Ploidy-specific exceptions inherit from PloidyError,
making it easy to catch any Ploidy error at the boundary.
"""


class PloidyError(Exception):
    """Base exception for all Ploidy errors."""


class ProtocolError(PloidyError):
    """Invalid state transition in the debate protocol.

    Raised when a phase transition is attempted that violates
    the protocol's state machine rules.
    """


class ConvergenceError(PloidyError):
    """Convergence analysis failure.

    Raised when the convergence engine cannot produce a result,
    e.g. because the debate has not reached the CONVERGENCE phase.
    """


class SessionError(PloidyError):
    """Session management error.

    Raised for issues with session creation, lookup, or
    context injection.
    """
