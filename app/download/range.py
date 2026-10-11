class InvalidRange(ValueError):
    """Raised when an HTTP Range header is malformed or unsatisfiable."""


def parse_single_range(value: str | None, size: int) -> tuple[int, int, bool]:
    """Return inclusive (start, end, is_partial) for one byte range."""
    if size < 0:
        raise InvalidRange("negative resource size")
    if value is None:
        if size == 0:
            raise InvalidRange("empty resource has no byte range")
        return 0, size - 1, False
    if not value.startswith("bytes="):
        raise InvalidRange("unsupported range unit")
    spec = value[6:].strip()
    if not spec or "," in spec:
        raise InvalidRange("multiple or empty ranges are unsupported")
    start_text, sep, end_text = spec.partition("-")
    if not sep or (not start_text and not end_text):
        raise InvalidRange("malformed range")
    try:
        if start_text:
            start = int(start_text)
            if start < 0 or start >= size:
                raise InvalidRange("range starts beyond resource")
            end = size - 1 if not end_text else int(end_text)
            if end < start or end < 0:
                raise InvalidRange("invalid range end")
            return start, min(end, size - 1), True
        suffix = int(end_text)
        if suffix <= 0 or size == 0:
            raise InvalidRange("invalid suffix range")
        return max(0, size - suffix), size - 1, True
    except (TypeError, ValueError) as exc:
        raise InvalidRange("malformed numeric range") from exc
