import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from core.models import (
    DiagnosticSession,
    EvidenceItem,
    KnowledgeTopic,
    LearningPath,
    Lesson,
    PracticeScenario,
    Problem,
    ProblemCategory,
    Resource,
    ResourceCategory,
    ResourceContext,
    Workflow,
    WorkflowNode,
)
from core.diagnostics import sync_session
from core.rag import answer_question


def _workflow_engine(workflow):
    if workflow is None:
        return {
            "workflow": {"slug": "", "title": "", "version": "", "problem": ""},
            "nodes": [],
        }
    return {
        "workflow": {
            "slug": workflow.slug,
            "title": workflow.title,
            "version": workflow.version,
            "problem": workflow.problem.name if workflow.problem else "",
        },
        "nodes": [node.as_engine_dict() for node in workflow.nodes.all()],
    }


def _active_path():
    return (
        LearningPath.objects.filter(is_active=True)
        .prefetch_related("levels__lessons")
        .first()
    )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def home(request):
    path = _active_path()
    levels = list(path.levels.all()) if path else []

    return render(
        request,
        "home.html",
        {
            "categories": ProblemCategory.objects.all(),
            "featured_problems": Problem.objects.select_related("category").filter(
                is_featured=True
            )[:6],
            "featured_workflows": Workflow.objects.select_related("problem")
            .prefetch_related("nodes")
            .filter(is_published=True, is_featured=True)[:3],
            "featured_resources": Resource.objects.filter(
                is_featured=True, status=Resource.Status.ACTIVE
            )[:3],
            "learning_path": path,
            "levels": levels,
            "lab_scenario": PracticeScenario.objects.filter(is_active=True).first(),
        },
    )


def workflows(request):
    published = list(
        Workflow.objects.select_related("problem__category")
        .prefetch_related("nodes")
        .filter(is_published=True)
    )

    categories = list(ProblemCategory.objects.all())
    for category in categories:
        category.workflow_count = sum(
            1 for workflow in published if workflow.problem.category_id == category.pk
        )

    return render(
        request,
        "workflows.html",
        {
            "workflows": published,
            "categories": [c for c in categories if c.workflow_count],
            "published_count": len(published),
        },
    )


@ensure_csrf_cookie
def problem_solver(request):
    problem_slug = request.GET.get("problem", "").strip()
    workflow_slug = request.GET.get("workflow", "").strip()

    workflows = (
        Workflow.objects.select_related("problem")
        .prefetch_related("nodes")
        .filter(is_published=True)
    )

    workflow = None
    if workflow_slug:
        workflow = workflows.filter(slug=workflow_slug).first()
    if workflow is None and problem_slug:
        workflow = workflows.filter(problem__slug=problem_slug).first()
        if workflow is None:
            workflow = workflows.filter(slug=problem_slug).first()

    if workflow is None:
        workflow = workflows.first()

    return render(
        request,
        "problem-solver.html",
        {
            "workflow": workflow,
            "engine": _workflow_engine(workflow),
            "problem": workflow.problem if workflow else None,
            "workflows": workflows,
        },
    )


def workflow_detail(request, slug):
    workflow = get_object_or_404(
        Workflow.objects.select_related("problem__category").prefetch_related(
            "nodes"
        ),
        slug=slug,
        is_published=True,
    )

    findings = next(
        (
            node
            for node in workflow.nodes.all()
            if node.kind == WorkflowNode.Kind.FINDINGS
        ),
        None,
    )
    config = findings.config if findings and findings.config else {}
    solution = {
        "intro": config.get("intro", ""),
        "rules": [
            rule.get("text", "")
            for rule in config.get("rules", [])
            if rule.get("text")
        ],
        "fallback": config.get("fallback", ""),
        "unverified": config.get("unverified", []),
        "actions": config.get("actions", []),
    }

    return render(
        request,
        "workflow_detail.html",
        {
            "workflow": workflow,
            "problem": workflow.problem,
            "engine": _workflow_engine(workflow),
            "solution": solution,
        },
    )


def learning(request):
    path = _active_path()
    levels = list(path.levels.all()) if path else []
    for level in levels:
        level.visible_lessons = [
            lesson for lesson in level.lessons.all() if lesson.is_published
        ]

    lessons = [lesson for level in levels for lesson in level.visible_lessons]

    completed_levels = sum(1 for level in levels if level.status == "completed")
    completed_lessons = sum(1 for lesson in lessons if lesson.is_completed)

    next_level = next(
        (level for level in levels if level.status != "completed"),
        levels[-1] if levels else None,
    )

    return render(
        request,
        "learning.html",
        {
            "learning_path": path,
            "levels": levels,
            "next_level": next_level,
            "total_levels": len(levels),
            "completed_levels": completed_levels,
            "level_percent": round(completed_levels / len(levels) * 100) if levels else 0,
            "total_lessons": len(lessons),
            "completed_lessons": completed_lessons,
            "lesson_percent": round(completed_lessons / len(lessons) * 100) if lessons else 0,
        },
    )


def lesson_detail(request, slug):
    lesson = get_object_or_404(
        Lesson.objects.select_related("level__path", "problem"),
        slug=slug,
        is_published=True,
    )
    levels = list(lesson.level.path.levels.all())

    for item in levels:
        item.visible_lessons = [
            sibling for sibling in item.lessons.all() if sibling.is_published
        ]
        item.is_active = item.pk == lesson.level_id

    level = next(item for item in levels if item.pk == lesson.level_id)
    siblings = level.visible_lessons
    try:
        index = next(i for i, sibling in enumerate(siblings) if sibling.pk == lesson.pk)
    except StopIteration:  # pragma: no cover - lesson is always in its own level
        index = 0

    return render(
        request,
        "lesson_detail.html",
        {
            "lesson": lesson,
            "level": level,
            "levels": levels,
            "previous_lesson": siblings[index - 1] if index > 0 else None,
            "next_lesson": siblings[index + 1] if index + 1 < len(siblings) else None,
            "problem": lesson.problem,
        },
    )


def practice_lab(request):
    scenarios = list(
        PracticeScenario.objects.select_related("problem").filter(is_active=True)
    )

    return render(
        request,
        "practice-lab.html",
        {
            "scenarios": scenarios,
        },
    )


def practice_scenario_detail(request, slug):
    scenario = get_object_or_404(
        PracticeScenario.objects.select_related("problem"),
        slug=slug,
        is_active=True,
    )
    siblings = list(
        PracticeScenario.objects.filter(is_active=True).order_by("order", "id")
    )
    try:
        index = next(i for i, item in enumerate(siblings) if item.pk == scenario.pk)
    except StopIteration:  # pragma: no cover - scenario is always in its own query
        index = 0

    return render(
        request,
        "practice_scenario_detail.html",
        {
            "scenario": scenario,
            "previous_scenario": siblings[index - 1] if index > 0 else None,
            "next_scenario": (
                siblings[index + 1] if index + 1 < len(siblings) else None
            ),
        },
    )


def resources(request):
    categories = list(ResourceCategory.objects.all())
    resources = list(Resource.objects.select_related("category"))

    for category in categories:
        category.resource_count = sum(
            1 for resource in resources if resource.category_id == category.pk
        )

    return render(
        request,
        "resources.html",
        {
            "resources": resources,
            "categories": [c for c in categories if c.resource_count],
            "contexts": ResourceContext.objects.all(),
        },
    )


def _suggestion_topics(limit=4):
    return list(
        KnowledgeTopic.objects.exclude(example_question="")
        .filter(is_suggestion=True)
        .order_by("order", "id")[:limit]
    )


def ask(request):
    suggestions = _suggestion_topics(limit=2)

    question = request.GET.get("question", "").strip()
    answer = answer_question(question, log_gap=True, log_question=True) if question else None

    return render(
        request,
        "ask.html",
        {
            "question": question,
            "answer": answer,
            "suggestions": suggestions,
            "is_example": False,
        },
    )


# ---------------------------------------------------------------------------
# JSON endpoints
# ---------------------------------------------------------------------------


@require_GET
def ask_answer(request):
    question = request.GET.get("question", "").strip()

    if not question:
        return JsonResponse(
            {"ok": False, "html": "", "no_match": True, "confidence": "low", "topic": None}
        )

    answer = answer_question(question, log_gap=True, log_question=True)
    template = (
        "partials/ask_no_topic.html"
        if answer["no_match"]
        else "partials/ask_answer.html"
    )
    html = render_to_string(
        template,
        {
            "answer": answer,
            "question": question,
            "suggestions": _suggestion_topics(),
        },
        request=request,
    )

    return JsonResponse(
        {
            "ok": True,
            "html": html,
            "no_match": answer["no_match"],
            "confidence": answer["confidence"],
            "topic": answer["topic"].title if answer.get("topic") else None,
        }
    )


@require_POST
def session_create(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    workflow = None
    workflow_id = payload.get("workflow")
    workflow_slug = payload.get("workflow_slug")

    if workflow_id:
        workflow = Workflow.objects.filter(pk=workflow_id, is_published=True).first()
    if workflow is None and workflow_slug:
        workflow = Workflow.objects.filter(slug=workflow_slug, is_published=True).first()
    if workflow is None:
        workflow = Workflow.objects.filter(is_published=True).first()
    if workflow is None:
        return JsonResponse({"ok": False, "error": "no workflow"}, status=404)

    session = DiagnosticSession.objects.create(
        workflow=workflow,
        workflow_version=workflow.version,
        state=payload.get("state", {}),
    )
    sync_session(session, session.state)

    return JsonResponse(
        {
            "ok": True,
            "token": str(session.token),
            "workflow_slug": workflow.slug,
        }
    )


@require_POST
def session_update(request, token):
    session = get_object_or_404(DiagnosticSession, token=token)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    if "state" in payload:
        session.state = payload["state"]

    status = payload.get("status")
    if status in dict(DiagnosticSession.Status.choices):
        session.status = status

    session.save(update_fields=["state", "status", "updated_at"])
    sync_session(session, session.state)

    return JsonResponse(
        {
            "ok": True,
            "token": str(session.token),
            "status": session.status,
        }
    )


def diagnostic_report(request, token):
    session = get_object_or_404(
        DiagnosticSession.objects.select_related(
            "workflow__problem", "workflow__problem__category"
        ).prefetch_related(
            "answers",
            "evidence",
            "findings",
            "actions",
        ),
        token=token,
    )

    return render(
        request,
        "diagnostic_report.html",
        {
            "session": session,
            "workflow": session.workflow,
            "problem": session.workflow.problem,
            "answers": session.answers.all(),
            "evidence": session.evidence.all(),
            "findings": session.findings.all(),
            "actions": session.actions.all(),
            "verified_evidence": session.evidence.filter(
                source=EvidenceItem.Source.VERIFIED
            ),
            "user_evidence": session.evidence.filter(
                source=EvidenceItem.Source.USER_REPORTED
            ),
        },
    )
