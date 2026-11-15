"""Locator repository for the 'app' page. Generated; selectors live only here."""

LOCATORS = {
    'main_input': {
        "primary": ('id', 'main-input'),
        "fallbacks": [('css', '[data-testid="main-input"]'), ('xpath', '//input[1]')],
    },
    'submit_button': {
        "primary": ('id', 'submit'),
        "fallbacks": [('css', 'button[type=submit]'), ('text', 'Submit')],
    },
    'result_message': {
        "primary": ('id', 'result'),
        "fallbacks": [('css', '.result'), ('attr', 'data-testid=result')],
    },
}
