import csv
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from decimal import Decimal
from io import StringIO
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from unittest.mock import patch

import persistencia
from capacidade import (
    calcular_crp,
    carregar_centros,
    carregar_roteiros,
    salvar_centro,
    salvar_roteiro,
)
from custos import calcular_custo_padrao
from estoque import (
    ARQUIVO_OPERACAO,
    consultar_kardex,
    consultar_saldos,
    registrar_movimento,
)
from main import main
from mps import carregar_mps
from ordens import (
    apontar_producao,
    carregar_ordens,
    firmar_ordem,
    liberar_ordem,
    recalcular_ordens,
    receber_compra,
)


def criar_item(codigo, custo, unidade="un"):
    return {
        "codigo": codigo, "tipo": codigo[:2], "descricao": f"Peça {codigo}",
        "unidade": unidade, "custo_unitario": custo, "estoque_seguranca": 0,
        "lote_minimo": 1, "lead_time": 1,
    }


def executar_menu(*opcoes):
    saida = StringIO()
    with patch("builtins.input", side_effect=opcoes), redirect_stdout(saida):
        main()
    return saida.getvalue()


class BaseTemporaria(unittest.TestCase):
    def setUp(self):
        pasta = TemporaryDirectory(prefix="pedal-mrp-")
        self.addCleanup(pasta.cleanup)
        self.raiz = Path(pasta.name)
        self.dados = self.raiz / "data"
        self.dados.mkdir()
        alterar_dir = patch.object(persistencia, "PASTA_DATA", self.dados)
        alterar_dir.start()
        self.addCleanup(alterar_dir.stop)
        configurar_mpl = patch.dict(os.environ, {
            "MPLBACKEND": "Agg", "MPLCONFIGDIR": str(self.raiz / "mpl"),
        })
        configurar_mpl.start()
        self.addCleanup(configurar_mpl.stop)

    def arquivos(self):
        return {
            arquivo.name: arquivo.read_bytes()
            for arquivo in self.dados.iterdir()
            if arquivo.suffix in (".json", ".csv")
        }


class TesteCiclo(BaseTemporaria):
    def setUp(self):
        super().setUp()
        itens = [
            criar_item("PA-001", 900),
            criar_item("SA-010", 100),
            criar_item("MP-101", 4, "m"),
            criar_item("MP-102", 5),
        ]
        persistencia.salvar_json("itens.json", itens)
        persistencia.salvar_json("estrutura.json", {
            "PA-001": {"SA-010": 2, "MP-101": 0.5},
            "SA-010": {"MP-101": 1.5, "MP-102": 1},
        })
        salvar_centro("CT-01", "Montagem", 1, 30)
        salvar_centro("CT-02", "Preparação", 3, 20)
        salvar_roteiro("PA-001", "CT-01", 0.5)
        salvar_roteiro("SA-010", "CT-02", 0.25)

    def planejar(self, semana=6, demanda=3):
        demandas = [0] * 8
        demandas[semana - 1] = demanda
        persistencia.salvar_json("mps.json", {"PA-001": demandas})
        return recalcular_ordens()

    def localizar(self, codigo):
        return next(ordem["id"] for ordem in carregar_ordens()
                    if ordem["codigo"] == codigo)

    def test_ciclo_pelo_menu_com_csv_e_quatro_png(self):
        saida = executar_menu(
            "1", "3", "PA-001", "9", "PA-001", "0",
            "3", "1", "PA-001", "0", "0", "0", "0", "0", "3", "0", "0", "0",
            "4", "1", "2", "PA-001", "0", "5", "1", "0", "0",
        )
        self.assertIn("Nível 2 | MP-101", saida)
        self.assertIn("MRP calculado para 4", saida)
        self.assertIn("Sem 8", saida)
        self.assertNotIn("Erro:", saida)
        self.assertEqual(carregar_mps()["PA-001"], [0, 0, 0, 0, 0, 3, 0, 0])

        ordens = carregar_ordens()
        self.assertEqual(len(ordens), 5)
        ids = {ordem["id"] for ordem in ordens}
        self.assertEqual(len(ids), 5)
        for ordem in ordens:
            self.assertEqual(ordem["status"], "PLANEJADA")
            self.assertIn(ordem["id"], saida)
            self.assertIn(
                "Operação confirmada",
                executar_menu("5", "2", ordem["id"], "0", "0"),
            )

        self.assertTrue(all(
            not sem["carga"] for sem in calcular_crp()["CT-01"]
        ))
        for ordem in ordens:
            self.assertIn(
                "Operação confirmada",
                executar_menu("5", "3", ordem["id"], "0", "0"),
            )
        saida = executar_menu("6", "1", "0", "7", "PA-001", "0")
        self.assertIn("150.0%", saida)
        self.assertIn("Total por unidade: R$ 49.00", saida)
        self.assertNotIn("Erro:", saida)
        crp = calcular_crp()
        self.assertEqual(len(crp["CT-01"]), 8)
        self.assertEqual(crp["CT-01"][4]["carga"], Decimal("1.5"))
        self.assertTrue(crp["CT-01"][4]["sobrecarga"])
        self.assertEqual(crp["CT-02"][3]["utilizacao"], 50)
        self.assertFalse(crp["CT-02"][3]["sobrecarga"])

        saida = executar_menu("8", "6", "CT-01", "0", "0")
        self.assertIn("capacidade_CT-01.png", saida)

        for ordem in ordens:
            if ordem["tipo"] == "OC":
                self.assertIn("Operação confirmada", executar_menu(
                    "5", "5", ordem["id"], "0", "0",
                ))
        saldos = consultar_saldos()
        self.assertEqual(saldos, {"MP-101": Decimal("10.5"), "MP-102": 6})

        for codigo in ("SA-010", "PA-001"):
            self.assertIn("Operação confirmada", executar_menu(
                "5", "4", self.localizar(codigo), "0", "0",
            ))
        self.assertEqual(consultar_saldos(), {
            "MP-101": 0, "MP-102": 0, "SA-010": 0, "PA-001": 3,
        })
        movimentos = consultar_kardex()
        self.assertEqual(len(movimentos), 9)
        self.assertEqual({mov["documento_motivo"] for mov in movimentos}, ids)
        self.assertEqual(movimentos[-1]["codigo"], "PA-001")
        self.assertEqual(movimentos[-1]["saldo_resultante"], "3")
        self.assertTrue(all(ordem["status"] == "ENCERRADA"
                            for ordem in carregar_ordens()))
        self.assertEqual(calcular_crp()["CT-01"][4]["carga"], 0)

        antes = self.arquivos()
        saida = executar_menu(
            "2", "4", "PA-001", "5", "", "0",
            "8", "1", "2", "3", "4", "PA-001", "5", "0", "0",
        )
        self.assertIn("Saldo de PA-001 | Peça PA-001: 3 un.", saida)
        self.assertIn(self.localizar("PA-001"), saida)
        self.assertNotIn("Erro:", saida)
        self.assertEqual(self.arquivos(), antes)

        saida = self.raiz / "saida"
        with (saida / "estoque.csv").open(encoding="utf-8", newline="") as arq:
            estoque = {linha["codigo"]: linha for linha in csv.DictReader(arq)}
        self.assertEqual(estoque["PA-001"]["saldo_atual"], "3")
        self.assertEqual(estoque["PA-001"]["descricao"], "Peça PA-001")
        self.assertEqual(estoque["MP-101"]["unidade"], "m")
        with (saida / "ordens.csv").open(encoding="utf-8", newline="") as arq:
            exportadas = list(csv.DictReader(arq))
        self.assertEqual({ordem["id"] for ordem in exportadas}, ids)
        self.assertEqual({ordem["tipo"] for ordem in exportadas}, {"OP", "OC"})
        self.assertTrue(all(ordem["status"] == "ENCERRADA"
                            for ordem in exportadas))

        from PIL import Image

        self.assertEqual({p.name for p in saida.glob("*.png")}, {
            "estoque_atual.png", "estoque_projetado_PA-001.png",
            "ordens_por_semana.png", "capacidade_CT-01.png",
        })
        for arquivo in saida.glob("*.png"):
            with Image.open(arquivo) as imagem:
                self.assertEqual(imagem.format, "PNG")
                self.assertGreater(imagem.width, 400)
                imagem.verify()

    def test_saldo_insuficiente_rejeita_toda_a_op(self):
        self.planejar()
        op = self.localizar("SA-010")
        firmar_ordem(op)
        liberar_ordem(op)
        registrar_movimento("MP-101", "ENTRADA", 9, "Estoque de teste")
        antes = self.arquivos()
        with self.assertRaisesRegex(ValueError, "Saldo insuficiente de MP-102"):
            apontar_producao(op)
        self.assertEqual(self.arquivos(), antes)
        registrar_movimento("MP-102", "ENTRADA", 6, "Estoque de teste")
        self.assertTrue(apontar_producao(op))
        with self.assertRaisesRegex(ValueError, "OP LIBERADA"):
            apontar_producao(op)
        self.assertEqual(consultar_saldos(), {"MP-101": 0, "MP-102": 0, "SA-010": 6})

    def test_transicoes_invalidas_e_tipo_da_ordem(self):
        self.planejar()
        op = self.localizar("PA-001")
        oc = self.localizar("MP-101")
        antes = self.arquivos()
        with self.assertRaisesRegex(ValueError, "FIRME"):
            liberar_ordem(op)
        with self.assertRaisesRegex(ValueError, "OC LIBERADA"):
            receber_compra(oc)
        with self.assertRaisesRegex(ValueError, "não encontrada"):
            firmar_ordem("OP-INEXISTENTE")
        self.assertEqual(self.arquivos(), antes)
        firmar_ordem(op)
        with self.assertRaisesRegex(ValueError, "PLANEJADA"):
            firmar_ordem(op)
        liberar_ordem(op)
        with self.assertRaisesRegex(ValueError, "OC LIBERADA"):
            receber_compra(op)

    def test_recalculo_preserva_ordens_e_explode_ops_abertas(self):
        self.planejar()
        ids_planejadas = {ordem["id"] for ordem in carregar_ordens()}
        pa = self.localizar("PA-001")
        sa = self.localizar("SA-010")
        mp = self.localizar("MP-102")
        firmar_ordem(pa)
        firmar_ordem(sa)
        liberar_ordem(sa)
        firmar_ordem(mp)
        liberar_ordem(mp)
        receber_compra(mp)
        resultados = recalcular_ordens()
        atuais = {ordem["id"]: ordem for ordem in carregar_ordens()}
        self.assertEqual(ids_planejadas & atuais.keys(), {pa, sa, mp})
        self.assertEqual(atuais[pa]["status"], "FIRME")
        self.assertEqual(atuais[sa]["status"], "LIBERADA")
        self.assertEqual(atuais[mp]["status"], "ENCERRADA")
        recebimento_pa = resultados["PA-001"]["semanas"][5]
        self.assertEqual(recebimento_pa["recebimento_programado"], 3)
        self.assertEqual(recebimento_pa["recebimento_planejado"], 0)
        recebimento_sa = resultados["SA-010"]["semanas"][4]
        self.assertEqual(recebimento_sa["necessidade_bruta"], 6)
        self.assertEqual(recebimento_sa["recebimento_programado"], 6)
        self.assertEqual(resultados["MP-101"]["semanas"][3]["necessidade_bruta"], 9)
        self.assertEqual(resultados["MP-102"]["semanas"][3]["recebimento_programado"], 0)
        self.assertEqual(resultados["MP-102"]["saldo_inicial"], 6)

    def test_atrasada_mantem_status_e_recibo_antes_do_horizonte(self):
        self.planejar(semana=1)
        ordens = carregar_ordens()
        self.assertTrue(all(ordem["atrasada"] for ordem in ordens))
        self.assertEqual({ordem["status"] for ordem in ordens}, {"PLANEJADA"})
        oc = next(ordem for ordem in ordens if ordem["codigo"] == "MP-102")
        self.assertEqual(oc["semana_recebimento"], -1)
        firmar_ordem(oc["id"])
        recalculado = recalcular_ordens()["MP-102"]
        anterior, = recalculado["necessidades_anteriores"]
        self.assertEqual(anterior["recebimento_programado"], 6)
        self.assertEqual(anterior["recebimento_planejado"], 0)
        self.assertEqual(recalculado["ordens_planejadas"], [])

    def test_gravacao_interrompida_cobre_antes_e_depois_da_confirmacao(self):
        self.planejar()
        oc = self.localizar("MP-102")
        firmar_ordem(oc)
        liberar_ordem(oc)
        salvar = persistencia.salvar_json
        antes = self.arquivos()

        def falhar_em(nome, dados):
            if nome == arquivo_com_falha:
                raise OSError("falha de gravação simulada")
            return salvar(nome, dados)

        arquivo_com_falha = ARQUIVO_OPERACAO
        with patch.object(persistencia, "salvar_json", side_effect=falhar_em):
            with self.assertRaisesRegex(OSError, "simulada"):
                receber_compra(oc)
        self.assertEqual(self.arquivos(), antes)

        arquivo_com_falha = "ordens.json"
        with patch.object(persistencia, "salvar_json", side_effect=falhar_em):
            self.assertFalse(receber_compra(oc))
        self.assertTrue((self.dados / ARQUIVO_OPERACAO).exists())
        self.assertEqual(consultar_saldos(), {"MP-102": 6})
        self.assertFalse((self.dados / ARQUIVO_OPERACAO).exists())
        with self.assertRaisesRegex(ValueError, "OC LIBERADA"):
            receber_compra(oc)
        self.assertEqual(len(consultar_kardex("MP-102")), 1)
        ordem = next(ordem for ordem in carregar_ordens() if ordem["id"] == oc)
        self.assertEqual(ordem["status"], "ENCERRADA")

    def test_recebimento_simultaneo_da_mesma_ordem(self):
        self.planejar()
        oc = self.localizar("MP-102")
        firmar_ordem(oc)
        liberar_ordem(oc)

        def tentar_receber():
            try:
                return receber_compra(oc)
            except ValueError as erro:
                self.assertIn("OC LIBERADA", str(erro))
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            tentativas = list(executor.map(lambda _: tentar_receber(), range(2)))
        self.assertEqual(sorted(tentativas), [False, True])
        self.assertEqual(consultar_saldos(), {"MP-102": 6})
        self.assertEqual(len(consultar_kardex()), 1)

    def test_custo_explode_materiais_compartilhados_e_mao_de_obra(self):
        custo = calcular_custo_padrao("PA-001")
        self.assertEqual(custo["materiais"]["MP-101"]["quantidade"], Decimal("3.5"))
        self.assertEqual(custo["total_material"], 24)
        self.assertEqual(custo["total_mao_de_obra"], 25)
        self.assertEqual(custo["total"], 49)
        self.assertEqual(calcular_custo_padrao("SA-010")["total"], 16)
        with self.assertRaisesRegex(ValueError, "PA ou SA"):
            calcular_custo_padrao("MP-101")

    def test_centro_e_roteiro_validam_e_persistem_alteracoes(self):
        with self.assertRaisesRegex(ValueError, "já está cadastrado"):
            salvar_centro("ct-01", "Duplicado", 2, 15)
        with self.assertRaises(ValueError):
            salvar_centro("CT-03", "Inválido", 0, 0)
        with self.assertRaises(ValueError):
            salvar_centro("CT-03", "Inválido", 1, "NaN")
        with self.assertRaisesRegex(ValueError, "PA ou SA"):
            salvar_roteiro("MP-101", "CT-01", 1)
        with self.assertRaisesRegex(ValueError, "não encontrado"):
            salvar_roteiro("PA-001", "CT-03", 1)
        with self.assertRaises(ValueError):
            salvar_roteiro("PA-001", "CT-01", 0)
        salvar_centro("CT-01", "Montagem final", 4, 35, alterar=True)
        salvar_roteiro("PA-001", "CT-02", "0.4")
        self.assertEqual(carregar_centros()["CT-01"]["custo_hora"], "35")
        self.assertEqual(carregar_roteiros()["PA-001"]["centro"], "CT-02")

    def test_cadastros_bom_estoque_e_mps_validam_e_persistem(self):
        saida = executar_menu(
            "1", "1", "invalido", "MP-999", "Refletor", "un", "3,5", "1",
            "5", "2", "1", "MP-999", "4", "MP-999", "Refletor traseiro",
            "", "", "", "", "", "5", "SA-010", "PA-001",
            "5", "PA-001", "MP-999", "0", "2", "7", "PA-001", "MP-999", "3",
            "8", "PA-001", "MP-999", "0",
            "2", "1", "MP-999", "2", "NF-1", "2", "MP-999", "3", "Excesso",
            "3", "MP-999", "1", "Contagem", "4", "MP-999", "0",
            "3", "1", "SA-010", "2", "PA-001", "9", "8", "-1", "4", "0", "0",
        )
        for mensagem in (
            "Formato inválido", "Já existe um item", "Item alterado",
            "Componentes permitidos", "maior que zero", "Componente cadastrado",
            "Quantidade alterada", "Componente removido", "Saldo insuficiente",
            "abaixo do estoque de segurança", "Somente produtos acabados",
            "Opção inválida", "Demanda de PA-001 na semana 8 alterada",
        ):
            self.assertIn(mensagem, saida)
        self.assertNotIn("MP-999", persistencia.carregar_json("estrutura.json")["PA-001"])
        self.assertEqual(carregar_mps()["PA-001"][-1], 4)
        self.assertEqual(consultar_saldos()["MP-999"], 1)
        self.assertEqual([mov["quantidade"] for mov in consultar_kardex("MP-999")],
                         ["2", "-1"])
        self.assertIn("Refletor traseiro", executar_menu(
            "1", "3", "MP-999", "0", "0",
        ))


class TesteDemonstracao(BaseTemporaria):
    def test_produz_os_dois_modelos_da_base_fornecida(self):
        origem = Path(__file__).resolve().parents[1] / "data"
        for nome in ("itens_demonstracao.json", "estrutura.json",
                     "centros.json", "roteiros.json"):
            copyfile(origem / nome, self.dados / nome)
        persistencia.inicializar_dados()
        persistencia.salvar_json("mps.json", {
            "PA-001": [0, 0, 0, 0, 0, 0, 0, 12],
            "PA-002": [0, 0, 0, 0, 0, 0, 0, 8],
        })
        self.assertEqual(len(recalcular_ordens()), 14)
        ordens = carregar_ordens()
        self.assertEqual(len(carregar_centros()), 2)
        self.assertEqual(len(carregar_roteiros()), 6)
        for ordem in ordens:
            firmar_ordem(ordem["id"])
            liberar_ordem(ordem["id"])
        for ordem in ordens:
            if ordem["tipo"] == "OC":
                receber_compra(ordem["id"])
        for prefixo in ("SA-", "PA-"):
            for ordem in ordens:
                if ordem["codigo"].startswith(prefixo):
                    apontar_producao(ordem["id"])

        saldos = consultar_saldos()
        self.assertGreaterEqual(saldos["PA-001"], 17)
        self.assertGreaterEqual(saldos["PA-002"], 12)
        self.assertGreater(calcular_custo_padrao("PA-001")["total"], 0)
        self.assertGreater(calcular_custo_padrao("PA-002")["total"], 0)
        for ordem in carregar_ordens():
            self.assertEqual(ordem["status"], "ENCERRADA")


if __name__ == "__main__":
    unittest.main()
