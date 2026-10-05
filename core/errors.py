"""The single exception type raised by the math core.

The core never prints or sends anything; it raises InputError and the app
layer turns it into a friendly {"ok": false, "error": ..., "field": ...} reply.
"""


class InputError(Exception):
    """A user-facing input problem.

    message: friendly explanation shown in the UI error banner
    field:   name of the input field at fault, e.g. "elements" or "relation"
    """

    def __init__(self, message, field):
        super().__init__(message)
        self.message = message
        self.field = field

    def __str__(self):
        return self.message
