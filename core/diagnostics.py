"""Deterministic diagnostic-engine helpers.

The browser owns the step-by-step interaction, but the server is the
authoritative place where answers become structured evidence, findings and
recommended actions. This keeps a saved report reproducible from the workflow
definition and the recorded session state.
"""

from django.utils import timezone

from core.models import (
    DiagnosticAnswer,
    DiagnosticFinding,
    DiagnosticSession,
    EvidenceItem,
    RecommendedAction,
    WorkflowNode,
)


def nodes_by_id(workflow):
    return {
        node.key or f"node-{node.pk}": node
        for node in workflow.nodes.all()
    }


def findings_node(workflow):
    return (
        workflow.nodes.filter(kind=WorkflowNode.Kind.FINDINGS)
        .order_by("order", "id")
        .first()
    )


def verify_node(workflow):
    return (
        workflow.nodes.filter(kind=WorkflowNode.Kind.VERIFY)
        .order_by("order", "id")
        .first()
    )


def evaluate_findings(workflow, answers):
    """Return hypothesis texts whose rule conditions are all satisfied."""

    node = findings_node(workflow)
    if node is None:
        return []

    config = node.config or {}
    matched = []
    for rule in config.get("rules", []):
        conditions = rule.get("when", {})
        if conditions and all(
            answers.get(key) == value for key, value in conditions.items()
        ):
            text = (rule.get("text") or "").strip()
            if text:
                matched.append(text)

    if not matched:
        fallback = (config.get("fallback") or "").strip()
        if fallback:
            matched.append(fallback)

    return matched


def sync_session(session, state):
    """Replace the session's structured records from its latest engine state."""

    state = state or {}
    answers = state.get("answers", {}) or {}
    skipped = state.get("skipped", {}) or {}
    verified = state.get("verified", {}) or {}
    workflow = session.workflow
    nodes = nodes_by_id(workflow)

    session.answers.all().delete()
    session.evidence.all().delete()
    session.findings.all().delete()
    session.actions.all().delete()

    for node_key, value in answers.items():
        node = nodes.get(node_key)
        text = str(value or "").strip()
        if node is None or not text:
            continue

        is_skipped = bool(skipped.get(node_key))
        is_verified = bool(verified.get(node_key))
        DiagnosticAnswer.objects.create(
            session=session,
            node_key=node_key,
            question=(node.prompt or node.title)[:200],
            answer=text,
            is_skipped=is_skipped,
            is_verified=is_verified,
        )
        EvidenceItem.objects.create(
            session=session,
            node_key=node_key,
            label=node.title[:200],
            value=text,
            source=(
                EvidenceItem.Source.VERIFIED
                if is_verified
                else EvidenceItem.Source.USER_REPORTED
            ),
        )

    for index, text in enumerate(
        evaluate_findings(workflow, answers), start=1
    ):
        DiagnosticFinding.objects.create(
            session=session,
            title=text[:200],
            explanation=text,
            confidence=DiagnosticFinding.Confidence.HYPOTHESIS,
            order=index,
        )

    node = findings_node(workflow)
    if node is not None:
        for index, action in enumerate(
            (node.config or {}).get("actions", []), start=1
        ):
            text = str(action or "").strip()
            if text:
                RecommendedAction.objects.create(
                    session=session,
                    text=text,
                    order=index,
                )

    if not session.workflow_version:
        session.workflow_version = workflow.version

    session.report = {
        "generated_at": timezone.now().isoformat(),
        "workflow": workflow.title,
        "workflow_slug": workflow.slug,
        "workflow_version": session.workflow_version,
        "problem": workflow.problem.name if workflow.problem else "",
        "answers": len(answers),
        "verified": sum(1 for value in verified.values() if value),
        "findings": session.findings.count(),
        "actions": session.actions.count(),
    }

    update_fields = ["report", "workflow_version", "updated_at"]
    if session.status == DiagnosticSession.Status.COMPLETED and not session.completed_at:
        session.completed_at = timezone.now()
        update_fields.append("completed_at")

    session.save(update_fields=update_fields)


def validate_workflow(workflow):
    """Return a list of authoring problems for a workflow definition."""

    errors = []
    nodes = list(workflow.nodes.all())
    if not nodes:
        return ["Workflow has no nodes."]

    by_key = {}
    for node in nodes:
        key = node.key or f"node-{node.pk}"
        if node.kind == WorkflowNode.Kind.QUESTION:
            if not node.key:
                errors.append(f"Question '{node.title}' has no stable key.")
            if not node.options:
                errors.append(f"Question '{node.title}' has no answer options.")
        if key in by_key:
            errors.append(f"Duplicate node key '{key}'.")
        by_key[key] = node

    for node in nodes:
        config = node.config if isinstance(node.config, dict) else {}
        targets = []
        if config.get("next"):
            targets.append(config["next"])
        for option in node.options:
            if isinstance(option, dict) and option.get("next"):
                targets.append(option["next"])
        for target in targets:
            if target not in by_key:
                errors.append(
                    f"Node '{node.key or node.pk}' points to missing node '{target}'."
                )

    if not any(node.kind == WorkflowNode.Kind.FINDINGS for node in nodes):
        errors.append("Workflow has no findings node.")
    if not any(node.kind == WorkflowNode.Kind.VERIFY for node in nodes):
        errors.append("Workflow has no verification node.")

    return errors
