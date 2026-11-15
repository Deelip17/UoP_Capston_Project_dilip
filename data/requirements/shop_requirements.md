# Demo Shop requirements (synthetic, for the Unit 6 evaluation)

## Accounts
- The system shall allow a registered customer to log in with an email address and a password.
- The system shall show the message "Invalid email or password" and keep the product list closed when the credentials are wrong.
- The system shall not show the product list, the cart or the checkout page to a visitor who is not logged in.

## Catalogue
- The system shall show a product list in which every product has a name and a price in dollars.
- The system shall show exactly three products: Backpack, Desk Lamp and Notebook.
- The product list shall contain an add button for every product.
- The product page should be easy to use.

## Cart
- The system shall add a product to the cart when the customer selects its add button.
- The system shall show each product in the cart with its name and price.
- The system shall remove a product from the cart when the customer selects its remove button.
- The system shall show the message "Your cart is empty" when the cart holds no products.
- The system shall provide a checkout button in a cart that holds at least one product.

## Checkout
- The system shall require a full name before an order can be placed.
- The system shall refuse an order when the full name is longer than 80 characters.
- The system shall refuse an order when the cart is empty.
- The system shall show a confirmation message after a successful order.
- The system shall empty the cart after an order is placed.
- The checkout should be fast.

## Other
- The system shall provide a link back to the product list on the confirmation page.
- The system shall refuse a request to add a product that is not in the catalogue.
