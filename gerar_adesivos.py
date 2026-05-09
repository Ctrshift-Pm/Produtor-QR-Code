# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple
from urllib.parse import quote

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_H

WHATSAPP_PHONE = "5564933002942"
WHATSAPP_DISPLAY = "(64) 93300-2942"

TEXTO_LINHA1 = "Aponte a câmera e descreva o problema"
TEXTO_LINHA2 = f"Não conseguiu? WhatsApp: {WHATSAPP_DISPLAY}"

LOGO_ESQ_CANDIDATOS = ["logo_prefeitura.png", "imagem_esq.png"]
LOGO_DIR_CANDIDATOS = ["brasao.png", "imagem_dir.png"]


@dataclass(frozen=True)
class ConfiguracaoAdesivo:
    dpi: int = 300
    largura_cm: float = 15
    altura_cm: float = 10

    margem_superior_ratio: float = 0.04
    margem_inferior_ratio: float = 0.035
    margem_lateral_ratio: float = 0.035
    margem_lateral_esq_ratio: float = 0.005

    gap_titulo_qr_ratio: float = 0.015
    gap_qr_texto_ratio: float = 0.018
    gap_entre_linhas_ratio: float = 0.006

    qr_largura_ratio: float = 0.48
    logo_altura_ratio: float = 0.26
    logo_esq_multiplicador: float = 3.0
    logo_qr_gap_ratio: float = 0.018
    logo_esq_gap_ratio: float = 0.004

    fonte_titulo_ratio: float = 0.055
    fonte_linha1_ratio: float = 0.046
    fonte_linha2_ratio: float = 0.052

    qr_borda: int = 4

    @property
    def largura_px(self) -> int:
        return round(self.largura_cm / 2.54 * self.dpi)

    @property
    def altura_px(self) -> int:
        return round(self.altura_cm / 2.54 * self.dpi)


def normalizar_id(id_poste: str) -> str:
    digitos = re.sub(r"\D", "", str(id_poste))
    if not digitos:
        raise ValueError("ID inválido: nenhum dígito encontrado.")
    if len(digitos) > 4:
        raise ValueError("ID inválido: mais de 4 dígitos.")
    return digitos.zfill(4)


def construir_url_whatsapp(id_poste: str) -> str:
    mensagem = (
        "Olá! Gostaria de informar um problema no poste de iluminação pública.\n\n"
        f"ID do poste: {id_poste}\n\n"
        "A seguir, descrevo o problema:"
    )
    return f"https://wa.me/{WHATSAPP_PHONE}?text={quote(mensagem, safe='')}"


class GerenciadorFontes:
    def __init__(self, diretorios_extras: Iterable[Path]) -> None:
        self._diretorios = [Path(d) for d in diretorios_extras]

    def _candidatos(self, negrito: bool) -> Iterable[Path]:
        nomes = (
            ["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]
            if negrito
            else ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf"]
        )

        for d in self._diretorios:
            for nome in nomes:
                yield d / nome

        pil_fonts = Path(ImageFont.__file__).resolve().parent / "Fonts"
        for nome in nomes:
            yield pil_fonts / nome

        win_fonts = Path("C:/Windows/Fonts")
        for nome in nomes:
            yield win_fonts / nome

    def carregar(self, tamanho: int, negrito: bool) -> ImageFont.ImageFont:
        for caminho in self._candidatos(negrito):
            try:
                if caminho.exists():
                    return ImageFont.truetype(str(caminho), size=tamanho)
            except Exception:
                continue

        try:
            nome = "DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf"
            return ImageFont.truetype(nome, size=tamanho)
        except Exception:
            return ImageFont.load_default()

    def ajustar_para_caber(
        self,
        draw: ImageDraw.ImageDraw,
        texto: str,
        max_largura: int,
        max_altura: int,
        tamanho_inicial: int,
        negrito: bool,
    ) -> Tuple[ImageFont.ImageFont, Tuple[int, int]]:
        tamanho = max(10, tamanho_inicial)
        while tamanho >= 10:
            fonte = self.carregar(tamanho, negrito=negrito)
            bbox = draw.textbbox((0, 0), texto, font=fonte)
            largura = bbox[2] - bbox[0]
            altura = bbox[3] - bbox[1]
            if largura <= max_largura and altura <= max_altura:
                return fonte, (largura, altura)
            tamanho -= 2

        fonte = self.carregar(10, negrito=negrito)
        bbox = draw.textbbox((0, 0), texto, font=fonte)
        return fonte, (bbox[2] - bbox[0], bbox[3] - bbox[1])


class GeradorQRCode:
    def __init__(self, borda: int = 4) -> None:
        self._borda = borda

    def gerar(self, url: str, tamanho_alvo: int) -> Image.Image:
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_H,
            box_size=1,
            border=self._borda,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        tamanho_base = img.size[0]
        escala = max(1, tamanho_alvo // tamanho_base)
        tamanho_final = tamanho_base * escala

        if tamanho_final != tamanho_base:
            img = img.resize((tamanho_final, tamanho_final), Image.NEAREST)

        return img


def redimensionar_logo(logo: Image.Image, altura_alvo: int, largura_max: int) -> Image.Image:
    largura, altura = logo.size
    if altura <= 0:
        return logo

    escala = altura_alvo / altura
    nova_largura = max(1, int(largura * escala))
    nova_altura = max(1, int(altura * escala))

    if nova_largura > largura_max:
        escala = largura_max / largura
        nova_largura = max(1, int(largura * escala))
        nova_altura = max(1, int(altura * escala))

    return logo.resize((nova_largura, nova_altura), Image.LANCZOS)


def resolver_logo(diretorio: Path, candidatos: Iterable[str]) -> Path:
    for nome in candidatos:
        caminho = diretorio / nome
        if caminho.exists():
            return caminho
    caminhos = ", ".join(str(diretorio / n) for n in candidatos)
    raise FileNotFoundError(f"Logo não encontrado. Procurado: {caminhos}")


class GeradorAdesivo:
    def __init__(self, config: ConfiguracaoAdesivo, assets_dir: Path) -> None:
        self._config = config
        self._assets_dir = Path(assets_dir)
        self._fontes = GerenciadorFontes([self._assets_dir, Path(__file__).parent])
        self._qr = GeradorQRCode(config.qr_borda)

        self._logo_esq = resolver_logo(self._assets_dir, LOGO_ESQ_CANDIDATOS)
        self._logo_dir = resolver_logo(self._assets_dir, LOGO_DIR_CANDIDATOS)

    def gerar(self, id_poste: str, caminho_saida: Path) -> None:
        id_poste = normalizar_id(id_poste)
        caminho_saida = Path(caminho_saida)
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)

        largura_px = self._config.largura_px
        altura_px = self._config.altura_px

        canvas = Image.new("RGB", (largura_px, altura_px), "white")
        draw = ImageDraw.Draw(canvas)

        texto_titulo = f"Poste N° {id_poste}"
        fonte_titulo, (titulo_w, titulo_h) = self._fontes.ajustar_para_caber(
            draw,
            texto_titulo,
            max_largura=int(largura_px * 0.9),
            max_altura=int(altura_px * 0.15),
            tamanho_inicial=int(altura_px * self._config.fonte_titulo_ratio),
            negrito=False,
        )

        fonte_linha1, (linha1_w, linha1_h) = self._fontes.ajustar_para_caber(
            draw,
            TEXTO_LINHA1,
            max_largura=int(largura_px * 0.92),
            max_altura=int(altura_px * 0.12),
            tamanho_inicial=int(altura_px * self._config.fonte_linha1_ratio),
            negrito=False,
        )

        fonte_linha2, (linha2_w, linha2_h) = self._fontes.ajustar_para_caber(
            draw,
            TEXTO_LINHA2,
            max_largura=int(largura_px * 0.92),
            max_altura=int(altura_px * 0.14),
            tamanho_inicial=int(altura_px * self._config.fonte_linha2_ratio),
            negrito=True,
        )

        margem_superior = int(altura_px * self._config.margem_superior_ratio)
        margem_inferior = int(altura_px * self._config.margem_inferior_ratio)
        margem_lateral = int(largura_px * self._config.margem_lateral_ratio)
        margem_lateral_esq = int(largura_px * self._config.margem_lateral_esq_ratio)
        gap_titulo_qr = int(altura_px * self._config.gap_titulo_qr_ratio)
        gap_qr_texto = int(altura_px * self._config.gap_qr_texto_ratio)
        gap_entre_linhas = int(altura_px * self._config.gap_entre_linhas_ratio)
        gap_logo_qr = int(largura_px * self._config.logo_qr_gap_ratio)
        gap_logo_qr_esq = int(largura_px * self._config.logo_esq_gap_ratio)

        titulo_x = (largura_px - titulo_w) // 2
        titulo_y = margem_superior

        linha2_y = altura_px - margem_inferior - linha2_h
        linha1_y = linha2_y - gap_entre_linhas - linha1_h

        topo_qr = titulo_y + titulo_h + gap_titulo_qr
        base_qr = linha1_y - gap_qr_texto
        altura_disponivel = base_qr - topo_qr
        if altura_disponivel <= 0:
            raise ValueError("Layout inválido: não há espaço vertical para o QR.")

        tamanho_qr_alvo = min(altura_disponivel, int(largura_px * self._config.qr_largura_ratio))
        tamanho_qr_alvo = min(tamanho_qr_alvo, largura_px - 2 * margem_lateral)

        url_qr = construir_url_whatsapp(id_poste)
        img_qr = self._qr.gerar(url_qr, tamanho_qr_alvo)
        tamanho_qr = img_qr.size[0]

        qr_x = (largura_px - tamanho_qr) // 2
        qr_y = topo_qr + (altura_disponivel - tamanho_qr) // 2

        logo_esq = Image.open(self._logo_esq).convert("RGBA")
        logo_dir = Image.open(self._logo_dir).convert("RGBA")

        largura_logo_max_dir = int((largura_px - 2 * margem_lateral - 2 * gap_logo_qr - tamanho_qr) / 2)
        largura_logo_max_dir = max(1, largura_logo_max_dir)

        largura_logo_max_esq = qr_x - margem_lateral_esq - gap_logo_qr_esq
        largura_logo_max_esq = max(1, largura_logo_max_esq)

        altura_logo_base = min(int(altura_px * self._config.logo_altura_ratio), int(tamanho_qr * 0.5))
        altura_logo_esq = min(
            int(altura_logo_base * self._config.logo_esq_multiplicador),
            int(tamanho_qr * 0.9),
        )

        logo_esq = redimensionar_logo(logo_esq, altura_logo_esq, largura_logo_max_esq)
        logo_dir = redimensionar_logo(logo_dir, altura_logo_base, largura_logo_max_dir)

        logo_esq_x = qr_x - gap_logo_qr_esq - logo_esq.size[0]
        logo_dir_x = qr_x + tamanho_qr + gap_logo_qr

        logo_esq_y = qr_y + (tamanho_qr - logo_esq.size[1]) // 2
        logo_dir_y = qr_y + (tamanho_qr - logo_dir.size[1]) // 2

        draw.text((titulo_x, titulo_y), texto_titulo, font=fonte_titulo, fill="black")
        canvas.paste(img_qr, (qr_x, qr_y))
        canvas.paste(logo_esq, (logo_esq_x, logo_esq_y), mask=logo_esq)
        canvas.paste(logo_dir, (logo_dir_x, logo_dir_y), mask=logo_dir)

        linha1_x = (largura_px - linha1_w) // 2
        linha2_x = (largura_px - linha2_w) // 2

        draw.text((linha1_x, linha1_y), TEXTO_LINHA1, font=fonte_linha1, fill="black")
        draw.text((linha2_x, linha2_y), TEXTO_LINHA2, font=fonte_linha2, fill="black")

        canvas.save(caminho_saida, format="PNG", dpi=(self._config.dpi, self._config.dpi))

def gerar_adesivo(poste_id: str, out_path: Path, assets_dir: Path) -> None:
    config = ConfiguracaoAdesivo()
    gerador = GeradorAdesivo(config, assets_dir)
    gerador.gerar(poste_id, out_path)


def gerar_por_intervalo(
    out_dir: Path,
    assets_dir: Path,
    bairro_inicio: int = 1,
    bairro_fim: int = 99,
    poste_inicio: int = 1,
    poste_fim: int = 99,
) -> int:
    out_dir = Path(out_dir)
    count = 0
    for bairro in range(bairro_inicio, bairro_fim + 1):
        for poste in range(poste_inicio, poste_fim + 1):
            id_poste = f"{bairro:02d}{poste:02d}"
            caminho_saida = out_dir / f"poste_{id_poste}.png"
            gerar_adesivo(id_poste, caminho_saida, assets_dir)
            count += 1
    return count


def _id_da_linha(linha: dict) -> str | None:
    if "id" in linha and linha["id"].strip():
        return normalizar_id(linha["id"].strip())

    bairro = linha.get("bairro", "").strip()
    poste = linha.get("poste", "").strip()
    if bairro and poste:
        bairro_digitos = re.sub(r"\D", "", bairro).zfill(2)
        poste_digitos = re.sub(r"\D", "", poste).zfill(2)
        return normalizar_id(bairro_digitos + poste_digitos)

    return None


def gerar_por_csv(csv_path: Path, out_dir: Path, assets_dir: Path) -> int:
    out_dir = Path(out_dir)
    csv_path = Path(csv_path)
    count = 0
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for linha in reader:
            id_poste = _id_da_linha(linha)
            if not id_poste:
                continue
            caminho_saida = out_dir / f"poste_{id_poste}.png"
            gerar_adesivo(id_poste, caminho_saida, assets_dir)
            count += 1
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gerador de adesivos com QR Code para postes de iluminação."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_single = sub.add_parser("single", help="Gera um adesivo por ID")
    p_single.add_argument("--id", required=True, help="ID do poste (4 dígitos)")
    p_single.add_argument("--assets-dir", default="assets")
    p_single.add_argument("--out-dir", default="output")

    p_range = sub.add_parser("range", help="Gera por faixa de bairros/postes")
    p_range.add_argument("--bairro-start", type=int, default=1)
    p_range.add_argument("--bairro-end", type=int, default=99)
    p_range.add_argument("--poste-start", type=int, default=1)
    p_range.add_argument("--poste-end", type=int, default=99)
    p_range.add_argument("--assets-dir", default="assets")
    p_range.add_argument("--out-dir", default="output")

    p_csv = sub.add_parser("csv", help="Gera a partir de CSV")
    p_csv.add_argument("--file", required=True, help="Caminho do CSV")
    p_csv.add_argument("--assets-dir", default="assets")
    p_csv.add_argument("--out-dir", default="output")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assets_dir = Path(args.assets_dir)
    out_dir = Path(args.out_dir)

    if args.cmd == "single":
        id_poste = normalizar_id(args.id)
        caminho_saida = out_dir / f"poste_{id_poste}.png"
        gerar_adesivo(id_poste, caminho_saida, assets_dir)
        print(f"Gerado: {caminho_saida}")
        return

    if args.cmd == "range":
        count = gerar_por_intervalo(
            out_dir=out_dir,
            assets_dir=assets_dir,
            bairro_inicio=args.bairro_start,
            bairro_fim=args.bairro_end,
            poste_inicio=args.poste_start,
            poste_fim=args.poste_end,
        )
        print(f"Gerados {count} arquivos em {out_dir}")
        return

    if args.cmd == "csv":
        count = gerar_por_csv(
            csv_path=Path(args.file),
            out_dir=out_dir,
            assets_dir=assets_dir,
        )
        print(f"Gerados {count} arquivos em {out_dir}")
        return


if __name__ == "__main__":
    main()
