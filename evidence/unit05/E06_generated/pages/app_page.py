"""Page object for 'app' (generated; locators are in the repository)."""

from locators.app_locators import LOCATORS


def _selector(strategy, value):
    if strategy == "id":
        return "#" + value
    if strategy == "css":
        return value
    if strategy == "xpath":
        return "xpath=" + value
    if strategy == "text":
        return "text=" + value
    if strategy == "role":
        return "role=" + value
    name, _, expected = value.partition("=")
    return "[" + name + '="' + expected + '"]'


class AppPage:
    def __init__(self, page, base_url):
        self._page = page
        self._base_url = base_url

    def open(self, path):
        self._page.goto(self._base_url + path)

    def _find(self, name):
        entry = LOCATORS[name]
        for strategy, value in [entry["primary"], *entry["fallbacks"]]:
            candidate = self._page.locator(_selector(strategy, value))
            if candidate.count() > 0:
                return candidate.first
        raise AssertionError("no locator strategy matched for " + name)

    def click(self, name):
        self._find(name).click()

    def type(self, name, value):
        self._find(name).fill(value)

    def select(self, name, value):
        self._find(name).select_option(value)

    def assert_text(self, name, expected):
        assert expected in self._find(name).inner_text()

    def assert_visible(self, name):
        assert self._find(name).is_visible()
