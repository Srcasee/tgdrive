from .identity import hash_stream


class ContentVerificationService:
    """Promote an indexed Resource to verified identity from an explicit full stream."""

    def __init__(self, resource_repository):
        self.resource_repository = resource_repository

    async def verify(self, resource_id, stream):
        """Consume a caller-supplied complete stream; never fetch or persist it."""
        content_hash = await hash_stream(stream)
        return self.resource_repository.verify(resource_id, content_hash)
