import collections


def _normalize_header_name(key):
    return str(key).lower().title()


class Headers(collections.UserDict):
    """
    Dictionary of HTTP headers.

    This IS NOT a standard case insensitive dictionary that most
    HTTP libraries provide.  The header names (keys) are normalized
    to title case during both lookup and storage.  This means that
    the values returned by :meth:`.keys` may differ from the values
    that were used to store the value.

    >>> h = Headers()
    >>> h['header-name'] = 'value'
    >>> list(h.keys())
    ['Header-Name']

    The same normalization is performed when values are retrieved
    so you do not have to be so careful when looking up values.
    You SHOULD be consistent in your code of course.

    >>> h = Headers()
    >>> h['header-name'] = 'value'
    >>> h['Header-Name'], h['header-name'], h['HEADER-NAME']
    ('value', 'value', 'value')

    Unlike :meth:`email.message.Message.__setitem__`, this class
    retains the standard dictionary behavior and always overwrites
    what is there.  If you want to append a new value to a header,
    then use the :meth:`.add_header` method instead of treating
    the instance like a dictionary.

    >>> h = Headers()
    >>> h['header'] = 'first'
    >>> h['header'] = 'second'
    >>> h['header']
    'second'
    >>> h.add_header('header', 2)
    >>> h['header']
    'second,2'

    """

    def __getitem__(self, item):
        return super(Headers, self).__getitem__(_normalize_header_name(item))

    def __setitem__(self, key, value):
        super(Headers, self).__setitem__(_normalize_header_name(key),
                                         str(value))

    def add_header(self, name, value):
        """
        Appends `value` to an existing header.

        :param name: name of the header to assign/append to
        :param value: value to append to the header

        The header name is normalized before retrieving the existing
        value.  If a value exists, then `value` is appended to the
        current value after appending a comma.  This opperation is
        described in :rfc:`7230#section-3.2.2`:

           "a recipient MAY combine multiple header values with the
           same field name into one "field-name: field-value" pair,
           without changing the semantics of the message, by appending
           each subsequent field value to the combined field value in
           order, separated by a comma."

        """
        try:
            self[name] = self[name] + ',' + str(value)
        except KeyError:
            self[name] = value
