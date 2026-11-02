import csv

from django.contrib import admin, messages
from django.http import HttpResponse

from core.models import (
    DiagnosticAnswer,
    DiagnosticFinding,
    DiagnosticSession,
    EvidenceItem,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeGap,
    KnowledgeTopic,
    LearningLevel,
    LearningPath,
    Lesson,
    PracticeScenario,
    Problem,
    ProblemCategory,
    QuestionLog,
    RecommendedAction,
    Resource,
    ResourceCategory,
    ResourceContext,
    SearchTerm,
    Workflow,
    WorkflowNode,
)
from core.diagnostics import validate_workflow
from core.rag import reindex_all, reindex_document


class WorkflowNodeInline(admin.TabularInline):
    model = WorkflowNode
    extra = 0
    fields = ("order", "kind", "key", "title", "prompt", "hint", "options", "config")


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("title", "problem", "version", "is_published", "is_featured", "order")
    list_filter = ("is_published", "is_featured", "problem__category")
    search_fields = ("title", "slug", "problem__name")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [WorkflowNodeInline]
    actions = ["validate_workflows"]

    @admin.action(description="Validate workflow branches")
    def validate_workflows(self, request, queryset):
        for workflow in queryset:
            errors = validate_workflow(workflow)
            if errors:
                self.message_user(
                    request,
                    f"{workflow.title}: " + " ".join(errors),
                    messages.ERROR,
                )
            else:
                self.message_user(
                    request,
                    f"{workflow.title}: workflow definition is valid.",
                    messages.SUCCESS,
                )


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = (
        "order",
        "title",
        "slug",
        "description",
        "duration_minutes",
        "problem",
        "is_completed",
        "is_published",
    )
    show_change_link = True


@admin.register(LearningLevel)
class LearningLevelAdmin(admin.ModelAdmin):
    list_display = ("title", "path", "status", "order")
    list_filter = ("status", "path")
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "level",
        "duration_minutes",
        "is_published",
        "is_completed",
        "order",
        "updated_at",
    )
    list_filter = ("is_published", "is_completed", "level__path", "level")
    search_fields = ("title", "slug", "description", "body")
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = ("level",)
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "Lesson details",
            {
                "fields": (
                    "level",
                    "title",
                    "slug",
                    "description",
                    "duration_minutes",
                    "problem",
                    "order",
                    "is_completed",
                    "is_published",
                    "updated_at",
                )
            },
        ),
        (
            "Tutorial content",
            {
                "fields": ("objectives", "body", "key_takeaways"),
                "description": (
                    "Use the editor to add headings, screenshots, tables and embedded "
                    "media. Images are uploaded to the media library."
                ),
            },
        ),
    )


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_featured", "order")
    list_filter = ("category", "is_featured")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ProblemCategory)
class ProblemCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tone", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "is_featured", "order")
    list_filter = ("status", "category", "is_featured")
    search_fields = ("title", "description")


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ResourceContext)
class ResourceContextAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "tone", "order")
    list_filter = ("category", "tone")


@admin.register(PracticeScenario)
class PracticeScenarioAdmin(admin.ModelAdmin):
    list_display = ("title", "category_label", "problem", "tone", "is_active", "order")
    list_filter = ("is_active", "tone")
    search_fields = ("title", "summary", "issue")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (
            "Scenario",
            {
                "fields": (
                    "slug",
                    "problem",
                    "title",
                    "category_label",
                    "issue",
                    "summary",
                    "description",
                    "tone",
                )
            },
        ),
        (
            "Simulated report",
            {
                "fields": (
                    "report_title",
                    "metrics",
                    "urls",
                    "sitemap",
                    "page_experience",
                )
            },
        ),
        (
            "Practice and solution",
            {
                "fields": (
                    "checklist",
                    "expected_cause",
                    "solution",
                    "solution_steps",
                )
            },
        ),
        ("Publishing", {"fields": ("is_active", "order")}),
    )


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active")


@admin.register(KnowledgeTopic)
class KnowledgeTopicAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "problem", "is_default", "is_suggestion", "order")
    list_filter = ("is_default", "is_suggestion")
    search_fields = ("title", "keywords", "example_question")
    prepopulated_fields = {"slug": ("title",)}


class KnowledgeChunkInline(admin.TabularInline):
    model = KnowledgeChunk
    extra = 0
    can_delete = False
    fields = ("order", "heading", "content", "embedding_model")
    readonly_fields = ("order", "heading", "content", "embedding_model")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "doc_type", "review_status", "is_published", "reviewed_on", "updated_at")
    list_filter = ("doc_type", "review_status", "is_published")
    search_fields = ("title", "slug", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [KnowledgeChunkInline]
    actions = ["reindex_documents"]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        reindex_document(form.instance)

    @admin.action(description="Rebuild chunks and retrieval index")
    def reindex_documents(self, request, queryset):
        total = reindex_all()
        self.message_user(
            request,
            f"Rebuilt {total} chunks across published, approved documents.",
            messages.SUCCESS,
        )


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "order", "heading", "embedding_model", "updated_at")
    list_filter = ("document", "embedding_model")
    search_fields = ("heading", "content", "document__title")


@admin.register(SearchTerm)
class SearchTermAdmin(admin.ModelAdmin):
    list_display = ("term", "category")
    list_filter = ("category",)
    search_fields = ("term",)


@admin.register(KnowledgeGap)
class KnowledgeGapAdmin(admin.ModelAdmin):
    list_display = ("question", "matched_topic", "retrieved_count", "created_at")
    list_filter = ("matched_topic",)
    search_fields = ("question",)
    readonly_fields = ("created_at",)


@admin.register(QuestionLog)
class QuestionLogAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "matched_topic",
        "confidence",
        "no_match",
        "retrieved_count",
        "created_at",
    )
    list_filter = ("no_match", "confidence", "matched_topic")
    search_fields = ("question",)
    date_hierarchy = "created_at"
    list_per_page = 50
    readonly_fields = (
        "question",
        "matched_topic",
        "confidence",
        "no_match",
        "retrieved_count",
        "created_at",
    )
    actions = ["export_csv"]

    @admin.action(description="Export selected questions to CSV")
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="knowgsc-questions.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            [
                "question",
                "matched_topic",
                "confidence",
                "no_match",
                "retrieved_count",
                "created_at",
            ]
        )
        for item in queryset.select_related("matched_topic"):
            writer.writerow(
                [
                    item.question,
                    item.matched_topic.title if item.matched_topic else "",
                    item.get_confidence_display(),
                    item.no_match,
                    item.retrieved_count,
                    item.created_at.isoformat(),
                ]
            )
        return response


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class DiagnosticAnswerInline(ReadOnlyInline):
    model = DiagnosticAnswer
    fields = ("node_key", "question", "answer", "is_skipped", "is_verified")
    readonly_fields = fields


class EvidenceItemInline(ReadOnlyInline):
    model = EvidenceItem
    fields = ("label", "value", "source")
    readonly_fields = fields


class DiagnosticFindingInline(ReadOnlyInline):
    model = DiagnosticFinding
    fields = ("order", "title", "confidence")
    readonly_fields = fields


class RecommendedActionInline(ReadOnlyInline):
    model = RecommendedAction
    fields = ("order", "text", "is_completed")
    readonly_fields = fields


@admin.register(DiagnosticSession)
class DiagnosticSessionAdmin(admin.ModelAdmin):
    list_display = (
        "token",
        "workflow",
        "status",
        "workflow_version",
        "completed_at",
        "updated_at",
    )
    list_filter = ("status", "workflow")
    search_fields = ("token", "workflow__title")
    list_select_related = ("workflow",)
    readonly_fields = (
        "token",
        "workflow_version",
        "state",
        "report",
        "created_at",
        "completed_at",
        "updated_at",
    )
    inlines = [
        DiagnosticAnswerInline,
        EvidenceItemInline,
        DiagnosticFindingInline,
        RecommendedActionInline,
    ]

