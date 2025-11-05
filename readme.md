# Chatbot API

docker-compose exec chatbot_api_app flask db upgrade

docker-compose exec chatbot_api_app flask list_apikeys
docker-compose exec chatbot_api_app flask create_apikey admin

# Wordpress
docker-compose exec chatbot_api_app flask populate_wordpress


sudo chown -R $USER:$USER instance/
docker-compose exec chatbot_api_app flask build_vs