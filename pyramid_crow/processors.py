from functools import partial

from raven._compat import (
    string_types,
    binary_type,
)
from raven.processors import SanitizePasswordsProcessor
from raven.utils import varmap


class PyramidSanitizePasswordsProcessor(SanitizePasswordsProcessor):
    """Do some extra sanitization to pick up places where pyramid tends to
    leak passwords through"""

    def sensitive_repr_filter(self, key, value):
        for field in self.FIELDS:
            if isinstance(value, string_types) and field + '=' in value:
                return '[Filtered]'

        return value

    def filter_stacktrace(self, data):
        """Filter out any local variables that contain sensitive-looking
        patterns in their repr()s"""
        super(PyramidSanitizePasswordsProcessor, self).filter_stacktrace(data)
        for frame in data.get('frames', []):
            if 'vars' not in frame:
                continue

            frame['vars'] = varmap(self.sensitive_repr_filter, frame['vars'])

    def filter_http(self, data):
        """Also descend into env, headers looking for keyval-ish strings"""
        super(PyramidSanitizePasswordsProcessor, self).filter_http(data)
        for n in ('headers', 'env', 'data'):
            if isinstance(data.get(n), dict):
                data[n] = varmap(
                    partial(self.vm_sanitize_keyval, delimiter='&'),
                    data[n],
                )
            elif isinstance(data.get(n), binary_type):
                data[n] = self.sensitive_repr_filter(
                    n, data.get(n).decode('utf8')
                ).encode('utf8')

    def vm_sanitize_keyval(self, key, keyval, delimiter):
        """varmap-friendly way to call _sanitize_keyvals

        Also handles mixed types in env"""
        if isinstance(keyval, string_types):
            return self._sanitize_keyvals(keyval, delimiter)
        else:
            return keyval
