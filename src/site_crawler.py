"""
Website crawler using crawl4ai to download and convert pages to markdown.

This script crawls a website starting from a root URL, following links up to a
specified depth and/or maximum number of pages, and saves each page as markdown.
"""

import os
import asyncio
import argparse
import re
from urllib.parse import urlparse, urljoin
from collections import deque
from typing import Set, Dict, Optional

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


class SiteCrawler:
    """Crawls a website and saves pages as markdown files."""

    def __init__(
        self,
        root_url: str,
        output_dir: str,
        max_depth: Optional[int] = None,
        max_pages: Optional[int] = None,
        same_domain_only: bool = True,
        exclude_patterns: Optional[list] = None,
        max_concurrent: int = 10,
    ):
        """
        Initialize the crawler.

        Args:
            root_url: Starting URL for crawling
            output_dir: Directory to save markdown files
            max_depth: Maximum link depth from root (None = unlimited)
            max_pages: Maximum number of pages to crawl (None = unlimited)
            same_domain_only: Only crawl pages on the same domain as root
            exclude_patterns: List of URL patterns to exclude
            max_concurrent: Maximum number of concurrent requests (default: 10)
        """
        self.root_url = root_url
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.same_domain_only = same_domain_only
        self.exclude_patterns = exclude_patterns or []
        self.max_concurrent = max_concurrent

        # Parse root domain
        parsed = urlparse(root_url)
        self.root_domain = parsed.netloc
        if self.root_domain.startswith("www."):
            self.root_domain = self.root_domain[4:]

        # Tracking
        self.visited: Set[str] = set()
        self.url_depths: Dict[str, int] = {root_url: 0}
        self.pages_crawled = 0

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes."""
        parsed = urlparse(url)
        # Remove fragment
        normalized = parsed._replace(fragment="").geturl()
        # Remove trailing slash except for root
        if normalized.endswith("/") and parsed.path != "/":
            normalized = normalized.rstrip("/")
        return normalized

    def _should_crawl(self, url: str, depth: int) -> bool:
        """Determine if a URL should be crawled."""
        # Check if already visited
        if url in self.visited:
            return False

        # Check max depth
        if self.max_depth is not None and depth > self.max_depth:
            return False

        # Check max pages
        if self.max_pages is not None and self.pages_crawled >= self.max_pages:
            return False

        # Check same domain
        if self.same_domain_only:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            if domain != self.root_domain:
                return False

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if pattern in url:
                return False

        # Check for non-HTML resources
        excluded_extensions = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".zip",
            ".tar",
            ".gz",
            ".mp4",
            ".mp3",
            ".css",
            ".js",
            ".json",
            ".xml",
        ]
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in excluded_extensions):
            return False

        return True

    def _extract_links(self, html: str, base_url: str) -> Set[str]:
        """Extract and normalize all links from HTML content."""
        from lxml import html as lxml_html

        links = set()
        try:
            tree = lxml_html.fromstring(html)
            # Get all href attributes
            for element, attribute, link, pos in tree.iterlinks():
                if attribute == "href":
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(base_url, link)
                    normalized = self._normalize_url(absolute_url)
                    # Only include http/https URLs
                    if normalized.startswith(("http://", "https://")):
                        links.add(normalized)
        except Exception as e:
            print(f"Error extracting links from {base_url}: {e}")

        return links

    def _clean_markdown(self, markdown: str) -> str:
        """Remove code line number anchor links and other unwanted patterns from markdown."""
        # Remove line number anchor links like [](url#__codelineno-X-Y)
        # These often appear in documentation sites with code blocks
        cleaned = re.sub(r'\[\]\([^)]*#__codelineno-\d+-\d+\)', '', markdown)

        # Remove any remaining empty markdown links at the start of lines
        cleaned = re.sub(r'^\[\]\([^)]*\)\s*', '', cleaned, flags=re.MULTILINE)

        return cleaned

    def _get_file_path(self, url: str) -> str:
        """Generate file path for a URL."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]

        path = parsed.path.strip("/")
        if not path:
            path = "index"

        # Replace slashes with underscores for the file path
        path = path.replace("/", "_")

        # Create directory structure
        domain_dir = os.path.join(self.output_dir, domain)
        os.makedirs(domain_dir, exist_ok=True)

        # Return markdown file path
        return os.path.join(domain_dir, f"{path}.md")

    def _save_markdown(self, url: str, markdown: str, depth: int):
        """Save markdown content to disk."""
        file_path = self._get_file_path(url)

        # Add metadata header
        metadata = f"""---
url: {url}
depth: {depth}
---

"""
        content = metadata + markdown

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✓ Saved: {url} (depth={depth}) -> {file_path}")

    async def _crawl_page(
        self,
        crawler,
        url: str,
        depth: int,
        config: CrawlerRunConfig,
        semaphore: asyncio.Semaphore
    ) -> Set[str]:
        """
        Crawl a single page and return new links found.

        Args:
            crawler: The AsyncWebCrawler instance
            url: URL to crawl
            depth: Current depth
            config: Crawler configuration
            semaphore: Semaphore for limiting concurrency

        Returns:
            Set of new URLs discovered on this page
        """
        async with semaphore:
            new_links = set()

            try:
                print(f"\n[{self.pages_crawled + 1}] Crawling: {url} (depth={depth})...")

                # Crawl the page
                result = await crawler.arun(url=url, config=config)

                if result.success:
                    # Save markdown
                    markdown = result.markdown.raw_markdown
                    # Clean up unwanted patterns like code line number links
                    markdown = self._clean_markdown(markdown)
                    self._save_markdown(url, markdown, depth)

                    # Extract links for next level
                    if self.max_depth is None or depth < self.max_depth:
                        links = self._extract_links(result.html, url)
                        for link in links:
                            normalized = self._normalize_url(link)
                            if normalized not in self.url_depths and normalized not in self.visited:
                                new_links.add((normalized, depth + 1))
                        print(f"  Found {len(new_links)} new links to explore")
                else:
                    print(f"  ✗ Failed: {result.error_message}")

            except Exception as e:
                print(f"  ✗ Error crawling {url}: {e}")

            return new_links

    async def crawl(self):
        """Main crawling method using BFS approach with concurrent fetching."""
        print(f"Starting crawl from: {self.root_url}")
        print(f"Output directory: {self.output_dir}")
        print(f"Max depth: {self.max_depth if self.max_depth else 'unlimited'}")
        print(f"Max pages: {self.max_pages if self.max_pages else 'unlimited'}")
        print(f"Same domain only: {self.same_domain_only}")
        print(f"Max concurrent requests: {self.max_concurrent}")
        print("-" * 60)

        # Initialize queue with root URL
        queue = deque([(self.root_url, 0)])

        # Configure crawler
        # Exclude common navigation elements to avoid clutter
        excluded_tags = ['nav', 'footer', 'aside', 'script', 'style', 'noscript']

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=DefaultMarkdownGenerator(),
            excluded_tags=excluded_tags,
            wait_for="body",
            page_timeout=30000,
        )

        # Create semaphore for limiting concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async with AsyncWebCrawler(verbose=False) as crawler:
            while queue and (
                self.max_pages is None or self.pages_crawled < self.max_pages
            ):
                # Collect a batch of URLs to process concurrently
                batch = []
                while queue and len(batch) < self.max_concurrent:
                    if self.max_pages and self.pages_crawled >= self.max_pages:
                        break

                    url, depth = queue.popleft()

                    # Check if we should crawl this URL
                    if not self._should_crawl(url, depth):
                        continue

                    # Mark as visited
                    self.visited.add(url)
                    self.pages_crawled += 1
                    batch.append((url, depth))

                if not batch:
                    break

                # Process the batch concurrently
                tasks = [
                    self._crawl_page(crawler, url, depth, config, semaphore)
                    for url, depth in batch
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Add new links to the queue
                for result in results:
                    if isinstance(result, set):
                        for normalized, new_depth in result:
                            if normalized not in self.url_depths:
                                self.url_depths[normalized] = new_depth
                                queue.append((normalized, new_depth))

                # Check if we've hit max pages
                if self.max_pages and self.pages_crawled >= self.max_pages:
                    print(f"\nReached maximum page limit ({self.max_pages})")
                    break

        print("\n" + "=" * 60)
        print(f"Crawl complete!")
        print(f"Pages crawled: {self.pages_crawled}")
        print(f"Pages visited: {len(self.visited)}")
        print(f"Output directory: {self.output_dir}")


def create_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Crawl a website and save pages as markdown using crawl4ai",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl up to 3 levels deep
  python site_crawler.py --url https://example.com --output-dir ./output --max-depth 3

  # Crawl maximum 50 pages
  python site_crawler.py --url https://example.com --output-dir ./output --max-pages 50

  # Combine depth and page limits
  python site_crawler.py --url https://example.com --output-dir ./output --max-depth 2 --max-pages 25

  # Allow external links
  python site_crawler.py --url https://example.com --output-dir ./output --allow-external

  # Exclude certain URL patterns
  python site_crawler.py --url https://example.com --output-dir ./output --exclude-patterns "/blog" "/archive"
        """,
    )

    parser.add_argument(
        "-u", "--url", required=True, type=str, help="Root URL to start crawling from"
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        type=str,
        help="Directory to save markdown files",
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum link depth from root URL (default: unlimited)",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to crawl (default: unlimited)",
    )

    parser.add_argument(
        "--allow-external",
        action="store_true",
        help="Allow crawling external domains (default: same domain only)",
    )

    parser.add_argument(
        "--exclude-patterns",
        nargs="+",
        default=[],
        help="URL patterns to exclude from crawling",
    )

    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum number of concurrent requests (default: 10)",
    )

    return parser


async def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    print("=" * 60)
    print("Site Crawler using crawl4ai")
    print("=" * 60)

    crawler = SiteCrawler(
        root_url=args.url,
        output_dir=args.output_dir,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        same_domain_only=not args.allow_external,
        exclude_patterns=args.exclude_patterns,
        max_concurrent=args.max_concurrent,
    )

    await crawler.crawl()


if __name__ == "__main__":
    asyncio.run(main())
