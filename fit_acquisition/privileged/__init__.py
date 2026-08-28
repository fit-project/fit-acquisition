"""Linux-only support for narrowly scoped privileged acquisition operations.

Keep this module import-free: Python loads it before the root-side CLI, which must
not initialize Qt or any of the unprivileged application components.
"""
