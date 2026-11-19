"""Share a small provider-call limit so ordinary pages keep a free server thread."""

from threading import BoundedSemaphore

GENERATION_SLOTS = BoundedSemaphore(2)
