# ruff: noqa: E501  (test sources are single-line strings; line length is irrelevant for data)
"""Recipes of the hold-out corpus: a second set of failures, written after the rule changes.

The first corpus was labelled, scored, and then used to improve the analyzer's rules, so
its score after the change is not independent. These recipes are different tests (other
elements, other wording, other servers, other kinds of input). They are meant to be
labelled by the author before the improved rules are scored on them. The analyzer is not run
on them here.
"""

from __future__ import annotations

LOCATOR_FAILURES = [
    ("login", "screen.open('/')\n    screen.click('password')"),
    ("login", "screen.open('/')\n    screen.assert_text('username', '')"),
    (
        "login",
        "screen.open('/products')\n    screen.click('add_backpack')\n    screen.click('cart_link')",
    ),
    (
        "login",
        "screen.open('/products')\n    screen.assert_text('add_backpack', 'Add Backpack to cart')",
    ),
    (
        "login",
        "screen.open('/checkout')\n    screen.type('ship_name', 'Ada Lovelace')\n    screen.click('place_order')",
    ),
    (
        "login",
        "screen.open('/')\n    screen.type('username', 'a@example.com')\n    screen.type('password', 'x')\n    screen.click('login_submit')",
    ),
    ("login", "screen.open('/products')\n    screen.assert_visible('cart_link')"),
    ("login", "screen.open('/checkout')\n    screen.assert_text('place_order', 'Place order')"),
]

RAW = [
    # missing elements and unusual selectors
    "page.goto(base_url + '/')\n    page.click('#does-not-exist')",
    "page.goto(base_url + '/products')\n    page.click('text=Add Teapot to cart', timeout=500)",
    "page.goto(base_url + '/')\n    page.locator('button').nth(7).click(timeout=500)",
    "page.goto(base_url + '/')\n    page.locator('input').click(timeout=500)",
    # expectations about page content
    "page.goto(base_url + '/')\n    assert page.inner_text('label') == 'E-mail'",
    "page.goto(base_url + '/products')\n    assert page.locator('.price').count() == 5",
    "page.goto(base_url + '/products')\n    assert 'Free shipping' in page.inner_text('body')",
    "page.goto(base_url + '/checkout')\n    assert page.title() == 'Checkout'",
    "page.goto(base_url + '/')\n    assert page.is_visible('text=Create account')",
    "page.goto(base_url + '/')\n    assert page.get_attribute('input[name=password]', 'type') == 'text'",
    "page.goto(base_url + '/products')\n    assert page.inner_text('h1') == 'Catalogue'",
    "page.goto(base_url + '/products')\n    assert page.locator('li').first.inner_text().startswith('Notebook')",
    "page.goto(base_url + '/')\n    assert page.url.endswith('/login')",
    "page.goto(base_url + '/checkout')\n    assert page.locator('button').count() == 0",
    # servers, hosts and addresses
    "page.goto('http://127.0.0.1:3/')",
    "page.goto('http://127.0.0.1:5/index.html')",
    "page.goto('http://shop.invalid/')",
    "page.goto('https://127.0.0.1:1/')",
    "page.goto('http://localhost:3/')",
    "response = page.goto(base_url + '/orders')\n    assert response.ok",
    "response = page.goto(base_url + '/admin')\n    assert response.status < 400",
    "page.goto('http://169.254.1.1/')",
    # waiting
    "page.goto(base_url + '/')\n    page.wait_for_load_state('networkidle', timeout=1)",
    "page.goto(base_url + '/')\n    page.wait_for_selector('.toast-success', timeout=400)",
    "page.goto(base_url + '/')\n    page.click('button', timeout=1)",
    "page.goto(base_url + '/products')\n    page.wait_for_timeout(50)\n"
    "    page.wait_for_selector('text=Out of stock', timeout=300)",
    "page.goto(base_url + '/')\n    page.wait_for_function('window.appReady === true', timeout=400)",
    "page.goto(base_url + '/')\n    with page.expect_navigation(timeout=300):\n        pass",
    # forms and input
    "page.goto(base_url + '/products')\n    page.click('text=Add Notebook to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', '')\n"
    "    page.click('text=Place order')\n    assert 'Thank you' in page.inner_text('body')",
    "page.goto(base_url + '/products')\n    page.click('text=Add Desk Lamp to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', 'Q' * 120)\n"
    "    page.click('text=Place order')\n    assert page.is_visible('text=Thank you for your order')",
    "page.goto(base_url + '/products')\n    page.click('text=Add Backpack to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', ' ')\n"
    "    page.click('text=Place order')\n    assert 'confirmed' in page.title().lower()",
    "page.goto(base_url + '/products')\n    page.click('text=Add Notebook to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', 'Z' * 81)\n"
    "    page.click('text=Place order')\n    assert page.inner_text('h2') == 'Thank you for your order'",
    "page.goto(base_url + '/')\n    page.fill('input[name=username]', 'x' * 500)\n"
    "    page.fill('input[name=password]', '')\n    page.click('text=Log in')\n"
    "    assert page.is_visible('text=Welcome back')",
    "expected = {'user': 'ada'}\n    assert expected['email'] == 'ada@example.com'",
    "rows = ['a', 'b']\n    assert rows[5] == 'c'",
    "import csv\n    with open('customers.csv') as handle:\n        csv.reader(handle)",
    "page.goto(base_url + '/products')\n    page.click('text=Add Backpack to cart')\n"
    "    page.goto(base_url + '/checkout')\n    page.fill('input[name=name]', '')\n"
    "    page.click('text=Place order')\n    assert page.locator('h2').count() == 1",
    # unexpected exceptions
    "value = None\n    value.strip()",
    "'abc' + 5",
    "assert False, 'the checkout total should be 69.40'",
    "items = []\n    items.pop()",
    "raise AssertionError('cart badge shows 2 but 3 items were added')",
    "raise TimeoutError('queue did not drain')",
    "raise ValueError('quantity must be positive')",
    "raise ConnectionError('payment gateway unreachable')",
    "raise RuntimeError('database migration not applied')",
    "assert 'a' == 'b', 'labels differ'",
    "{}.update(1)",
    "raise PermissionError('cannot write report')",
]
