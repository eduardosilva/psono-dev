# PSONO Dev Example

> **WARNING: Do Not Use in Production**
> 
> This README provides instructions for setting up a local development environment with PSONO. It is important to note that all configuration files provided here are intended for development purposes only and should not be used in a production environment.

## Getting Started

The official documentation about [PSONO CE](https://doc.psono.com/admin/installation/install-psono-ce.html#preamble) you can find more options about running PSONO, especially in a production environment.

1. Generate credentials and update the `server-settings.yaml`:

```bash
docker run --rm -ti psono/psono-combo:latest python3 ./psono/manage.py generateserverkeys

# Copy paste this content into your settings.yml and replace existing occurrences
# 
# WARNING: Do this only for a fresh installation!
# Changing those variables afterwards will break the program e.g.:
# Activation links will not work, Server will not be able to read user emails, ...

SECRET_KEY: 'SOME SUPER SECRET KEY THAT SHOULD BE RANDOM AND 32 OR MORE DIGITS LONG'
ACTIVATION_LINK_SECRET: 'SOME SUPER SECRET ACTIVATION LINK SECRET THAT SHOULD BE RANDOM AND 32 OR MORE DIGITS LONG'
DB_SECRET: 'SOME SUPER SECRET DB SECRET THAT SHOULD BE RANDOM AND 32 OR MORE DIGITS LONG'
EMAIL_SECRET_SALT: '$2b$12$XUG.sKxC2jmkUvWQjg53.e'
PRIVATE_KEY: '02...0b'
PUBLIC_KEY: '02...0b'
```

2. Start by running the following command to bring up the PSONO services using Docker Compose:

```bash
docker compose up -d
```

3. Once the services are up, open your browser and navigate to http://localhost:10200/server/info/ to access the PSONO server information.
4. Create an admin user:

```bash
docker container exec -it psono-combo python3 ./psono/manage.py createuser admin@example.com admin admin@example.com
```
> **Make sure Docker Compose is up and running**

5. Follow [this guideline](https://doc.psono.com/user/api-key/creation.html#guide) to create an API key.
6. Update the information in the `main.py`:

```python
# Replace the values of the variables below with the details of your unrestricted API key:
api_key_id = 'f8..8f'
api_key_private_key = '66...3b'
api_key_secret_key = '0a...52'
server_url = 'https://example.com/server'
server_public_key = '02...0b'
server_signature = '4c...d1'
```

7. Create a python environment:

```bash
python3 -m venv .env
```

8. Install the requirements:

```bash
pip install -r requirements.txt
```

9. Run the `read.py` to read/test the API:

```bash
python3 read.py
```

10. Run the `write.py` to write a new secret:

```bash
python3 write.py
```