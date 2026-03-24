"""
Admin mixins for gate app.
PerPageListMixin: default 10 per page + per-page dropdown (10, 20, 30, 50, 100) in change list.
"""
ADMIN_PER_PAGE_OPTIONS = [10, 20, 30, 50, 100]


class PerPageListMixin:
    """Mixin for ModelAdmin: list_per_page from GET param 'per_page', default 10. Adds dropdown to change list."""
    list_per_page = 10
    change_list_template = 'admin/change_list_with_per_page.html'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        default_per_page = getattr(type(self), 'list_per_page', 10)
        per_page_param = request.GET.get('per_page')
        if per_page_param and per_page_param.isdigit():
            n = int(per_page_param)
            if n in ADMIN_PER_PAGE_OPTIONS:
                self.list_per_page = n
            else:
                self.list_per_page = default_per_page
        else:
            self.list_per_page = default_per_page
        q = request.GET.copy()
        q.pop('p', None)  # admin page param
        q.pop('per_page', None)
        extra_context['admin_per_page_options'] = ADMIN_PER_PAGE_OPTIONS
        extra_context['admin_per_page'] = self.list_per_page
        extra_context['admin_query_base'] = q.urlencode()
        return super().changelist_view(request, extra_context)
