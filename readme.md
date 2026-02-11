# Chatbot API

## Secret Key

```bash
docker-compose exec chatbot_api_app flask generate_secret_key
```
## Database migrations

```bash
docker-compose exec chatbot_api_app flask db upgrade
```

## App keys

```bash
docker-compose exec chatbot_api_app flask list_apikeys
docker-compose exec chatbot_api_app flask create_apikey admin
```

## Configurar WP jwt

```bash
docker cp chatbot_api_wordpress:/var/www/html/wp-config.php ./wp-config.php
```

## Fill WP products

```bash
docker-compose exec chatbot_api_app flask populate_wordpress
```

## Fill DB with wordpress products

```bash
docker-compose exec chatbot_api_app flask import_wordpress_posts
```

## Create Vector Store

```bash
docker-compose exec chatbot_api_app flask build_vs
```

## Delete Vector Store

```bash
docker-compose exec chatbot_api_app flask delete_vs <VS>
```
