import os

from googleapiclient.discovery import build


# Función para leer una clave de API desde un archivo
def read_api_key(filename):
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", filename)
    try:
        with open(secrets_path, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {filename}")
        exit(1)


# Leer claves de API
SHEETS_API_KEY = read_api_key("SHEETS_API_KEY.txt")
DRIVE_API_KEY = read_api_key("DRIVE_API_KEY.txt")