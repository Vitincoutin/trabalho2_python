import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import persistencia
from estoque import registrar_movimento
from main import main
from mrp import executar_mrp


def criar_item(codigo, seguranca, lote, lead_time, unidade="un"):
    return {
        "codigo": codigo,
        "tipo": codigo[:2],
        "descricao": codigo,
        "unidade": unidade,
        "estoque_seguranca": seguranca,
        "lote_minimo": lote,
        "lead_time": lead_time,
    }


class TesteMRP(unittest.TestCase):
    def setUp(self):
        pasta = TemporaryDirectory(prefix="pedal-mrp-")
        self.addCleanup(pasta.cleanup)
        self.dados = Path(pasta.name)
        caminho = patch.object(persistencia, "PASTA_DATA", self.dados)
        caminho.start()
        self.addCleanup(caminho.stop)

        itens = [
            criar_item("MP-108", 0, 1, 1, "m"),
            criar_item("SA-010", 0, 5, 1),
            criar_item("PA-001", 5, 10, 2),
            criar_item("MP-109", 0, 1, 0),
            criar_item("PA-002", 0, 8, 1),
        ]
        self.planos = {
            "PA-001": [6, 0, 0, 12, 0, 0, 0, 0],
            "PA-002": [0, 0, 7, 0, 0, 0, 0, 0],
        }
        estrutura = {
            "PA-001": {"SA-010": 2, "MP-108": 1},
            "PA-002": {"SA-010": 1},
            "SA-010": {"MP-108": 3.5},
        }
        persistencia.salvar_json("itens.json", itens)
        persistencia.salvar_json("mps.json", self.planos)
        persistencia.salvar_json("estrutura.json", estrutura)
        registrar_movimento("PA-001", "ENTRADA", 2, "Saldo do teste")

    def arquivos(self):
        return {
            arquivo.name: arquivo.read_bytes()
            for arquivo in self.dados.iterdir()
        }

    def test_demanda_estoque_seguranca_lote_e_lead_time(self):
        resultados = executar_mrp()
        self.assertEqual(
            list(resultados),
            ["PA-001", "PA-002", "SA-010", "MP-108", "MP-109"],
        )
        pa = resultados["PA-001"]
        semanas = pa["semanas"]
        self.assertEqual(
            [sem["semana"] for sem in semanas], list(range(1, 9))
        )
        self.assertEqual(
            [sem["necessidade_bruta"] for sem in semanas],
            self.planos["PA-001"],
        )
        # Semana 1: NL = 6 + 5 - (2 + 0) = 9 e EP = 2 + 10 - 6.
        self.assertEqual(semanas[0]["necessidade_liquida"], 9)
        self.assertEqual(semanas[0]["recebimento_planejado"], 10)
        self.assertEqual(semanas[0]["estoque_projetado"], 6)
        self.assertEqual(semanas[1]["estoque_projetado"], 6)
        self.assertEqual(semanas[3]["necessidade_liquida"], 11)
        self.assertEqual(semanas[3]["recebimento_planejado"], 11)
        self.assertEqual(semanas[3]["estoque_projetado"], 5)
        self.assertEqual(semanas[1]["liberacao_planejada"], 11)
        atrasada, normal = pa["ordens_planejadas"]
        self.assertEqual(atrasada["semana_liberacao"], -1)
        self.assertEqual(atrasada["status"], "ATRASADA")
        self.assertEqual(normal["semana_liberacao"], 2)
        self.assertEqual(normal["status"], "PLANEJADA")
        self.assertEqual(resultados["MP-109"]["ordens_planejadas"], [])

    def test_explosao_compartilhada_com_atrasos(self):
        resultados = executar_mrp()
        sa = resultados["SA-010"]
        anterior, = sa["necessidades_anteriores"]
        self.assertEqual(anterior["semana"], -1)
        self.assertEqual(anterior["necessidade_bruta"], 20)
        # Os dois PA liberam na semana 2: 11 * 2 + 8 * 1 = 30.
        self.assertEqual(sa["semanas"][1]["necessidade_bruta"], 30)
        self.assertEqual(sa["semanas"][0]["liberacao_planejada"], 30)

        mp = resultados["MP-108"]
        self.assertEqual(
            [(sem["semana"], sem["necessidade_bruta"])
             for sem in mp["necessidades_anteriores"]],
            [(-2, 70), (-1, 10)],
        )
        self.assertEqual(mp["semanas"][0]["necessidade_bruta"], 105)
        self.assertEqual(mp["semanas"][1]["necessidade_bruta"], 11)
        self.assertEqual(mp["ordens_planejadas"][0]["semana_liberacao"], -3)
        self.assertEqual(mp["ordens_planejadas"][0]["tipo"], "COMPRA")

    def test_recebimentos_firmes_e_liberados(self):
        ordens = [
            {"codigo": "PA-001", "semana_recebimento": semana,
             "status": status, "quantidade": quantidade}
            for semana, status, quantidade in (
                (1, "FIRME", 3), (1, "LIBERADA", 4),
                (1, "PLANEJADA", 100), (1, "ATRASADA", 100), (9, "FIRME", 100),
            )
        ]
        semana = executar_mrp(ordens)["PA-001"]["semanas"][0]
        self.assertEqual(semana["recebimento_programado"], 7)
        self.assertEqual(semana["necessidade_liquida"], 2)
        self.assertEqual(semana["recebimento_planejado"], 10)
        self.assertEqual(semana["estoque_projetado"], 13)

    def test_pendencias_consumem_saldo_inicial(self):
        registrar_movimento("MP-108", "ENTRADA", 75, "Saldo do teste")
        mp = executar_mrp()["MP-108"]
        primeira, segunda = mp["necessidades_anteriores"]
        self.assertEqual(primeira["estoque_projetado"], 5)
        self.assertEqual(primeira["recebimento_planejado"], 0)
        self.assertEqual(segunda["recebimento_planejado"], 5)
        self.assertEqual(mp["semanas"][0]["necessidade_liquida"], 105)

    def test_recalculo_e_preservacao_dos_arquivos(self):
        # Simula uma interrupção após gravar o kardex, mas antes do JSON.
        persistencia.salvar_json("estoque.json", {"PA-001": "0"})
        antes = self.arquivos()
        resultado = executar_mrp()
        self.assertEqual(resultado["PA-001"]["saldo_inicial"], 2)
        self.assertEqual(executar_mrp(), resultado)
        self.assertEqual(self.arquivos(), antes)

        self.planos["PA-001"][0] = 0
        persistencia.salvar_json("mps.json", self.planos)
        registrar_movimento("PA-001", "ENTRADA", 7, "Nova entrada de teste")
        antes = self.arquivos()
        recalculado = executar_mrp()["PA-001"]
        self.assertEqual(recalculado["saldo_inicial"], 9)
        self.assertEqual(recalculado["semanas"][0]["necessidade_bruta"], 0)
        self.assertEqual(recalculado["semanas"][0]["recebimento_planejado"], 0)
        self.assertEqual(self.arquivos(), antes)

    def test_menu_executa_e_consulta(self):
        opcoes = ["4", "2", "1", "2", "PA-001", "2", "SA-010", "0", "0"]
        saida = StringIO()
        with patch("builtins.input", side_effect=opcoes):
            with redirect_stdout(saida):
                main()
        texto = saida.getvalue()
        self.assertIn("Execute o cálculo antes de consultar um item.", texto)
        self.assertIn("MRP calculado para 5", texto)
        self.assertIn("Necessidade líquida", texto)
        self.assertIn("Sem 8", texto)
        self.assertNotIn("Sem 9", texto)
        self.assertIn("ATRASADA | PA-001", texto)
        self.assertIn("Necessidades anteriores ao horizonte", texto)


if __name__ == "__main__":
    unittest.main()
