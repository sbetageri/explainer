# Site Crawler Usage Guide

A powerful website crawler using crawl4ai that downloads entire websites and converts all pages to markdown format.

## Features

- **Depth Control**: Specify how many link levels deep to crawl from the root URL
- **Page Limits**: Set maximum number of pages to crawl
- **Domain Filtering**: Choose to crawl only same-domain or allow external links
- **Smart Filtering**: Automatically excludes non-HTML resources (PDFs, images, etc.)
- **URL Pattern Exclusion**: Exclude specific URL patterns (e.g., `/blog`, `/archive`)
- **Markdown Conversion**: Clean markdown with preserved links, headers, and structure
- **Progress Tracking**: Real-time crawl progress with detailed logging
- **Metadata**: Each markdown file includes URL and depth information

## Installation

Dependencies are already included in `pyproject.toml`:
- `crawl4ai>=0.7.8`
- `lxml==5.3.0`

Make sure dependencies are installed:
```bash
uv sync
```

## Usage

### Basic Examples

**1. Crawl with depth limit:**
```bash
python src/site_crawler.py \
  --url https://docs.python.org/3/ \
  --output-dir ./crawled_sites \
  --max-depth 2
```
This crawls the Python docs up to 2 levels deep from the root.

**2. Crawl with page limit:**
```bash
python src/site_crawler.py \
  --url https://example.com \
  --output-dir ./output \
  --max-pages 50
```
This crawls up to 50 pages regardless of depth.

**3. Combine depth and page limits:**
```bash
python src/site_crawler.py \
  --url https://docs.anthropic.com \
  --output-dir ./anthropic_docs \
  --max-depth 3 \
  --max-pages 100
```
This crawls up to 3 levels deep but stops at 100 pages.

**4. Allow external links:**
```bash
python src/site_crawler.py \
  --url https://example.com \
  --output-dir ./output \
  --max-depth 2 \
  --allow-external
```
This allows following links to external domains.

**5. Exclude URL patterns:**
```bash
python src/site_crawler.py \
  --url https://example.com \
  --output-dir ./output \
  --max-depth 3 \
  --exclude-patterns "/blog" "/archive" "/news"
```
This excludes any URLs containing `/blog`, `/archive`, or `/news`.

### Command-Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `-u, --url` | Yes | Root URL to start crawling from |
| `-o, --output-dir` | Yes | Directory to save markdown files |
| `--max-depth` | No | Maximum link depth from root (default: unlimited) |
| `--max-pages` | No | Maximum number of pages to crawl (default: unlimited) |
| `--allow-external` | No | Allow crawling external domains (default: same domain only) |
| `--exclude-patterns` | No | Space-separated URL patterns to exclude |

### Output Structure

Markdown files are organized by domain and URL path:

```
output_dir/
└── example.com/
    ├── index.md                    # Root page
    ├── docs.md                     # /docs page
    ├── docs---getting-started.md   # /docs/getting-started page
    └── api---reference.md          # /api/reference page
```

Each markdown file includes metadata:
```markdown
---
url: https://example.com/docs/getting-started
depth: 1
---

# Getting Started
...
```

## Understanding Depth

Depth indicates how many links away from the root URL a page is:

- **Depth 0**: The root URL itself
- **Depth 1**: Pages directly linked from the root
- **Depth 2**: Pages linked from depth 1 pages
- **Depth 3**: Pages linked from depth 2 pages
- etc.

## Best Practices

1. **Start Small**: Test with `--max-pages 10` first to verify the crawler works as expected
2. **Use Depth Limits**: For large sites, use `--max-depth 2` or `--max-depth 3` to avoid crawling too deep
3. **Combine Limits**: Use both `--max-depth` and `--max-pages` for better control
4. **Exclude Wisely**: Use `--exclude-patterns` to skip blogs, archives, or other non-essential sections
5. **Same Domain**: Keep `same-domain-only` (default) unless you specifically need external links

## Automatic Filtering

The crawler automatically excludes:
- Non-HTML resources (`.pdf`, `.jpg`, `.png`, `.zip`, `.mp4`, etc.)
- Duplicate URLs (handles trailing slashes and URL fragments)
- Already visited pages

## Examples for Common Use Cases

### Documentation Sites
```bash
python src/site_crawler.py \
  --url https://docs.example.com \
  --output-dir ./docs_backup \
  --max-depth 4 \
  --exclude-patterns "/changelog" "/release-notes"
```

### Small Company Website
```bash
python src/site_crawler.py \
  --url https://company.com \
  --output-dir ./company_site \
  --max-pages 100
```

### Large Site (Controlled Crawl)
```bash
python src/site_crawler.py \
  --url https://large-site.com \
  --output-dir ./large_site_sample \
  --max-depth 2 \
  --max-pages 50
```

## Comparison with seeder.py

| Feature | site_crawler.py (new) | seeder.py (existing) |
|---------|----------------------|---------------------|
| Technology | crawl4ai | Strands agents + browser |
| Speed | Fast (concurrent) | Slower (sequential) |
| Markdown conversion | Built-in | LLM-based |
| Depth control | Yes (--max-depth) | No |
| Full site crawl | Yes | No (manual URL list) |
| Link discovery | Automatic | Manual |

## Troubleshooting

**Issue**: Crawler stops early
- Check if you hit `--max-pages` or `--max-depth` limit
- Check console for error messages

**Issue**: Some pages missing
- They might be beyond your depth limit
- They might match an exclude pattern
- They might not be linked from crawled pages

**Issue**: Too many pages
- Reduce `--max-depth`
- Add `--max-pages` limit
- Use `--exclude-patterns` to skip sections
