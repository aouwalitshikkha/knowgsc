import uuid

from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Tone(models.TextChoices):
    BRAND = "brand", "Brand"
    WARN = "warn", "Warning"
    DANGER = "danger", "Danger"
    OK = "ok", "Success"
    NEUTRAL = "neutral", "Neutral"


class ToneMixin(models.Model):
    """Shared helper so templates can use semantic tones instead of raw CSS."""

    TONE_SURFACES = {
        "brand": "bg-brand-50 text-brand-600 ring-brand-200",
        "warn": "bg-amber-50 text-amber-600 ring-amber-200",
        "danger": "bg-rose-50 text-rose-600 ring-rose-200",
        "ok": "bg-emerald-50 text-emerald-600 ring-emerald-200",
        "neutral": "bg-slate-100 text-slate-500 ring-slate-200",
    }

    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.NEUTRAL)

    class Meta:
        abstract = True

    @property
    def chip_class(self):
        return f"chip-{self.tone}"

    @property
    def icon_class(self):
        return self.TONE_SURFACES.get(self.tone, self.TONE_SURFACES["neutral"])


class ProblemCategory(ToneMixin):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "problem categories"

    def __str__(self):
        return self.name


class Problem(models.Model):
    category = models.ForeignKey(ProblemCategory, on_delete=models.PROTECT, related_name="problems")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    summary = models.TextField(help_text="Short card description.")
    detail = models.TextField(blank=True, help_text="Optional long description.")
    badge = models.CharField(max_length=40, blank=True, help_text="Small label shown on the card.")
    is_featured = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f"{reverse('problem_solver')}?problem={self.slug}"


class Workflow(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="workflows")
    slug = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=160)
    version = models.CharField(max_length=20, default="1.0")
    summary = models.TextField()
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return f"{self.title} (v{self.version})"

    @property
    def published_label(self):
        return f"Published · v{self.version}"

    @property
    def node_kinds(self):
        seen = []
        for node in self.nodes.all():
            label = node.get_kind_display()
            if label not in seen:
                seen.append(label)
        return seen

    def get_absolute_url(self):
        return reverse("workflow_detail", kwargs={"slug": self.slug})


class WorkflowNode(models.Model):
    class Kind(models.TextChoices):
        QUESTION = "question", "Question"
        FINDINGS = "findings", "Findings"
        VERIFY = "verify", "Verification"

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="nodes")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    key = models.SlugField(
        max_length=60,
        blank=True,
        help_text="Stable identifier used by the diagnostic engine (questions only).",
    )
    title = models.CharField(max_length=160)
    prompt = models.TextField(blank=True, help_text="Question text (questions only).")
    hint = models.TextField(blank=True, help_text="'How to check' guidance.")
    options = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Answer labels, or {label, next} objects for branching questions. "
            "'next' is the stable key of the node to open."
        ),
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Node routing, findings rules, verification notes and other settings. "
            "Use 'next' for a default branch target."
        ),
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.workflow.slug} · {self.title}"

    def as_engine_dict(self):
        options = []
        for option in self.options:
            if isinstance(option, dict):
                options.append(
                    {
                        "label": option.get("label", ""),
                        "next": option.get("next", ""),
                    }
                )
            else:
                options.append({"label": str(option), "next": ""})

        config = self.config if isinstance(self.config, dict) else {}
        return {
            "id": self.key or f"node-{self.pk}",
            "type": self.kind,
            "title": self.title,
            "question": self.prompt,
            "hint": self.hint,
            "options": options,
            "next": config.get("next", ""),
            "config": config,
        }


class DiagnosticSession(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="sessions")
    workflow_version = models.CharField(max_length=20, blank=True)
    state = models.JSONField(default=dict, blank=True)
    report = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Session {self.token} · {self.workflow}"


class DiagnosticAnswer(models.Model):
    session = models.ForeignKey(
        DiagnosticSession, on_delete=models.CASCADE, related_name="answers"
    )
    node_key = models.CharField(max_length=80)
    question = models.CharField(max_length=200)
    answer = models.TextField()
    is_skipped = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.node_key}: {self.answer[:60]}"


class EvidenceItem(models.Model):
    class Source(models.TextChoices):
        USER_REPORTED = "user_reported", "User reported"
        VERIFIED = "verified", "Verified"

    session = models.ForeignKey(
        DiagnosticSession, on_delete=models.CASCADE, related_name="evidence"
    )
    node_key = models.CharField(max_length=80, blank=True)
    label = models.CharField(max_length=200)
    value = models.TextField()
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.USER_REPORTED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.label}: {self.value[:60]}"


class DiagnosticFinding(models.Model):
    class Confidence(models.TextChoices):
        HYPOTHESIS = "hypothesis", "Hypothesis"
        CONFIRMED = "confirmed", "Confirmed"

    session = models.ForeignKey(
        DiagnosticSession, on_delete=models.CASCADE, related_name="findings"
    )
    title = models.CharField(max_length=200)
    explanation = models.TextField(blank=True)
    confidence = models.CharField(
        max_length=20, choices=Confidence.choices, default=Confidence.HYPOTHESIS
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class RecommendedAction(models.Model):
    session = models.ForeignKey(
        DiagnosticSession, on_delete=models.CASCADE, related_name="actions"
    )
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:80]


class ResourceCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "resource categories"

    def __str__(self):
        return self.name


class Resource(ToneMixin):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FUTURE = "future", "Future"

    category = models.ForeignKey(ResourceCategory, on_delete=models.PROTECT, related_name="resources")
    title = models.CharField(max_length=160)
    url = models.URLField(blank=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    icon = models.CharField(
        max_length=24,
        default="book",
        help_text="Icon key: book, help, bolt, rich, url, api.",
    )
    tags = models.JSONField(default=list, blank=True)
    checked_on = models.DateField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    @property
    def is_available(self):
        return self.status == self.Status.ACTIVE


class ResourceContext(ToneMixin):
    category = models.ForeignKey(
        ResourceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contexts",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    link_url = models.URLField()
    link_label = models.CharField(max_length=120, default="Open resources")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class LearningPath(models.Model):
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title


class LearningLevel(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        IN_PROGRESS = "in_progress", "In progress"
        NOT_STARTED = "not_started", "Not started"
        LOCKED = "locked", "Locked"

    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name="levels")
    title = models.CharField(max_length=160)
    subtitle = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    @property
    def number(self):
        return self.order

    @property
    def chip_class(self):
        return {
            self.Status.COMPLETED: "chip-ok",
            self.Status.IN_PROGRESS: "chip-warn",
            self.Status.NOT_STARTED: "chip-neutral",
            self.Status.LOCKED: "chip-neutral",
        }[self.status]

    @property
    def status_label(self):
        return self.get_status_display()

    @property
    def is_current(self):
        return self.status == self.Status.IN_PROGRESS

    @property
    def short_title(self):
        _, _, remainder = self.title.partition("—")
        return remainder.strip() or self.title


class Lesson(models.Model):
    level = models.ForeignKey(LearningLevel, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True,
        help_text="Used in the lesson URL. Leave blank to generate it from the title.",
    )
    description = models.TextField(blank=True, help_text="Short summary shown on the roadmap.")
    body = RichTextUploadingField(
        blank=True,
        help_text="Full tutorial. Add headings, screenshots, tables and embedded media.",
    )
    objectives = models.JSONField(
        default=list,
        blank=True,
        help_text="List of learning objectives shown at the top of the lesson.",
    )
    key_takeaways = models.JSONField(
        default=list,
        blank=True,
        help_text="List of takeaways shown at the end of the lesson.",
    )
    duration_minutes = models.PositiveIntegerField(default=10)
    is_completed = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    problem = models.ForeignKey(
        Problem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
        help_text="Optional problem workflow linked from the lesson.",
    )
    order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:180] or "lesson"
            candidate = base
            suffix = 2
            siblings = Lesson.objects.exclude(pk=self.pk)
            while siblings.filter(slug=candidate).exists():
                candidate = f"{base}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("lesson_detail", kwargs={"slug": self.slug})


class PracticeScenario(ToneMixin):
    slug = models.SlugField(max_length=80, unique=True)
    problem = models.ForeignKey(
        Problem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenarios",
        help_text="Workflow linked from the 'Run the workflow' action.",
    )
    title = models.CharField(max_length=120)
    category_label = models.CharField(max_length=60)
    issue = models.CharField(max_length=120)
    summary = models.CharField(max_length=200)
    description = models.TextField(
        blank=True,
        help_text="Scenario briefing shown above the simulated report.",
    )
    report_title = models.CharField(max_length=160, default="Indexing Report — Fictional Property")
    metrics = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {label, value, delta, note, tone} metric cards.",
    )
    urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of URL Inspection rows.",
    )
    sitemap = models.JSONField(default=dict, blank=True)
    page_experience = models.JSONField(default=dict, blank=True)
    checklist = models.JSONField(default=list, blank=True)
    expected_cause = models.TextField(blank=True)
    solution = models.TextField(
        blank=True,
        help_text="Worked explanation of the fix.",
    )
    solution_steps = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of fix steps.",
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("practice_scenario_detail", kwargs={"slug": self.slug})


class KnowledgeTopic(models.Model):
    slug = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=160)
    problem = models.ForeignKey(
        Problem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="topics",
        help_text="Problem used for the 'investigate' call to action.",
    )
    example_question = models.CharField(max_length=240, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    explanation = models.TextField(help_text="Short introduction shown first.")
    definition = models.TextField(blank=True)
    causes = models.JSONField(default=list, blank=True, help_text="List of hypothesis strings.")
    articles = models.JSONField(default=list, blank=True, help_text="List of {title, description}.")
    external_resources = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {title, url}.",
    )
    is_default = models.BooleanField(default=False)
    is_suggestion = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class KnowledgeGap(models.Model):
    question = models.CharField(max_length=500)
    matched_topic = models.ForeignKey(
        KnowledgeTopic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gaps",
    )
    retrieved_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question[:60]


class QuestionLog(models.Model):
    """Every question asked of the assistant, answered or not."""

    class Confidence(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        NONE = "none", "No match"

    question = models.CharField(max_length=500)
    matched_topic = models.ForeignKey(
        KnowledgeTopic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="question_logs",
    )
    confidence = models.CharField(
        max_length=20, choices=Confidence.choices, blank=True
    )
    no_match = models.BooleanField(default=False)
    retrieved_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question[:60]


class KnowledgeDocument(models.Model):
    class DocType(models.TextChoices):
        ARTICLE = "article", "Article"
        GUIDE = "guide", "Guide"
        GOOGLE = "google", "Google documentation"
        FAQ = "faq", "FAQ"
        INTERNAL = "internal", "Internal learning"

    class ReviewStatus(models.TextChoices):
        APPROVED = "approved", "Approved"
        DRAFT = "draft", "Draft"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    doc_type = models.CharField(max_length=20, choices=DocType.choices, default=DocType.ARTICLE)
    url = models.URLField(blank=True)
    summary = models.TextField(blank=True)
    body = models.TextField(help_text="Plain text or light Markdown. Use '## Heading' for sections.")
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.APPROVED,
    )
    reviewed_on = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    @property
    def is_approved(self):
        return self.review_status == self.ReviewStatus.APPROVED


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks")
    order = models.PositiveIntegerField(default=0)
    heading = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    embedding = models.JSONField(null=True, blank=True)
    embedding_model = models.CharField(max_length=120, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_id", "order", "id"]

    def __str__(self):
        return f"{self.document.title} · {self.heading or 'section'}"


class SearchTerm(models.Model):
    term = models.CharField(max_length=80, unique=True)
    misspellings = models.JSONField(default=list, blank=True)
    synonyms = models.JSONField(default=list, blank=True)
    category = models.ForeignKey(
        ProblemCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_terms",
    )

    class Meta:
        ordering = ["term"]

    def __str__(self):
        return self.term
