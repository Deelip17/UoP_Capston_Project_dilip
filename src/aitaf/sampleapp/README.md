# sampleapp

The local web shop that serves as the system under test, with locators that can be changed reproducibly (FR-38). It imports nothing from the framework, so the application being tested is independent of the system that tests it. Content and credentials are synthetic (ADR-005).

| Module | Purpose | Requirements |
|---|---|---|
| `elements` | The ten target elements over five pages (login, products, cart, checkout, confirmation) and their id, class, XPath and text locators | FR-38 |
| `mutations` | The ordered catalogue of 37 mutations (id, class, structure, text), each changing one element in one way | FR-38, NFR-08 |
| `pages` | Pure rendering of each page with chosen mutations; an `oracle` mode adds a ground-truth attribute so the evaluation knows which element a test meant | FR-38, NFR-08 |
| `server` | Standard-library HTTP server on the loopback address only; serves the mutations it was started with | FR-21, NFR-11 |
| `snapshots` | Writes DOM snapshots (`data/dom/shop/`) used as healing fixtures | FR-38 |

## Use

```text
python -m aitaf.sampleapp serve --port 8765 [--mutation M-login_submit-id]
python -m aitaf.sampleapp snapshot --out data/dom/shop
python -m aitaf.sampleapp list
```

Log in as `demo@example.com` / `demo-pass`. The 20 requirements the shop satisfies are in `data/requirements/shop_requirements.md`.

## Tests

`tests/unit/sampleapp/`: every baseline locator resolves to exactly one element; every mutation breaks its own locator, damages no other element and leaves the element findable by the ground-truth attribute; the committed DOM fixtures match the application; the server journey (login, add, remove, checkout) runs over real HTTP.

## Not built

- One shared session in memory: no cookies, no concurrent users, no persistence. It is a fixture, not a web application.
- Ten elements and four mutation kinds only; no mutations that remove an element, move it to another page, or change several attributes at once.
- Mutations are static page rewrites: no JavaScript, no timing changes, no flaky behaviour.
- Not yet connected to the Execution Engine or the evaluation harness (Unit 6, later slices).
