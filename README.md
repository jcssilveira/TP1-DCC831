# TP1: Composição Musical Algorítmica via Cadeias de Markov (PICO-8)
---

## Como Executar

### 1. Instalação das Dependências

Recomenda-se o uso de um ambiente virtual Python (versão $\ge 3.10$):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Treinamento e Geração das Músicas

Para rodar a Cadeia de Markov, treinar nos dados e gerar as três faixas experimentais:

```bash
python simple_markov.py
```

O script treinará os modelos em cerca de 10 a 15 segundos e gerará os arquivos `.wav` diretamente na pasta `outputs/`.

---


