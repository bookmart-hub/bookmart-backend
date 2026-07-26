from rest_framework.pagination import PageNumberPagination


class NearbyListingPagination(PageNumberPagination):
    """Pagination for the nearby listings endpoint."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

