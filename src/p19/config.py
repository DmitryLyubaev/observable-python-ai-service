import os


def database_url():
    return os.environ["P19_DATABASE_URL"]


def token():
    return os.environ["P19_TOKEN"]
