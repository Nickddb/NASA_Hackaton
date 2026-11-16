# Base de Conhecimento: Monitoramento da Saúde de Astronautas

Este documento consolida fontes de dados científicas, efeitos fisiológicos e psicológicos por fase de voo, relatos reais de tripulantes (incluindo a missão Artemis II) e a arquitetura tecnológica utilizada atualmente para telemetria biomédica espacial.

---

## 1. Fontes de Dados e Repositórios de Referência

Para estruturar pipelines de dados, modelos preditivos ou painéis de monitoramento, as seguintes bases abertas da NASA e parceiros fornecem datasets reais e protocolos clínicos:

* **NASA OSDR (Open Science Data Repository):** Repositório oficial de dados biológicos, ômicos, fisiológicos e de exposição à radiação de voos espaciais (`osdr.nasa.gov`). Inclui estudos sobre atrofia muscular, alterações epigenéticas, microbioma e resposta imunológica.
* **NASA Human Research Program (HRP) & Standard Measures:** Documenta os protocolos padronizados de coleta biométrica (*Spaceflight Standard Measures*), abrangendo parâmetros cardiovasculares, sensório-motores, densidade óssea e avaliações cognitivas.
* **TRISH (Translational Research Institute for Space Health) — Plataformas EXPAND e HERMES:** Consórcio financiado pela NASA focado em saúde no espaço profundo:
  * **EXPAND:** Banco de dados biomédicos e clínicos padronizados entre diferentes missões (incluindo voos comerciais como Polaris Dawn e missões Artemis).
  * **HERMES:** Arquitetura de referência para coleta *offline-first* via *wearables* sob alta latência de comunicação.
* **NASA Life Sciences Data Archive (LSDA):** Arquivo histórico com metadados clínicos e resultados de experimentos humanos desde os programas Mercury e Apollo até a Estação Espacial Internacional (ISS) e Artemis.
* **ESA (European Space Agency) — Space Medicine:** Publicações e dados sobre contramedidas de exercício, reabilitação pós-voo e monitoramento de sono e ritmo circadiano.

---

## 2. Impactos na Saúde por Fase da Missão

A medicina espacial organiza os riscos nos cinco grandes perigos do voo espacial (**RIDGE**: *Radiation, Isolation, Distance, Gravity, Environment*) e acompanha a tripulação em um ciclo contínuo de três fases:

| Fase da Missão | Foco do Monitoramento | Principais Efeitos Fisiológicos e Psicológicos |
| :--- | :--- | :--- |
| **Pré-voo (Preflight)** | Linha de base (*Baseline*), imunidade e preparação psicológica | • **Quarentena rigorosa (14 dias antes):** Evita que vírus latentes ou infecções leves eclodam em órbita.<br>• **Estresse pré-lançamento e carga logística:** Pressão emocional intensa na preparação familiar e protocolos de contingência.<br>• **Coleta de Baseline:** Mapeamento genético, metabólico, cardiovascular e cognitivo individual para comparação futura. |
| **Em voo (In-flight)** | Adaptação à microgravidade, radiação e autonomia médica | • **Deslocamento de fluidos e SANS:** Líquidos sobem para a cabeça, elevando a pressão intracraniana e alterando o formato do globo ocular (*Spaceflight-Associated Neuro-ocular Syndrome*).<br>• **Perda óssea e muscular:** Perda de ~1% a 1,5% de massa óssea por mês, exigindo ~2 horas diárias de exercícios resistivos.<br>• **Radiação cósmica e solar:** Fora da magnetosfera terrestre (como na Artemis), há maior risco de dano ao DNA e flashes visuais causados por raios cósmicos.<br>• **Ritmo circadiano e $CO_2$:** Alterações no sono e cefaleias ou irritabilidade ligadas a bolsões de dióxido de carbono e confinamento. |
| **Pós-voo (Postflight)** | Readaptação à gravidade ($1g$) e reabilitação | • **Intolerância ortostática:** Queda brusca na regulação da pressão arterial ao ficar de pé devido à redução do volume sanguíneo.<br>• **Déficit sensório-motor e vestibular:** Vertigem, perda de equilíbrio e dificuldade de locomoção imediata após o pouso.<br>• **Hipersensibilidade e fadiga:** Dor muscular, sensibilidade na pele e necessidade de descompressão psicológica após o retorno. |

---

## 3. Depoimentos Reais: Missão Artemis II e Longa Duração

Os relatos da tripulação da **Artemis II** (que orbitou a Lua em abril de 2026) e de veteranos da ISS evidenciam o impacto humano por trás dos indicadores biomédicos:

### Antes do Lançamento (Preparação Mental e Familiar)
* **Jeremy Hansen (Especialista de Missão, Artemis II):** Sobre a aceitação psicológica dos riscos e o controle do estresse para preservar o sono antes do embarque:
  > *"Você está agudamente ciente dos riscos. Você pensa neles com antecedência e faz muita preparação mental antes de ir... Você entra nesse modo de 'eu aceito o que vier'. Na noite anterior ao lançamento, eu apenas disse ao meu corpo: 'precisamos muito dormir', e tive uma ótima noite de sono."*
* **Christina Koch (Especialista de Missão, Artemis II):** Sobre o impacto emocional nos familiares quando o risco da missão se torna concreto:
  > *"Só caiu a ficha de verdade para o meu marido quando ele viu o foguete. Até que aquele foguete gigante de 90 metros estivesse na frente dele, não acho que tinha sido totalmente internalizado. Nossas conversas mudaram naquele dia e ficaram muito mais reais."*

### Durante a Viagem (Isolamento, Sensores e Coesão)
* **Reid Wiseman (Comandante, Artemis II):** Sobre o peso psicológico da distância de mais de 380 mil km da Terra e o uso contínuo dos dispositivos biométricos (*actigraphy watches*) para monitorar sono e atividade:
  > *"Não foi fácil estar a mais de 200 mil milhas de distância de casa. Antes de lançar, parece o maior sonho da Terra. Quando você está lá fora, você só quer voltar para suas famílias e amigos."*
  > *"Nós usamos esses relógios ativos [de monitoramento]... Sempre que ficávamos um pouco distraídos durante a missão, fazíamos muita sincronização deles sem motivo nenhum, apenas porque isso nos trazia de volta ao foco."*
* **Scott Kelly (Astronauta da NASA, 340 dias na ISS):** Sobre o efeito da radiação cósmica e a correlação entre níveis de $CO_2$ na cabine e alterações de humor:
  > *"É algo em que você pensa especialmente quando fecha os olhos e vê aqueles flashes [de luz], percebendo: 'Ei, aquele raio cósmico não passou apenas pelo meu olho [passou pelo meu cérebro]'."*
  > *"Minha noiva conseguia perceber pelo tom da minha voz e pelo meu humor como estavam os níveis de $CO_2$ na estação naquele momento."*

### Após o Retorno (Readaptação Física e Processamento Emocional)
* **Victor Glover (Piloto, Artemis II):** Sobre a sobrecarga sensorial e emocional logo após a amerissagem e os testes imediatos de readaptação:
  > *"Vou ser breve porque tenho medo de começar a falar. Ainda não processei o que acabamos de fazer... A gratidão de ver o que vimos e estar com quem eu estava é grande demais para caber em um único corpo."*
* **Scott Kelly (Pós-voo de 1 ano):** Sobre o choque físico da gravidade terrestre após meses em microgravidade (incluindo hipersensibilidade cutânea ao atrito das roupas):
  > *"A gravidade definitivamente dá uma surra em você quando você volta. Você não se sente bem e seu corpo está reagindo à gravidade novamente, tentando se readaptar."*

---

## 4. Arquitetura Atual de Monitoramento Biomédico

O monitoramento moderno opera como um ecossistema híbrido dividido em quatro camadas principais:

### 4.1. Sensores Vestíveis (Wearables) e Telemetria Passiva
* **Actígrafos de Pulso (ex: ActTrust / Actiwatch):** Monitoram ciclos de sono-vigília, exposição à luz e padrões de movimento via acelerômetros e sensores ópticos. Na missão **Artemis II**, a NASA utilizou um actígrafo desenvolvido pela startup brasileira *Condor Instruments* para mapear o ritmo circadiano e as interações da tripulação.
* **Smartwatches e Anéis Biométricos (ex: Garmin Fenix, Oura Ring):** Acompanham frequência cardíaca (FC), variabilidade da frequência cardíaca (HRV), saturação de oxigênio ($SpO_2$) e recuperação fisiológica.
* **Adesivos Multiparamétricos e Camisetas Inteligentes (ex: BioButton, Hexoskin):** Medem temperatura cutânea contínua, frequência respiratória, postura e eletrocardiograma (ECG) durante exercícios físicos ou atividades extraveiculares (EVAs).
* **Monitoramento Contínuo de Glicose (CGM) e Suor:** Dispositivos como o *Dexcom G6* e sensores microfluídicos analisam glicose intersticial e biomarcadores no suor (cortisol, lactato, eletrólitos) para detectar estresse metabólico de forma não invasiva.

### 4.2. Diagnóstico por Imagem e Monitoramento Ocular a Bordo
* **Ultrassom Portátil 3D (ex: Butterfly iQ+):** Conectado a tablets para exames rápidos do coração, vasos sanguíneos (detecção de tromboses por deslocamento de fluidos) e nervo óptico, com orientação remota ou guiada por software.
* **Tomografia Ocular (OCT) e Lentes Inteligentes:** Tomógrafos de coerência óptica a bordo e lentes com microssensores (como *Triggerfish*) monitoram alterações estruturais no olho e variações na pressão intraocular ligadas à síndrome SANS.

### 4.3. Coleta Biológica e Telemetria Ambiental Integrada
* **Dosímetros Ativos Pessoais:** Fornecem alertas em tempo real sobre picos de radiação solar ou cósmica, permitindo que a tripulação busque áreas mais blindadas da espaçonave.
* **Sensores de $CO_2$ e Qualidade do Ar:** Monitores fixos e portáteis rastreiam bolsões de $CO_2$ ao redor dos astronautas (ausência de convecção natural na microgravidade) e cruzam os dados com cefaleias e quedas cognitivas.
* **Análise de Fluidos e Sequenciamento a Bordo:** Amostras de sangue, urina e saliva são processadas ou analisadas em mini-sequenciadores de DNA (como o *MinION*) para acompanhar reativação viral, microbioma e perda óssea.

### 4.4. Fluxo de Dados e Comunicação (Órbita Baixa vs. Espaço Profundo)

| Aspecto Técnico | Órbita Terrestre Baixa (ISS) | Espaço Profundo (Artemis / Marte) |
| :--- | :--- | :--- |
| **Sincronização de Dados** | Quase em tempo real via satélites TDRSS, com teleconferências médicas privadas semanais (*Private Medical Conferences*). | Arquitetura *offline-first* (ex: plataforma **HERMES** do TRISH): armazenamento local em hubs de bordo e sincronização em pacotes conforme a janela de banda. |
| **Tomada de Decisão** | Centralizada no Controle de Missão (cirurgiões de voo em terra analisam os painéis e orientam a tripulação). | **EIMO (*Earth-Independent Medical Operations*):** Sistemas embarcados de apoio à decisão clínica e modelos preditivos locais que alertam a tripulação sem depender de resposta imediata da Terra. |
| **Avaliação Cognitiva** | Baterias de testes computadorizados (ex: *Cognition Test Battery*) aplicadas periodicamente em tablets para medir tempo de reação, memória e fadiga. | Testes rápidos integrados à rotina diária combinados com análise passiva de padrões de fala, sono e erro operacional. |

---

## 5. Diretrizes de Engenharia de Dados para o Projeto

Para estruturar a camada analítica de um sistema de monitoramento de astronautas, recomenda-se seguir três princípios adotados nos sistemas atuais:

1. **Ingestão Multimodal Sincronizada:** Correlacionar séries temporais fisiológicas (FC, HRV, sono, $SpO_2$) com séries temporais ambientais (nível de $CO_2$, dose de radiação, temperatura da cabine) na mesma janela temporal.
2. **Normalização por Baseline Individual:** Como cada organismo responde de maneira distinta à microgravidade, os limiares de alerta não devem usar apenas médias populacionais gerais, mas sim o desvio em relação à linha de base (*baseline*) coletada no período pré-voo de cada tripulante.
3. **Resiliência Offline-First:** Garantir armazenamento local em buffer, resolução de conflitos de sincronização e execução de modelos leves de detecção de anomalias diretamente na borda (*edge computing*), simulando cenários de alta latência ou perda de sinal (*loss of signal*).