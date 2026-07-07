import random
import time
from urllib.parse import quote_plus

import pyautogui

from imitator import Browser, Element, Wait, WaitStrategy


SEARCH_QUERY = "википедия англ"
WIKI_HOPS = 4
START_WIKI_URL = "https://en.wikipedia.org/wiki/Wikipedia"


def human_pause(min_seconds: float = 0.4, max_seconds: float = 1.2) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def wait_ready(browser: Browser, seconds: float = 0.7) -> None:
    browser.wait_for_idle(silence=seconds, timeout=20)
    human_pause(0.3, seconds + 0.6)


def human_hover(element: Element) -> None:
    element.scroll_into_view()
    human_pause(0.2, 0.6)
    element.hover(
        offset_x=random.uniform(-4, 4),
        offset_y=random.uniform(-3, 3),
        human=True,
    )
    human_pause(0.4, 1.0)


def human_click(element: Element) -> None:
    human_hover(element)
    element.click(human=True)
    human_pause(0.5, 1.2)


def human_scroll_down() -> None:
    for _ in range(random.randint(2, 5)):
        pyautogui.scroll(-random.randint(3, 7))
        human_pause(0.25, 0.8)


def href_of(element: Element) -> str:
    return element.attrs.get("href", "")


def clean_text(element: Element) -> str:
    return " ".join(element.text.split())


def first_visible(elements: list[Element]) -> Element | None:
    for element in elements:
        if element.visible:
            return element
    return elements[0] if elements else None


def click_google_consent_if_present(browser: Browser) -> None:
    consent_words = [
        "отклонить все",
        "reject all",
        "принять все",
        "accept all",
        "i agree",
        "согласен",
    ]
    controls = browser.query_selector_all(
        'button, div[role="button"], input[type="submit"], a[role="button"]'
    )
    for control in controls:
        label = " ".join(
            [
                clean_text(control),
                control.attrs.get("value", ""),
                control.attrs.get("aria-label", ""),
            ]
        ).strip().lower()
        if any(word in label for word in consent_words):
            print("Google consent page detected, clicking:", label[:60])
            human_click(control)
            wait_ready(browser)
            return


def open_google_result(browser: Browser) -> bool:
    print("Opening Google search...")
    browser.goto(f"https://www.google.com/search?q={quote_plus(SEARCH_QUERY)}")
    wait_ready(browser)
    click_google_consent_if_present(browser)
    print("Google:", browser.title, browser.url)

    google_links = browser.query_selector_all("a[href]")
    wikipedia_links = [
        link
        for link in google_links
        if "en.wikipedia.org" in href_of(link)
        and "/wiki/" in href_of(link)
        and ":" not in href_of(link).split("/wiki/", 1)[-1]
    ]
    if not wikipedia_links:
        wikipedia_links = [
            link
            for link in google_links
            if "wikipedia.org" in href_of(link) and "/wiki/" in href_of(link)
        ]

    result = first_visible(wikipedia_links)
    if result is None:
        print("No Wikipedia result found on Google.")
        return False

    print("Clicking Google result:", clean_text(result)[:80] or href_of(result))
    human_click(result)
    wait_ready(browser)
    if "wikipedia.org" in browser.url:
        return True

    title_links = browser.query_selector_all("a[href*='wikipedia.org'] h3")
    title = first_visible(title_links)
    if title is not None:
        print("Google result did not open; trying the visible result title.")
        human_click(title)
        wait_ready(browser)

    return "wikipedia.org" in browser.url


def ensure_article_page(browser: Browser) -> None:
    if "en.wikipedia.org" in browser.url and "/wiki/" in browser.url:
        if ":" not in browser.url.split("/wiki/", 1)[-1]:
            return

    links = browser.query_selector_all("a[href]")
    article_links = [
        link
        for link in links
        if "en.wikipedia.org" in href_of(link)
        and "/wiki/" in href_of(link)
        and ":" not in href_of(link).split("/wiki/", 1)[-1]
    ]
    article_link = first_visible(article_links)
    if article_link is not None:
        print("Clicking an English Wikipedia article link.")
        human_click(article_link)
        wait_ready(browser)
        return

    raise RuntimeError("Could not open an English Wikipedia article using visible links.")


def wikipedia_article_links(browser: Browser) -> list[Element]:
    links = browser.query_selector_all("p a[href*='/wiki/']")
    usable: list[Element] = []
    for link in links:
        href = href_of(link)
        if "/wiki/" not in href:
            continue
        page = href.split("/wiki/", 1)[-1]
        text = clean_text(link)
        if len(text) < 4:
            continue
        if ":" in page or "#" in href:
            continue
        usable.append(link)
    return usable


def browse_wikipedia(browser: Browser) -> None:
    browser.wait(
        "body",
        strategy=WaitStrategy.STABLE,
        condition=Wait().visible().stable(duration_ms=500),
        timeout=20,
    )
    ensure_article_page(browser)
    wait_ready(browser)
    print("Wikipedia article:", browser.title, browser.url)

    for hop in range(WIKI_HOPS):
        human_scroll_down()

        links = wikipedia_article_links(browser)
        if not links:
            print("No internal article links found, stopping.")
            break

        link = random.choice(links[min(hop * 2, len(links) - 1) :])
        description = clean_text(link)[:80] or href_of(link)
        print(f"Hop {hop + 1}: moving cursor to '{description}'")
        human_click(link)
        wait_ready(browser)
        print("Now at:", browser.title, browser.url)


def main() -> None:
    with Browser() as browser:
        if not open_google_result(browser):
            print("Google click did not navigate; opening the starting article.")
            browser.goto(START_WIKI_URL)
            wait_ready(browser)
        browse_wikipedia(browser)
        print("Done.")


if __name__ == "__main__":
    main()
