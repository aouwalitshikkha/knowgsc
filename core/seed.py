"""Idempotent demo content for KnowGSC.

Run with ``python manage.py seed``. The same routine backs the initial data
migration so a fresh database is immediately usable.
"""

from datetime import date

from django.db import transaction

from core.knowledge_seed import KNOWLEDGE_DOCS, SEARCH_TERMS
from core.models import (
    DiagnosticSession,
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
    Resource,
    ResourceCategory,
    ResourceContext,
    SearchTerm,
    Tone,
    Workflow,
    WorkflowNode,
)
from core.rag import reindex_all


CATEGORIES = [
    ("Indexing", "indexing", Tone.WARN, "Pages that Google has not indexed."),
    ("Crawling", "crawling", Tone.DANGER, "Pages Google cannot fetch."),
    ("Content", "content", Tone.WARN, "Pages that look empty or low value."),
    ("Server", "server", Tone.DANGER, "Availability and server response problems."),
]

PROBLEMS = [
    {
        "slug": "discovered",
        "name": "Discovered – currently not indexed",
        "category": "indexing",
        "badge": "Most common",
        "order": 1,
        "summary": "Google found the page but hasn't indexed it yet. Weak internal discovery signals or sitemap omission may be at play.",
    },
    {
        "slug": "crawled",
        "name": "Crawled – currently not indexed",
        "category": "indexing",
        "badge": "Frequent",
        "order": 2,
        "summary": "Google crawled the page but still won't index it. Often related to crawl directives or canonicalization.",
    },
    {
        "slug": "noindex",
        "name": "Excluded by noindex",
        "category": "indexing",
        "badge": "Intentional",
        "order": 3,
        "summary": "The page was explicitly excluded from indexing via a noindex directive or header.",
    },
    {
        "slug": "robots",
        "name": "Blocked by robots.txt",
        "category": "crawling",
        "badge": "Blocking",
        "order": 4,
        "summary": "robots.txt prevented Googlebot from fetching the page, so it can't be crawled or indexed.",
    },
    {
        "slug": "soft-404",
        "name": "Soft 404",
        "category": "content",
        "badge": "Quality signal",
        "order": 5,
        "summary": "The page returns a 200 status but effectively contains no meaningful content.",
    },
    {
        "slug": "server-error",
        "name": "Server error (5xx)",
        "category": "server",
        "badge": "Availability",
        "order": 6,
        "summary": "The server returned a 5xx error while Googlebot was crawling. Check reproducibility and stability.",
    },
]

FLOWS = {
    "discovered": {
        "slug": "discovered-not-indexed",
        "title": "Discovered – currently not indexed",
        "summary": "Confirms GSC status → branches on sitemap, noindex, robots and HTTP evidence → checks the cause that matches your answers → generates findings.",
        "featured": True,
        "order": 1,
        "nodes": [
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "status",
                "title": "Confirm GSC status",
                "prompt": "What does your GSC report show for these URLs?",
                "hint": "Open Search Console → Indexing → Pages, then select the affected URL group.",
                "options": [
                    {
                        "label": "Discovered – currently not indexed",
                        "next": "sitemap",
                    },
                    {
                        "label": "Crawled – currently not indexed",
                        "next": "status_crawled",
                    },
                    {"label": "Excluded by noindex", "next": "status_noindex"},
                    {"label": "Blocked by robots.txt", "next": "status_robots"},
                    {"label": "Not sure", "next": "sitemap"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "status_crawled",
                "title": "Confirm the status group",
                "prompt": "This workflow is tuned for Discovered – currently not indexed. Have you confirmed the URLs are in that group?",
                "hint": "In the Pages report, check the reason column. Crawled – currently not indexed is a different diagnosis path.",
                "options": [
                    {"label": "Yes, confirmed", "next": "sitemap"},
                    {
                        "label": "No — it is Crawled – currently not indexed",
                        "next": "sitemap",
                    },
                    {"label": "Not sure", "next": "sitemap"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "status_noindex",
                "title": "Check noindex intent",
                "prompt": "Is the noindex directive on these URLs intentional?",
                "hint": "Inspect the rendered HTML for a robots meta tag or the X-Robots-Tag response header.",
                "options": [
                    {"label": "Intentional", "next": "findings"},
                    {"label": "Accidental", "next": "sitemap"},
                    {"label": "Not sure", "next": "sitemap"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "status_robots",
                "title": "Check robots.txt intent",
                "prompt": "Is the robots.txt block intentional?",
                "hint": "Fetch /robots.txt and find the rule that matches the affected path. Check whether it came from a staging configuration.",
                "options": [
                    {"label": "Intentional", "next": "findings"},
                    {"label": "Accidental", "next": "sitemap"},
                    {"label": "Not sure", "next": "sitemap"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "sitemap",
                "title": "Check sitemap inclusion",
                "prompt": "Is the URL included in your submitted sitemap?",
                "hint": "Open the Sitemaps report, then fetch the sitemap URL and search for the page.",
                "options": [
                    {"label": "Missing", "next": "sitemap_intent"},
                    {"label": "Present", "next": "internal"},
                    {"label": "Not sure", "next": "sitemap_help"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "sitemap_intent",
                "title": "Confirm sitemap intent",
                "prompt": "Is the URL intentionally left out of the sitemap?",
                "hint": "Check your sitemap generation rules and whether the page is meant to be indexed.",
                "options": [
                    {"label": "Intentional", "next": "findings"},
                    {"label": "Accidental", "next": "internal"},
                    {"label": "Not sure", "next": "internal"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "sitemap_help",
                "title": "Verify sitemap inclusion",
                "prompt": "After checking the sitemap directly, what did you find?",
                "hint": "Search the XML for the exact URL. Confirm the sitemap is the one submitted in GSC.",
                "options": [
                    {"label": "Missing", "next": "sitemap_intent"},
                    {"label": "Present", "next": "internal"},
                    {"label": "Not sure", "next": "internal"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "internal",
                "title": "Check internal links",
                "prompt": "How strong are the internal links pointing to this page?",
                "hint": "Search your site for the URL, or inspect the page in a crawler to count internal inlinks.",
                "options": [
                    {"label": "Strong", "next": "http"},
                    {"label": "Weak", "next": "internal_weak"},
                    {"label": "None found", "next": "internal_weak"},
                    {"label": "Not sure", "next": "http"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "internal_weak",
                "title": "Assess internal linking options",
                "prompt": "Can you add contextual internal links from relevant indexed pages?",
                "hint": "Look for pages that already discuss this topic, then link to the affected URL from their body content.",
                "options": [
                    {"label": "Yes, I can add links", "next": "http"},
                    {"label": "No, links are not relevant", "next": "http"},
                    {"label": "Not sure", "next": "http"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "http",
                "title": "Check HTTP response",
                "prompt": "What HTTP response does the URL return?",
                "hint": "Use URL Inspection → Test live URL, and confirm with curl or your server logs.",
                "options": [
                    {"label": "200", "next": "evidence"},
                    {"label": "5xx", "next": "server_trend"},
                    {"label": "Redirect", "next": "redirect_target"},
                    {"label": "Not sure", "next": "evidence"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "server_trend",
                "title": "Check the server error pattern",
                "prompt": "Is the 5xx response intermittent or persistent?",
                "hint": "Check Crawl Stats and server logs over several days. Intermittent errors may only affect a share of Googlebot requests.",
                "options": [
                    {"label": "Intermittent", "next": "evidence"},
                    {"label": "Persistent", "next": "evidence"},
                    {"label": "Not sure", "next": "evidence"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "redirect_target",
                "title": "Check the redirect target",
                "prompt": "Does the redirect point to the intended canonical URL?",
                "hint": "Follow the full redirect chain and compare the final URL with your declared canonical and sitemap entry.",
                "options": [
                    {"label": "Yes", "next": "evidence"},
                    {"label": "No", "next": "evidence"},
                    {"label": "Not sure", "next": "evidence"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "evidence",
                "title": "Collect additional evidence",
                "prompt": "Which additional evidence do you have?",
                "hint": "Useful sources: server logs, Crawl Stats, Coverage API exports, rendered HTML.",
                "options": [
                    {
                        "label": "Googlebot fetch errors in logs",
                        "next": "findings",
                    },
                    {"label": "Coverage API data", "next": "findings"},
                    {"label": "Rendering issues", "next": "findings"},
                    {"label": "None of these", "next": "findings"},
                    {"label": "Not sure", "next": "findings"},
                ],
            },
            {
                "kind": WorkflowNode.Kind.FINDINGS,
                "key": "findings",
                "title": "Generate findings & action plan",
                "config": {
                    "intro": "The workflow evaluated the collected evidence. Causes below are still hypotheses until each one is verified against real data.",
                    "rules": [
                        {
                            "when": {"status": "Crawled – currently not indexed"},
                            "text": "The URLs are reported as crawled but not indexed, so this discovery-focused workflow may be looking at the wrong status group.",
                        },
                        {
                            "when": {
                                "status": "Excluded by noindex",
                                "status_noindex": "Intentional",
                            },
                            "text": "The noindex directive appears intentional, so exclusion from search is working as designed unless the page should be indexed.",
                        },
                        {
                            "when": {
                                "status": "Excluded by noindex",
                                "status_noindex": "Accidental",
                            },
                            "text": "An accidental noindex directive is likely preventing these URLs from being indexed.",
                        },
                        {
                            "when": {
                                "status": "Blocked by robots.txt",
                                "status_robots": "Intentional",
                            },
                            "text": "The robots.txt block appears intentional, so Google cannot fetch the URL by design.",
                        },
                        {
                            "when": {
                                "status": "Blocked by robots.txt",
                                "status_robots": "Accidental",
                            },
                            "text": "A robots.txt rule is blocking Googlebot from fetching the affected URLs.",
                        },
                        {
                            "when": {
                                "sitemap": "Missing",
                                "sitemap_intent": "Intentional",
                            },
                            "text": "The URL is intentionally absent from the sitemap, which is acceptable if the page should not be indexed.",
                        },
                        {
                            "when": {
                                "sitemap": "Missing",
                                "sitemap_intent": "Accidental",
                            },
                            "text": "An accidental sitemap omission is weakening discovery for the affected URLs.",
                        },
                        {
                            "when": {"sitemap": "Missing"},
                            "text": "The URL appears to be missing from the submitted sitemap, which limits discovery.",
                        },
                        {
                            "when": {"internal": "Weak"},
                            "text": "Internal links to the page are weak, so crawl priority may be low.",
                        },
                        {
                            "when": {"internal": "None found"},
                            "text": "No internal links were found, so Google may treat the page as orphaned.",
                        },
                        {
                            "when": {
                                "internal_weak": "No, links are not relevant"
                            },
                            "text": "Internal linking cannot be improved in this case, so discovery depends on sitemaps and other signals.",
                        },
                        {
                            "when": {"http": "5xx"},
                            "text": "A 5xx response may be preventing reliable crawling.",
                        },
                        {
                            "when": {
                                "http": "5xx",
                                "server_trend": "Persistent",
                            },
                            "text": "The server error is persistent, so Googlebot is likely to keep failing until the origin is fixed.",
                        },
                        {
                            "when": {
                                "http": "5xx",
                                "server_trend": "Intermittent",
                            },
                            "text": "The server error is intermittent, so the page may be discoverable but unreliable to crawl.",
                        },
                        {
                            "when": {"http": "Redirect"},
                            "text": "A redirect may be sending Googlebot to a different URL than the one being inspected.",
                        },
                        {
                            "when": {
                                "http": "Redirect",
                                "redirect_target": "No",
                            },
                            "text": "The redirect points somewhere other than the intended canonical URL, which can split or misdirect indexing signals.",
                        },
                        {
                            "when": {"evidence": "Rendering issues"},
                            "text": "Rendering problems may hide the main content from Googlebot.",
                        },
                    ],
                    "fallback": "The collected evidence does not yet point to a single confirmed cause.",
                    "unverified": [
                        "Whether the HTTP response is reproducible for Googlebot.",
                        "Whether the pages are intended to be indexed at all.",
                        "Whether a canonical or noindex directive is applied in the rendered HTML.",
                        "Whether the sitemap omission or robots block was intentional.",
                    ],
                    "actions": [
                        "Confirm the affected URL group and status in the Indexing report.",
                        "Check the sitemap and internal links for discovery signals.",
                        "Re-run the HTTP check and confirm the response is stable.",
                        "Inspect proxy and application logs for Googlebot requests.",
                        "Add meaningful internal links from relevant pages where appropriate.",
                        "Verify Googlebot can fetch the URL, then request indexing.",
                        "Recheck the Page indexing report after one to two weeks.",
                    ],
                },
            },
            {
                "kind": WorkflowNode.Kind.VERIFY,
                "key": "verify",
                "title": "Verify results",
                "config": {
                    "intro": "Repeat the relevant checks and confirm what actually changed. KnowGSC will not claim a fix until verification is complete.",
                    "completed": "Every recorded item has been re-checked. Save the report as your evidence record before making changes.",
                },
            },
        ],
    },
    "crawled": {
        "slug": "crawled-not-indexed",
        "title": "Crawled – currently not indexed",
        "summary": "Confirms GSC status → checks crawl eligibility → validates directives → inspects canonicals → collects evidence → generates findings.",
        "featured": True,
        "order": 2,
        "nodes": [
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "status",
                "title": "Confirm GSC status",
                "prompt": "What does your GSC report show for these URLs?",
                "hint": "Open Search Console → Indexing → Pages, then select the affected URL group.",
                "options": [
                    "Crawled – currently not indexed",
                    "Discovered – currently not indexed",
                    "Excluded by noindex",
                    "Not sure",
                ],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "directives",
                "title": "Validate directives",
                "prompt": "Do the pages contain a noindex directive (meta tag or HTTP header)?",
                "hint": "Check the rendered HTML and response headers with URL Inspection → View crawled page.",
                "options": ["No noindex", "noindex present", "Not sure"],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "canonical",
                "title": "Inspect canonicals",
                "prompt": "Which URL does the canonical point to?",
                "hint": "Inspect the rendered HTML for rel=canonical and compare it with the inspected URL.",
                "options": ["Self-referencing", "Points elsewhere", "Not sure"],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "eligibility",
                "title": "Check crawl eligibility",
                "prompt": "Is the page indexable and free of blocking rules?",
                "hint": "Confirm the HTTP status, robots meta, X-Robots-Tag header and robots.txt rules.",
                "options": ["Indexable", "Blocked", "Not sure"],
            },
            {
                "kind": WorkflowNode.Kind.FINDINGS,
                "title": "Generate findings & action plan",
                "config": {
                    "intro": "Google fetched these pages but chose not to index them. The evidence narrows down why.",
                    "rules": [
                        {
                            "when": {"directives": "noindex present"},
                            "text": "A noindex directive is present, so Google is correctly excluding the page.",
                        },
                        {
                            "when": {"canonical": "Points elsewhere"},
                            "text": "The canonical points to another URL, so this page is treated as a duplicate.",
                        },
                        {
                            "when": {"eligibility": "Blocked"},
                            "text": "A blocking rule prevents indexing even though the page was crawled.",
                        },
                    ],
                    "fallback": "No single blocking cause was confirmed. Indexing may be limited by content quality or duplication.",
                    "unverified": [
                        "Whether the page adds unique value compared with competing pages.",
                        "Whether internal links signal that the page is important.",
                        "Whether canonical signals are consistent across the site.",
                    ],
                    "actions": [
                        "Remove noindex directives from pages that should be indexed.",
                        "Make the canonical self-referencing where appropriate.",
                        "Differentiate content so it is not a near-duplicate.",
                        "Strengthen internal links from relevant pages.",
                        "Request indexing after the changes ship.",
                    ],
                },
            },
            {
                "kind": WorkflowNode.Kind.VERIFY,
                "title": "Verify results",
                "config": {
                    "intro": "Re-inspect the URL and confirm that Google now sees the corrected signals.",
                    "completed": "All recorded checks have been verified. Keep the URL Inspection output as evidence.",
                },
            },
        ],
    },
    "robots": {
        "slug": "blocked-by-robots",
        "title": "Blocked by robots.txt",
        "summary": "Fetches robots.txt → evaluates matching rules → distinguishes intentional blocking → recommends a safe rule change → verifies recrawl.",
        "featured": False,
        "order": 3,
        "nodes": [
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "rule",
                "title": "Evaluate robots.txt rules",
                "prompt": "Does a robots.txt rule match the affected URL?",
                "hint": "Open /robots.txt and compare the longest matching Allow or Disallow rule for Googlebot.",
                "options": ["Disallow matches this URL", "No matching rule", "Not sure"],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "intent",
                "title": "Distinguish intent",
                "prompt": "Was blocking this URL intentional?",
                "hint": "Check recent deployments and staging-to-production configuration changes.",
                "options": ["Intentional", "Accidental", "Not sure"],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "fetch",
                "title": "Verify fetch access",
                "prompt": "Can Googlebot fetch the URL now?",
                "hint": "Use URL Inspection → Test live URL after updating robots.txt.",
                "options": ["Blocked", "Allowed", "Not sure"],
            },
            {
                "kind": WorkflowNode.Kind.FINDINGS,
                "title": "Generate findings & action plan",
                "config": {
                    "intro": "robots.txt rules decide what Googlebot may fetch before it can index anything.",
                    "rules": [
                        {
                            "when": {"rule": "Disallow matches this URL"},
                            "text": "A Disallow rule matches the URL and is blocking Googlebot.",
                        },
                        {
                            "when": {"intent": "Accidental"},
                            "text": "The rule appears accidental, likely copied from a staging configuration.",
                        },
                        {
                            "when": {"fetch": "Blocked"},
                            "text": "Live fetching is still blocked, so the fix has not propagated yet.",
                        },
                    ],
                    "fallback": "The evidence does not confirm a robots.txt cause yet.",
                    "unverified": [
                        "Whether the rule also blocks other important URL patterns.",
                        "Whether the rule was introduced by a recent deployment.",
                    ],
                    "actions": [
                        "Remove or narrow the Disallow rule for pages that should rank.",
                        "Keep intentional blocks for private or duplicate URL patterns.",
                        "Deploy robots.txt and confirm it is publicly fetchable.",
                        "Re-test the URL with URL Inspection.",
                    ],
                },
            },
            {
                "kind": WorkflowNode.Kind.VERIFY,
                "title": "Verify results",
                "config": {
                    "intro": "Confirm that robots.txt now allows Googlebot and that the page can be fetched.",
                    "completed": "Live fetch works again. Request indexing and monitor the Page indexing report.",
                },
            },
        ],
    },
    "server-error": {
        "slug": "server-error",
        "title": "Server error (5xx)",
        "summary": "Checks reproducibility → reviews timeout behavior → inspects logs → validates server stability → recommends fixes.",
        "featured": True,
        "order": 4,
        "nodes": [
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "reproducible",
                "title": "Check reproducibility",
                "prompt": "Can you reproduce the 5xx response?",
                "hint": "Repeat the request several times and compare with URL Inspection → Test live URL.",
                "options": ["Always", "Intermittent", "Only for Googlebot", "Not sure"],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "logs",
                "title": "Review server logs",
                "prompt": "What do the server and proxy logs show?",
                "hint": "Filter by Googlebot user agent and look for 5xx responses or timeouts.",
                "options": ["5xx in logs", "Timeouts", "No errors", "Not sure"],
            },
            {
                "kind": WorkflowNode.Kind.QUESTION,
                "key": "stability",
                "title": "Validate stability",
                "prompt": "Is the server stable now?",
                "hint": "Check uptime monitoring, recent deploys and error-rate dashboards.",
                "options": ["Stable now", "Still failing", "Not sure"],
            },
            {
                "kind": WorkflowNode.Kind.FINDINGS,
                "title": "Generate findings & action plan",
                "config": {
                    "intro": "5xx errors are temporary failures, but recurring ones can delay crawling and indexing.",
                    "rules": [
                        {
                            "when": {"logs": "Timeouts"},
                            "text": "Timeouts suggest the application or upstream proxy cannot respond in time.",
                        },
                        {
                            "when": {"logs": "5xx in logs"},
                            "text": "Server logs confirm 5xx responses for Googlebot requests.",
                        },
                        {
                            "when": {"reproducible": "Only for Googlebot"},
                            "text": "Errors only affect Googlebot, which points to bot filtering, rate limiting or WAF rules.",
                        },
                    ],
                    "fallback": "The evidence does not yet isolate the source of the server errors.",
                    "unverified": [
                        "Whether the error rate correlates with traffic spikes.",
                        "Whether a CDN or WAF is returning an error before the origin.",
                    ],
                    "actions": [
                        "Raise or remove bot rate limits for verified Googlebot traffic.",
                        "Fix the slow endpoint or increase its timeout budget.",
                        "Check CDN and WAF logs for blocked or failed requests.",
                        "Monitor error rates after the fix before requesting a recrawl.",
                    ],
                },
            },
            {
                "kind": WorkflowNode.Kind.VERIFY,
                "title": "Verify results",
                "config": {
                    "intro": "Confirm the endpoint returns a stable 200 response over repeated fetches.",
                    "completed": "The server is stable. Monitor Crawl Stats for lingering 5xx errors.",
                },
            },
        ],
    },
}

RESOURCE_CATEGORIES = [
    ("Indexing", "indexing", 1),
    ("Performance", "performance", 2),
    ("Tooling", "tooling", 3),
]

RESOURCES = [
    {
        "title": "Google Search Central",
        "url": "https://developers.google.com/search/docs",
        "description": "Search and crawling documentation.",
        "category": "indexing",
        "tone": Tone.BRAND,
        "icon": "book",
        "tags": ["Indexing", "Crawling", "Rendering"],
        "checked_on": date(2026, 10, 1),
        "is_featured": True,
        "order": 1,
    },
    {
        "title": "Search Console Help",
        "url": "https://support.google.com/webmasters/",
        "description": "GSC reports and troubleshooting.",
        "category": "indexing",
        "tone": Tone.BRAND,
        "icon": "help",
        "tags": ["Indexing", "Crawling", "Performance"],
        "checked_on": date(2026, 9, 22),
        "is_featured": True,
        "order": 2,
    },
    {
        "title": "PageSpeed Insights",
        "url": "https://pagespeed.web.dev/",
        "description": "Performance and Core Web Vitals analysis.",
        "category": "performance",
        "tone": Tone.OK,
        "icon": "bolt",
        "tags": ["Core Web Vitals", "Server errors"],
        "checked_on": date(2026, 9, 30),
        "is_featured": True,
        "order": 3,
    },
    {
        "title": "Rich Results Test",
        "url": "https://search.google.com/test/rich-results",
        "description": "Structured data testing and eligibility checks.",
        "category": "tooling",
        "tone": Tone.BRAND,
        "icon": "rich",
        "tags": ["Structured data", "Rendering"],
        "checked_on": date(2026, 9, 18),
        "order": 4,
    },
    {
        "title": "URL Inspection",
        "url": "https://search.google.com/search-console",
        "description": "Check live index status and request indexing.",
        "category": "tooling",
        "tone": Tone.WARN,
        "icon": "url",
        "tags": ["Indexing", "Crawling"],
        "checked_on": date(2026, 10, 4),
        "order": 5,
    },
    {
        "title": "Search Console API",
        "url": "",
        "description": "Programmatic access for automated reporting (planned).",
        "category": "tooling",
        "tone": Tone.NEUTRAL,
        "icon": "api",
        "status": Resource.Status.FUTURE,
        "tags": ["All reports"],
        "order": 6,
    },
]

RESOURCE_CONTEXTS = [
    {
        "title": "When investigating duplicate or canonical issues",
        "description": "Canonicalization guides, duplicate handling, and self-referencing rules.",
        "link_url": "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
        "link_label": "Open canonical resources",
        "category": "indexing",
        "tone": Tone.BRAND,
        "order": 1,
    },
    {
        "title": "When investigating 5xx server errors",
        "description": "HTTP status handling, timeout reproducibility, and log analysis guides.",
        "link_url": "https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
        "link_label": "Open server error resources",
        "category": "performance",
        "tone": Tone.DANGER,
        "order": 2,
    },
]

LEVELS = [
    {
        "order": 1,
        "title": "Level 1 — GSC Fundamentals",
        "subtitle": "Understand reports and indexing terminology",
        "status": LearningLevel.Status.COMPLETED,
        "lessons": [
            {
                "slug": "gsc-reports-overview",
                "title": "GSC reports overview",
                "description": "Learn what each Search Console report measures — and when to trust it.",
                "duration_minutes": 12,
                "is_completed": True,
                "order": 1,
                "objectives": [
                    "Name the six Search Console reports you will use most often.",
                    "Explain the difference between performance, coverage and enhancement data.",
                    "Choose the right report for a traffic, indexing or experience question.",
                ],
                "key_takeaways": [
                    "Search Console is a sample of Google traffic, not your analytics platform.",
                    "Performance data answers 'how visible?'; the Pages report answers 'what is indexed?'.",
                    "Always confirm a suspect URL with URL Inspection before changing the site.",
                ],
                "body": """
<p class="lead">Search Console contains dozens of screens, but most day-to-day work happens in six reports. This lesson gives you a mental map so you stop guessing where a problem belongs.</p>

<h2>What Search Console actually measures</h2>
<p>Search Console reports what Google observed about your property. It is not a complete analytics tool: performance data is sampled and filtered, and many reports update on a delay. Treat every number as a directional signal that you confirm with a second source.</p>

<table>
  <thead>
    <tr><th>Report</th><th>Answers this question</th><th>Typical delay</th></tr>
  </thead>
  <tbody>
    <tr><td>Performance</td><td>Which queries and pages earned clicks and impressions?</td><td>1–3 days</td></tr>
    <tr><td>URL Inspection</td><td>What does Google know about this exact URL right now?</td><td>Live / recent crawl</td></tr>
    <tr><td>Pages (Indexing)</td><td>Which URLs are indexed or excluded, and why?</td><td>Days to weeks</td></tr>
    <tr><td>Sitemaps</td><td>Did Google fetch my sitemap and discover the listed URLs?</td><td>Hours to days</td></tr>
    <tr><td>Core Web Vitals</td><td>How do real users experience page speed and stability?</td><td>28-day rolling window</td></tr>
    <tr><td>Enhancements</td><td>Are structured-data features eligible to appear?</td><td>Days</td></tr>
  </tbody>
</table>

<figure>
  <img src="/static/img/lesson/performance-report.svg" alt="Mock Search Console Performance report showing clicks, impressions and a query filter" width="1200" height="700">
  <figcaption>The Performance report is the starting point for visibility questions, not for indexing questions.</figcaption>
</figure>

<h2>How the reports fit together</h2>
<ol>
  <li><strong>Start with the symptom.</strong> A drop in clicks is a performance question. A missing page is an indexing question. A broken rich result is an enhancement question.</li>
  <li><strong>Check the Pages report for scope.</strong> One excluded URL is usually a page-level issue; hundreds suggest a template, sitemap or crawl-budget problem.</li>
  <li><strong>Inspect a representative URL.</strong> URL Inspection shows the crawled version, canonical, robots directives and rendered HTML for one URL.</li>
  <li><strong>Cross-check outside Search Console.</strong> Server logs, your CMS and analytics explain <em>why</em> Google saw what it saw.</li>
</ol>

<blockquote>
  <p><strong>Practical rule:</strong> Search Console tells you what Google recorded. It rarely tells you why. The “why” lives in your site, your server and your content.</p>
</blockquote>

<h2>A five-minute weekly review</h2>
<ul>
  <li>Open <strong>Performance</strong> and compare the last 7 days with the previous 7 days. Filter to your most valuable query group.</li>
  <li>Open <strong>Pages</strong> and scan for new exclusion reasons or a jump in a single reason.</li>
  <li>Open <strong>Sitemaps</strong> and confirm the last read date is recent and the discovered-URL count looks sane.</li>
  <li>Check <strong>Core Web Vitals</strong> for newly failing URL groups, not just the site-wide average.</li>
  <li>Record one hypothesis and one verification step. Do not “fix” five things at once.</li>
</ul>

<h3>Common mistake: reading the wrong date range</h3>
<p>Search Console uses the property time zone and a reporting delay. A change made today may not appear for several days. When you compare periods, use the same length and account for weekends and seasonality.</p>
""",
            },
            {
                "slug": "indexing-terminology",
                "title": "Indexing terminology",
                "description": "Discovered, Crawled, Indexed, Excluded — and what each implies.",
                "duration_minutes": 14,
                "is_completed": True,
                "order": 2,
                "objectives": [
                    "Describe the crawl-to-index lifecycle in the correct order.",
                    "Distinguish 'discovered', 'crawled', 'indexed' and 'excluded'.",
                    "Recognise when a status is expected versus when it needs investigation.",
                ],
                "key_takeaways": [
                    "Discovered means Google knows the URL exists; it does not mean Google fetched it.",
                    "Crawled means Google fetched the page; indexing is a separate decision.",
                    "Excluded is not automatically an error — many exclusions are intentional.",
                ],
                "body": """
<p class="lead">Most indexing arguments are really vocabulary arguments. Get the lifecycle right and the correct next check becomes obvious.</p>

<h2>The lifecycle in order</h2>
<ol>
  <li><strong>Discovered:</strong> Google found a URL through a link, sitemap, redirect or another source.</li>
  <li><strong>Queued for crawl:</strong> the URL is waiting for Googlebot. Queue time depends on host load, crawl budget and perceived value.</li>
  <li><strong>Crawled:</strong> Googlebot fetched the URL and received a response. The response may be HTML, a redirect, an error or a non-HTML file.</li>
  <li><strong>Indexed:</strong> Google selected the page as a canonical candidate for one or more queries. Indexing is not guaranteed by crawling.</li>
  <li><strong>Served:</strong> the page can appear in results. Ranking is a separate step after indexing.</li>
</ol>

<figure>
  <img src="/static/img/lesson/url-inspection.svg" alt="Mock URL Inspection panel showing coverage, canonical and crawl details" width="1200" height="700">
  <figcaption>URL Inspection collapses the lifecycle into one view for a single URL. Read it from top to bottom.</figcaption>
</figure>

<h2>Status labels you will meet</h2>
<table>
  <thead>
    <tr><th>Label</th><th>What it means</th><th>First check</th></tr>
  </thead>
  <tbody>
    <tr><td>Discovered – currently not indexed</td><td>Known, but not yet crawled or not yet selected.</td><td>Sitemap, internal links, server response, content value.</td></tr>
    <tr><td>Crawled – currently not indexed</td><td>Fetched, but Google chose not to index this URL.</td><td>Canonical, directives, duplication, thin content.</td></tr>
    <tr><td>Excluded by ‘noindex’ tag</td><td>Google respected an explicit noindex directive.</td><td>Confirm the directive is intentional and correctly scoped.</td></tr>
    <tr><td>Alternate page with proper canonical tag</td><td>Google selected a different canonical URL.</td><td>Check whether the canonical target is the page you want.</td></tr>
    <tr><td>Redirect error</td><td>A redirect chain or loop prevented a final URL.</td><td>Follow the redirect chain to a single 200 response.</td></tr>
    <tr><td>Soft 404</td><td>The page looks empty or error-like despite returning 200.</td><td>Check rendered content, status code and template behaviour.</td></tr>
  </tbody>
</table>

<h2>“Excluded” is not a synonym for “broken”</h2>
<p>Tag pages, filtered URLs, staging hosts, thank-you pages and duplicates are often excluded on purpose. Before “fixing” an exclusion, ask whether the URL <em>should</em> be indexed. If the answer is no, the correct action is to keep it excluded and document why.</p>

<blockquote>
  <p><strong>Verification habit:</strong> write the expected status for a URL before you inspect it. If Google's status differs, you have a concrete hypothesis to test.</p>
</blockquote>

<h2>Checklist</h2>
<ul>
  <li>Does the URL return a single 200 response without a redirect chain?</li>
  <li>Is it linked from an indexable page, not only from the sitemap?</li>
  <li>Is the canonical self-referencing and consistent with the sitemap?</li>
  <li>Does the rendered page contain unique, useful content?</li>
  <li>Is any noindex directive intentional and limited to the right URLs?</li>
</ul>
""",
            },
        ],
    },
    {
        "order": 2,
        "title": "Level 2 — Indexing Diagnostics",
        "subtitle": "Investigate common indexing exclusions",
        "status": LearningLevel.Status.IN_PROGRESS,
        "lessons": [
            {
                "slug": "discovered-currently-not-indexed",
                "title": "Discovered – currently not indexed",
                "description": "Walk through sitemap, internal linking and HTTP checks.",
                "duration_minutes": 18,
                "problem": "discovered",
                "order": 1,
                "objectives": [
                    "Separate a discovery problem from a crawl-priority problem.",
                    "Verify that Google can fetch the URL without errors.",
                    "Build an evidence-based case for why a URL is still waiting.",
                ],
                "key_takeaways": [
                    "Being in a sitemap does not guarantee a crawl.",
                    "Internal links from strong pages are stronger discovery signals than sitemap entries alone.",
                    "If the URL already returns 200 and is linked, the remaining lever is usually perceived value.",
                ],
                "body": """
<p class="lead">“Discovered – currently not indexed” means Google knows the URL exists but has not crawled or selected it. It is a queue, not a verdict. Your job is to find out which part of the queue is stuck.</p>

<h2>What this status does and does not tell you</h2>
<p>It does <strong>not</strong> prove that Googlebot was blocked. It also does not prove the content is bad. It means the URL is known and Google has not yet invested a crawl in it, or has crawled it without selecting it for the index.</p>

<figure>
  <img src="/static/img/lesson/indexing-report.svg" alt="Mock Search Console Pages report filtered to Discovered – currently not indexed" width="1200" height="700">
  <figcaption>Start with the count and the URL pattern, not with a single URL in isolation.</figcaption>
</figure>

<h2>Diagnostic sequence</h2>
<ol>
  <li><strong>Check the sitemap.</strong> In the Sitemaps report, confirm the sitemap was read successfully and the discovered count is plausible. A sitemap that returns HTML, a login page or the wrong host sends Google the wrong signals.</li>
  <li><strong>Inspect one representative URL.</strong> Use URL Inspection to see the last crawl, robots.txt status, canonical and rendered content. If the URL has never been crawled, there may be no rendered data yet.</li>
  <li><strong>Test the raw response.</strong> Fetch the URL with a tool that does not run JavaScript. Confirm a single 200 response, no redirect chain and no accidental noindex.</li>
  <li><strong>Check internal linking.</strong> Is the URL reachable from an indexable page with a normal followable link? Links buried in JavaScript menus or only in XML sitemaps are weaker.</li>
  <li><strong>Assess the URL pattern.</strong> If hundreds of near-duplicate URLs share the same status, fix the template or the discovery rule rather than requesting indexing one by one.</li>
</ol>

<h3>Discovery versus crawl priority</h3>
<table>
  <thead>
    <tr><th>Evidence</th><th>Likely interpretation</th><th>Next action</th></tr>
  </thead>
  <tbody>
    <tr><td>URL never crawled, no internal links</td><td>Discovery is weak.</td><td>Add links from relevant, indexed pages.</td></tr>
    <tr><td>URL never crawled, strong links and sitemap entry</td><td>Crawl priority is low.</td><td>Improve uniqueness and importance; reduce low-value URL volume.</td></tr>
    <tr><td>URL crawled with 200 and self-canonical, still not indexed</td><td>Index selection, not access.</td><td>Review content quality and duplication.</td></tr>
    <tr><td>URL crawled but canonical points elsewhere</td><td>Google selected a different canonical.</td><td>Align canonical, internal links and sitemap.</td></tr>
  </tbody>
</table>

<h2>What to change first</h2>
<ul>
  <li>Remove or consolidate low-value URLs that inflate the discovered queue.</li>
  <li>Link to important URLs from pages that already receive crawls.</li>
  <li>Make each URL meaningfully different from its siblings.</li>
  <li>Keep sitemap coverage to canonical, indexable URLs only.</li>
  <li>After changes, request validation or inspection for a small sample — not every URL.</li>
</ul>

<blockquote>
  <p><strong>Do not</strong> repeatedly press “Request indexing” on hundreds of URLs. It does not create crawl budget, and it hides the structural issue you need to fix.</p>
</blockquote>

<h2>Verification</h2>
<p>Recheck the same sample after a crawl cycle. Success looks like a move from “Discovered” to “Crawled” or “Indexed”, plus a matching entry in URL Inspection. Record the date, the sample and the change you made so you can attribute the result.</p>
""",
            },
            {
                "slug": "crawled-currently-not-indexed",
                "title": "Crawled – currently not indexed",
                "description": "Investigate crawl eligibility, directives and canonicals.",
                "duration_minutes": 20,
                "problem": "crawled",
                "order": 2,
                "objectives": [
                    "Explain why a crawled URL can still be excluded from the index.",
                    "Audit canonical, robots and content signals in the right order.",
                    "Decide whether an exclusion is intentional or needs a fix.",
                ],
                "key_takeaways": [
                    "A successful crawl only proves Googlebot could fetch the page.",
                    "Canonical conflicts are a common reason a crawled URL is not indexed.",
                    "Thin or near-duplicate content can be crawled and still rejected.",
                ],
                "body": """
<p class="lead">“Crawled – currently not indexed” is the most misunderstood status in Search Console. Google fetched the page successfully and then decided not to index it. The cause is usually in the page signals, not in crawl access.</p>

<h2>Start with the page Google actually saw</h2>
<p>Use URL Inspection and open the <strong>More info</strong> section. Compare the crawled HTML with what you expect. Check the canonical, meta robots, X-Robots-Tag and the rendered content. A page can look correct in a browser and still send a conflicting signal to Google.</p>

<figure>
  <img src="/static/img/lesson/render-check.svg" alt="Mock URL Inspection rendered HTML panel comparing raw and rendered content" width="1200" height="700">
  <figcaption>Compare raw and rendered HTML. A canonical or noindex added by JavaScript is easy to miss.</figcaption>
</figure>

<h2>The usual suspects</h2>
<table>
  <thead>
    <tr><th>Signal</th><th>What to check</th><th>Typical fix</th></tr>
  </thead>
  <tbody>
    <tr><td>Canonical</td><td>Self-referencing? Consistent with internal links and sitemap?</td><td>Choose one canonical URL and align every signal.</td></tr>
    <tr><td>Meta robots</td><td>Accidental <code>noindex</code> in a template, CMS setting or header?</td><td>Remove the directive only where indexing is intended.</td></tr>
    <tr><td>Duplication</td><td>Near-identical variants, filters, pagination or syndicated copy?</td><td>Consolidate, canonicalise or keep excluded deliberately.</td></tr>
    <tr><td>Thin content</td><td>Does the page answer a distinct intent with unique value?</td><td>Improve or merge; do not pad word count.</td></tr>
    <tr><td>Soft 404</td><td>Empty results, expired products or error copy served with 200?</td><td>Return a real 404/410 or restore meaningful content.</td></tr>
  </tbody>
</table>

<h3>Canonical example</h3>
<pre><code>&lt;link rel="canonical" href="https://example.com/guides/search-console/"&gt;
&lt;meta name="robots" content="index,follow"&gt;</code></pre>
<p>If the canonical points to a different URL, Google may treat this page as an alternate and exclude it from the index. That is correct when the pages are duplicates and wrong when they serve different intents.</p>

<h2>Intentional exclusions</h2>
<p>Not every crawled-not-indexed URL needs action. Internal search results, filtered listings, staging URLs and low-value archives are often excluded on purpose. The question is not “how do I force indexing?” but “should this URL be indexed at all?”</p>

<blockquote>
  <p><strong>Decision rule:</strong> if the URL has a unique search intent, a self-canonical and useful content, treat the exclusion as a defect. If it is a duplicate or utility URL, document the exclusion and move on.</p>
</blockquote>

<h2>Verification plan</h2>
<ol>
  <li>Capture the current inspection screenshot or notes.</li>
  <li>Fix one signal at a time and record the change date.</li>
  <li>Request inspection for the sample URL after deployment.</li>
  <li>Recheck after the next crawl. Do not judge within hours.</li>
  <li>If the status persists, compare a working URL from the same template. Differences reveal the cause faster than guessing.</li>
</ol>
""",
            },
        ],
    },
    {
        "order": 3,
        "title": "Level 3 — Technical SEO",
        "subtitle": "Analyze HTTP, crawling, rendering and server behavior",
        "status": LearningLevel.Status.NOT_STARTED,
        "lessons": [
            {
                "slug": "http-status-codes-server-errors",
                "title": "HTTP status codes & server errors",
                "description": "5xx, redirects, timeouts and log analysis.",
                "duration_minutes": 16,
                "order": 1,
                "objectives": [
                    "Read HTTP status codes correctly during a crawl investigation.",
                    "Distinguish transient server errors from persistent access problems.",
                    "Use logs to confirm what Googlebot actually received.",
                ],
                "key_takeaways": [
                    "A 5xx tells Google the URL may return later; repeated 5xx erodes crawl trust.",
                    "Redirect chains waste crawl requests and can hide the final status.",
                    "Server logs are the best evidence for intermittent failures.",
                ],
                "body": """
<p class="lead">Status codes are the contract between your server and Googlebot. When indexing looks wrong, verify the contract before editing content.</p>

<h2>Status codes you need to know</h2>
<table>
  <thead>
    <tr><th>Code</th><th>Meaning</th><th>Crawl implication</th></tr>
  </thead>
  <tbody>
    <tr><td>200</td><td>OK</td><td>The page is fetchable. Indexing is still a separate decision.</td></tr>
    <tr><td>301 / 308</td><td>Permanent redirect</td><td>Follow the redirect to a single final 200 URL.</td></tr>
    <tr><td>302 / 307</td><td>Temporary redirect</td><td>Fine for temporary moves; avoid using it as a permanent architecture.</td></tr>
    <tr><td>404</td><td>Not found</td><td>Expected for removed URLs. Remove them from sitemaps.</td></tr>
    <tr><td>410</td><td>Gone</td><td>Explicit permanent removal. Google may drop the URL faster.</td></tr>
    <tr><td>429</td><td>Too many requests</td><td>Slow down crawl rate or fix rate limiting.</td></tr>
    <tr><td>500 / 502 / 503</td><td>Server errors</td><td>Retryable, but persistent errors can suppress crawling.</td></tr>
  </tbody>
</table>

<h2>Triage a 5xx spike</h2>
<ol>
  <li><strong>Confirm scope.</strong> Is it one URL, one template, one host or the whole property?</li>
  <li><strong>Reproduce outside Search Console.</strong> Fetch the URL with and without a Googlebot user agent.</li>
  <li><strong>Check the origin.</strong> Load balancer, application server, database and third-party dependencies all appear as 5xx to Googlebot.</li>
  <li><strong>Look for timeouts.</strong> A slow response that exceeds the crawl timeout can look like a failure even when the page eventually renders.</li>
  <li><strong>Fix and monitor.</strong> Use logs to confirm the error rate falls before requesting validation.</li>
</ol>

<h3>Reading a log line</h3>
<pre><code>66.249.66.1 - - [12/May/2026:09:14:02 +0000] "GET /guides/gsc/ HTTP/1.1" 503 128 "-" "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"</code></pre>
<p>The status code, URL, timestamp and user agent are the four fields you need. Group by status and URL pattern to find whether failures cluster around a template or a deploy window.</p>

<blockquote>
  <p><strong>Do not</strong> return 200 with an error page to “keep the page indexed”. That creates a soft 404 and hides the real failure from monitoring.</p>
</blockquote>

<h2>Verification</h2>
<ul>
  <li>The failing URL returns a stable 200 for a Googlebot user agent.</li>
  <li>Redirects resolve in one hop to the canonical URL.</li>
  <li>Logs show the error rate returning to baseline.</li>
  <li>Search Console stops reporting new server errors for the affected pattern.</li>
</ul>
""",
            },
            {
                "slug": "rendering-javascript",
                "title": "Rendering & JavaScript",
                "description": "Crawl accessibility and rendered content.",
                "duration_minutes": 17,
                "order": 2,
                "objectives": [
                    "Compare raw HTML with the rendered DOM.",
                    "Identify content or directives injected only by JavaScript.",
                    "Test whether Googlebot can access the resources needed to render.",
                ],
                "key_takeaways": [
                    "Google can render JavaScript, but rendering is a second wave and can be delayed.",
                    "Critical content and directives should not depend on fragile client-side code.",
                    "Blocked JS or API calls can turn a rich page into an empty one for Googlebot.",
                ],
                "body": """
<p class="lead">Modern sites ship HTML, CSS and JavaScript as separate resources. Googlebot must fetch and render them before it can evaluate the final page. Every blocked or slow resource is a chance for the rendered page to differ from what users see.</p>

<h2>Raw HTML versus rendered HTML</h2>
<p>Use URL Inspection to view the crawled HTML and the rendered screenshot. If the main content, canonical or robots directive appears only after JavaScript runs, you are relying on the render wave.</p>

<figure>
  <img src="/static/img/lesson/render-check.svg" alt="Mock comparison of raw HTML and rendered page content" width="1200" height="700">
  <figcaption>If the rendered screenshot is empty but the browser looks fine, check blocked resources and API calls.</figcaption>
</figure>

<h2>Render audit checklist</h2>
<ol>
  <li><strong>Disable JavaScript</strong> in a test browser. Can you still see the primary content, title and links?</li>
  <li><strong>Check robots.txt.</strong> Are JS, CSS or API paths blocked for Googlebot?</li>
  <li><strong>Check the network panel.</strong> Which requests are required for content, and which fail intermittently?</li>
  <li><strong>Inspect the rendered DOM.</strong> Confirm that canonical, meta robots and structured data are present after rendering.</li>
  <li><strong>Test as Googlebot.</strong> Some servers serve different responses by user agent. Make sure the Googlebot response is the one you intend.</li>
</ol>

<h3>Signals that should be server-rendered</h3>
<table>
  <thead>
    <tr><th>Signal</th><th>Why it matters</th></tr>
  </thead>
  <tbody>
    <tr><td>Canonical link</td><td>Google may use the raw HTML canonical before rendering completes.</td></tr>
    <tr><td>Meta robots / X-Robots-Tag</td><td>Conflicting directives are a common source of accidental exclusion.</td></tr>
    <tr><td>Primary content and internal links</td><td>Rendering delays can leave the page looking thin.</td></tr>
    <tr><td>Structured data</td><td>Enhancement eligibility depends on the rendered markup.</td></tr>
  </tbody>
</table>

<blockquote>
  <p><strong>Practical default:</strong> server-render the title, primary content, canonical and robots directives. Use JavaScript to enhance the page, not to create the page.</p>
</blockquote>

<h2>Verification</h2>
<ul>
  <li>URL Inspection shows the expected rendered content.</li>
  <li>No required JS, CSS or API request is blocked for Googlebot.</li>
  <li>The canonical and robots directives match between raw and rendered HTML.</li>
  <li>A no-JavaScript fetch still exposes the core page and links.</li>
</ul>
""",
            },
        ],
    },
    {
        "order": 4,
        "title": "Level 4 — Search Performance",
        "subtitle": "Investigate traffic and ranking changes",
        "status": LearningLevel.Status.NOT_STARTED,
        "lessons": [
            {
                "slug": "query-and-page-filters",
                "title": "Query and page filters",
                "description": "Slice performance data to isolate the real change.",
                "duration_minutes": 13,
                "order": 1,
                "objectives": [
                    "Use query, page, country and device filters together.",
                    "Isolate whether a decline is broad or concentrated.",
                    "Compare equal periods and account for reporting lag.",
                ],
                "key_takeaways": [
                    "A site-wide average can hide a decline limited to one query group.",
                    "Filter to the smallest segment that still has enough data.",
                    "Always compare equal-length periods and note the reporting delay.",
                ],
                "body": """
<p class="lead">Performance data becomes useful when you slice it. The goal is to turn “traffic is down” into a precise statement about queries, pages, countries or devices.</p>

<h2>Build a comparison</h2>
<ol>
  <li>Open <strong>Performance</strong> and set a date range long enough to be stable, such as 28 days.</li>
  <li>Use the <strong>Compare</strong> tab with the previous period or the same period last year.</li>
  <li>Add a <strong>Query</strong> filter for the topic you care about.</li>
  <li>Add a <strong>Page</strong> filter containing a URL pattern to see whether the issue is template-wide.</li>
  <li>Split by <strong>Device</strong> or <strong>Country</strong> only after the first three slices.</li>
</ol>

<figure>
  <img src="/static/img/lesson/performance-report.svg" alt="Mock Performance report with query and page filters and a comparison period" width="1200" height="700">
  <figcaption>Filter combinations reveal whether a change is query-specific, page-specific or site-wide.</figcaption>
</figure>

<h2>Interpreting the obvious patterns</h2>
<table>
  <thead>
    <tr><th>Pattern</th><th>What it suggests</th></tr>
  </thead>
  <tbody>
    <tr><td>Impressions flat, clicks down</td><td>CTR change: titles, snippets, SERP features or intent mismatch.</td></tr>
    <tr><td>Impressions down, CTR stable</td><td>Visibility loss: ranking, indexing or demand change.</td></tr>
    <tr><td>One query down, others stable</td><td>Query-specific ranking or SERP change; check the page and competitors.</td></tr>
    <tr><td>One page down across queries</td><td>Page-level issue: content, canonical, rendering or a recent deploy.</td></tr>
    <tr><td>All pages in a template down</td><td>Template, internal linking or technical regression.</td></tr>
  </tbody>
</table>

<blockquote>
  <p><strong>Sample-size warning:</strong> a 40% drop on 10 impressions is noise. Require enough clicks or impressions before treating a percentage as meaningful.</p>
</blockquote>

<h2>Save the evidence</h2>
<p>Export the filtered table or capture a screenshot before you change anything. Record the filter set, date range and comparison period. Without that, you cannot tell whether a later “recovery” is real or just a different slice.</p>

<h2>Verification</h2>
<ul>
  <li>The decline is reproducible with the same filters.</li>
  <li>A control segment (another query or page group) did not move in the same way.</li>
  <li>The timing matches a deploy, content change or known SERP update.</li>
  <li>The fix is measured against the same filtered view.</li>
</ul>
""",
            },
            {
                "slug": "ranking-change-triage",
                "title": "Ranking change triage",
                "description": "Separate demand shifts from visibility shifts.",
                "duration_minutes": 15,
                "order": 2,
                "objectives": [
                    "Distinguish demand, ranking and CTR changes.",
                    "Prioritise investigations using impact and confidence.",
                    "Design a verification step for each hypothesis.",
                ],
                "key_takeaways": [
                    "Not every traffic decline is a ranking decline.",
                    "Impressions proxy demand; position proxies visibility; CTR proxies snippet appeal.",
                    "Change one variable at a time so verification is possible.",
                ],
                "body": """
<p class="lead">A ranking change is a hypothesis, not a diagnosis. Triage first: demand, visibility and click-through can all move independently.</p>

<h2>The three-way split</h2>
<table>
  <thead>
    <tr><th>Metric</th><th>Question</th><th>If it moves alone</th></tr>
  </thead>
  <tbody>
    <tr><td>Impressions</td><td>Are users still searching this topic?</td><td>Demand or query-mix change.</td></tr>
    <tr><td>Average position</td><td>Is the page still visible for the same queries?</td><td>Ranking or SERP-layout change.</td></tr>
    <tr><td>CTR</td><td>Does the result still earn clicks when shown?</td><td>Title, snippet or intent mismatch.</td></tr>
  </tbody>
</table>

<h2>Triage sequence</h2>
<ol>
  <li><strong>Define the segment.</strong> One query group, one page template or one country — not the whole site.</li>
  <li><strong>Check demand.</strong> Compare impressions for the same queries. If impressions fell, the market may have moved.</li>
  <li><strong>Check visibility.</strong> Compare average position and the number of queries ranking in the top 10.</li>
  <li><strong>Check the SERP.</strong> New features, AI summaries, shopping units or competitor changes can reduce clicks without a ranking loss.</li>
  <li><strong>Check the page.</strong> Recent deploy, canonical change, rendering failure, content removal or internal-link loss.</li>
  <li><strong>Write one hypothesis and one test.</strong> Avoid changing title, content and internal links on the same day.</li>
</ol>

<blockquote>
  <p><strong>Impact × confidence:</strong> fix the high-impact, high-confidence issue first. A dramatic theory with no evidence is usually a distraction.</p>
</blockquote>

<h2>Common false alarms</h2>
<ul>
  <li><strong>Seasonality:</strong> compare year over year, not only week over week.</li>
  <li><strong>Reporting lag:</strong> the last two or three days are incomplete.</li>
  <li><strong>Query cannibalisation:</strong> one URL replaces another; total visibility may be unchanged.</li>
  <li><strong>Brand vs non-brand:</strong> a brand spike can mask a non-brand decline.</li>
</ul>

<h2>Verification</h2>
<p>State the expected result before deploying: for example, “the affected query group should regain top-10 visibility within two crawl cycles while the control group stays flat.” Then measure the same filtered view and record the outcome, including a negative result.</p>
""",
            },
        ],
    },
    {
        "order": 5,
        "title": "Level 5 — Advanced SEO",
        "subtitle": "Handle large-scale and complex technical cases",
        "status": LearningLevel.Status.NOT_STARTED,
        "lessons": [
            {
                "slug": "large-site-auditing",
                "title": "Large-site auditing",
                "description": "Segment, sample and prioritize at scale.",
                "duration_minutes": 22,
                "order": 1,
                "objectives": [
                    "Design a sampling plan that represents templates and URL patterns.",
                    "Separate crawl waste from indexing and quality problems.",
                    "Prioritise fixes by coverage, impact and verification cost.",
                ],
                "key_takeaways": [
                    "On large sites, patterns matter more than individual URLs.",
                    "Sample across templates and traffic tiers, not just the first 100 URLs.",
                    "Measure the size of each issue before choosing a fix.",
                ],
                "body": """
<p class="lead">Large-site work is pattern work. You cannot inspect every URL, so you sample deliberately and let the pattern tell you where the leverage is.</p>

<h2>Build a URL inventory</h2>
<ol>
  <li>Group URLs by template: product, category, article, tag, search, filter, pagination.</li>
  <li>Add traffic and index status for each group.</li>
  <li>Estimate the number of URLs and the share that are indexable.</li>
  <li>Mark URLs that exist only for users, only for crawlers, or for both.</li>
</ol>

<table>
  <thead>
    <tr><th>Segment</th><th>URL count</th><th>Indexed</th><th>Primary risk</th></tr>
  </thead>
  <tbody>
    <tr><td>Product detail</td><td>12,400</td><td>78%</td><td>Out-of-stock variants and duplicate descriptions.</td></tr>
    <tr><td>Category</td><td>340</td><td>91%</td><td>Thin pages at deep pagination.</td></tr>
    <tr><td>Faceted filter</td><td>48,000</td><td>6%</td><td>Crawl waste and near-duplicate combinations.</td></tr>
    <tr><td>Editorial guide</td><td>610</td><td>88%</td><td>Canonical drift after migrations.</td></tr>
    <tr><td>Internal search</td><td>Unbounded</td><td>&lt;1%</td><td>Should remain excluded and unlinked.</td></tr>
  </tbody>
</table>

<h2>Sampling that survives scrutiny</h2>
<ul>
  <li>Sample 30–50 URLs per template, including high-traffic and low-traffic examples.</li>
  <li>Include URLs from each crawl-depth band, not only sitemap entries.</li>
  <li>Record the sample method so another person can reproduce it.</li>
  <li>Recheck the same sample after a fix; do not switch samples to find a better result.</li>
</ul>

<h2>Prioritisation</h2>
<ol>
  <li><strong>Coverage:</strong> how many URLs does the issue affect?</li>
  <li><strong>Impact:</strong> does it block indexing or clicks on valuable pages?</li>
  <li><strong>Confidence:</strong> do you have evidence from logs, inspection and rendering?</li>
  <li><strong>Cost:</strong> can the fix be applied at the template level?</li>
</ol>

<blockquote>
  <p><strong>Leverage test:</strong> a template fix that affects 10,000 URLs is usually worth more than manually requesting indexing for 50 pages.</p>
</blockquote>

<h2>Verification</h2>
<ul>
  <li>The issue count falls in Search Console for the affected pattern.</li>
  <li>The sample URLs move to the expected status.</li>
  <li>Crawl requests shift away from waste and toward valuable URLs in logs.</li>
  <li>Performance for the affected segment is measured against a control segment.</li>
</ul>
""",
            },
        ],
    },
]

SCENARIOS = [
    {
        "slug": "discovered",
        "problem": "discovered",
        "title": "Discovered – not indexed",
        "category_label": "Indexing",
        "issue": "Discovered – currently not indexed",
        "summary": "42 URLs discovered but not indexed.",
        "description": (
            "A blog migration last month moved the entire article archive to a new URL "
            "structure. The sitemap is accepted and the pages return 200 OK when you "
            "test them manually, yet 42 URLs remain discovered but not indexed. Use the "
            "simulated reports to decide whether this is a crawling, canonicalization "
            "or discovery problem — and what to fix first."
        ),
        "tone": Tone.WARN,
        "report_title": "Indexing Report — Fictional Property",
        "order": 1,
        "metrics": [
            {"label": "Indexed URLs", "value": "1,284", "delta": "▲ 0.5%", "tone": "ok", "note": "Previous: 1,290"},
            {"label": "Discovered – not indexed", "value": "42", "delta": "▲ 10%", "tone": "warn", "note": "Previous: 38"},
            {"label": "Crawled – not indexed", "value": "7", "delta": "▲ 40%", "tone": "warn", "note": "Previous: 5"},
            {"label": "Crawl errors", "value": "3", "delta": "stable", "tone": "danger", "note": "2 server errors"},
        ],
        "urls": [
            {
                "url": "https://example.com/blog/seo-tips",
                "final_url": "https://example.com/blog/seo-tips",
                "indexability": "Discovered – currently not indexed",
                "indexability_tone": "warn",
                "crawlability": "Discovered",
                "state": "200 OK",
            },
            {
                "url": "https://example.com/docs/technical-seo",
                "final_url": "https://example.com/docs/technical-seo",
                "indexability": "Blocked by robots.txt",
                "indexability_tone": "danger",
                "crawlability": "Blocked",
                "state": "200 OK",
            },
            {
                "url": "https://example.com/blog/canonical-issue",
                "final_url": "https://example.com/blog/seo-tips",
                "indexability": "Crawled – currently not indexed",
                "indexability_tone": "warn",
                "crawlability": "Crawled",
                "state": "200 OK",
            },
        ],
        "sitemap": {"status": "Fetched", "tone": "ok", "submitted": "1,290", "excluded": "6", "errors": "1"},
        "page_experience": {
            "status": "Needs improvement",
            "tone": "warn",
            "lcp": "3.2s",
            "lcp_tone": "warn",
            "inp": "180ms",
            "cls": "0.05",
        },
        "checklist": [
            "Confirmed the reported status in the Indexing report",
            "Checked whether the URL appears in the submitted sitemap",
            "Inspected the rendered HTML for noindex or canonical hints",
            "Verified the HTTP response and redirect chain",
        ],
        "expected_cause": "the URL is discovered through the sitemap but has weak internal discovery signals and an intermittent 504. Fix internal linking, confirm stable response times, then request indexing.",
        "solution": (
            "The sitemap tells Google the URLs exist, but the pages have very few "
            "internal links and the origin intermittently returns a 504. Google can "
            "discover the URLs but deprioritises crawling them. Strengthen internal "
            "discovery and stabilise the server before requesting indexing."
        ),
        "solution_steps": [
            "Audit the sitemap and confirm every affected URL is listed and returns a consistent 200 OK.",
            "Add contextual internal links from indexed, high-traffic pages to the affected URLs.",
            "Find and fix the intermittent 504 at the origin or CDN, then monitor response times.",
            "Use URL Inspection to test the live URL before requesting indexing for the highest-value pages.",
            "Recheck the Page indexing report after one to two weeks and track the count trend.",
        ],
    },
    {
        "slug": "canonical",
        "problem": "crawled",
        "title": "Duplicate canonical",
        "category_label": "Canonicalization",
        "issue": "Duplicate, Google chose different canonical",
        "summary": "11 URL groups collapse to one canonical.",
        "description": (
            "A newsletter campaign appended tracking parameters to blog links, and a "
            "trailing-slash variant of the same article is also live. Search Console "
            "reports 11 URL groups as duplicate with a different canonical, so ranking "
            "signals are split across variants. Work out which URL should win and how "
            "to consolidate the rest."
        ),
        "tone": Tone.BRAND,
        "report_title": "Indexing Report — Fictional Property",
        "order": 2,
        "metrics": [
            {"label": "Indexed URLs", "value": "1,284", "delta": "▲ 0.5%", "tone": "ok", "note": "Previous: 1,290"},
            {"label": "Duplicate, different canonical", "value": "11", "delta": "▲ 2", "tone": "warn", "note": "11 URL groups"},
            {"label": "Alternate page with canonical", "value": "8", "delta": "stable", "tone": "warn", "note": "Consolidated"},
            {"label": "Crawl errors", "value": "3", "delta": "stable", "tone": "danger", "note": "2 server errors"},
        ],
        "urls": [
            {
                "url": "https://example.com/blog/seo-tips?utm_source=newsletter",
                "final_url": "https://example.com/blog/seo-tips",
                "indexability": "Duplicate, Google chose different canonical",
                "indexability_tone": "warn",
                "crawlability": "Crawled",
                "state": "200 OK",
            },
            {
                "url": "https://example.com/blog/seo-tips/",
                "final_url": "https://example.com/blog/seo-tips",
                "indexability": "Alternate page with proper canonical",
                "indexability_tone": "neutral",
                "crawlability": "Crawled",
                "state": "200 OK",
            },
            {
                "url": "https://example.com/blog/canonical-issue",
                "final_url": "https://example.com/blog/seo-tips",
                "indexability": "Crawled – currently not indexed",
                "indexability_tone": "warn",
                "crawlability": "Crawled",
                "state": "200 OK",
            },
        ],
        "sitemap": {"status": "Fetched", "tone": "ok", "submitted": "1,290", "excluded": "6", "errors": "1"},
        "page_experience": {
            "status": "Good",
            "tone": "ok",
            "lcp": "2.1s",
            "lcp_tone": "ok",
            "inp": "140ms",
            "cls": "0.02",
        },
        "checklist": [
            "Compared the inspected URL with the chosen canonical",
            "Checked for tracking parameters and trailing-slash variants",
            "Confirmed the canonical tag is self-referencing where appropriate",
            "Checked internal links for the non-canonical variants",
        ],
        "expected_cause": "tracking parameters and a trailing-slash variant create duplicate URLs. Use a single canonical version, link internally to it, and keep the canonical tag self-referencing.",
        "solution": (
            "Tracking parameters and the trailing-slash variant create near-duplicate "
            "URLs. Google consolidates them onto whichever URL it considers strongest, "
            "which is not always the one you declared. Standardise on one canonical URL "
            "and remove the competing signals."
        ),
        "solution_steps": [
            "Pick one canonical URL per article — usually the clean, slash-free version.",
            "Add a self-referencing canonical tag to every indexable page.",
            "Update internal links, sitemap entries and campaign links to point at the canonical URL.",
            "Use 301 redirects for legacy variants that should no longer exist.",
            "Verify the canonical selection with URL Inspection and recheck the Duplicate report after recrawling.",
        ],
    },
    {
        "slug": "robots",
        "problem": "robots",
        "title": "Blocked by robots.txt",
        "category_label": "Crawling",
        "issue": "Blocked by robots.txt",
        "summary": "A staging rule leaked into production.",
        "description": (
            "A deployment copied the staging robots.txt file into production. Sixteen "
            "documentation URLs that previously ranked are now reported as blocked by "
            "robots.txt. Decide whether the block is intentional, trace the rule to its "
            "source, and restore crawling without exposing private paths."
        ),
        "tone": Tone.DANGER,
        "report_title": "Indexing Report — Fictional Property",
        "order": 3,
        "metrics": [
            {"label": "Indexed URLs", "value": "1,284", "delta": "▼ 0.2%", "tone": "danger", "note": "Previous: 1,287"},
            {"label": "Blocked by robots.txt", "value": "16", "delta": "▲ 16", "tone": "danger", "note": "New this week"},
            {"label": "Crawled – not indexed", "value": "7", "delta": "stable", "tone": "warn", "note": "Previous: 7"},
            {"label": "Crawl errors", "value": "3", "delta": "stable", "tone": "danger", "note": "2 server errors"},
        ],
        "urls": [
            {
                "url": "https://example.com/docs/technical-seo",
                "final_url": "https://example.com/docs/technical-seo",
                "indexability": "Blocked by robots.txt",
                "indexability_tone": "danger",
                "crawlability": "Blocked",
                "state": "200 OK",
            },
            {
                "url": "https://example.com/docs/crawling",
                "final_url": "https://example.com/docs/crawling",
                "indexability": "Blocked by robots.txt",
                "indexability_tone": "danger",
                "crawlability": "Blocked",
                "state": "200 OK",
            },
            {
                "url": "https://example.com/blog/seo-tips",
                "final_url": "https://example.com/blog/seo-tips",
                "indexability": "Discovered – currently not indexed",
                "indexability_tone": "warn",
                "crawlability": "Discovered",
                "state": "200 OK",
            },
        ],
        "sitemap": {"status": "Fetched", "tone": "ok", "submitted": "1,290", "excluded": "6", "errors": "1"},
        "page_experience": {
            "status": "Good",
            "tone": "ok",
            "lcp": "2.4s",
            "lcp_tone": "ok",
            "inp": "160ms",
            "cls": "0.03",
        },
        "checklist": [
            "Fetched robots.txt and located the matching rule",
            "Checked whether the rule came from a staging configuration",
            "Confirmed the rule targets the correct path pattern",
            "Re-tested the URL with URL Inspection after the change",
        ],
        "expected_cause": "a staging Disallow rule was copied to production. Remove the rule, confirm robots.txt is publicly fetchable, then request indexing.",
        "solution": (
            "A staging Disallow rule is blocking production URLs. Google cannot fetch "
            "blocked URLs, so it cannot index or refresh them. Remove the leaked rule, "
            "confirm the file is publicly readable, and let Google recrawl."
        ),
        "solution_steps": [
            "Fetch /robots.txt and locate the Disallow rule that matches the affected paths.",
            "Compare the file against the staging configuration and remove the leaked rule.",
            "Keep intentional private paths blocked with narrowly scoped rules.",
            "Confirm robots.txt returns 200 OK and is not blocked by the CDN or WAF.",
            "Request indexing for the affected URLs and monitor the Blocked by robots.txt count.",
        ],
    },
    {
        "slug": "server",
        "problem": "server-error",
        "title": "5xx server errors",
        "category_label": "Server",
        "issue": "Server error (5xx)",
        "summary": "Timeouts after a traffic spike.",
        "description": (
            "A flash sale drove a traffic spike, and Crawl Stats now shows 128 server "
            "errors in 24 hours. Product pages are returning 503 and 504 responses to "
            "Googlebot while normal visitors still see intermittent errors. Diagnose "
            "whether the problem is capacity, caching or bot protection before changing "
            "anything."
        ),
        "tone": Tone.DANGER,
        "report_title": "Crawl Stats — Fictional Property",
        "order": 4,
        "metrics": [
            {"label": "Indexed URLs", "value": "1,284", "delta": "▼ 0.4%", "tone": "danger", "note": "Previous: 1,289"},
            {"label": "Server errors (5xx)", "value": "128", "delta": "▲ 128", "tone": "danger", "note": "Last 24 hours"},
            {"label": "Crawled – not indexed", "value": "7", "delta": "stable", "tone": "warn", "note": "Previous: 7"},
            {"label": "Avg. response time", "value": "1.8s", "delta": "▲ 60%", "tone": "danger", "note": "Previous: 1.1s"},
        ],
        "urls": [
            {
                "url": "https://example.com/products/peak",
                "final_url": "https://example.com/products/peak",
                "indexability": "Server error (5xx)",
                "indexability_tone": "danger",
                "crawlability": "Crawled",
                "state": "504 Gateway Timeout",
            },
            {
                "url": "https://example.com/products/sale",
                "final_url": "https://example.com/products/sale",
                "indexability": "Server error (5xx)",
                "indexability_tone": "danger",
                "crawlability": "Crawled",
                "state": "503 Service Unavailable",
            },
            {
                "url": "https://example.com/blog/seo-tips",
                "final_url": "https://example.com/blog/seo-tips",
                "indexability": "Discovered – currently not indexed",
                "indexability_tone": "warn",
                "crawlability": "Discovered",
                "state": "200 OK",
            },
        ],
        "sitemap": {"status": "Fetched", "tone": "ok", "submitted": "1,290", "excluded": "6", "errors": "1"},
        "page_experience": {
            "status": "Poor",
            "tone": "danger",
            "lcp": "6.4s",
            "lcp_tone": "danger",
            "inp": "420ms",
            "cls": "0.12",
        },
        "checklist": [
            "Checked Crawl Stats for the 5xx error trend",
            "Filtered server logs by Googlebot user agent",
            "Compared error timestamps with traffic spikes",
            "Reviewed CDN, WAF and application timeout settings",
        ],
        "expected_cause": "a traffic spike saturates the origin and requests time out. Add caching or capacity, raise the timeout budget, and confirm a stable 200 response before recrawling.",
        "solution": (
            "The origin is saturated during traffic spikes, so requests from Googlebot "
            "time out or are rejected. Repeated 5xx responses reduce crawl rate and can "
            "drop pages from the index. Stabilise the origin before requesting a "
            "recrawl."
        ),
        "solution_steps": [
            "Check Crawl Stats and server logs to confirm the 5xx trend and the affected paths.",
            "Compare error timestamps with traffic spikes, deploys and cache purges.",
            "Add caching or capacity, and raise timeout budgets where appropriate.",
            "Allow verified Googlebot traffic through the WAF or bot-protection layer.",
            "Confirm a stable 200 response with URL Inspection before requesting indexing.",
        ],
    },
]

TOPICS = [
    {
        "slug": "discovered-not-indexed",
        "title": "Discovered – currently not indexed",
        "example_question": "My site pages are discovered not index. What can be the problem?",
        "keywords": [
            "discovered",
            "not index",
            "not indexed",
            "discovered not index",
            "discovered - currently not indexed",
        ],
        "explanation": "Your pages are marked “Discovered – currently not indexed” in Google Search Console. This means Google found the URLs but has not added them to its index yet.",
        "definition": "Discovered – currently not indexed means Google discovered the page through discovery signals (such as your sitemap or internal links) but has not indexed it. It does not mean the page is broken — it means indexing has not happened.",
        "causes": [
            "Sitemap omission: the URL may be missing or incorrect in your submitted sitemap.",
            "Weak internal discovery signals: few or no internal links point to the page, so crawl priority may be low.",
            "Crawl accessibility: intermittent issues such as HTTP 504 may prevent reliable crawling.",
        ],
        "articles": [
            {
                "title": "Internal linking and discovery signals",
                "description": "How internal links help Google discover and prioritize pages.",
            },
            {
                "title": "Sitemap submission and validation",
                "description": "How to check sitemap inclusion and validity.",
            },
        ],
        "external_resources": [
            {
                "title": "Google Search Central — Indexing & crawling documentation",
                "url": "https://developers.google.com/search/docs",
            },
            {
                "title": "Google Search Console Help — Index coverage troubleshooting",
                "url": "https://support.google.com/webmasters/",
            },
        ],
        "is_default": True,
        "order": 1,
        "problem": "discovered",
    },
    {
        "slug": "crawled-not-indexed",
        "title": "Crawled – currently not indexed",
        "example_question": "Google crawled my page but still won't index it. Why?",
        "keywords": ["crawled", "crawled not indexed", "crawled - currently not indexed"],
        "explanation": "Google fetched the page, so the URL is reachable. The remaining question is why Google decided the page does not deserve an index entry.",
        "definition": "Crawled – currently not indexed means Googlebot successfully fetched the page but chose not to index it. Common causes are duplicate content, weak quality signals or conflicting directives.",
        "causes": [
            "The page is a near-duplicate of another indexed URL.",
            "A canonical or noindex directive points Google elsewhere.",
            "The content adds little unique value compared with competing pages.",
        ],
        "articles": [
            {
                "title": "Canonicalization for SEO",
                "description": "How Google chooses a canonical and how to make it explicit.",
            },
            {
                "title": "Evaluating content quality",
                "description": "Signals that make a page worth indexing.",
            },
        ],
        "external_resources": [
            {
                "title": "Google Search Central — Page indexing report",
                "url": "https://support.google.com/webmasters/answer/7440203",
            }
        ],
        "order": 2,
        "problem": "crawled",
    },
    {
        "slug": "blocked-by-robots",
        "title": "Blocked by robots.txt",
        "example_question": "Google says my page is blocked by robots.txt. How do I fix it?",
        "keywords": ["robots", "robots.txt", "blocked", "disallow"],
        "explanation": "A robots.txt rule is telling Googlebot not to fetch the affected URLs, so they cannot be crawled or indexed.",
        "definition": "Blocked by robots.txt means the URL matches a Disallow rule for Googlebot. Google may still list the URL if other pages link to it, but it will not fetch the content.",
        "causes": [
            "A staging or development robots.txt file was deployed to production.",
            "A broad Disallow pattern also matches pages that should be indexed.",
            "The rule is intentional, but the URL should not be promoted in search.",
        ],
        "articles": [
            {
                "title": "robots.txt basics",
                "description": "How crawling rules are matched, including longest-match behaviour.",
            },
            {
                "title": "Debugging robots.txt changes",
                "description": "A safe workflow for editing and deploying rules.",
            },
        ],
        "external_resources": [
            {
                "title": "Google Search Central — robots.txt specifications",
                "url": "https://developers.google.com/search/docs/crawling-indexing/robots/intro",
            }
        ],
        "order": 3,
        "problem": "robots",
    },
    {
        "slug": "canonical-issues",
        "title": "Canonical and duplicate pages",
        "example_question": "Google chose a different canonical than the one I declared.",
        "keywords": ["canonical", "duplicate", "alternate page", "different canonical"],
        "explanation": "Google consolidates duplicate URLs into a single canonical. If it disagrees with your declaration, it found stronger signals pointing elsewhere.",
        "definition": "“Duplicate, Google chose different canonical” means Google indexed a different URL as the canonical for a group of similar pages.",
        "causes": [
            "Internal links point to a different URL than the declared canonical.",
            "Tracking parameters or trailing slashes create competing variants.",
            "The canonical tag conflicts with a redirect or sitemap entry.",
        ],
        "articles": [
            {
                "title": "Consolidating duplicate URLs",
                "description": "Canonical tags, redirects and internal linking.",
            },
            {
                "title": "Self-referencing canonicals",
                "description": "Why every indexable page should name itself.",
            },
        ],
        "external_resources": [
            {
                "title": "Google Search Central — Consolidate duplicate URLs",
                "url": "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
            }
        ],
        "order": 4,
        "problem": "crawled",
    },
    {
        "slug": "server-errors",
        "title": "Server errors (5xx)",
        "example_question": "Googlebot is hitting 5xx errors on my site. What should I check?",
        "keywords": ["5xx", "server error", "503", "504", "timeout", "gateway"],
        "explanation": "5xx responses tell Googlebot that the server failed to fulfil a valid request. Repeated failures slow crawling and can remove pages from the index.",
        "definition": "Server error (5xx) means the origin, proxy or CDN returned an error while Googlebot was fetching the page.",
        "causes": [
            "The origin times out under load or during traffic spikes.",
            "A WAF or bot-protection rule rejects Googlebot requests.",
            "A recent deploy introduced an application error.",
        ],
        "articles": [
            {
                "title": "Reading Crawl Stats",
                "description": "Spot response-time and error-rate trends.",
            },
            {
                "title": "Bot filtering vs. blocking",
                "description": "How to verify Googlebot without breaking crawling.",
            },
        ],
        "external_resources": [
            {
                "title": "Google Search Central — HTTP network errors",
                "url": "https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
            }
        ],
        "order": 5,
        "problem": "server-error",
    },
]


def _problem(slug):
    return Problem.objects.get(slug=slug)


@transaction.atomic
def seed_all():
    """Create or refresh all demo content. Safe to run repeatedly."""

    categories = {}
    for name, slug, tone, description in CATEGORIES:
        categories[slug], _ = ProblemCategory.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "tone": tone, "description": description},
        )

    problems = {}
    for item in PROBLEMS:
        problem, _ = Problem.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "category": categories[item["category"]],
                "name": item["name"],
                "summary": item["summary"],
                "badge": item["badge"],
                "is_featured": True,
                "order": item["order"],
            },
        )
        problems[item["slug"]] = problem

    for problem_slug, flow in FLOWS.items():
        workflow, _ = Workflow.objects.update_or_create(
            slug=flow["slug"],
            defaults={
                "problem": problems[problem_slug],
                "title": flow["title"],
                "summary": flow["summary"],
                "version": "1.0",
                "is_published": True,
                "is_featured": flow["featured"],
                "order": flow["order"],
            },
        )
        workflow.nodes.all().delete()
        for index, node in enumerate(flow["nodes"], start=1):
            WorkflowNode.objects.create(
                workflow=workflow,
                kind=node["kind"],
                key=node.get("key", ""),
                title=node["title"],
                prompt=node.get("prompt", ""),
                hint=node.get("hint", ""),
                options=node.get("options", []),
                config=node.get("config", {}),
                order=index,
            )

    resource_categories = {}
    for name, slug, order in RESOURCE_CATEGORIES:
        resource_categories[slug], _ = ResourceCategory.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "order": order},
        )

    for item in RESOURCES:
        Resource.objects.update_or_create(
            title=item["title"],
            defaults={
                "category": resource_categories[item["category"]],
                "url": item["url"],
                "description": item["description"],
                "status": item.get("status", Resource.Status.ACTIVE),
                "tone": item["tone"],
                "icon": item["icon"],
                "tags": item["tags"],
                "checked_on": item.get("checked_on"),
                "is_featured": item.get("is_featured", False),
                "order": item["order"],
            },
        )

    for item in RESOURCE_CONTEXTS:
        ResourceContext.objects.update_or_create(
            title=item["title"],
            defaults={
                "category": resource_categories[item["category"]],
                "description": item["description"],
                "link_url": item["link_url"],
                "link_label": item["link_label"],
                "tone": item["tone"],
                "order": item["order"],
            },
        )

    path, _ = LearningPath.objects.update_or_create(
        title="GSC Problem Solving",
        defaults={
            "description": "Progress from GSC fundamentals to advanced technical SEO, one level at a time.",
            "is_active": True,
        },
    )

    for level_data in LEVELS:
        level, _ = LearningLevel.objects.update_or_create(
            path=path,
            order=level_data["order"],
            defaults={
                "title": level_data["title"],
                "subtitle": level_data["subtitle"],
                "status": level_data["status"],
            },
        )
        for lesson in level_data["lessons"]:
            lesson_obj, created = Lesson.objects.get_or_create(
                slug=lesson["slug"],
                defaults={
                    "level": level,
                    "title": lesson["title"],
                    "description": lesson["description"],
                    "body": lesson.get("body", ""),
                    "objectives": lesson.get("objectives", []),
                    "key_takeaways": lesson.get("key_takeaways", []),
                    "duration_minutes": lesson.get("duration_minutes", 10),
                    "is_completed": lesson.get("is_completed", False),
                    "is_published": lesson.get("is_published", True),
                    "problem": problems.get(lesson.get("problem")),
                    "order": lesson["order"],
                },
            )
            if created:
                continue

            # Never overwrite tutorial content that an editor has authored in
            # the admin. Structural metadata and empty legacy rows are refreshed.
            updates = []
            for field, value in (
                ("level", level),
                ("order", lesson["order"]),
                ("is_published", lesson.get("is_published", True)),
            ):
                if getattr(lesson_obj, field) != value:
                    setattr(lesson_obj, field, value)
                    updates.append(field)

            if not lesson_obj.body:
                lesson_obj.body = lesson.get("body", "")
                updates.append("body")
            if not lesson_obj.objectives:
                lesson_obj.objectives = lesson.get("objectives", [])
                updates.append("objectives")
            if not lesson_obj.key_takeaways:
                lesson_obj.key_takeaways = lesson.get("key_takeaways", [])
                updates.append("key_takeaways")

            if updates:
                lesson_obj.save(update_fields=updates + ["updated_at"])

    for item in SCENARIOS:
        PracticeScenario.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "problem": problems.get(item.get("problem")),
                "category_label": item["category_label"],
                "issue": item["issue"],
                "summary": item["summary"],
                "description": item.get("description", ""),
                "tone": item["tone"],
                "report_title": item["report_title"],
                "metrics": item["metrics"],
                "urls": item["urls"],
                "sitemap": item["sitemap"],
                "page_experience": item["page_experience"],
                "checklist": item["checklist"],
                "expected_cause": item["expected_cause"],
                "solution": item.get("solution", ""),
                "solution_steps": item.get("solution_steps", []),
                "is_active": True,
                "order": item["order"],
            },
        )

    for item in TOPICS:
        KnowledgeTopic.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "problem": problems.get(item.get("problem")),
                "example_question": item.get("example_question", ""),
                "keywords": item["keywords"],
                "explanation": item["explanation"],
                "definition": item.get("definition", ""),
                "causes": item.get("causes", []),
                "articles": item.get("articles", []),
                "external_resources": item.get("external_resources", []),
                "is_default": item.get("is_default", False),
                "is_suggestion": item.get("is_suggestion", True),
                "order": item["order"],
            },
        )

    for item in KNOWLEDGE_DOCS:
        KnowledgeDocument.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "doc_type": item.get("doc_type", KnowledgeDocument.DocType.ARTICLE),
                "url": item.get("url", ""),
                "summary": item.get("summary", ""),
                "body": item["body"],
                "review_status": KnowledgeDocument.ReviewStatus.APPROVED,
                "reviewed_on": item.get("reviewed_on"),
                "is_published": True,
            },
        )

    for item in SEARCH_TERMS:
        SearchTerm.objects.update_or_create(
            term=item["term"],
            defaults={
                "misspellings": item.get("misspellings", []),
                "synonyms": item.get("synonyms", []),
                "category": categories.get(item.get("category")),
            },
        )

    reindex_all()

    return {
        "categories": ProblemCategory.objects.count(),
        "problems": Problem.objects.count(),
        "workflows": Workflow.objects.count(),
        "nodes": WorkflowNode.objects.count(),
        "resources": Resource.objects.count(),
        "levels": LearningLevel.objects.count(),
        "lessons": Lesson.objects.count(),
        "scenarios": PracticeScenario.objects.count(),
        "topics": KnowledgeTopic.objects.count(),
        "documents": KnowledgeDocument.objects.count(),
        "chunks": KnowledgeChunk.objects.count(),
        "search_terms": SearchTerm.objects.count(),
        "sessions": DiagnosticSession.objects.count(),
        "gaps": KnowledgeGap.objects.count(),
    }
