# The aim of this file is threefold
# 1. Navigate and save n urls to use as a seed
# 2. Download the corresponding HTML to disk
# 3. Use an LLM to convert the HTML to an MD file containing the essential aspects

import os
import argparse

from dotenv import load_dotenv
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from strands import Agent
from strands_tools import browser
from strands.models.anthropic import AnthropicModel

import constants

load_dotenv()

NAVIGATION_PROMPT = """Navigate to {url}"""
COOKIE_PROMPT = (
    """Click on any cookie banner or any similar banner. Please accept it."""
)
URLS_PROMPT = """Find a set of {num_urls} that you can navigate to from your current page. Ensure that each url is a documentation based URL."""
MARKDOWN_PROMPT = """Convert the given page to markdown. Preserve all links, headers, headers, images and citations."""


class UrlInfo(BaseModel):
    """Model to capture basic url information"""

    url: str = Field("Complete hyperlink")


class SiteSamples(BaseModel):
    """URLs to documentations samples from the site"""

    url_samples: list[UrlInfo] = Field(
        description="A set of urls that can be navigated to from the current page"
    )


class MarkDownModel(BaseModel):
    """Model to capture webpage as markdown"""

    url: str = Field(description="URL which is being converted to markdown")
    markdown: str = Field(description="Markdown content of the url")


def get_last_session_name(message_list):
    """
    Extract the last session name from the message_list

    message_list: list[dict]: contains the role and content of messages
    """
    for message in message_list[::-1]:
        if message[constants.ROLE] == constants.ASSISTANT:
            content = message[constants.CONTENT]
            for content_item in content:
                if (
                    constants.TOOL_USE in content_item
                    and content_item[constants.TOOL_USE][constants.NAME]
                    == constants.BROWSER
                ):
                    action = content_item[constants.TOOL_USE][constants.INPUT][
                        constants.BROWSER_INPUT
                    ][constants.ACTION]
                    session_name = action[constants.SESSION_NAME]
                    return session_name
    return None


def get_model(max_tokens=4096, model_name=constants.SONNET):
    """
    Return a strands model object

    max_tokens: int
    model_name: str
    """
    model = AnthropicModel(
        client_args={"api_key": os.getenv(constants.ANTHROPIC_API_KEY)},
        max_tokens=max_tokens,
        model_id=model_name,
    )
    return model


def get_browser(headless=False):
    """
    Return a strands browser object

    headless: bool
    """
    local_browser = browser.LocalChromiumBrowser(
        launch_options={constants.HEADLESS: headless}
    )
    return local_browser


def get_urls(root_url, num_urls=3):
    """
    Return a list of urls extracted from the root url

    root_url: str
    num_urls: int
    """
    local_browser = get_browser(headless=True)
    model = get_model()
    agent = Agent(model=model, tools=[local_browser.browser])

    _ = agent(NAVIGATION_PROMPT.format(url=root_url))
    _ = agent(COOKIE_PROMPT)

    responses = agent(
        URLS_PROMPT.format(num_urls=num_urls), structured_output_model=SiteSamples
    )

    local_browser._cleanup()

    return responses.structured_output


def get_html_md(url):
    """
    Obtains the MD and the html of a given URL

    url: str
    """
    local_browser = get_browser(headless=True)
    model = get_model()
    agent = Agent(model=model, tools=[local_browser.browser])

    _ = agent(NAVIGATION_PROMPT.format(url=url))
    _ = agent(COOKIE_PROMPT)
    response = agent(MARKDOWN_PROMPT, structured_output_model=MarkDownModel)

    md_str = response.structured_output.markdown

    session_name = get_last_session_name(agent.messages)

    raw_html = agent.tool.browser(
        browser_input={
            constants.ACTION: {
                constants.TYPE: constants.EVALUATE,
                constants.SESSION_NAME: session_name,
                constants.SCRIPT: "document.documentElement.outerHTML",
            }
        }
    )

    raw_html = raw_html[constants.CONTENT][0][constants.TEXT]
    raw_html = raw_html.replace("Evaluation result :", "")

    return raw_html, md_str


def get_domain_path(url: str):
    """
    Parses domain and path from the URL
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path

    # Remove 'www.' prefix if present
    if domain.startswith("www."):
        domain = domain[4:]

    return domain, path


def seeder(root_url: str, num_urls: int, dst_dir: str):
    """
    Navigates from root_url to num_urls and downloads the HTML
    Also uses an LLM to extract the webpage in MD format

    root_url: url from which to start
    num_urls: number of pages to parse
    dst_dir: destination directory to store HTML and MD files
    """
    print("Initiating")
    domain, path = get_domain_path(root_url)

    dst_dir = os.path.join(dst_dir, domain)
    print(f"Saving to {dst_dir}")

    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    site_samples = get_urls(root_url, num_urls)
    for url_info in site_samples.url_samples:
        url = url_info.url
        print(f"Parsing {url}")
        _, path = get_domain_path(url)
        path = path.strip("/")
        path = path.replace("/", "---")
        html_str, md_str = get_html_md(url)

        final_dir = os.path.join(dst_dir, path)
        if not os.path.exists(final_dir):
            os.makedirs(final_dir)

        html_path = os.path.join(final_dir, "page.html")
        md_path = os.path.join(final_dir, "page.md")
        with open(html_path, "w") as f:
            f.write(html_str)

        with open(md_path, "w") as f:
            f.write(md_str)


def create_parser():
    """Create the argument parser"""
    parser = argparse.ArgumentParser(description="Seed Documentation URLs")
    parser.add_argument(
        "-r", "--root_url", required=True, type=str, help="Root URL to process"
    )
    parser.add_argument(
        "-n", "--num_urls", required=True, type=str, help="Number of URLs to seed"
    )

    parser.add_argument(
        "-d", "--dst_dir", required=True, type=str, help="Destination directory"
    )
    return parser


def main():
    parer = create_parser()
    args = parer.parse_args()

    print(f"Root URL: {args.root_url}")
    print(f"Num URLs: {args.num_urls}")
    print(f"Dest Dir: {args.dst_dir}")

    seeder(args.root_url, args.num_urls, args.dst_dir)


if __name__ == "__main__":
    main()
