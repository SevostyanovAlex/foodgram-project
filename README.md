## Проект Foodgram

Foodgram - продуктовый помощник с базой кулинарных рецептов. Позволяет публиковать рецепты, сохранять избранные, а также формировать список покупок для выбранных рецептов. Можно подписываться на любимых авторов.

### Технологии:

Python, Django, Django Rest Framework, Docker, Gunicorn, NGINX, PostgreSQL, Yandex Cloud, Continuous Integration, Continuous Deployment

### Развернуть проект на удаленном сервере:

1. Клонируйте репозиторий на компьютер:
    ```
    git clone github.com/SevostyanovAlex/foodgram
    ```
2. Создайте файл переменных окружения `.env` и наполните его своими данными.

3. Создаете образы локально на вашем компьютере

    ```
    docker build -t <your_username>/foodgram_frontend .
    docker build -t your_username/foodgram_backend .
    docker build -t your_username/foodgram_gateway .
    Создание выполняется из той дерриктории, где хранится Dockerfile
    ```

4. Загрузите образы на DockerHub:

    ```
    docker push your_username/foodgram_frontend
    docker push your_username/foodgram_backend
    docker push your_username/foodgram_gateway
    ```

5. Деплой на сервер:

    1. Подключаемся к серверу

    ```
    ssh -i путь_до_файла_с_SSH_ключом/название_файла_закрытого_SSH-ключа login@ip
    ```

    2. Установить на сервере Docker, Docker Compose:

    ```
    sudo apt install curl                                   # установка утилиты для скачивания файлов
    curl -fsSL https://get.docker.com -o get-docker.sh      # скачать скрипт для установки
    sh get-docker.sh                                        # запуск скрипта
    sudo apt-get install docker-compose-plugin              # последняя версия docker compose
    ```

    3. Скопировать на сервер файлы docker-compose.yml
        (команды выполнять находясь в папке infra)
    
    ```
    scp -i PATH_TO_SSH_KEY/SSH_KEY_NAME docker-compose.yml YOUR_USERNAME@SERVER_IP_ADDRESS:/home/YOUR_USERNAME/foodgram/docker-compose.yml
    ```
    - `PATH_TO_SSH_KEY` - путь к файлу с вашим SSH-ключом
    - `SSH_KEY_NAME` - имя файла с вашим SSH-ключом
    - `YOUR_USERNAME` - ваше имя пользователя на сервере
    - `SERVER_IP_ADDRESS` - IP-адрес вашего сервера

    4. Для работы с GitHub Actions необходимо в репозитории в разделе Secrets > Actions создать переменные окружения:

    ```
    SECRET_KEY              # секретный ключ Django проекта
    DOCKER_PASSWORD         # пароль от Docker Hub
    DOCKER_USERNAME         # логин Docker Hub
    HOST                    # публичный IP сервера
    USER                    # имя пользователя на сервере
    PASSPHRASE              # *если ssh-ключ защищен паролем
    SSH_KEY                 # приватный ssh-ключ
    TELEGRAM_TO             # ID телеграм-аккаунта для посылки сообщения
    TELEGRAM_TOKEN          # токен бота, посылающего сообщение

    DB_ENGINE               # django.db.backends.postgresql
    POSTGRES_DB             # postgres
    POSTGRES_USER           # postgres
    POSTGRES_PASSWORD       # postgres
    DB_HOST                 # db
    DB_PORT                 # 5432 (порт по умолчанию)
    ```

    5. Создать и запустить контейнеры Docker, выполнить команду на сервере:

    ```
    sudo docker compose up -d
    ```

    - После успешной сборки выполнить миграции:

    ```
    sudo docker-compose exec backend python manage.py migrate
    ```


    - Собрать статику:

    ```
    sudo docker-compose exec backend python manage.py collectstatic
    ```

    - Скопировать статику в /backend_static/static/:

    ```
    sudo docker compose exec backend cp -r /app/collected_static/. /backend_static/static/
    ```

    - Наполнить базу данных содержимым из файла ingredients.json:

    ```
    sudo docker-compose exec backend python manage.py load_data
    ```

    - Создать суперпользователя:
    ```
    sudo docker compose exec backend python manage.py createsuperuser
    ```

    - Для остановки контейнеров Docker:
    ```
    sudo docker compose down -v      # с их удалением
    sudo docker compose stop         # без удаления
    ```

    6. Откройте конфигурационный файл Nginx в редакторе nano:

        ```
        sudo nano /etc/nginx/sites-enabled/default
        ```

    7. Измените настройки `location` в секции `server`:

        ```
        location / {
            proxy_set_header Host $http_host;
            proxy_pass http://127.0.0.1:9000;
        }
        ```
    8. Перезапустите Nginx:

        ```
        sudo service nginx reload
        ```

Автор:
[Александр Севостьянов](https://github.com/SevostyanovAlex/)