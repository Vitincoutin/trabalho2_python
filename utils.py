import math
import re


def ler_texto(mensagem, atual=None):
    while True:
        texto = input(mensagem).strip()
        if texto:
            return texto
        if atual is not None:
            return atual
        print("Preencha este campo.")


def ler_opcao(mensagem, opcoes):
    while True:
        opcao = input(mensagem).strip()
        if opcao in opcoes:
            return opcao
        print("Opção inválida. Tente novamente.")


def ler_codigo(mensagem):
    while True:
        codigo = input(mensagem).strip().upper()
        if re.fullmatch(r"(PA|SA|MP)-[0-9]{3}", codigo):
            return codigo
        print("Formato inválido. Use um código como PA-001, SA-010 ou MP-100.")


def ler_numero(mensagem, conversor=int, minimo=0, atual=None):
    while True:
        texto = input(mensagem).strip()
        if not texto and atual is not None:
            return atual
        try:
            if conversor is float:
                texto = texto.replace(",", ".")
            valor = conversor(texto)
            if valor >= minimo and (conversor is int or math.isfinite(valor)):
                return valor
        except ValueError:
            pass
        tipo = "inteiro" if conversor is int else "numérico"
        print(f"Informe um valor {tipo} maior ou igual a {minimo}.")
