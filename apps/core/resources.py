from import_export import fields, resources
from import_export.widgets import DateTimeWidget

from .models import College


class CollegeResource(resources.ModelResource):
    created_at = fields.Field(
        attribute="created_at",
        column_name="created_at",
        widget=DateTimeWidget(format="%Y-%m-%d %H:%M:%S"),
        readonly=True,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Dynamic internal cache table dictionary
        self.existing_colleges_cache = {}

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        """
        Executes EXACTLY 1 query to fetch the entire existing directory pool,
        storing it into memory for instant O(1) row evaluations.
        """
        all_colleges = College.objects.all().only("id", "name", "district", "state")
        for college in all_colleges:
            # Create a unique cache string signature
            cache_key = f"{college.name.strip().lower()}|{college.district.strip().lower()}|{college.state.strip().lower()}"
            self.existing_colleges_cache[cache_key] = college

    def get_instance(self, instance_loader, row):
        """
        Intercepts standard slow row database queries and uses the fast local dictionary cache.
        """
        name = str(row.get("name", "")).strip().lower()
        district = str(row.get("district", "")).strip().lower()
        state = str(row.get("state", "")).strip().lower()

        cache_key = f"{name}|{district}|{state}"

        # Instantly yields match out of memory without hitting PostgreSQL
        if cache_key in self.existing_colleges_cache:
            return self.existing_colleges_cache[cache_key]

        return None

    class Meta:
        model = College
        fields = ("id", "name", "district", "state", "created_at")
        export_order = ("id", "name", "district", "state", "created_at")
        import_id_fields = ("name", "district", "state")

        # --- PERFORMANCE OPTIMIZATION TUNES ---

        # 1. Force the engine to append records into a memory cache array
        # instead of running separate INSERT operations for every row.
        use_bulk = True
        batch_size = 2000  # Groups PostgreSQL records in packets of 2000

        # 2. Skips rendering a heavy visual "diff" preview screen for clean rows
        # which heavily reduces memory overhead during major file execution tracking.
        skip_unchanged = True
        report_skipped = False
