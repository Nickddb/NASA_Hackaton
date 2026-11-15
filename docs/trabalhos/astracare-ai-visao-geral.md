# 🚀 AstraCare AI: Ecossistema Autônomo de Monitoramento e Triagem de Saúde Aeroespacial

> **Submissão Oficial:** NASA Space Apps Challenge 2026  
> **Desafio:** Software de Monitoramento de Saúde para Astronautas em Missões Espaciais (*Creating Health Monitoring Software for Astronauts on Space Missions*)  
> **Categoria:** Exploração Humana / Software / Saúde Espacial

---

## 📋 Sumário

1. [Visão Geral e Resumo Executivo](#1-visão-geral-e-resumo-executivo)
2. [Contexto Científico e os 5 Perigos da NASA (HRP)](#2-contexto-científico-e-os-5-perigos-da-nasa-hrp)
3. [A Solução: Arquitetura e Funcionalidades Principais](#3-a-solução-arquitetura-e-funcionalidades-principais)
   - [3.1. Interface Frontend & Modelo Corporal 3D Interativo](#31-interface-frontend--modelo-corporal-3d-interativo)
   - [3.2. Agente Inteligente Embarcado no Smartwatch](#32-agente-inteligente-embarcado-no-smartwatch)
   - [3.3. Assistente Conversacional (Chatbot Multimodal e Nutricional)](#33-assistente-conversacional-chatbot-multimodal-e-nutricional)
   - [3.4. Motor Preditivo (ML + Regras Clínicas) e Cruzamento de Variáveis](#34-motor-preditivo-ml--regras-clínicas-e-cruzamento-de-variáveis)
   - [3.5. Protocolo de Emergência Crítica ("B.O.") e Alerta à Terra](#35-protocolo-de-emergência-crítica-bo-e-alerta-à-terra)
   - [3.6. Módulo de Telemedicina Assíncrona e Síncrona](#36-módulo-de-telemedicina-assíncrona-e-síncrona)
4. [Matriz Completa de Indicadores, Causas Espaciais e Métodos de Medição](#4-matriz-completa-de-indicadores-causas-espaciais-e-métodos-de-medição)
5. [Matriz de Cruzamento Preditivo (Exemplos de Diagnóstico Combinado)](#5-matriz-de-cruzamento-preditivo-exemplos-de-diagnóstico-combinado)
6. [Garantia de Qualidade de Dados nos Diferentes Ambientes Espaciais](#6-garantia-de-qualidade-de-dados-nos-diferentes-ambientes-espaciais)
7. [Alinhamento com as Regras e Critérios do Hackathon](#7-alinhamento-com-as-regras-e-critérios-do-hackathon)
8. [Documentação de IA, Transparência e Fontes Oficiais](#8-documentação-de-ia-transparência-e-fontes-oficiais)

---

## 1. Visão Geral e Resumo Executivo

Com o avanço do **Programa Artemis** da NASA e os planos concretos para missões tripuladas a Marte, os seres humanos enfrentarão expedições de longa duração longe da proteção atmosférica e magnética da Terra. Nessas jornadas, o atraso nas comunicações (que pode chegar a mais de 20 minutos em cada sentido no caso de Marte) torna inviável depender exclusivamente de diagnósticos médicos terrestres em tempo real.

O **AstraCare AI** é um ecossistema inteligente de software e hardware vestível concebido para atuar como o **Oficial Médico Virtual a bordo**. Integrando um agente autônomo que roda em um **smartwatch biométrico** a uma **central visual interativa com modelo humano 3D**, o sistema automatiza coletas, cruza múltiplos biomarcadores por meio de Machine Learning e regras clínicas, gerencia a nutrição e a saúde mental do astronauta e dispara alertas imediatos de emergência para a Terra diante de anomalias críticas.

---

## 2. Contexto Científico e os 5 Perigos da NASA (HRP)

Toda a engenharia de requisitos do **AstraCare AI** foi fundamentada nos estudos do **Human Research Program (HRP)** da NASA, que mapeia os cinco grandes riscos do voo espacial humano:

1. **Radiação Espacial:** Fora da magnetosfera terrestre, os astronautas sofrem exposição contínua a Raios Cósmicos Galácticos (GCR) e eventos imprevisíveis de Partículas Solares (SPE), aumentando o risco de danos celulares, doenças degenerativas e síndrome aguda da radiação.
2. **Isolamento e Confinamento:** O convívio prolongado em espaços reduzidos, longe da família e da Terra, desencadeia fadiga emocional, alterações de humor, ansiedade, depressão e declínio cognitivo.
3. **Distância da Terra:** Impossibilita evacuações médicas de emergência e impõe latência na comunicação, exigindo sistemas de suporte à decisão clínica totalmente autônomos a bordo (*Edge AI*).
4. **Campos Gravitacionais Alterados:** A transição entre microgravidade (0g), gravidade lunar (1/6g) e marciana (3/8g) provoca redistribuição cefálica de fluidos, descondicionamento cardiovascular, perda de massa muscular e desmineralização óssea.
5. **Ambientes Fechados Hostis:** Ecossistemas fechados com ar reciclado, ruído constante, alteração dos ciclos de luz/escuridão (rompimento do ritmo circadiano) e maior virulência de microrganismos oportunistas combinada à supressão imunológica do tripulante.

---

## 3. A Solução: Arquitetura e Funcionalidades Principais

O sistema é dividido em seis pilares operacionais perfeitamente sincronizados:

### 3.1. Interface Frontend & Modelo Corporal 3D Interativo
* **Avatar Anatômico 3D Clicável:** Em vez de planilhas frias, o astronauta visualiza uma representação tridimensional do próprio corpo. Cada sistema orgânico (Cardiovascular, Nervoso, Respiratório, Metabólico, Musculoesquelético) exibe uma **codificação dinâmica por cores** (Verde: Nominal | Amarelo: Atenção | Vermelho: Crítico).
* **Gatilhos Manuais de Exame:** Ao clicar em uma região do corpo 3D (ex: tórax/coração), o astronauta visualiza o histórico daquele sistema e pode acionar um **gatilho manual** para iniciar uma medição imediata nos sensores conectados.
* **Dashboards Dinâmicos:** Gráficos temporais interativos permitem acompanhar tendências de horas de sono, variação glicêmica, dose acumulada de radiação e metas nutricionais ao longo das semanas de missão.

### 3.2. Agente Inteligente Embarcado no Smartwatch
* **Operação Contínua em Borda (Edge Computing):** O núcleo do agente roda diretamente no smartwatch do astronauta e sincroniza com o terminal da nave/base, garantindo funcionamento pleno mesmo sem conexão com a Terra.
* **Rotina Agendada (Scheduled Monitoring):** O agente executa coletas silenciosas e programadas (ex: leitura de batimentos a cada 5 minutos, análise de fases do sono durante o repouso, verificação de dosimetria contínua) e notifica gentilmente quando é hora de realizar um exame ativo (como glicemia capilar ou pressão arterial matinal).

### 3.3. Assistente Conversacional (Chatbot Multimodal e Nutricional)
* **Mesmo Cérebro, Múltiplos Canais:** O chatbot integrado no dashboard e no relógio é a interface conversacional direta com o agente de saúde.
* **Registro Ativo por Linguagem Natural:** O astronauta pode conversar naturalmente com o agente para registrar hábitos e sintomas. 
  * *Exemplo prático:* Se o tripulante digita ou fala *"Hoje comi 2 maçãs e bebi 500ml de água"*, o agente extrai as entidades nutricionais, calcula calorias, carboidratos, fibras e hidratação, e **atualiza automaticamente a barra de metas nutricionais** no dashboard.
* **Check-in Psicológico e Insights:** O chatbot realiza perguntas breves e empáticas para avaliar o estado emocional, oferecendo técnicas de respiração, higiene do sono ou ajustes na rotina de exercícios conforme o perfil do tripulante.

### 3.4. Motor Preditivo (ML + Regras Clínicas) e Cruzamento de Variáveis
* **Análise Multifatorial:** O agente não avalia sinais vitais de forma isolada. Ele combina um **Motor de Regras Determinísticas da NASA** com modelos de **Machine Learning Preditivo** (classificação e detecção de anomalias em séries temporais) para cruzar múltiplos exames simultaneamente.
* **Diagnóstico Probabilístico e Plano de Ação:** Ao cruzar temperatura, pressão arterial, frequência cardíaca, sono e radiação, o sistema aponta a causa mais provável da alteração e entrega um **roteiro prático de conduta física e psicológica** para o astronauta agir imediatamente.

### 3.5. Protocolo de Emergência Crítica ("B.O.") e Alerta à Terra
* **Detecção de Severidade Alta:** Caso o cruzamento de dados identifique uma condição grave, complexa ou potencialmente fatal — seja **física** (ex: arritmia severa, choque hipovolêmico, pico agudo de radiação solar, febre alta persistente) ou **psicológica** (ex: colapso por estresse agudo, privação severa de sono com desorientação) — o agente entra em **Modo de Alerta Crítico**.
* **Notificação Imediata à Central (Terra) e Tripulação:**
  1. Dispara um pacote telemétrico prioritário de alta urgência para o Controle da Missão e os Cirurgiões de Voo na Terra.
  2. Notifica os demais membros da tripulação a bordo para suporte mútuo imediato.
  3. Exibe na tela do relógio e do painel central um **protocolo passo a passo de estabilização** (ex: *"1. Dirija-se ao abrigo anti-radiação; 2. Administre medicação X do Kit Médico B; 3. Permaneça em repouso até confirmação"*).

### 3.6. Módulo de Telemedicina Assíncrona e Síncrona
* **Consulta Remota Integrada:** Quando o astronauta precisa de suporte humano especializado, o painel oferece um botão direto de **Telemedicina**.
* **Dossiê Automático Pré-Consulta:** Antes mesmo da chamada de vídeo (ou envio de mensagem de vídeo em caso de alta latência com Marte), o agente compila um relatório clínico estruturado com os últimos gráficos, logs nutricionais e diagnósticos sugeridos, economizando tempo precioso do médico em Terra.

---

## 4. Matriz Completa de Indicadores, Causas Espaciais e Métodos de Medição

| Indicador de Saúde | Causas no Espaço (Perigos NASA) | Método de Coleta na Solução | Desafios Espaciais e Garantia de Boa Medição |
| :--- | :--- | :--- | :--- |
| **Frequência Cardíaca (FC) & Variabilidade (HRV)** | **Microgravidade** (redistribuição de fluidos e descondicionamento cardíaco), estresse operacional e radiação. | **Smartwatch Biométrico** contínuo com sensores ópticos (PPG) e ECG sob demanda. | **Desafio:** Flutuação do braço e perda de contato em 0g.<br>**Solução:** Filtro de ruído via acelerômetro de 6 eixos e pulseira ergonômica de ajuste firme. |
| **Pressão Arterial (PA)** | **Campos gravitacionais alterados** causando deslocamento de fluidos para o tórax e cabeça ("puffy face, bird legs"). | **Manguito Digital Integrado** ao pulso/braço com sincronização Bluetooth automática. | **Desafio:** Ausência de coluna hidrostática altera valores basais.<br>**Solução:** Protocolo agendado matinal com o astronauta ancorado e em repouso por 5 minutos. |
| **Glicemia (Açúcar no Sangue)** | **Isolamento, estresse crônico** (aumento de cortisol), alterações nutricionais e resistência insulínica induzida pelo voo espacial. | **Sensor Contínuo de Glicose (CGM)** subcutâneo OU **Tiras Reativas** com micropunção capilar. | **Desafio:** Degradação química das tiras por radiação cósmica.<br>**Solução:** Armazenamento dos insumos em compartimentos blindados e calibração periódica. |
| **Temperatura Corporal** | **Ambientes fechados hostis** e infecções oportunistas devido à imunossupressão espacial. | **Sensor Térmico Cutâneo Contínuo** no smartwatch + **Termômetro Infravermelho** de confirmação. | **Desafio:** Variações térmicas da cabine influenciam leituras de pele.<br>**Solução:** Algoritmo de compensação que subtrai a temperatura ambiente da espaçonave. |
| **Sono e Ritmo Circadiano** | **Confinamento** e ausência do ciclo natural de 24h (16 amanheceres/anoiteceres por dia em órbita baixa). | **Acelerometria + HRV no Smartwatch** combinados ao check-in diário de energia no chatbot. | **Desafio:** Flutuar imóvel pode simular sono em sensores simples.<br>**Solução:** Cruzamento obrigatório entre imobilidade, queda da FC basal e padrão respiratório. |
| **Humor, Estresse e Carga Cognitiva** | **Isolamento prolongado**, distância da Terra e sobrecarga de tarefas críticas. | **Análise de Sentimento no Chatbot**, check-in rápido de humor (1 a 5) e biomarcadores de estresse (HRV). | **Desafio:** Subnotificação de problemas psicológicos pelo astronauta.<br>**Solução:** Detecção passiva de queda na variabilidade cardíaca associada a padrões de sono irregulares. |
| **Dose de Radiação Absorvida** | **Raios Cósmicos Galácticos (GCR)** e tempestades solares (**Solar Particle Events - SPE**). | **Dosímetro Pessoal de Radiação** integrado via BLE ao smartwatch e ao agente central. | **Desafio:** Picos súbitos de radiação exigem reação em segundos.<br>**Solução:** Limiar de disparo instantâneo (hardware interrupt) com alarme sonoro/háptico no pulso. |
| **Balanço Nutricional e Hidratação** | **Perda de apetite em microgravidade**, alteração do paladar por congestão nasal e risco de cálculo renal por desidratação. | **Input Conversacional no Chatbot** (ex: *"comi 2 maçãs"*) + leitura de código QR das embalagens espaciais. | **Desafio:** Esquecimento de registro durante rotinas intensas.<br>**Solução:** Lembretes contextuais inteligentes e registro por voz/texto em linguagem natural. |

---

## 5. Matriz de Cruzamento Preditivo (Exemplos de Diagnóstico Combinado)

Abaixo estão exemplos reais de como o motor híbrido (**Regras Clínicas + ML Preditivo**) interpreta combinações de exames para evitar falsos alarmes e agir com precisão:

| Combinação de Indicadores Detectados | Diagnóstico Provável Inferido | Severidade | Ação do Agente (Astronauta + Terra) |
| :--- | :--- | :---: | :--- |
| **Temp $\ge 38.2^\circ\text{C}$** + **PA $80/50\text{ mmHg}$** + **FC $112\text{ bpm}$** | **Infecção Sistêmica / Quadro Viral Agudo com Risco de Desidratação** | 🔴 **CRÍTICA** | **1.** Envia alerta imediato aos cirurgiões de voo na Terra.<br>**2.** Orienta isolamento na cabine.<br>**3.** Prescreve protocolo de hidratação eletrolítica e antitérmico do kit médico. |
| **Temp $36.6^\circ\text{C}$** + **PA $85/55\text{ mmHg}$** + **FC $108\text{ bpm}$** (após retorno à gravidade ou EVA) | **Intolerância Ortostática / Hipotensão por Redistribuição de Fluidos** | 🟠 **ALERTA** | **1.** Orienta o astronauta a deitar-se ou ativar compressão nos membros inferiores.<br>**2.** Recomenda ingestão imediata de solução salina.<br>**3.** Reavalia em 15 minutos. |
| **Sono $< 4.5\text{h}$ (3 dias seguidos)** + **HRV Baixa** + **Humor $\le 2/5$** | **Fadiga Comportamental Severa e Risco de Erro Operacional** | 🔴 **CRÍTICA** | **1.** Notifica o comandante da missão e a equipe psicológica em Terra.<br>**2.** Recomenda suspensão imediata de tarefas críticas (ex: caminhada espacial/robótica) e protocolo de descanso. |
| **Glicemia $62\text{ mg/dL}$** + **Registro Nutricional < 50% da meta** + **Tremor/FC alta** | **Hipoglicemia por Déficit Calórico em Atividade Intensa** | 🟠 **ALERTA** | **1.** Alerta no smartwatch para ingestão imediata de carboidrato de absorção rápida.<br>**2.** Atualiza o plano alimentar do dia no chatbot. |
| **Dosímetro $> 0.5\text{ mSv/h}$** (pico súbito) + demais vitais normais | **Evento de Partículas Solares (Tempestade Solar) em Curso** | 🔴 **CRÍTICA** | **1.** Alarme máximo no relógio e na estação.<br>**2.** Orienta deslocamento imediato para a zona blindada contra radiação.<br>**3.** Comunica telemetria à Terra. |

---

## 6. Garantia de Qualidade de Dados nos Diferentes Ambientes Espaciais

O **AstraCare AI** adapta seus protocolos de calibração e instrução de acordo com o local onde o astronauta se encontra na missão:

* **Em Trânsito (Cápsula Orion / Espaçonave Interplanetária):**
  * Ambiente de microgravidade contínua e espaço físico restrito.
  * Todos os sensores operam via protocolos sem fio de baixíssimo consumo (BLE), evitando cabos soltos na cabine.
  * O agente aplica fatores de correção para deslocamento cefálico de fluidos nas leituras de pressão e frequência cardíaca.
* **Em Estação Orbital (ISS / Lunar Gateway):**
  * Integração com os equipamentos médicos de bordo (ultrassom, analisadores sanguíneos) via sincronização com o painel central.
  * Gestão automatizada dos ciclos de iluminação da cabine em sincronia com os dados de sono do smartwatch.
* **Em Superfície Planetária ou Lunar (Rovers / Habitats Artemis & Marte):**
  * Exposição ao regolito lunar ou poeira marciana (partículas altamente abrasivas e tóxicas).
  * Antes de qualquer exame ativo (como micropunção glicêmica ou uso de manguito), o agente exibe um **checklist obrigatório de descontaminação e vedação** para garantir que nenhuma partícula externa contamine a amostra ou o ferimento.

---

## 7. Alinhamento com as Regras e Critérios do Hackathon

O desenvolvimento do **AstraCare AI** atende integralmente a todos os objetivos e considerações recomendadas pelo **NASA Space Apps Challenge**:

1. **Autonomia e Empoderamento do Astronauta:** Não pressupõe que o tripulante tenha formação médica; traduz dados complexos em explicações simples, visuais e planos de ação passo a passo.
2. **Entrada Multimodal de Dados:** Aceita telemetria automática (smartwatch/dosímetro), cliques interativos no modelo 3D, leituras laboratoriais e linguagem natural via chatbot.
3. **Visualização Intuitiva e Gamificação:** Utiliza modelo corporal 3D clicável, codificação universal por cores, gráficos dinâmicos e sistema de acompanhamento de metas nutricionais e de saúde para engajar o tripulante na rotina preventiva.
4. **Resiliência Operacional:** Projetado para funcionar offline-first (borda), mantendo a inteligência diagnóstica ativa independentemente da latência de comunicação com a Terra.

---

## 8. Documentação de IA, Transparência e Fontes Oficiais

### Como a Inteligência Artificial é Aplicada no Projeto
* **Arquitetura Híbrida (Segurança Clínica + Predição):** Na medicina espacial, modelos puramente "caixa-preta" podem gerar alucinações perigosas. Por isso, o **AstraCare AI** utiliza **Regras Clínicas Determinísticas** (baseadas nos protocolos médicos da NASA) como camada de segurança primária para alertas críticos, combinadas com **Machine Learning Preditivo** para detectar tendências sutis e correlações multivariadas ao longo do tempo.
* **Processamento de Linguagem Natural (NLP) no Chatbot:** Utilizado para interpretar entradas livres do astronauta (alimentação, sintomas subjetivos, diário emocional) e estruturá-las automaticamente no banco de dados de saúde da missão.

### Fontes Científicas e Referências Utilizadas
1. **NASA Human Research Program (HRP) — Five Hazards of Human Spaceflight:** Referência primária para mapeamento dos riscos fisiológicos, psicológicos e ambientais de missões de longa duração ([nasa.gov/hrp/hazards](https://www.nasa.gov/hrp/hazards/)).
2. **NASA Space Apps Challenge 2026 — Official Challenge Kit:** Diretrizes de escopo, arquitetura e requisitos de interface do desafio *Creating Health Monitoring Software for Astronauts on Space Missions* ([github.com/angelinopires/space-apps-2026-kit](https://github.com/angelinopires/space-apps-2026-kit)).
3. **Canadian Space Agency (CSA) — Monitoring Radiation to Protect Astronaut Health:** Parâmetros de dosimetria pessoal, limiares de exposição aguda/crônica e protocolos de proteção contra radiação espacial ([asc-csa.gc.ca](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp)).