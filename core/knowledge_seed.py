"""Reviewed knowledge base used by the RAG pipeline.

Each document is chunked by ``##`` headings and indexed in the database.
Keep the language plain, factual and aligned with Google's documentation.
"""

from datetime import date

KNOWLEDGE_DOCS = [
    {
        "slug": "gsc-reports-overview",
        "title": "Google Search Console reports overview",
        "doc_type": "guide",
        "url": "https://support.google.com/webmasters/answer/9128668",
        "summary": "What each Search Console report measures and when to use it.",
        "reviewed_on": date(2026, 10, 1),
        "body": """Search Console groups its data into a small number of reports. Knowing which report answers which question prevents most misdiagnosis.

## Performance report
The Performance report shows clicks, impressions, click-through rate and average position for queries and pages. Use it to investigate changes in organic visibility. It does not tell you whether a URL is indexed; use the Page indexing report or URL Inspection for that.

## Page indexing report
The Page indexing report lists indexed and not-indexed URLs grouped by reason. Reasons include Discovered – currently not indexed, Crawled – currently not indexed, Excluded by noindex, Blocked by robots.txt, Duplicate with a different canonical, Soft 404 and Server error.

## Sitemaps report
The Sitemaps report shows submitted sitemaps, the number of discovered URLs and any parsing or fetch errors. It confirms that a sitemap was read, not that its URLs were indexed.

## Crawl Stats report
Crawl Stats shows how often Googlebot fetched the site, response times, and host status. Use it to correlate crawling problems with server load or configuration changes.

## URL Inspection
URL Inspection reports the indexed version of a specific URL, the live rendering, canonical selection, crawlability and any detected structured data. It is the fastest way to confirm what Google sees for one page.

## How to use the reports together
Start with Page indexing to identify the affected group, then use URL Inspection on a representative URL, then compare with Crawl Stats and server logs. Confirm the cause with evidence rather than assuming the first plausible explanation.""",
    },
    {
        "slug": "page-indexing-report",
        "title": "Page indexing report: statuses explained",
        "doc_type": "guide",
        "url": "https://support.google.com/webmasters/answer/7440203",
        "summary": "A reference for every Page indexing status and what it implies.",
        "reviewed_on": date(2026, 9, 28),
        "body": """The Page indexing report groups URLs by the reason Google did or did not index them. The status is a signal, not a diagnosis.

## Indexed statuses
Indexed, not submitted in sitemap means Google indexed the URL without finding it in a sitemap. Submitted and indexed means the URL is in a sitemap and in the index. Both are healthy.

## Discovered – currently not indexed
Google knows the URL exists but has not crawled or indexed it yet. This is common for new or weakly linked pages and can persist for weeks.

## Crawled – currently not indexed
Google fetched the page but chose not to index it. Common causes are duplicate or thin content, conflicting canonical signals or a page that adds little value.

## Excluded by noindex
A noindex meta tag or X-Robots-Tag header told Google not to index the page. Confirm whether the exclusion is intentional.

## Blocked by robots.txt
A robots.txt rule prevents Googlebot from fetching the URL. Blocked URLs cannot be indexed or used to pass signals.

## Alternate page with proper canonical tag
The URL is a duplicate and correctly points to another URL. This is normal for variants such as tracking parameters.

## Duplicate, Google chose different canonical
Google selected a different canonical than the one declared. Internal links, redirects or sitemap entries may point elsewhere.

## Soft 404
The page returns a success status but has little or no meaningful content, so Google treats it like a missing page.

## Server error (5xx)
The server returned a 5xx response while Googlebot was fetching. Repeated errors can delay crawling and remove pages from the index.

## How to investigate
Open the affected group, choose a representative URL, run URL Inspection, and compare the live page with the indexed version. Confirm the cause before changing directives.""",
    },
    {
        "slug": "discovered-not-indexed",
        "title": "Discovered – currently not indexed",
        "doc_type": "article",
        "url": "https://support.google.com/webmasters/answer/7440203",
        "summary": "Why Google knows a URL but has not indexed it, and how to investigate.",
        "reviewed_on": date(2026, 10, 2),
        "body": """Discovered – currently not indexed means Google found the URL but has not added it to the index. It is a queue status, not a permanent rejection.

## What it means
Google discovered the URL through a sitemap, an internal link or another signal. Crawling or indexing has not happened yet. The page is not necessarily broken, and it is not necessarily excluded.

## Common causes
- The URL is missing from the submitted sitemap or the sitemap is stale.
- The page has few or no internal links, so crawl priority is low.
- The site is new or small and Google has not scheduled a crawl.
- The server responds slowly or intermittently with 5xx errors.
- The content duplicates other pages, reducing the value of indexing it.

## How to check
1. Confirm the status in the Page indexing report.
2. Fetch the sitemap and search for the URL.
3. Count internal links pointing to the page.
4. Run URL Inspection and test the live URL.
5. Check Crawl Stats for response time and host errors.

## How to fix
- Add the URL to a valid, submitted sitemap.
- Link to the page from relevant, indexed pages using descriptive anchors.
- Remove duplicate or thin content, or consolidate it.
- Fix server errors and slow responses before requesting a crawl.
- Request indexing with URL Inspection after the changes are live.

## How to verify
Re-run URL Inspection and confirm the live test succeeds. Monitor the Page indexing report over the following days and weeks. Crawling is not immediate, so allow time before concluding that the fix failed.""",
    },
    {
        "slug": "crawled-not-indexed",
        "title": "Crawled – currently not indexed",
        "doc_type": "article",
        "url": "https://support.google.com/webmasters/answer/7440203",
        "summary": "Google fetched the page but decided not to index it. Here is why.",
        "reviewed_on": date(2026, 10, 2),
        "body": """Crawled – currently not indexed means Googlebot fetched the page successfully but did not add it to the index.

## What it means
The URL is reachable. The decision not to index is about the page itself: its content, its duplication, or the signals Google associates with it.

## Common causes
- The page is a near-duplicate of another indexed page.
- The canonical points to a different URL.
- The content is thin, repetitive or not useful compared with competing pages.
- A noindex directive was present when Google crawled the page.
- The page is primarily a login screen, an app shell or otherwise inaccessible content.
- Quality and trust signals for the site are weak.

## How to check
- Compare the page with similar indexed URLs.
- Inspect the rendered HTML for canonical and robots directives.
- Check whether internal links point to a different canonical variant.
- Review the content for unique value, not just word count.
- Confirm the page is not intentionally excluded.

## How to fix
- Make the canonical self-referencing if this URL should rank.
- Remove noindex directives from pages that should be indexed.
- Differentiate or consolidate duplicate content.
- Add unique information that serves the search intent.
- Strengthen internal links from relevant pages.

## How to verify
Request indexing after the changes ship, then monitor the report. A single crawl does not guarantee indexing, so track the group over time.""",
    },
    {
        "slug": "robots-txt-blocked",
        "title": "Blocked by robots.txt",
        "doc_type": "article",
        "url": "https://developers.google.com/search/docs/crawling-indexing/robots/intro",
        "summary": "How robots.txt rules block crawling and how to fix accidental blocks.",
        "reviewed_on": date(2026, 9, 25),
        "body": """robots.txt tells crawlers which URLs they may fetch. A matching Disallow rule prevents Googlebot from crawling the URL.

## What it means
Blocked by robots.txt means the URL matches a rule that disallows Googlebot. Google may still learn the URL exists from links, but it will not fetch the content.

## Common causes
- A staging or development robots.txt file was deployed to production.
- A broad Disallow pattern also matches pages that should be indexed.
- A CMS or security plugin added rules automatically.
- The rules target all user agents instead of a specific bot.

## How to check
1. Open https://example.com/robots.txt in a browser.
2. Find the longest matching Allow or Disallow rule for Googlebot.
3. Confirm whether the rule is intentional.
4. Use URL Inspection to test whether Googlebot can fetch the URL.
5. Check recent deployments for robots.txt changes.

## How to fix
- Remove or narrow the rule so that pages meant for search are allowed.
- Keep intentional blocks for private, duplicate or low-value URL patterns.
- Deploy the change and confirm robots.txt is publicly reachable.
- Do not use robots.txt to remove a page from the index; use noindex for that.

## How to verify
Re-test the URL with URL Inspection and confirm the live fetch succeeds. Request indexing after access is restored. Crawling may take time to resume.""",
    },
    {
        "slug": "noindex-directives",
        "title": "noindex and indexing directives",
        "doc_type": "article",
        "url": "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
        "summary": "Where noindex can come from and how to confirm it.",
        "reviewed_on": date(2026, 9, 20),
        "body": """A noindex directive tells Google not to index a page. It can appear in HTML, in an HTTP header, or be implied by conflicting configuration.

## What it means
Excluded by noindex means Google respected an explicit instruction not to index the URL. If the exclusion is unintended, find and remove the source.

## Where noindex can come from
- A robots meta tag in the HTML head.
- An X-Robots-Tag HTTP header, often added by a server, CDN or framework.
- A CMS setting for the page or content type.
- A staging or preview environment leaking into production.
- A plugin or theme applied to specific templates.

## How to check
- View the rendered HTML and search for the robots meta tag.
- Inspect response headers for X-Robots-Tag.
- Use URL Inspection to see the crawled page and detected directives.
- Check CMS, framework and CDN configuration for indexing defaults.

## How to fix
- Remove the directive from pages that should be indexed.
- Keep noindex on private, duplicate or low-value pages.
- Prefer noindex over robots.txt for removing a page from search results.
- Deploy and confirm the header or tag is gone in production.

## How to verify
Run URL Inspection, confirm the directive is absent, then request indexing. Excluded pages can take time to return.""",
    },
    {
        "slug": "canonicalization-duplicates",
        "title": "Canonicalization and duplicate URLs",
        "doc_type": "article",
        "url": "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
        "summary": "How Google chooses a canonical and how to make your preference clear.",
        "reviewed_on": date(2026, 9, 22),
        "body": """Canonicalization is how Google selects one URL to represent a group of duplicate or near-duplicate pages.

## What it means
If Google chooses a different canonical than the one you declared, it found stronger signals elsewhere. That is a signal conflict, not necessarily an error.

## Common causes
- Internal links point to a different variant than the declared canonical.
- Tracking parameters create many versions of the same page.
- Both HTTP and HTTPS, or both trailing-slash variants, resolve to the same content.
- The sitemap lists a different URL than the canonical tag.
- Redirects form a chain instead of a single hop.

## How to check
- Compare the inspected URL, the declared canonical and the user-declared canonical.
- Search for internal links to non-canonical variants.
- Check the sitemap for inconsistent URLs.
- Confirm the canonical is self-referencing on the preferred URL.
- Look for conflicting hreflang or pagination signals.

## How to fix
- Pick one canonical URL per piece of content.
- Link internally to the canonical URL only.
- Redirect duplicate variants when appropriate.
- Keep the canonical tag self-referencing on the chosen URL.
- Align the sitemap, internal links and canonicals.

## How to verify
Re-inspect a representative URL and confirm Google selects the intended canonical. Consolidation can take time as Google recrawls the variants.""",
    },
    {
        "slug": "server-errors-5xx",
        "title": "Server errors (5xx) and crawling",
        "doc_type": "article",
        "url": "https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
        "summary": "Why Googlebot sees 5xx responses and how to diagnose them.",
        "reviewed_on": date(2026, 10, 3),
        "body": """A 5xx response tells Googlebot that the server failed to fulfil a valid request. Repeated failures can slow crawling and remove URLs from the index.

## What it means
Server error (5xx) means the origin, proxy, CDN or WAF returned an error. The page itself may be fine; the delivery path is failing.

## Common causes
- The origin times out under load or during traffic spikes.
- A database or upstream service is slow or unavailable.
- A WAF or bot-protection rule rejects Googlebot requests.
- A recent deployment introduced an application error.
- Rate limiting treats Googlebot like an abusive client.

## How to check
1. Reproduce the response with repeated requests.
2. Compare URL Inspection live tests with normal browser requests.
3. Filter server and CDN logs by the Googlebot user agent.
4. Correlate error timestamps with traffic, deploys and incidents.
5. Review timeout and rate-limit settings.

## How to fix
- Fix the failing endpoint or increase its timeout budget.
- Raise or remove rate limits for verified Googlebot traffic.
- Check CDN and WAF rules for blocked or failed requests.
- Add caching or capacity to absorb traffic spikes.
- Deploy and confirm a stable 200 response.

## How to verify
Repeat the fetch several times and monitor Crawl Stats and server logs. Request a recrawl once the error rate returns to normal.""",
    },
    {
        "slug": "soft-404",
        "title": "Soft 404: pages that look missing",
        "doc_type": "article",
        "url": "https://support.google.com/webmasters/answer/181708",
        "summary": "Why a 200 response can still be treated as a missing page.",
        "reviewed_on": date(2026, 9, 30),
        "body": """A soft 404 is a URL that returns a success status but has little or no meaningful content, so Google treats it like a missing page.

## What it means
Google does not want to show empty or error-like pages in search results. If a page looks like an error page or has no useful content, it may be classified as a soft 404 even when the HTTP status is 200.

## Common causes
- The page renders an empty template or an error message.
- Content is loaded by JavaScript that Googlebot cannot execute.
- A product or article was removed but the page still returns 200.
- The page requires login or geolocation and shows no content otherwise.
- A redirect or canonical sends users to a different page.

## How to check
- View the rendered page as Googlebot with URL Inspection.
- Compare the visible content with the template and data source.
- Confirm the HTTP status and any client-side redirects.
- Check whether the page returns different content for different user agents.

## How to fix
- Return a real 404 or 410 for removed content that should not rank.
- Restore meaningful content if the page should rank.
- Render important content server-side where possible.
- Avoid serving empty shells to crawlers.

## How to verify
Re-test the URL with URL Inspection and confirm the rendered content matches the intent. Monitor the Page indexing report for recurrence.""",
    },
    {
        "slug": "sitemaps",
        "title": "Sitemaps: submission and validation",
        "doc_type": "guide",
        "url": "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview",
        "summary": "How sitemaps support discovery and what they do not guarantee.",
        "reviewed_on": date(2026, 9, 18),
        "body": """A sitemap lists URLs that should be considered for crawling. It supports discovery but does not guarantee crawling or indexing.

## What it means
Submitting a sitemap tells Google which URLs exist. It does not force Google to crawl or index them. The Page indexing status remains the authority on indexing.

## Common sitemap problems
- The sitemap is not fetchable or returns an error.
- URLs in the sitemap return 404, 5xx or redirect to another URL.
- The sitemap contains non-canonical or blocked URLs.
- The sitemap exceeds size or count limits.
- The sitemap is not referenced in robots.txt or Search Console.

## How to check
- Fetch the sitemap URL directly and confirm it parses.
- Search for the affected URL in the sitemap content.
- Compare sitemap URLs with canonical URLs.
- Check the Sitemaps report for fetch and parsing errors.
- Confirm the sitemap is submitted for the correct property.

## How to fix
- Include only canonical, indexable URLs.
- Remove erroring or redirected URLs.
- Split large sitemaps and update the sitemap index.
- Keep lastmod values accurate.
- Resubmit after changes.

## How to verify
Confirm Google fetched the updated sitemap, then monitor indexing. Use URL Inspection for individual URLs when a sitemap change should trigger a recrawl.""",
    },
    {
        "slug": "internal-linking",
        "title": "Internal linking and discovery signals",
        "doc_type": "article",
        "url": "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
        "summary": "How internal links influence discovery, crawling and priority.",
        "reviewed_on": date(2026, 9, 26),
        "body": """Internal links are one of the strongest signals that a URL exists and matters. They also help crawlers reach pages efficiently.

## Why internal links matter
A page with no internal links is effectively orphaned. Google may discover it through a sitemap but has little reason to crawl it often or treat it as important.

## Common problems
- Important pages are only linked from JavaScript menus that crawlers cannot use.
- Links use fragments or event handlers instead of real href values.
- Navigation links to non-canonical variants.
- Deep pages have no path from the home page.
- Anchor text is generic and gives no context.

## How to check
- Search the site for the URL and count contextual links.
- Review navigation and footer links.
- Use a crawler to map internal inlinks.
- Confirm links are real anchor elements with crawlable href values.
- Check that links point to canonical URLs.

## How to fix
- Link to important pages from relevant, indexed pages.
- Use descriptive anchor text.
- Keep navigation crawlable without JavaScript.
- Remove links to duplicate or non-canonical variants.
- Add breadcrumbs or related-content links where useful.

## How to verify
Recrawl the site and confirm the page now has internal inlinks. Then request indexing and monitor the report.""",
    },
    {
        "slug": "javascript-rendering",
        "title": "JavaScript rendering and crawlability",
        "doc_type": "article",
        "url": "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics",
        "summary": "What Googlebot can render and where client-side rendering breaks.",
        "reviewed_on": date(2026, 9, 16),
        "body": """Google can render JavaScript, but rendering is a second step and is not guaranteed to be immediate or complete. Important content should not depend solely on client-side execution.

## What it means
If key content, links or directives only exist after JavaScript runs, Google may see an empty or incomplete page. That can lead to Discovered, Crawled or Soft 404 classifications.

## Common problems
- Content is fetched client-side and fails for Googlebot.
- Links are buttons with JavaScript click handlers instead of anchors.
- The page blocks its own scripts in robots.txt.
- Rendering depends on APIs that reject Googlebot.
- Critical meta tags are injected after load.

## How to check
- Use URL Inspection to compare the raw HTML and the rendered page.
- Disable JavaScript and inspect the page source.
- Confirm robots.txt allows the scripts and APIs required for rendering.
- Test API responses with the Googlebot user agent.

## How to fix
- Server-render or pre-render critical content.
- Use real anchor links for navigation.
- Do not block required scripts or data endpoints.
- Ensure meta robots and canonical tags exist in the initial HTML.
- Provide meaningful fallbacks when APIs fail.

## How to verify
Re-test with URL Inspection and confirm the rendered content includes the important text and links. Monitor indexing after deployment.""",
    },
    {
        "slug": "crawl-budget",
        "title": "Crawl budget and Crawl Stats",
        "doc_type": "guide",
        "url": "https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget",
        "summary": "How crawl capacity is allocated and what Crawl Stats reveals.",
        "reviewed_on": date(2026, 9, 12),
        "body": """Crawl budget describes how much crawling Google is willing to do on a site. For small sites it is rarely a constraint. For large or slow sites it can matter.

## What influences crawling
- Site response time and host availability.
- Perceived site quality and demand.
- Duplicate and low-value URLs consuming capacity.
- Internal linking and sitemap signals.
- Server errors and rate limiting.

## What Crawl Stats shows
Crawl Stats reports crawl requests, average response time, host status and response codes by purpose and file type. It helps correlate crawling behaviour with infrastructure changes.

## Common problems
- Slow responses reduce crawl rate.
- Large numbers of low-value URLs consume capacity.
- 5xx errors and timeouts interrupt crawling.
- Infinite spaces or parameter permutations create crawl traps.
- Blocked resources prevent rendering.

## How to check
- Review Crawl Stats trends around the incident.
- Compare crawl requests with server capacity.
- Identify URL patterns that generate many low-value pages.
- Check response times by directory.
- Correlate errors with deploys and traffic.

## How to fix
- Improve server response time and stability.
- Remove or noindex low-value URL patterns.
- Fix broken links and redirect chains.
- Keep sitemaps focused on canonical, indexable URLs.
- Reduce duplicate content that wastes crawl capacity.

## How to verify
Watch Crawl Stats after the change. Improved response times and fewer errors usually precede better crawling. Indexing changes follow over time.""",
    },
    {
        "slug": "redirects-http-status",
        "title": "Redirects and HTTP status codes",
        "doc_type": "guide",
        "url": "https://developers.google.com/search/docs/crawling-indexing/301-redirects",
        "summary": "How Google treats redirects, 404s and other status codes.",
        "reviewed_on": date(2026, 9, 14),
        "body": """HTTP status codes tell Googlebot what happened to a request. The status determines whether content is indexed, consolidated or ignored.

## Key status codes
- 200 OK: the page is available.
- 301 Moved Permanently: the URL has permanently moved; signals consolidate to the target.
- 302 Found: a temporary redirect; the original URL remains the canonical.
- 304 Not Modified: the cached version can be reused.
- 404 Not Found: the URL is missing.
- 410 Gone: the URL is intentionally removed.
- 5xx: a server failure; retry later.

## Common problems
- Redirect chains with multiple hops.
- Redirect loops.
- Redirects to irrelevant or soft-404 pages.
- 302 used for permanent moves.
- Mixed HTTP and HTTPS or trailing-slash variants.

## How to check
- Use curl or browser dev tools to inspect the status and Location header.
- Confirm a single hop to the final destination.
- Check whether the destination returns 200 and is indexable.
- Compare internal links with the redirect target.

## How to fix
- Point redirects directly at the final URL.
- Use 301 for permanent moves.
- Update internal links to the destination.
- Remove redirect loops and chains.
- Return 404 or 410 for content that no longer exists.

## How to verify
Re-check the status codes and confirm the destination is indexed. Monitor the report for pages that remain in a redirect state.""",
    },
]

SEARCH_TERMS = [
    {
        "term": "indexed",
        "misspellings": ["indexd", "indxed"],
        "synonyms": ["indexing", "indexation"],
        "category": "indexing",
    },
    {
        "term": "crawl",
        "misspellings": ["crwal", "crawel", "crawling"],
        "synonyms": ["crawled", "crawler", "googlebot"],
        "category": "crawling",
    },
    {
        "term": "sitemap",
        "misspellings": ["sitemp", "sitemaps", "site-map"],
        "synonyms": ["sitemaps", "urlset"],
        "category": "indexing",
    },
    {
        "term": "canonical",
        "misspellings": ["canonicalization", "canonicalisation", "canonicle"],
        "synonyms": ["canonicals", "duplicate", "rel canonical"],
        "category": "indexing",
    },
    {
        "term": "robots.txt",
        "misspellings": ["robot.txt", "robots", "robotstxt"],
        "synonyms": ["disallow", "allow rule"],
        "category": "crawling",
    },
    {
        "term": "noindex",
        "misspellings": ["noindx", "noindexx", "no-indx"],
        "synonyms": ["x-robots-tag", "robots meta"],
        "category": "indexing",
    },
    {
        "term": "5xx",
        "misspellings": ["5xx", "500", "502", "503", "504"],
        "synonyms": ["server error", "timeout", "gateway"],
        "category": "server",
    },
    {
        "term": "soft 404",
        "misspellings": ["soft404", "soft-404"],
        "synonyms": ["empty page", "missing content"],
        "category": "content",
    },
    {
        "term": "rendering",
        "misspellings": ["render", "rendring", "javascript"],
        "synonyms": ["client-side", "server-side", "hydration"],
        "category": "crawling",
    },
    {
        "term": "redirect",
        "misspellings": ["redirection", "redirct", "301"],
        "synonyms": ["302", "redirect chain", "redirect loop"],
        "category": "crawling",
    },
]
