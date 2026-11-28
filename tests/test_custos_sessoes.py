"""Testes de scripts/custos.py (SPEC/2026-11-24-custos-gerados.md, #54)."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("custos", RAIZ / "scripts" / "custos.py")
custos = importlib.util.module_from_spec(_spec)
sys.modules["custos"] = custos  # as dataclasses do script procuram o módulo aqui
_spec.loader.exec_module(custos)

SESSAO = "2026-11-30-2350"


def resposta(ident, ts, entrada=0, saida=0, escrita=0, leitura=0, modelo="claude-opus-5-5"):
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {
            "id": ident,
            "model": modelo,
            "usage": {
                "input_tokens": entrada,
                "output_tokens": saida,
                "cache_creation_input_tokens": escrita,
                "cache_read_input_tokens": leitura,
            },
        },
    }


def gravar(pasta: Path, nome: str, entradas) -> None:
    (pasta / nome).write_text(
        "".join(json.dumps(e) + "\n" for e in entradas), encoding="utf-8"
    )


@pytest.fixture
def pasta(tmp_path):
    """Sessão de 30/11 23:50 que passa da meia-noite, com streaming, <synthetic> e um subagente."""
    gravar(
        tmp_path,
        f"{SESSAO}-claudecode.jsonl",
        [
            {"type": "user", "timestamp": "2026-12-01T02:50:00Z", "message": {"content": "oi"}},
            resposta("msg_1", "2026-12-01T02:50:10Z", 1, 10, 100, 1000),
            # Streaming: o mesmo id aparece de novo, com o mesmo usage.
            resposta("msg_1", "2026-12-01T02:50:11Z", 1, 10, 100, 1000),
            resposta("msg_2", "2026-12-01T02:55:00Z", 2, 20, 200, 2000),
            resposta("syn_1", "2026-12-01T02:56:00Z", 5000, 5000, 5000, 5000, modelo="<synthetic>"),
            {"type": "system", "timestamp": "2026-12-01T03:05:59Z"},
        ],
    )
    gravar(
        tmp_path,
        f"{SESSAO}-claudecode-subagente-1.jsonl",
        [resposta("sub_1", "2026-12-01T02:52:00Z", 3, 30, 300, 3000, modelo="claude-haiku-5-5")],
    )
    return tmp_path


def linha_da_sessao(texto: str) -> list[str]:
    for linha in texto.splitlines():
        if linha.startswith(f"| `{SESSAO}"):
            return [c.strip() for c in linha.strip("|").split("|")]
    raise AssertionError("linha da sessão ausente")


def linha_total(texto: str) -> list[str]:
    linha = next(l for l in texto.splitlines() if l.startswith("| **Total**"))
    return [c.strip().strip("*") for c in linha.strip("|").split("|")]


def test_soma_uma_vez_por_id_sem_synthetic_e_com_subagente(pasta):
    assert custos.main(["--dir", str(pasta)]) == 0
    texto = (pasta / "CUSTOS.md").read_text(encoding="utf-8")
    sessao, inicio, fim, modelos, entrada, saida, escrita, leitura, total = linha_da_sessao(texto)
    assert sessao == f"`{SESSAO}-claudecode.jsonl`"
    assert inicio == "30/11 23:50"
    # msg_1 uma vez + msg_2 + sub_1; o <synthetic> fica de fora.
    assert (entrada, saida, escrita, leitura) == ("6", "60", "600", "6,000")
    assert total == "6,666"
    assert modelos == "claude-haiku-5-5, claude-opus-5-5"
    # Último timestamp (00:05:59 de 01/12 em São Paulo), em outro dia.
    assert fim == "00:05 (01/12)"
    assert linha_total(texto)[4:] == ["6", "60", "600", "6,000", "6,666"]


def test_synthetic_nao_entra_nos_modelos(pasta):
    uso = custos.ler_uso(pasta / f"{SESSAO}-claudecode.jsonl")
    assert uso.modelos == {"claude-opus-5-5"}
    assert uso.total == 3 + 30 + 300 + 3000


def test_total_soma_todas_as_sessoes(pasta):
    gravar(
        pasta,
        "2026-11-29-1000-claudecode.jsonl",
        [resposta("outra", "2026-11-29T13:00:00Z", 1, 1, 1, 1_000_000)],
    )
    custos.main(["--dir", str(pasta)])
    texto = (pasta / "CUSTOS.md").read_text(encoding="utf-8")
    assert linha_total(texto)[4:] == ["7", "61", "601", "1,006,000", "1,006,669"]
    # Ordem por nome da sessão.
    assert texto.index("2026-11-29-1000") < texto.index(SESSAO)


def test_notas_com_link_para_a_sessao(pasta):
    (pasta / f"{SESSAO}.notas.md").write_text("Texto *da* nota.\n", encoding="utf-8")
    custos.main(["--dir", str(pasta)])
    notas = (pasta / "NOTAS.md").read_text(encoding="utf-8")
    arquivo = f"{SESSAO}-claudecode.jsonl"
    assert f"### [{arquivo}]({arquivo})\n\nTexto *da* nota.\n" in notas


def test_subagente_sem_sessao_principal_falha(pasta, capsys):
    gravar(pasta, "2026-11-01-0900-claudecode-subagente-1.jsonl", [])
    assert custos.main(["--dir", str(pasta)]) == 2
    assert "2026-11-01-0900-claudecode-subagente-1.jsonl" in capsys.readouterr().err
    assert not (pasta / "CUSTOS.md").exists()


def test_nota_sem_sessao_principal_falha(pasta, capsys):
    (pasta / "2026-11-01-0900.notas.md").write_text("x\n", encoding="utf-8")
    assert custos.main(["--dir", str(pasta)]) == 2
    assert "2026-11-01-0900.notas.md" in capsys.readouterr().err


def test_check_passa_em_dia_e_falha_desatualizado(pasta, capsys):
    assert custos.main(["--dir", str(pasta), "--check"]) == 1  # ainda não gerados
    assert custos.main(["--dir", str(pasta)]) == 0
    assert custos.main(["--dir", str(pasta), "--check"]) == 0

    # Uma sessão nova sem rodar o script deixa o CUSTOS.md para trás.
    gravar(pasta, "2026-12-02-1000-claudecode.jsonl", [resposta("n", "2026-12-02T13:00:00Z", 1)])
    capsys.readouterr()
    assert custos.main(["--dir", str(pasta), "--check"]) == 1
    assert "CUSTOS.md desatualizado" in capsys.readouterr().err

    # Uma nota nova deixa só o NOTAS.md para trás.
    custos.main(["--dir", str(pasta)])
    (pasta / f"{SESSAO}.notas.md").write_text("nova\n", encoding="utf-8")
    capsys.readouterr()
    assert custos.main(["--dir", str(pasta), "--check"]) == 1
    erro = capsys.readouterr().err
    assert "NOTAS.md desatualizado" in erro and "CUSTOS.md" not in erro


def test_check_nao_grava(pasta):
    custos.main(["--dir", str(pasta), "--check"])
    assert not (pasta / "CUSTOS.md").exists()
    assert not (pasta / "NOTAS.md").exists()


def test_arquivos_do_repositorio_em_dia():
    """O CUSTOS.md e o NOTAS.md commitados batem com os .jsonl e as notas."""
    assert custos.main(["--check"]) == 0
