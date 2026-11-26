# BatSignal — historical project context

> This file describes the original prototype and earlier ideas. Some details below
> are historical and do not match the current implementation. Use [README.md](README.md)
> for current behavior, [ROADMAP.md](ROADMAP.md) for implemented priorities and future work,
> and [CONTRIBUTING.md](CONTRIBUTING.md) for development instructions.

**Autor:** Guilherme Barbosa Freire Silva  
**Artigo Original:** [Medium - Como eu criei um mapa de sinal Wi-Fi](https://theycallmefreire.medium.com/como-eu-criei-um-mapa-de-sinal-wi-fi-e-analisei-a-qualidade-em-cada-c%C3%B4modo-da-minha-casa-da08bfc1fbca)  
**Data:** 31 de Março de 2026  
**Status:** Beta | **Licença:** Open Source  

---

## 📊 O QUÊ É BATSIGNAL?

### Definição
**BatSignal** é uma ferramenta Python para **mapear e analisar a intensidade de sinal Wi-Fi** em diferentes cômodos de um imóvel. Permite visualizar onde o sinal é mais forte ou fraco através de gráficos automáticos.

### Propósito Principal
Fornecer uma **solução gratuita e open-source** para análise de cobertura Wi-Fi, substituindo ferramentas pagas que cobram por este serviço.

### Motivação Original
O criador precisava saber qual era o melhor local para posicionar seu PC baseado na qualidade do sinal Wi-Fi, e como as soluções existentes cobravam por isso, desenvolveu uma ferramenta própria.

### Público-Alvo
- **Usuários domésticos:** Otimizar posicionamento de equipamentos
- **Técnicos:** Mapear cobertura de rede
- **Pesquisadores:** Estudar propagação de sinais Wi-Fi
- **Desenvolvedores:** Base para projetos de análise de redes

---

## 🔧 COMO FUNCIONA - TECNICAMENTE

### Arquitetura Geral

```
┌─────────────────────────────────────────────────────────────┐
│                        BatSignal                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  COLETA DE DADOS                                     │  │
│  │  └─ wifi_coleta.py: get_wifi_strength()            │  │
│  │     └─ Executa: netsh wlan show interfaces         │  │
│  │     └─ Extrai: Linha com "Sinal"                   │  │
│  │     └─ Retorna: % intensidade (0-100)             │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PERSISTÊNCIA DE DADOS                               │  │
│  │  └─ wifi_dados.py:                                  │  │
│  │     └─ salvar_mapeamento() → JSON                   │  │
│  │     └─ carregar_mapeamento() ← JSON                │  │
│  │     └─ listar_mapeamentos()                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  GERAÇÃO DE GRÁFICOS                                 │  │
│  │  └─ wifi_graficos.py:                               │  │
│  │     └─ criar_grafico_linha() → Variação por tempo   │  │
│  │     └─ criar_grafico_barras() → Comparação média    │  │
│  │     └─ Usa: pandas, matplotlib, seaborn             │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  INTERFACE GRÁFICA (Tkinter)                         │  │
│  │  └─ app_main.py:                                    │  │
│  │     └─ AppWiFiComodos: UI principal                 │  │
│  │     └─ Seleção de cômodo                            │  │
│  │     └─ Botões: Iniciar, Parar, Salvar              │  │
│  │     └─ Visualização em tempo real                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

```
1. USUÁRIO SELECIONA CÔMODO
   └─ app_main.py: ComboBox com opções (Sala, Quarto, Cozinha, etc)

2. USUÁRIO CLICA "INICIAR COLETA"
   └─ Inicia thread com coleta contínua
   └─ Intervalo: 1s (configurável)
   └─ Duração: 60s (configurável)
   └─ Total: 60 medições por cômodo

3. COLETA EM TEMPO REAL
   └─ wifi_coleta.get_wifi_strength() → % do sinal
   └─ Armazena: força + timestamp
   └─ UI atualiza com cada medição

4. APÓS TERMINAR A COLETA
   └─ Calcula: min, max, média, desvio padrão
   └─ Exibe estatísticas na UI

5. USUÁRIO CLICA "SALVAR MAPEAMENTO"
   └─ wifi_dados.salvar_mapeamento()
   └─ Formato: JSON com timestamp
   └─ Estrutura: {cômodo → [medições]}

6. USUÁRIO CLICA "GERAR GRÁFICOS"
   └─ wifi_graficos.criar_grafico_linha()
   └─ wifi_graficos.criar_grafico_barras()
   └─ Visualiza variação e comparação
   └─ Exporta para Excel (opcionalmente)
```

### Tecnologia de Coleta (Windows)

**Comando usado:**
```bash
netsh wlan show interfaces
```

**Saída esperada:**
```
Interface : Wi-Fi
    Descrição                : [...]
    GUID                     : [...]
    Estado Físico            : Conectada
    SSID                     : [...]
    BSSID                    : [...]
    Tipo de Rede             : Infraestrutura
    Tipo de Rádio            : 802.11n
    Autenticação             : WPA2-Pessoal
    Cifra                    : CCMP
    Tipo de Conexão          : Autenticação bem-sucedida
    Sinal                    : 95%  ← EXTRAÍDO AQUI
    Perfil de Transmissão    : [...]
    [...]
```

**Extração:**
```python
# Procura por linha contendo "Sinal"
# Extrai primeiro número encontrado (0-100)
# Retorna como porcentagem
```

---

## 📈 COMO FUNCIONA - FEATURES E FLUXO

### Tela Principal

**Componentes:**
1. **Logo e Banner** - Branding com logo em PNG/ICO
2. **Seleção de Cômodo** - ComboBox dropdown
3. **Display de Força** - Número grande (% atual)
4. **Barra de Progresso** - Visualização 0-100%
5. **Estatísticas** - Min, Max, Média em tempo real
6. **Botões de Controle:**
   - "Iniciar Coleta" - Começa thread de captura
   - "Parar" - Para coleta
   - "Limpar" - Reseta dados
7. **Abas** - Coleta | Gráficos | Histórico

### Fluxo de Uso Típico

**Cenário 1: Primeira Análise**

```
1. Abrir aplicação
   └─ Carrega interface Tkinter
   └─ Logo aparece no banner

2. Selecionar "Sala" no combo box
   └─ UI ativa

3. Clicar "Iniciar Coleta"
   └─ Thread começa capturando Wi-Fi
   └─ A cada 1s: netsh wlan show interfaces
   └─ Display atualiza em tempo real
   └─ Duração: ~60s (12 medições)

4. Após terminar (automático)
   └─ Exibe: Min, Max, Média, Desvio Padrão
   └─ Coleta fica salva em memória

5. Repetir para cada cômodo (Quarto, Cozinha, Banheiro)

6. Clicar "Salvar Mapeamento"
   └─ Dialog pergunta nome
   └─ Salva em JSON: dados/Casa_2026-03-31_12-15-30.json
   └─ Estrutura:
      {
        "nome": "Casa",
        "data": "2026-03-31 12:15:30",
        "comodos": {
          "Sala": [
            {"forca": 95, "timestamp": "2026-03-31T12:15:00"},
            {"forca": 94, "timestamp": "2026-03-31T12:15:01"},
            ...
          ],
          "Quarto": [...],
          "Cozinha": [...],
          "Banheiro": [...]
        }
      }

7. Clicar "Ver Gráficos"
   └─ Aba "Gráficos" mostra:
      - Gráfico de Linha: Variação ao longo do tempo
      - Gráfico de Barras: Comparação entre cômodos
```

**Cenário 2: Análise Existente**

```
1. Abrir aplicação
2. Clicar aba "Histórico"
   └─ Lista mapeamentos salvos
   └─ Mostra: Nome, Data, Quantidade de cômodos
   └─ Opções: Carregar, Deletar, Exportar Excel
3. Selecionar um mapeamento
   └─ Carrega dados
   └─ Exibe gráficos automaticamente
4. Exportar para Excel
   └─ Cria arquivo .xlsx com dados brutos
```

### Tipos de Gráficos Gerados

**1. Gráfico de Linha**
- **Eixo X:** Número da medição (0-60)
- **Eixo Y:** Força (%) 80-105%
- **Uma linha por cômodo** com cor diferente
- **Linha de média** em tracejado
- **Uso:** Visualizar flutuação ao longo do tempo

**2. Gráfico de Barras**
- **Eixo X:** Cômodos
- **Eixo Y:** Força Média (%)
- **Ordenado:** Do mais forte pro mais fraco
- **Cores dinâmicas:**
  - Verde: ≥ 95% (Excelente)
  - Laranja: 92-94% (Bom)
  - Vermelho: < 92% (Fraco)
- **Anotações:** Min, Max, Média em cada barra
- **Uso:** Comparação rápida entre cômodos

---

## 🎯 O QUE DEVERIA SER - VISÃO FUTURA

### Versão 1.0 - Aplicativo Desktop Profissional (PRÓXIMO)

#### Arquitetura Modular
```
✅ Separar core (wifi_scanner, data_manager, analytics)
✅ Separar UI em widgets
✅ Adicionar logging estruturado
✅ Tratamento robusto de erros
✅ Suporte cross-platform (Windows/Linux/macOS)
```

#### Build & Distribuição
```
✅ PyInstaller para executável standalone
✅ Instalador MSI para Windows
✅ Makefile para automação
✅ CI/CD com GitHub Actions
✅ Versionamento semântico
```

#### Testes & Qualidade
```
✅ Testes unitários (pytest)
✅ Cobertura > 70%
✅ Code quality (pylint, black)
✅ Documentação completa
```

### Versão 1.5 - Features Principais

#### Interface Melhorada
```
🔄 Tema claro/escuro
🔄 Suporte a múltiplas residências
🔄 Edição de mapeamentos
🔄 Comparação entre mapeamentos (antes/depois)
🔄 Exportar para PDF + relatório
```

#### Funcionalidades Avançadas
```
🔄 Heatmap visual (mapa 2D da casa)
🔄 Suporte a múltiplos routers
🔄 Calibração de pontos conhecidos
🔄 Simulação de posicionamento ideal
🔄 Histórico de mudanças por cômodo
```

#### Análise Inteligente
```
🔄 IA para recomendação de posicionamento
🔄 Detecção de padrões de interferência
🔄 Análise de refluxo e multipercurso
🔄 Simulação de posição ideais de router
🔄 Scoring de qualidade por cômodo
```

### Versão 2.0 - Expansão

#### Plataformas Adicionais
```
⭐ Versão Linux (usando iwconfig)
⭐ Versão macOS (usando airport)
⭐ Aplicativo mobile (Kivy para Android/iOS)
⭐ Versão web (Flask/Django + frontend)
```

#### Integração com Hardware
```
⭐ Suporte para routers SNMP
⭐ Coleta de dados de mesh networks
⭐ Integração com dispositivos IoT
⭐ Captura remota (via SSH/WinRM)
```

#### Cloud & Sincronização
```
⭐ Sincronização na nuvem
⭐ Compartilhamento de mapas
⭐ Backup automático
⭐ Histórico de versões
⭐ Colaboração em tempo real
```

---

## 📋 CONCEITOS TÉCNICOS IMPORTANTES

### Fatores que Afetam o Sinal

**1. Distância do Roteador**
- Maior distância = Sinal mais fraco
- Relação não-linear (expoente 2-4)

**2. Barreiras Físicas**
- Paredes de alvenaria: -5 a -10 dB
- Porcelana e espelhos: Reflexão (pode melhorar ou piorar)
- Porta de metal: Bloqueio significativo

**3. Interferência Eletromagnética**
- Outros routers vizinhos
- Dispositivos 2.4 GHz (micro-ondas, baby monitors)
- Fornos de micro-ondas são os piores
- Causa redução mesmo sem LOS (line of sight)

**4. Padrão de Radiação da Antena**
- Antenas omnidirecionais teóricas: radiam em todas direções
- Antenas omnidirecionais reais: padrão toroidal (rosca)
- Máxima potência: perpendicular ao eixo
- Mínima potência: acima e abaixo da antena

**5. Fenômenos de Propagação**
- **Reflexão:** Sinal rebota em superfícies
- **Refração:** Sinal muda direção ao passar por materiais
- **Multipercurso (Multipath):** Múltiplos caminhos chegam simultaneamente
  - Pode criar interferência construtiva (melhora)
  - Pode criar interferência destrutiva (piora)
- **Difração:** Sinal passa ao redor de obstáculos

### Métricas de Qualidade

| Força | Status | Uso |
|-------|--------|-----|
| > 95% | Excelente | Streaming 4K, Video call HD |
| 92-95% | Bom | Streaming HD, Navegação |
| 85-92% | Aceitável | Whatsapp, Web browsing |
| < 85% | Fraco | Instável, problemas |

### Limitações Conhecidas

**Atual (Versão Beta):**
```
❌ Windows only (usa netsh)
❌ Sem suporte a múltiplos routers
❌ Sem heatmap visual
❌ Sem análise de multipercurso
❌ Sem recomendações automáticas
❌ Sem backup em nuvem
❌ Sem aplicativo mobile
```

---

## 📁 ESTRUTURA ATUAL DO PROJETO

```
BatSignal-wifi/
├── app_main.py (476 linhas) ← Interface Tkinter
├── wifi_coleta.py (23 linhas) ← Coleta de força
├── wifi_dados.py (124 linhas) ← Persistência JSON
├── wifi_graficos.py (128 linhas) ← Gráficos pandas/matplotlib
├── requeriments.txt ← Dependências
├── imagens/ ← Assets (logo, ícone)
├── dados/ ← Armazena JSONs com medições
└── README.md

Dependencies:
- pandas==2.0.3
- openpyxl==3.1.2
- matplotlib==3.7.2
- seaborn==0.12.2
- Pillow (para logo)
- tkinter (built-in Python)
```

**Arquivo de Exemplo (dados/Casa_2026-03-31_12-15-30.json):**
```json
{
  "nome": "Casa",
  "data": "2026-03-31 12:15:30",
  "comodos": {
    "Sala": [
      {"forca": 95, "timestamp": "2026-03-31T12:15:00"},
      {"forca": 94, "timestamp": "2026-03-31T12:15:01"},
      ...
    ],
    "Quarto": [
      {"forca": 92, "timestamp": "2026-03-31T12:16:00"},
      ...
    ]
  }
}
```

---

## ✅ STATUS ATUAL E PRÓXIMOS PASSOS

### O Que Funciona ✅
- ✅ Coleta de força Wi-Fi em Windows
- ✅ Interface Tkinter básica
- ✅ Salvamento em JSON
- ✅ Gráficos com pandas/matplotlib
- ✅ Exportação para Excel

### O Que Precisa Ser Feito 🚀

**FASE 1 - Arquitetura Profissional (2-3 semanas)**
```
□ Refatorar em módulos profissionais
□ Core modules (wifi_scanner, data_manager, analytics)
□ Separar UI em widgets
□ Adicionar logging centralizado
□ Tratamento robusto de erros
```

**FASE 2 - Build & Distribuição (1-2 semanas)**
```
□ setup.py e pyproject.toml
□ PyInstaller para executável
□ Instalador MSI para Windows
□ Makefile para automação
□ CI/CD com GitHub Actions
```

**FASE 3 - Testes & Documentação (1-2 semanas)**
```
□ Testes unitários completos
□ Documentação de API
□ Guia de contribuição
□ Exemplos de uso
□ Troubleshooting guide
```

**FASE 4 - Features Avançadas (Futuro)**
```
□ Suporte cross-platform
□ Heatmap visual
□ Recomendações de IA
□ Sincronização na nuvem
□ Aplicativo mobile
```

---

## 🎓 Caso de Uso Real (do Artigo)

**Ambiente:** Casa com 4 cômodos  
**Roteador:** Sala (omnidirecional)  
**Duração coleta:** 1 minuto por cômodo (12 medições)  

**Resultados:**

| Cômodo | Mínimo | Máximo | Média | Status |
|--------|--------|--------|-------|--------|
| Sala | 92% | 97% | 95% | ⭐ Excelente |
| Cozinha | 89% | 95% | 92% | ✅ Bom |
| Quarto | 88% | 94% | 91% | ✅ Aceitável |
| Banheiro | 87% | 91% | 89% | ⚠️ Fraco |

**Análise:**
- Sala é ideal (roteador aqui)
- Cozinha surpreendentemente bom (sem interferência de vizinhos)
- Banheiro fraco por: espessura de paredes + porcelana/espelhos

---

## 🔗 Referências

- **Artigo original:** https://medium.com/...
- **Repositório:** https://github.com/theycallmefreire/BatSignal-wifi
- **Documentação de WiFi:** IEEE 802.11 specifications
- **Padrão de Radiação:** Antenna Patterns (toroidal)
- **Fenômenos de Propagação:** Fading, Multipath, Shadowing

---

## 📞 Contato & Contribuição

**Autor:** Guilherme Barbosa Freire Silva  
**Localização:** Palmas, Tocantins, Brasil  
**Área de Interesse:** Cybersecurity, Backend, Networking  

**Como Contribuir:**
1. Fork o repositório
2. Crie branch para sua feature
3. Submeta pull request
4. Siga as guidelines de contribuição

---

## 📄 Changelog

**v0.1 (Beta - Atual)**
- ✅ Coleta básica funcionando
- ✅ Interface Tkinter
- ✅ Gráficos funcionando
- ✅ Salvamento em JSON

**v1.0 (Planejado)**
- ⏳ Arquitetura profissional
- ⏳ Build e instalador
- ⏳ Testes completos
- ⏳ Documentação
- ⏳ Cross-platform

---

**Última atualização:** 24/09/2026  
**Versão do Documento:** 1.0  
**Status:** Pronto para desenvolvimento

