import os
from dotenv import load_dotenv
from utils.db_functions import list_ultimos_periodos

load_dotenv()
database_path = os.getenv('DATABASE')

def show_periods() -> None:
    """Muestra los períodos disponibles en la base de datos"""
    periodos = list_ultimos_periodos(database_path)
    print("Períodos disponibles:")
    for periodo in sorted(periodos):
        print(f"- {periodo}")

if __name__ == "__main__":
    show_periods()