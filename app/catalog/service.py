class CatalogService:
    """Application boundary for browsing and classifying logical Resources."""

    def __init__(self, repository):
        self.repository = repository

    def list_resources(self, page, size, category_id=None, sort="id", order="desc", account_id=None, chat_id=None, topic_id=None):
        return self.repository.list_resources(size, (page - 1) * size, category_id, sort, order, account_id, chat_id, topic_id)

    def search(self, query, limit=100, category_id=None, account_id=None, chat_id=None, topic_id=None):
        return self.repository.search_resources(query, limit, category_id, account_id, chat_id, topic_id)

    def get_tree(self):
        return self.repository.get_resource_tree()

    def get(self, resource_id):
        return self.repository.get_resource(resource_id)

    # Manual category assignment is disabled for now; retain the original implementation as a comment.
    # def set_categories(self, resource_id, category_ids):
    #     return self.repository.set_categories(resource_id, category_ids)
