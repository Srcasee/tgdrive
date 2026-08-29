from .identity import hash_stream


class ContentVerificationService:
    """Verify one explicitly streamed Telegram file and promote its Resource."""

    def __init__(self, resource_repository):
        self.resource_repository = resource_repository

    async def verify_file(self, file_id, stream):
        """Consume a caller-supplied complete stream; never fetch or persist it."""
        content_hash = await hash_stream(stream)
        return self.resource_repository.verify_file(file_id, content_hash)
