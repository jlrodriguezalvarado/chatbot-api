# Vinum Wines – WordPress / WooCommerce plugin

This plugin exposes a REST API to register and list wine products using the **xtrawine** schema (e.g. from `xtrawine_wines.json`).

## Requirements

- WordPress 5.9+
- WooCommerce 5.0+ (must be installed and active)
- PHP 7.4+

## Installation

1. Copy this folder to `wp-content/plugins/vinum-wines` or use the docker-compose volume (already mapped in this repo).
2. In WP Admin, go to **Plugins** and activate **Vinum Wines**.
3. Ensure WooCommerce is installed and activated.

## REST API

Base path: `/wp-json/vinum/v1`

### Create product (POST /products)

Creates a WooCommerce product and stores the full wine payload in product meta.

- **Auth:** Application password or user with `manage_woocommerce` / `manage_options`.
- **Body:** One wine object (same structure as in `xtrawine_wines.json`), e.g.:
  - `schema_version`, `source`, `product`, `pricing`, `tasting_notes`, `serving`, `pairings`, `awards`, `producer_info`, `media`, `technical_sheet`, `raw`, etc.

### List products (GET /products)

Returns all products that have wine data (meta `_vinum_wine_data`).

- **Params:** `per_page` (1–100, default 100), `page` (default 1).
- **Response:** `{ "products": [ { "id", "title", "content", "wine_data" }, ... ], "total", "page", "per_page" }`.
- **Auth:** Not required (public read).

## Usage with this repo

1. Run `flask populate_wordpress` to send `xtrawine_wines.json` to WordPress (uses `WP_USER`, `WP_PASSWORD`, optional `WP_BASE_URL`).
2. Run `flask import_wordpress_posts` to pull those products into the local `post` table (title, content, wp_id, wine_data).
3. Run `flask build_vs` to build the Vector Store from the `post` table for the chatbot.
