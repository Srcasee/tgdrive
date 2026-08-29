class CatalogService:
    """Application boundary for browsing and classifying logical Resources."""

    def __init__(self, repository):
        self.repository = repository

    def list_resources(self, page, size, category_id=None):
        return self.repository.list_resources(size, (page - 1) * size, category_id)

    def search(self, query, limit=100, category_id=None):
        return self.repository.search_resources(query, limit, category_id)

    def get(self, resource_id):
        return self.repository.get_resource(resource_id)

    def set_categories(self, resource_id, category_ids):
        return self.repository.set_categories(resource_id, category_ids)
