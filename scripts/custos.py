"""Gera prompts/sessoes/CUSTOS.md e prompts/sessoes/NOTAS.md a partir das sessões.

Regra de soma (SPEC/2026-11-24-custos-gerados.md): entradas ``assistant``, sem o
modelo ``<synthetic>``, uma vez por ``message.id``; os subagentes
(``<sessão>-claudecode-subagente-<n>.jsonl``) entram na linha da sessão principal.

Uso:
    python scripts/custos.py           # regrava os dois arquivos
    python scripts/custos.py --check   # falha se algum estiver desatualizado
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
PASTA_PADRAO = Path(__file__).resolve().parent.parent / "prompts" / "sessoes"

SUFIXO = "-claudecode.jsonl"
RE_PRINCIPAL = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})-claudecode\.jsonl$")
RE_SUBAGENTE = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{4})-claudecode-subagente-(\d+)\.jsonl$")
RE_NOTA = re.compile(r"^(\d{4}-\d{2}-\d{2}-\d{4})\.notas\.md$")

MODELO_SINTETICO = "<synthetic>"
CAMPOS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


class ErroSessoes(Exception):
    """Arquivo de sessão inválido ou sem a sessão principal."""


@dataclass
class Uso:
    tokens: dict[str, int] = field(default_factory=lambda: dict.fromkeys(CAMPOS, 0))
    modelos: set[str] = field(default_factory=set)
    fim: datetime | None = None

    @property
    def total(self) -> int:
        return sum(self.tokens.values())

    def somar(self, outro: Uso) -> None:
        for campo in CAMPOS:
            self.tokens[campo] += outro.tokens[campo]
        self.modelos |= outro.modelos
        if outro.fim is not None and (self.fim is None or outro.fim > self.fim):
            self.fim = outro.fim


def _instante(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def ler_uso(caminho: Path) -> Uso:
    """Soma o uso de tokens de um .jsonl pela regra da spec."""
    uso = Uso()
    vistos: set[str] = set()
    with caminho.open(encoding="utf-8") as arquivo:
        for numero, linha in enumerate(arquivo, start=1):
            linha = linha.strip()
            if not linha:
                continue
            try:
                entrada = json.loads(linha)
            except json.JSONDecodeError as erro:
                raise ErroSessoes(f"{caminho.name}:{numero}: JSON inválido ({erro.msg})") from erro
            if not isinstance(entrada, dict):
                continue
            carimbo = entrada.get("timestamp")
            if isinstance(carimbo, str):
                instante = _instante(carimbo)
                if uso.fim is None or instante > uso.fim:
                    uso.fim = instante
            if entrada.get("type") != "assistant":
                continue
            mensagem = entrada.get("message") or {}
            modelo = mensagem.get("model")
            if modelo == MODELO_SINTETICO:
                continue
            ident = mensagem.get("id")
            if ident is not None:
                if ident in vistos:
                    continue
                vistos.add(ident)
            if modelo:
                uso.modelos.add(modelo)
            usage = mensagem.get("usage") or {}
            for campo in CAMPOS:
                uso.tokens[campo] += int(usage.get(campo) or 0)
    return uso


@dataclass
class Sessao:
    nome: str  # AAAA-MM-DD-HHMM
    inicio: datetime
    uso: Uso

    @property
    def arquivo(self) -> str:
        return f"{self.nome}{SUFIXO}"


def coletar(pasta: Path) -> tuple[list[Sessao], dict[str, Path]]:
    """Lê as sessões principais, soma os subagentes e localiza as notas."""
    principais: dict[str, Path] = {}
    subagentes: dict[str, list[Path]] = {}
    notas: dict[str, Path] = {}
    for caminho in sorted(pasta.iterdir()):
        nome = caminho.name
        if m := RE_PRINCIPAL.match(nome):
            principais[nome[: -len(SUFIXO)]] = caminho
        elif m := RE_SUBAGENTE.match(nome):
            subagentes.setdefault(m.group(1), []).append(caminho)
        elif m := RE_NOTA.match(nome):
            notas[m.group(1)] = caminho

    for nome, arquivos in subagentes.items():
        if nome not in principais:
            raise ErroSessoes(
                f"{arquivos[0].name}: subagente sem a sessão principal {nome}{SUFIXO}"
            )
    for nome, caminho in notas.items():
        if nome not in principais:
            raise ErroSessoes(f"{caminho.name}: nota sem a sessão principal {nome}{SUFIXO}")

    sessoes = []
    for nome in sorted(principais):
        m = RE_PRINCIPAL.match(principais[nome].name)
        ano, mes, dia, hora, minuto = (int(g) for g in m.groups())
        uso = ler_uso(principais[nome])
        for sub in sorted(subagentes.get(nome, []), key=_ordem_subagente):
            uso.somar(ler_uso(sub))
        inicio = datetime(ano, mes, dia, hora, minuto, tzinfo=FUSO)
        sessoes.append(Sessao(nome=nome, inicio=inicio, uso=uso))
    return sessoes, notas


def _ordem_subagente(caminho: Path) -> int:
    return int(RE_SUBAGENTE.match(caminho.name).group(2))


def _n(valor: int) -> str:
    return f"{valor:,}"


def _fim(sessao: Sessao) -> str:
    if sessao.uso.fim is None:
        return ""
    fim = sessao.uso.fim.astimezone(FUSO)
    texto = fim.strftime("%H:%M")
    if fim.date() != sessao.inicio.date():
        texto += fim.strftime(" (%d/%m)")
    return texto


def gerar_custos(sessoes: list[Sessao]) -> str:
    linhas = [
        "# Custo das sessões com agente",
        "",
        "Gerado por `python scripts/custos.py` a partir dos `.jsonl` desta pasta; não edite à mão. "
        "Tokens do campo `message.usage` das respostas do agente, uma vez por `message.id`, sem o "
        "modelo `<synthetic>`, somando os subagentes da sessão "
        "(`<sessão>-claudecode-subagente-<n>.jsonl`). Horários em America/Sao_Paulo. "
        "As observações de cada sessão estão em [NOTAS.md](NOTAS.md).",
        "",
        "| Sessão | Início | Fim | Modelos | Input | Output | Cache (escrita) | Cache (leitura) | Total |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    soma = Uso()
    for s in sessoes:
        t = s.uso.tokens
        linhas.append(
            f"| `{s.arquivo}` | {s.inicio:%d/%m %H:%M} | {_fim(s)} | "
            f"{', '.join(sorted(s.uso.modelos))} | {_n(t['input_tokens'])} | "
            f"{_n(t['output_tokens'])} | {_n(t['cache_creation_input_tokens'])} | "
            f"{_n(t['cache_read_input_tokens'])} | {_n(s.uso.total)} |"
        )
        soma.somar(s.uso)
    t = soma.tokens
    linhas.append(
        f"| **Total** | | | | **{_n(t['input_tokens'])}** | **{_n(t['output_tokens'])}** | "
        f"**{_n(t['cache_creation_input_tokens'])}** | **{_n(t['cache_read_input_tokens'])}** | "
        f"**{_n(soma.total)}** |"
    )
    return "\n".join(linhas) + "\n"


def gerar_notas(sessoes: list[Sessao], notas: dict[str, Path]) -> str:
    partes = [
        "# Notas das sessões com agente\n\n"
        "Gerado por `python scripts/custos.py` a partir dos `<sessão>.notas.md` desta pasta; "
        "não edite à mão. Os tokens de cada sessão estão em [CUSTOS.md](CUSTOS.md).\n"
    ]
    for s in sessoes:
        if s.nome not in notas:
            continue
        texto = notas[s.nome].read_text(encoding="utf-8").strip()
        partes.append(f"### [{s.arquivo}]({s.arquivo})\n\n{texto}\n")
    return "\n".join(partes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="só confere, sem gravar")
    parser.add_argument("--dir", type=Path, default=PASTA_PADRAO, help="pasta das sessões")
    args = parser.parse_args(argv)

    try:
        sessoes, notas = coletar(args.dir)
    except ErroSessoes as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 2

    esperados = {
        args.dir / "CUSTOS.md": gerar_custos(sessoes),
        args.dir / "NOTAS.md": gerar_notas(sessoes, notas),
    }

    if args.check:
        desatualizados = [
            caminho
            for caminho, conteudo in esperados.items()
            if not caminho.exists() or caminho.read_text(encoding="utf-8") != conteudo
        ]
        for caminho in desatualizados:
            print(
                f"{caminho.name} desatualizado: rode python scripts/custos.py e commite o resultado.",
                file=sys.stderr,
            )
        return 1 if desatualizados else 0

    for caminho, conteudo in esperados.items():
        caminho.write_text(conteudo, encoding="utf-8")
        print(f"{caminho.name}: gravado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
