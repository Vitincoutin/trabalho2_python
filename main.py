from menu import menu_principal
from persistencia import inicializar_dados


def main():
    try:
        inicializar_dados()
        menu_principal()
    except (EOFError, KeyboardInterrupt):
        print("\nSistema encerrado.")
    except (OSError, ValueError) as erro:
        print(f"Erro ao acessar os dados: {erro}")


if __name__ == "__main__":
    main()

