# Produtor de QR Code

Projeto em Python para gerar QR Codes e adesivos de identificação em massa.

## Contexto

Foi pensado para uso operacional na prefeitura de Santo Antônio da Barra, permitindo identificar problemas em postes de iluminação pública por meio de QR Codes e contato via WhatsApp.

## Funcionalidades

- Geração de QR Code por identificador de poste
- Montagem de adesivos com layout pronto para impressão
- Uso de logos e assets locais
- Saida de imagens para distribuição em campo

## Arquivos principais

- `gerar_adesivos.py`

## Dependências

O projeto usa bibliotecas como:

- `qrcode`
- `Pillow`

## Saida

Os arquivos gerados são gravados em `output/`.
