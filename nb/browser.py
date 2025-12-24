"""
Playwright-based browser tool for AWS Strands agents.
Provides web scraping, navigation, and content extraction capabilities.
Uses sync wrapper pattern over async implementation for Jupyter compatibility.
"""

from typing import Optional, Any
import asyncio
from playwright.async_api import async_playwright, Browser as AsyncBrowser, Page as AsyncPage, Playwright as AsyncPlaywright
from strands import tool
import nest_asyncio


class BrowserTool:
    """
    A browser automation tool using Playwright for AWS Strands agents.
    Provides synchronous interface over async implementation for Jupyter compatibility.
    """

    def __init__(self, headless: bool = True):
        """
        Initialize the browser tool with Playwright.
        Works seamlessly in both regular Python and Jupyter notebooks.

        Args:
            headless: Whether to run browser in headless mode (default: True)
        """
        self.headless = headless
        self._playwright: Optional[AsyncPlaywright] = None
        self._browser: Optional[AsyncBrowser] = None
        self._page: Optional[AsyncPage] = None
        self._started = False
        self._nest_asyncio_applied = False

        # Create dedicated event loop
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    def _execute_async(self, coro) -> Any:
        """
        Execute async coroutine synchronously using dedicated event loop.
        Applies nest_asyncio for Jupyter compatibility.
        """
        if not self._nest_asyncio_applied:
            nest_asyncio.apply()
            self._nest_asyncio_applied = True
        return self._loop.run_until_complete(coro)

    def _start(self):
        """Initialize Playwright browser instance lazily."""
        if not self._started:
            self._playwright = self._execute_async(async_playwright().start())
            self._browser = self._execute_async(
                self._playwright.chromium.launch(headless=self.headless)
            )
            self._page = self._execute_async(self._browser.new_page())
            self._started = True

    async def _navigate_async(self, url: str) -> dict:
        """Async implementation of navigate."""
        response = await self._page.goto(url, wait_until="networkidle")
        return {
            "status": "success",
            "message": f"Successfully navigated to {url}",
            "final_url": self._page.url,
            "status_code": response.status if response else None
        }

    async def _save_as_pdf_async(self, url: str, output_path: str) -> dict:
        """Async implementation of save_as_pdf."""
        await self._page.goto(url, wait_until="networkidle")
        await self._page.emulate_media(media="screen")
        await self._page.pdf(path=output_path, format="A4", print_background=True)
        return {
            "status": "success",
            "message": f"Successfully saved {url} as PDF",
            "output_path": output_path
        }

    async def _save_current_page_as_pdf_async(self, output_path: str) -> dict:
        """Async implementation of save_current_page_as_pdf."""
        await self._page.emulate_media(media="screen")
        await self._page.pdf(path=output_path, format="A4", print_background=True)
        return {
            "status": "success",
            "message": f"Successfully saved current page as PDF",
            "current_url": self._page.url,
            "output_path": output_path
        }

    async def _save_html_async(self, url: str, output_path: str) -> dict:
        """Async implementation of save_html."""
        await self._page.goto(url, wait_until="networkidle")
        html_content = await self._page.content()

        # Use sync file write for simplicity
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return {
            "status": "success",
            "message": f"Successfully saved HTML from {url}",
            "output_path": output_path,
            "content_length": len(html_content)
        }

    async def _click_async(self, selector: str) -> dict:
        """Async implementation of click."""
        await self._page.click(selector)
        return {
            "status": "success",
            "message": f"Successfully clicked element: {selector}",
            "current_url": self._page.url
        }

    async def _fill_form_async(self, selector: str, text: str) -> dict:
        """Async implementation of fill_form."""
        await self._page.fill(selector, text)
        return {
            "status": "success",
            "message": f"Successfully filled field {selector} with text"
        }

    async def _get_text_async(self, selector: str) -> dict:
        """Async implementation of get_text."""
        text = await self._page.text_content(selector)
        return {
            "status": "success",
            "message": f"Successfully extracted text from {selector}",
            "text": text
        }

    async def _get_current_url_async(self) -> dict:
        """Async implementation of get_current_url."""
        return {
            "status": "success",
            "url": self._page.url,
            "title": await self._page.title()
        }

    @tool
    def navigate(self, url: str) -> dict:
        """
        Navigate to a specified URL.

        Args:
            url: The URL to navigate to (must include protocol, e.g., https://)

        Returns:
            dict: Status message and final URL after navigation
        """
        try:
            self._start()
            return self._execute_async(self._navigate_async(url))
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to navigate to {url}: {str(e)}"
            }

    @tool
    def save_as_pdf(self, url: str, output_path: str) -> dict:
        """
        Navigate to a URL and save the entire webpage as a PDF file.

        Args:
            url: The URL of the webpage to save
            output_path: The file path where the PDF should be saved (must end with .pdf)

        Returns:
            dict: Status message and output location
        """
        try:
            self._start()
            return self._execute_async(self._save_as_pdf_async(url, output_path))
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to save PDF: {str(e)}"
            }

    @tool
    def save_current_page_as_pdf(self, output_path: str) -> dict:
        """
        Save the current page as a PDF file without navigating.
        Useful after navigation and interactions have already been performed.

        Args:
            output_path: The file path where the PDF should be saved (must end with .pdf)

        Returns:
            dict: Status message, current URL, and output location
        """
        try:
            self._start()
            return self._execute_async(self._save_current_page_as_pdf_async(output_path))
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to save current page as PDF: {str(e)}"
            }

    @tool
    def save_html(self, url: str, output_path: str) -> dict:
        """
        Navigate to a URL and save the raw HTML content to a file.

        Args:
            url: The URL of the webpage to extract HTML from
            output_path: The file path where the HTML should be saved (e.g., page.html)

        Returns:
            dict: Status message and output location
        """
        try:
            self._start()
            return self._execute_async(self._save_html_async(url, output_path))
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to save HTML: {str(e)}"
            }

    @tool
    def click(self, selector: str) -> dict:
        """
        Click on an element specified by a CSS selector.

        Args:
            selector: CSS selector for the element to click (e.g., "button#submit", ".nav-link")

        Returns:
            dict: Status message
        """
        try:
            self._start()
            return self._execute_async(self._click_async(selector))
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to click element {selector}: {str(e)}"
            }

    @tool
    def fill_form(self, selector: str, text: str) -> dict:
        """
        Fill a form field with text.

        Args:
            selector: CSS selector for the input field (e.g., "input[name='email']")
            text: The text to enter into the field

        Returns:
            dict: Status message
        """
        try:
            self._start()
            return self._execute_async(self._fill_form_async(selector, text))
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to fill field {selector}: {str(e)}"
            }

    @tool
    def get_text(self, selector: str) -> dict:
        """
        Extract text content from an element.

        Args:
            selector: CSS selector for the element (e.g., "h1.title", "#content")

        Returns:
            dict: Status and extracted text content
        """
        try:
            self._start()
            return self._execute_async(self._get_text_async(selector))
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to extract text from {selector}: {str(e)}"
            }

    @tool
    def get_current_url(self) -> dict:
        """
        Get the current URL of the browser page.

        Returns:
            dict: Current URL and page title
        """
        try:
            self._start()
            return self._execute_async(self._get_current_url_async())
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get current URL: {str(e)}"
            }

    def close(self):
        """Clean up browser resources."""
        if self._started:
            if self._page:
                self._execute_async(self._page.close())
            if self._browser:
                self._execute_async(self._browser.close())
            if self._playwright:
                self._execute_async(self._playwright.stop())
            self._started = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()
