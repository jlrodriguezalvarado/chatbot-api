# Vinum Chatbot (WordPress Plugin)

Plugin for WordPress that adds a floating chatbot widget to the frontend. The widget communicates with the Vinum chatbot backend API.

## Features

- **Floating button** at the bottom-right of the page; click to open the chat window.
- **Configurable in WordPress admin** (Settings → Vinum Chatbot):
  - **API Key** – Used for `Authorization: Bearer` when calling the backend.
  - **Endpoint URL** – Base URL of the chatbot API (e.g. `https://api.example.com`). Chat requests go to `{Endpoint URL}/chat`.
  - **Title** – Shown in the chat header and as the button tooltip.
  - **Button color** – Color picker for the floating button and header.
  - **Button image URL** – Optional image for the floating button (and small logo in the header). Leave empty for the default 💬 icon.
  - **Refresh knowledge URL** – URL called when you click “Aggiorna conoscenza del chatbot” in the admin.
- **“Aggiorna conoscenza del chatbot”** button in the admin to trigger knowledge refresh; it sends a POST request to the configured refresh URL with the same API key in the `Authorization` header.

All settings are stored in the WordPress database (`options` table, option name `vinum_chatbot_settings`).

## Backend expectations

- **Chat:** `POST {api_url}/chat` with body `{ "q": "user message" }` and header `Authorization: Bearer {api_key}`. Response: `{ "answer": "..." }`.
- **Refresh:** Your backend can expose any URL (e.g. `POST /refresh-knowledge`) that triggers a knowledge/vector store refresh. Configure that URL in “Refresh knowledge URL”. The plugin sends POST with the same API key.

## Installation

1. Copy the `vinum-chatbot` folder into `wp-content/plugins/`.
2. In WordPress admin, go to **Plugins** and activate **Vinum Chatbot**.
3. Go to **Settings → Vinum Chatbot** and set at least **Endpoint URL** and **API Key**, then save. The floating widget will appear on the frontend.

## File structure

```
vinum-chatbot/
├── vinum-chatbot.php      # Main plugin: options, admin page, enqueue
├── assets/
│   ├── vinum-chatbot-admin.js   # Admin: color picker, refresh button
│   └── vinum-chatbot-widget.js  # Frontend: floating button + chat UI
└── README.md
```
