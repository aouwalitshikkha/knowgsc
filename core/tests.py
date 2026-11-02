import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.html import escape

from core.diagnostics import validate_workflow
from core.models import (
    DiagnosticSession,
    EvidenceItem,
    KnowledgeGap,
    KnowledgeTopic,
    LearningLevel,
    Lesson,
    PracticeScenario,
    QuestionLog,
    Workflow,
)
from core.rag import answer_question, split_sections
from core.seed import seed_all


class ChunkingTests(TestCase):
    def test_split_sections_uses_headings(self):
        sections = split_sections(
            "Lead paragraph.\n\n## First heading\nBody one.\n\n## Second heading\nBody two."
        )
        self.assertEqual([heading for heading, _ in sections], ["Overview", "First heading", "Second heading"])
        self.assertEqual(sections[1][1], "Body one.")

    def test_split_sections_without_headings_is_one_chunk(self):
        sections = split_sections("Only a body with no headings.")
        self.assertEqual(sections, [("Overview", "Only a body with no headings.")])


class RetrievalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_all()

    def test_known_question_is_grounded_and_cited(self):
        answer = answer_question("My pages are discovered but not indexed", log_gap=False)
        self.assertFalse(answer["no_match"])
        self.assertTrue(answer["sources"])
        self.assertTrue(answer["passages"])
        slugs = [passage["source_slug"] for passage in answer["passages"]]
        self.assertIn("discovered-not-indexed", slugs)

    def test_misspelling_is_tolerated(self):
        answer = answer_question("my canoncial is wrong", log_gap=False)
        self.assertFalse(answer["no_match"])
        self.assertTrue(
            any("canonical" in source["title"].lower() for source in answer["sources"])
        )

    def test_robots_synonym_reaches_the_right_document(self):
        answer = answer_question("robot.txt blocking my pages", log_gap=False)
        self.assertFalse(answer["no_match"])
        self.assertTrue(
            any("robots" in source["title"].lower() for source in answer["sources"])
        )

    def test_unrelated_question_is_recorded_as_a_gap(self):
        answer = answer_question("how do i bake sourdough bread", log_gap=True)
        self.assertTrue(answer["no_match"])
        self.assertEqual(KnowledgeGap.objects.count(), 1)
        self.assertEqual(KnowledgeGap.objects.first().question, "how do i bake sourdough bread")

    def test_answer_never_claims_verification(self):
        answer = answer_question("googlebot is getting 5xx timeout errors", log_gap=False)
        self.assertFalse(answer["no_match"])
        self.assertIn(answer["confidence"], {"high", "medium", "low"})
        self.assertNotIn("confirmed cause for your site", answer["intro"].lower())

    def test_answered_question_can_be_logged(self):
        answer = answer_question(
            "googlebot is getting 5xx timeout errors",
            log_gap=False,
            log_question=True,
        )
        self.assertFalse(answer["no_match"])
        log = QuestionLog.objects.get()
        self.assertEqual(log.question, "googlebot is getting 5xx timeout errors")
        self.assertFalse(log.no_match)
        self.assertIn(log.confidence, {"high", "medium", "low"})

    def test_unanswered_question_is_logged_as_a_gap_and_a_question(self):
        answer = answer_question(
            "how do i bake sourdough bread",
            log_gap=True,
            log_question=True,
        )
        self.assertTrue(answer["no_match"])
        self.assertEqual(KnowledgeGap.objects.count(), 1)
        log = QuestionLog.objects.get()
        self.assertTrue(log.no_match)
        self.assertEqual(log.confidence, QuestionLog.Confidence.NONE)


class PageAndApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_all()

    def test_all_public_pages_render(self):
        paths = [
            "/",
            "/ask/",
            "/ask/?question=my+canoncial+is+wrong",
            "/problem-solver/",
            "/problem-solver/?problem=robots",
            "/workflows/",
            "/workflows/blocked-by-robots/",
            "/learning/",
            "/practice-lab/",
            "/resources/",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_ask_page_starts_without_a_loaded_conversation(self):
        response = self.client.get("/ask/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ask about a Search Console problem")
        self.assertContains(response, 'id="chat-input"')
        self.assertNotContains(response, "data-chat-user-message")
        self.assertNotContains(response, "High confidence")
        self.assertNotContains(response, "DEFINITION")

    def test_ask_page_shows_empty_state_when_no_topics_exist(self):
        KnowledgeTopic.objects.all().delete()
        response = self.client.get("/ask/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ask about a Search Console problem")
        self.assertContains(response, 'id="chat-input"')

    def test_ask_answer_api_returns_cited_html(self):
        response = self.client.get("/ask/answer/", {"question": "googlebot 5xx errors"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["no_match"])
        self.assertIn("Retrieved passages", payload["html"])
        self.assertIn("Sources used", payload["html"])

    def test_ask_answer_api_returns_gap_partial(self):
        response = self.client.get("/ask/answer/", {"question": "how do i bake bread"})
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["no_match"])
        self.assertIn("Knowledge gap", payload["html"])

    def test_session_create_then_update(self):
        created = self.client.post(
            "/api/sessions/",
            data=json.dumps(
                {
                    "workflow_slug": "discovered-not-indexed",
                    "state": {"index": 1, "answers": {"status": "Not sure"}},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200)
        payload = created.json()
        self.assertTrue(payload["ok"])

        token = payload["token"]
        updated = self.client.post(
            f"/api/sessions/{token}/",
            data=json.dumps({"state": {"index": 2}, "status": "completed"}),
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["status"], "completed")

    def test_session_create_rejects_invalid_json(self):
        response = self.client.post(
            "/api/sessions/",
            data="not-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_problem_solver_exposes_workflow_selector_and_typed_answer(self):
        response = self.client.get("/problem-solver/?workflow=blocked-by-robots")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="workflow"')
        self.assertContains(response, "Blocked by robots.txt")
        self.assertContains(response, "Guided workflow")
        self.assertContains(response, "Or type your own answer")
        self.assertContains(response, "Use typed answer")

    def test_workflow_get_absolute_url_targets_the_workflow(self):
        workflow = Workflow.objects.get(slug="blocked-by-robots")
        self.assertEqual(
            workflow.get_absolute_url(),
            "/workflows/blocked-by-robots/",
        )

    def test_unknown_workflow_slug_falls_back_to_first_published_workflow(self):
        response = self.client.get("/problem-solver/?workflow=does-not-exist")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guided workflow")


class LessonDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_all()

    def test_learning_roadmap_links_every_published_lesson(self):
        response = self.client.get("/learning/")
        self.assertEqual(response.status_code, 200)
        for lesson in Lesson.objects.filter(is_published=True):
            with self.subTest(slug=lesson.slug):
                self.assertContains(response, lesson.get_absolute_url())

    def test_every_published_lesson_has_a_detail_page(self):
        for lesson in Lesson.objects.filter(is_published=True):
            with self.subTest(slug=lesson.slug):
                response = self.client.get(lesson.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, escape(lesson.title))
                self.assertContains(response, 'class="lesson-content')

    def test_lesson_detail_renders_seeded_tutorial_and_navigation(self):
        lesson = Lesson.objects.get(slug="discovered-currently-not-indexed")
        response = self.client.get(lesson.get_absolute_url())
        self.assertContains(response, "Diagnostic sequence")
        self.assertContains(response, "Next lesson")
        self.assertContains(response, "Open workflow")

    def test_unpublished_lesson_is_hidden_and_returns_404(self):
        lesson = Lesson.objects.get(slug="gsc-reports-overview")
        lesson.is_published = False
        lesson.save(update_fields=["is_published", "updated_at"])

        roadmap = self.client.get("/learning/")
        self.assertNotContains(roadmap, lesson.get_absolute_url())
        self.assertEqual(self.client.get(lesson.get_absolute_url()).status_code, 404)

    def test_lesson_slug_is_generated_from_title(self):
        level = LearningLevel.objects.first()
        lesson = Lesson.objects.create(level=level, title="A Brand New Lesson")
        self.assertEqual(lesson.slug, "a-brand-new-lesson")
        self.assertTrue(lesson.get_absolute_url().endswith("/learning/a-brand-new-lesson/"))

    def test_reseeding_preserves_editor_authored_content(self):
        lesson = Lesson.objects.get(slug="gsc-reports-overview")
        lesson.body = "<p>Editor-authored tutorial</p>"
        lesson.save()

        seed_all()

        lesson.refresh_from_db()
        self.assertEqual(lesson.body, "<p>Editor-authored tutorial</p>")

    def test_lesson_admin_uses_ckeditor(self):
        user = get_user_model().objects.create_superuser(
            username="editor",
            email="editor@example.com",
            password="test-password",
        )
        self.client.force_login(user)
        lesson = Lesson.objects.get(slug="discovered-currently-not-indexed")
        response = self.client.get(f"/admin/core/lesson/{lesson.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ckeditor-init.js")
        self.assertContains(response, 'id="id_body"')


class PracticeLabTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_all()

    def test_practice_lab_shows_only_scenario_cards(self):
        response = self.client.get("/practice-lab/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a problem")
        self.assertNotContains(response, "Your findings")
        self.assertNotContains(response, "URL Inspection results")

        for scenario in PracticeScenario.objects.filter(is_active=True):
            with self.subTest(slug=scenario.slug):
                self.assertContains(response, scenario.get_absolute_url())
                self.assertContains(response, escape(scenario.title))

    def test_scenario_url_uses_practice_lab_detail_path(self):
        scenario = PracticeScenario.objects.get(slug="robots")
        self.assertEqual(scenario.get_absolute_url(), "/practice-lab/robots/")

    def test_every_active_scenario_has_a_detail_page(self):
        for scenario in PracticeScenario.objects.filter(is_active=True):
            with self.subTest(slug=scenario.slug):
                response = self.client.get(scenario.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, escape(scenario.title))
                self.assertContains(response, "Scenario briefing")
                self.assertContains(response, "Worked solution")
                self.assertContains(response, "URL Inspection results")
                self.assertContains(response, escape(scenario.expected_cause))
                self.assertContains(response, escape(scenario.solution))
                for step in scenario.solution_steps:
                    self.assertContains(response, escape(step))

    def test_scenario_detail_renders_report_and_navigation(self):
        scenario = PracticeScenario.objects.get(slug="discovered")
        response = self.client.get(scenario.get_absolute_url())
        self.assertContains(response, escape(scenario.report_title))
        self.assertContains(response, scenario.metrics[0]["value"])
        self.assertContains(response, "Investigation checklist")
        self.assertContains(response, "Next scenario")

    def test_inactive_scenario_is_hidden_and_returns_404(self):
        scenario = PracticeScenario.objects.get(slug="server")
        scenario.is_active = False
        scenario.save(update_fields=["is_active"])

        listing = self.client.get("/practice-lab/")
        self.assertNotContains(listing, scenario.get_absolute_url())
        self.assertEqual(self.client.get(scenario.get_absolute_url()).status_code, 404)

    def test_scenario_detail_contains_workflow_link_when_problem_is_set(self):
        scenario = PracticeScenario.objects.select_related("problem").get(slug="canonical")
        response = self.client.get(scenario.get_absolute_url())
        self.assertContains(response, scenario.problem.get_absolute_url())

    def test_scenario_admin_shows_authoring_fields(self):
        user = get_user_model().objects.create_superuser(
            username="scenario-editor",
            email="scenario-editor@example.com",
            password="test-password",
        )
        self.client.force_login(user)
        scenario = PracticeScenario.objects.get(slug="discovered")
        response = self.client.get(f"/admin/core/practicescenario/{scenario.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="description"')
        self.assertContains(response, 'name="solution"')
        self.assertContains(response, 'name="solution_steps"')


class WorkflowDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_all()

    def test_workflows_page_links_each_workflow_to_its_detail_page(self):
        response = self.client.get("/workflows/")
        self.assertEqual(response.status_code, 200)
        for workflow in Workflow.objects.filter(is_published=True):
            with self.subTest(slug=workflow.slug):
                self.assertContains(response, workflow.get_absolute_url())

    def test_every_published_workflow_has_a_detail_page(self):
        for workflow in Workflow.objects.filter(is_published=True):
            with self.subTest(slug=workflow.slug):
                response = self.client.get(workflow.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, escape(workflow.title))
                self.assertContains(response, 'id="question-panel"')
                self.assertContains(response, "Reference solution")

    def test_workflow_detail_contains_questions_and_solution(self):
        workflow = Workflow.objects.get(slug="blocked-by-robots")
        response = self.client.get(workflow.get_absolute_url())
        self.assertContains(
            response, "Does a robots.txt rule match the affected URL?"
        )
        self.assertContains(response, "Action plan")
        self.assertContains(
            response, "A Disallow rule matches the URL and is blocking Googlebot"
        )

    def test_unpublished_workflow_detail_returns_404(self):
        workflow = Workflow.objects.get(slug="blocked-by-robots")
        workflow.is_published = False
        workflow.save(update_fields=["is_published"])

        self.assertEqual(
            self.client.get(f"/workflows/{workflow.slug}/").status_code,
            404,
        )


class DiagnosticEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_all()

    def _start_session(self):
        response = self.client.post(
            "/api/sessions/",
            data=json.dumps({"workflow_slug": "discovered-not-indexed"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["token"]

    def test_first_workflow_exposes_branching_options(self):
        workflow = Workflow.objects.get(slug="discovered-not-indexed")
        node = workflow.nodes.get(key="status")
        engine_node = node.as_engine_dict()

        self.assertTrue(engine_node["options"])
        self.assertTrue(all(isinstance(option, dict) for option in engine_node["options"]))
        self.assertIn(
            {"label": "Crawled – currently not indexed", "next": "status_crawled"},
            engine_node["options"],
        )

    def test_session_update_materializes_evidence_findings_and_actions(self):
        token = self._start_session()
        state = {
            "answers": {
                "status": "Discovered – currently not indexed",
                "sitemap": "Missing",
                "sitemap_intent": "Accidental",
                "internal": "Weak",
                "internal_weak": "Yes, I can add links",
                "http": "5xx",
                "server_trend": "Intermittent",
                "evidence": "Googlebot fetch errors in logs",
            },
            "skipped": {},
            "verified": {"http": True},
            "path": [
                "status",
                "sitemap",
                "sitemap_intent",
                "internal",
                "internal_weak",
                "http",
                "server_trend",
                "evidence",
                "findings",
                "verify",
            ],
        }
        response = self.client.post(
            f"/api/sessions/{token}/",
            data=json.dumps({"state": state, "status": "completed"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        session = DiagnosticSession.objects.get(token=token)
        self.assertEqual(session.status, DiagnosticSession.Status.COMPLETED)
        self.assertIsNotNone(session.completed_at)
        self.assertEqual(session.answers.count(), 8)
        self.assertEqual(session.evidence.count(), 8)
        self.assertEqual(session.actions.count(), 7)
        self.assertGreaterEqual(session.findings.count(), 3)
        self.assertEqual(session.report["answers"], 8)
        self.assertEqual(
            session.evidence.get(node_key="http").source,
            EvidenceItem.Source.VERIFIED,
        )
        self.assertTrue(
            session.findings.filter(
                explanation__icontains="accidental sitemap omission"
            ).exists()
        )

        report = self.client.get(f"/problem-solver/report/{token}/")
        self.assertEqual(report.status_code, 200)
        self.assertContains(report, "Diagnostic report")
        self.assertContains(report, "accidental sitemap omission")
        self.assertContains(report, "Recheck the Page indexing report")
        self.assertContains(report, "Verified")

    def test_report_returns_404_for_unknown_token(self):
        response = self.client.get(
            "/problem-solver/report/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(response.status_code, 404)

    def test_workflow_validation_rejects_broken_branch_target(self):
        workflow = Workflow.objects.get(slug="discovered-not-indexed")
        node = workflow.nodes.get(key="status")
        node.options = [{"label": "Broken", "next": "missing-node"}]
        node.save(update_fields=["options"])

        errors = validate_workflow(workflow)
        self.assertTrue(any("missing node" in error for error in errors))

    def test_workflow_validation_accepts_seeded_workflow(self):
        workflow = Workflow.objects.get(slug="discovered-not-indexed")
        self.assertEqual(validate_workflow(workflow), [])


class QuestionLogAdminTests(TestCase):
    def test_selected_questions_export_to_csv(self):
        user = get_user_model().objects.create_superuser(
            username="question-admin",
            email="question-admin@example.com",
            password="test-password",
        )
        self.client.force_login(user)
        log = QuestionLog.objects.create(
            question="how do i bake sourdough bread",
            confidence=QuestionLog.Confidence.NONE,
            no_match=True,
            retrieved_count=0,
        )

        response = self.client.post(
            "/admin/core/questionlog/",
            {
                "action": "export_csv",
                "_selected_action": [str(log.pk)],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("question,matched_topic,confidence", content)
        self.assertIn("how do i bake sourdough bread", content)
