# AstraCare AI — Task Board & Model Allocation

> **GitHub Project:** https://github.com/users/Nickddb/projects/5  
> **Repository:** https://github.com/Nickddb/NASA_Hackaton  
> **Central Orchestrator:** `Orchestrator (Argon)` (`gemini-pro-orchestrator-g1-pro`) — Coordenação geral, revisão de arquitetura e integração entre tarefas.  
> **Política de Esforço:** Todos os agentes rodam em esforço **`Medium`** por padrão para economizar cota e ganhar velocidade. Modelos **`High`** são usados **somente em último caso** nas tarefas mais difíceis (`T13`, `T14`, `T15`). Fallbacks **100% Gemini**.

---

## Model Allocation Summary by Complexity Tier

| Tier | Complexidade | Modelos Primários | Modelos Fallback (somente Gemini) | Política de Esforço |
| :--- | :--- | :--- | :--- | :--- |
| **Coordinator** | Orquestração & Revisão | `Orchestrator (Argon)` (`gemini-pro-orchestrator-g1-pro`) | `Gemini 4 Argon (Medium)` (`gemini-4-argon-medium`) | Coordenação central |
| **🟢 Nível 1** | Baixa | `Gemini 3.8 Flash (Medium)`, `Gemini 4 Hydrogen (Medium)` | `Gemini 3.8 Flash (Low / Medium)`, `Gemini 4 Hydrogen (Low)` | Sempre `Medium` / `Low` |
| **🟡 Nível 2** | Média | `Gemini 4 Hydrogen (Medium)`, `Claude Sonnet 5.5 (Medium)` | `Gemini 4 Hydrogen (Medium)`, `Gemini 4 Argon (Medium)`, `Gemini 3.8 Flash (Medium)` | Sempre `Medium` |
| **🔴 Nível 3** | Alta | `Gemini 4 Hydrogen (Medium)`, `Gemini 4 Argon (Medium)`, `Claude Opus 5.5 (Medium)`, `Claude Sonnet 5.5 (Medium)` | `Gemini 4 Argon (High)` / `Gemini 4 Hydrogen (High)` *(apenas último caso)*, `Gemini 4 Hydrogen (Medium)` | `Medium` por padrão; `High` só em último caso em `T13`–`T15` |

---

## 🟢 Nível 1 — Baixa Complexidade (Fundação, Dados & Documentação)

| ID | Tarefa | Modelo Primário | Modelo Fallback (Gemini) | Área | Entregável | Dependências | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **T01** | **Design System (`DESIGN.md`)** | `Gemini 3.8 Flash (Medium)` (`gemini-3.8-flash-medium`) | `Gemini 4 Hydrogen (Low)` (`gemini-4-hydrogen-low`) | Design / UI | Paleta *Deep Space Medical Cockpit* (cores semafóricas Verde/Amarelo/Vermelho de alto contraste, tipografia e tokens Tailwind) via `design-reference`. | Nenhuma | Done |
| **T02** | **Setup Backend Python (`uv` + FastAPI)** | `Gemini 3.8 Flash (Medium)` (`gemini-3.8-flash-medium`) | `Gemini 3.8 Flash (Low)` (`gemini-3.8-flash-low`) | Backend | Criação do `backend/` com Python 3.12+ via `uv`, `FastAPI`, CORS configurado e rota `/api/health` rodando. | Nenhuma | Done |
| **T03** | **Setup Frontend (`Vite + React + Tailwind + Three.js`)** | `Gemini 3.8 Flash (Medium)` (`gemini-3.8-flash-medium`) | `Gemini 3.8 Flash (Low)` (`gemini-3.8-flash-low`) | Frontend | Criação do `frontend/` com Tailwind CSS, `lucide-react`, `recharts` e Three.js (`@react-three/fiber`, `@react-three/drei`). | T01 | Done |
| **T04** | **Datasets de Cenários, Ambientes e Guias (`scenarios.json`)** | `Gemini 3.8 Flash (Medium)` (`gemini-3.8-flash-medium`) | `Gemini 4 Hydrogen (Low)` (`gemini-4-hydrogen-low`) | Dados / Clínica | JSON estruturado em inglês com os 6 presets de missão (*Nominal* + 5 cenários críticos), os 3 ambientes (*Transit*, *Orbital Station*, *Planetary Surface*) e os textos *"How to Measure"* / *"Why it Matters"* (incluindo referências de sono/polissonografia e dessincronia circadiana). | Nenhuma | Done |
| **T05** | **Documentação Final, `README.md`, `SUBMISSION.md` & Pitch** | `Gemini 4 Hydrogen (Medium)` (`gemini-4-hydrogen-medium`) | `Gemini 3.8 Flash (Medium)` (`gemini-3.8-flash-medium`) | Docs / Pitch | Textos finais em inglês para a página do Space Apps (`SUBMISSION.md`), roteiro de 30s/7 slides (`DEMO.md`), `README.md` público e pitch local (`pitch-deck`). | T12 (MVP no ar) | Done |

---

## 🟡 Nível 2 — Média Complexidade (Regras Clínicas, API NASA & Componentes Visuais)

| ID | Tarefa | Modelo Primário | Modelo Fallback (Gemini) | Área | Entregável | Dependências | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **T06** | **Motor Clínico Determinístico (`NASA-STD-3001`)** | `Gemini 4 Hydrogen (Medium)` (`gemini-4-hydrogen-medium`) | `Gemini 4 Argon (Medium)` (`gemini-4-argon-medium`) | Backend / Clínica | Módulo `clinical_rules.py` que avalia os 8 indicadores (FC/HRV, PA, Glicemia, Temp, Sono, Humor, Radiação, Nutrição), classifica sistemas orgânicos em `NOMINAL` / `WARNING` / `CRITICAL` e aplica ajustes por ambiente (fluidos 0g e checklist de descontaminação lunar/marciana). | T02, T04 | Done |
| **T07** | **Integração API `NASA DONKI` + Fallback Local** | `Gemini 4 Hydrogen (Medium)` (`gemini-4-hydrogen-medium`) | `Gemini 3.8 Flash (Medium)` (`gemini-3.8-flash-medium`) | Backend / NASA Data | Módulo `nasa_donki.py` que busca eventos reais de tempestades solares/radiação (`FLR` e `SEP` na `api.nasa.gov`) e salva `nasa_donki_sample.json` para funcionamento offline garantido. | T02 | Done |
| **T08** | **Dashboard de Sinais Vitais & Gráficos (`VitalsDashboard.jsx`)** | `Claude Sonnet 5.5 (Medium)` (`claude-sonnet-5-5-medium`) | `Gemini 4 Hydrogen (Medium)` (`gemini-4-hydrogen-medium`) | Frontend / UI | Componente `VitalsDashboard.jsx` com cards dos 8 indicadores, barras de metas nutricionais/hidratação, gráficos de tendência temporal (`recharts`) e guia rápido para astronautas não-médicos. | T03, T04 | Done |
| **T09** | **Simulador de Smartwatch & Seletor de Cenários (`SmartwatchSim.jsx`)** | `Claude Sonnet 5.5 (Medium)` (`claude-sonnet-5-5-medium`) | `Gemini 4 Hydrogen (Medium)` (`gemini-4-hydrogen-medium`) | Frontend / UI | Widget `SmartwatchSim.jsx` (coletas agendadas em borda, batimentos, sono/HRV, dosímetro e alertas hápticos visuais) + barra de troca rápida entre os 6 cenários e 3 ambientes. | T03, T06 | Done |
| **T10** | **Protocolo de Emergência Crítica ("B.O.") (`EmergencyProtocol.jsx`)** | `Claude Sonnet 5.5 (Medium)` (`claude-sonnet-5-5-medium`) | `Gemini 3.8 Flash (Medium)` (`gemini-3.8-flash-medium`) | Frontend / UI | Banner/Modal `EmergencyProtocol.jsx` acionado automaticamente em estado `CRITICAL`, exibindo checklist passo a passo de estabilização e status do pacote telemétrico enviado à Terra (com simulação da latência de Marte ~20 min). | T06, T08 | Done |
| **T11** | **Módulo de Telemedicina & Dossiê Automático (`TelemedDossier.jsx` + API)** | `Gemini 4 Hydrogen (Medium)` (`gemini-4-hydrogen-medium`) | `Gemini 4 Argon (Medium)` (`gemini-4-argon-medium`) | Fullstack | Endpoint `/api/telemedicine/dossier` + Modal `TelemedDossier.jsx` que compila automaticamente vitais, logs nutricionais, avaliação de sono e diagnóstico da IA em relatório pronto para envio aos Cirurgiões de Voo. | T06, T08 | Done |
| **T12** | **Deploy Público (Frontend + Backend)** | `Gemini 4 Hydrogen (Medium)` (`gemini-4-hydrogen-medium`) | `Gemini 3.8 Flash (Medium)` (`gemini-3.8-flash-medium`) | DevOps | Publicação do frontend e backend em URL pública acessível em janela anônima sem login (regra eliminatória do hackathon). | T08, T09, T10, T11, T13, T14, T15, T16 | In Progress |

---

## 🔴 Nível 3 — Alta Complexidade (Core de IA, ML Preditivo & 3D Interativo)

| ID | Tarefa | Modelo Primário | Modelo Fallback (Gemini) | Área | Entregável | Dependências | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **T13** | **Motor de Machine Learning (`scikit-learn`: IsolationForest + RandomForest)** | `Gemini 4 Hydrogen (Medium)` (`gemini-4-hydrogen-medium`) | `Gemini 4 Argon (High)` (`gemini-4-argon-high`) *(só em último caso)* | Backend / ML | Módulo `ml_predictor.py` com `IsolationForest` (Anomaly Score 0–100%) e `RandomForestClassifier` treinados na inicialização sobre dataset sintético calibrado (padrão NASA OSDR / Standard Measures), retornando probabilidades das 5 síndromes e *Feature Importance*. | T02, T04 | Done |
| **T14** | **Agente Orquestrador LangChain + 6 Tools + Fallback Offline-First** | `Gemini 4 Argon (Medium)` (`gemini-4-argon-medium`) | `Gemini 4 Hydrogen (High)` (`gemini-4-hydrogen-high`) *(só em último caso)* | Backend / IA | Módulos `agent/tools.py` e `orchestrator.py` com 6 tools (`evaluate_clinical_rules`, `predict_ml_risk`, `check_nasa_donki_weather`, `log_nutrition_hydration`, `log_sleep_mood_checkin`, `compile_telemedicine_dossier`), integração Gemini via LangChain e fallback offline determinístico/NLP+ML. | T06, T07, T13 | Done |
| **T15** | **Modelo Corporal 3D Holográfico Interativo (`BodyModel3D.jsx` em Three.js/R3F)** | `Claude Opus 5.5 (Medium)` (`claude-opus-5-5-medium`) | `Gemini 4 Argon (High)` (`gemini-4-argon-high`) *(só em último caso)* | Frontend / 3D | Componente `BodyModel3D.jsx` com câmera orbital, avatar anatômico holográfico procedural em Three.js e 6 regiões/sistemas clicáveis (Cardiovascular, Nervoso/Sono, Respiratório, Metabólico, Musculoesquelético, Radiação) com cores dinâmicas e disparo de exames manuais. | T03, T06 | Done |
| **T16** | **Painel Conversacional do Agente & Trace de Decisão em Tempo Real (`AgentChatPanel.jsx`)** | `Claude Sonnet 5.5 (Medium)` (`claude-sonnet-5-5-medium`) | `Gemini 4 Hydrogen (Medium)` (`gemini-4-hydrogen-medium`) | Frontend / IA | Componente `AgentChatPanel.jsx` conectado ao `/api/agent/chat` com *quick-prompts*, atualização em tempo real das barras nutricionais/sono/3D e exibição visual dos Badges de Raciocínio (Tools LangChain acionadas, Anomaly Score do ML e regra `NASA-STD-3001`). | T03, T14, T15 | Done |
