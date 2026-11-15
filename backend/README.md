# AstraCare AI — Backend (Machine Learning + Continuidade Clínica)

Este diretório contém o backend completo refatorado (**Fase 1: Machine Learning & Continuidade Clínica; Fase 2: Chatbot**) construído sobre 5 pilares médicos e aeroespaciais:

1. **Baseline Individual Adaptativo (`app/ml/adaptive_baseline.py`):**
   - Combina o histórico pré-voo de cada astronauta (`CDR Elena Vance`, `MS-1 Lucas Ferreira`, `PLT Kenji Sato`), *priors* de adaptação gravitacional do **NASA OSDR (`OSD-570` / `OSD-571`)** (`0g`, `1/6g` Lunar, `3/8g` Marciano), média móvel exponencial (**EWMA**) + desvio absoluto mediano robusto (**MAD**) e matriz de covariância regularizada de **Ledoit-Wolf** para calcular a **Distância Multivariada de Mahalanobis** e o `individual_z_score` vs. `population_z_score`.
2. **Inteligência Contextual da Missão (`app/ml/contextual_intelligence.py`):**
   - Correlaciona sinais vitais com sono/ciclo circadiano, exercício físico (`ARED`, `T2`, `CEVIS` e tempo pós-treino), status de EVA, fase gravitacional e ambiente da cabine (`ppCO2`, `O2`, pressão, temperatura).
   - Atenua falsos positivos (ex.: taquicardia e elevação térmica fisiológicas 15 min após treino no `T2` ou bolso localizado de `CO2` em microgravidade) e inclui `causal_disclaimer` explícito (**correlação observacional sem assumir causalidade automática**).
3. **Ciclo de Acompanhamento Fechado (`app/engine/followup_loop.py`):**
   - Todo alerta abre ou atualiza um `ClinicalFollowUpCase` com máquina de estados auditável:
     `OPEN_PENDING_CONFIRMATION` → `CONFIRMED_ACTIVE_MONITORING` / `DOWNGRADED_CONFOUNDER_OR_ARTIFACT` → `ACTION_EXECUTED_AWAITING_REASSESSMENT` → `RESOLVED` / `ESCALATED_TO_EARTH`.
   - Registra medições de confirmação, ações executadas pela tripulação e reavaliações programadas com prazo (`T+15m`, `T+30m`).
4. **IA Explicável, Calibrada e Auditável (`app/ml/predictor.py` & `app/engine/clinical_rules.py`):**
   - Ensemble calibrado (`CalibratedClassifierCV` + `HistGradientBoostingClassifier` + `RandomForestClassifier` + `IsolationForest`) validado com *5-Fold Stratified Cross-Validation* (`Accuracy`, `Macro-F1`, `Brier Score`, `ECE`).
   - Quantificação de incerteza **epistêmica** (variância entre árvores do ensemble) + **aleatória** (qualidade do sinal PPG/ECG, artefato de movimento, calibração do CGM/NIBP) + entropia de Shannon.
   - Atribuição contrafactual por perturbação local frente ao baseline pessoal do astronauta e previsão longitudinal de **24h, 48h e 72h** com intervalos de credibilidade de 80% via `BayesianRidge`.
   - Trava explícita de governança médica (`AutonomyGuardrail`: `autonomous_diagnosis_blocked=True`, `autonomous_treatment_blocked=True`, `human_in_the_loop_required=True`).
5. **Continuidade entre Nave e Terra (`app/engine/earth_sync.py` & `app/engine/nasa_feeds.py`):**
   - Operação 100% *offline-first* com ledger persistente (`data/local_mission_ledger.json`) e pacotes *Store-and-Forward* (`EarthSyncPackage`) assinados com hash de integridade **SHA-256**, integrando latência *light-time* via **NASA JPL Horizons** e clima espacial via **NASA DONKI (`FLR`, `SEP`, `CME`, `GST`)**.
6. **Chatbot & Orquestrador Clínico Agêntico — Fase 2 (`app/agent/orchestrator.py` & `app/agent/tools.py`):**
   - Opera em modo dual: **LangChain + Gemini (`langchain_gemini`)** com *tool-calling* ou **Pipeline Determinístico Offline-First Bilíngue PT/EN (`offline_hybrid_edge`)**.
   - **9 Tools Especializadas:**
     1. `inspect_adaptive_baseline_tool` (Pilar 1: EWMA, MAD, Mahalanobis, troca de perfil de astronauta)
     2. `evaluate_contextual_intelligence_tool` (Pilar 2: correlações não-causais com sono, exercício ARED/T2, EVA, gravidade e CO2)
     3. `predict_calibrated_ml_and_uncertainty_tool` (Pilar 4: ensemble calibrado, incerteza epistêmica/aleatória, atribuição contrafactual e previsão `BayesianRidge` 72h)
     4. `audit_explainable_alerts_and_rules_tool` (Pilar 4: auditoria de sinais originadores, qualidade do sensor, referências `NASA-STD-3001`/`OCHMO`/`OSDR` e `AutonomyGuardrail`)
     5. `manage_closed_loop_followup_tool` (Pilar 3: confirmações, ações executadas e reavaliações programadas via linguagem natural)
     6. `sync_spacecraft_earth_continuity_tool` (Pilar 5: dossiê `OCHMO-TB-044` + pacote `EarthSyncPackage` com hash `SHA-256` e sincronização com MCC-Houston)
     7. `check_nasa_donki_and_horizons_tool` (NASA DONKI `FLR`/`SEP`/`CME`/`GST` + JPL Horizons *light-time delay*)
     8. `log_nutrition_hydration_tool` (registro nutricional em linguagem natural + limites espaciais de Sódio `<=3500mg` e Ferro `<=10mg`)
     9. `log_sleep_mood_context_tool` (registro de sono, humor, dor no ombro EVA e contexto pós-treino/CO2)
     10. `trigger_psychological_biofeedback_tool` (**Pilar 6 — Contramedida Psicofisiológica & Alerta Central MCC-BHP**: pondera os desvios individuais `individual_z_score` de cada astronauta em 6 diagnósticos emocionais/autonômicos, aciona estímulos do *Personal Crew Vault* [vídeos da família, áudios de amigos, sons da natureza/animais, jogos e música calma], modela a recuperação vagal em ciclo fechado [FC, PA, HRV, Estresse, Humor], agenda reavaliação em `T+15 min` e envia alerta imediato + pacote `SHA-256` para a Central em Terra)

## Melhorias da v0.3.0 (consolidação `teste/` → `backend/`)

- **Baseline adaptativo:** janela móvel de até 14 dias com **quarentena de leituras anômalas** (> 2.5σ do baseline ajustado à fase), para que uma rampa patológica lenta não "ensine" o modelo que aquilo é normal. Novo campo de **tendência** por métrica (`trend_slope_sigma_per_day`, `trend_status`) que detecta deriva de vários dias antes de cruzar limiares. Covariância Ledoit-Wolf passa a usar o histórico real do astronauta (e seed reproduzível; antes usava `hash()`, que muda a cada processo).
- **Ciclo fechado:** cada reavaliação tem `due_at`; leituras marcam `OVERDUE` automaticamente e o caso expõe `pending_items` / `next_due_at`. Escalonamento para a Terra é **sempre humano** (`POST /api/followup/{id}/escalate`); o motor só sinaliza. Casos resolvidos não podem ser alterados (HTTP 409). Casos persistem em disco (`followup_cases.json`).
- **Continuidade nave–Terra:** hash SHA-256 sobre o **conteúdo completo** de cada pacote, encadeado ao pacote anterior; log de auditoria também encadeado. `GET /api/earth-sync/verify` recalcula as cadeias (detecta edição, remoção ou reordenação). A sincronização respeita a janela de comunicação (`comms_available`). Escrita atômica do ledger.
- **Estado de runtime fora do git:** `ASTRACARE_STATE_DIR` (padrão `backend/data/`) guarda `local_mission_ledger.json` e `followup_cases.json`, ambos no `.gitignore`.

## Como executar localmente

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

A porta 8000 é a que o proxy do Vite (`frontend/vite.config.js`) usa.

## Variáveis de ambiente

Copie `backend/.env.example` para `backend/.env` e preencha. O arquivo é lido sozinho na inicialização (`app/config.py`), está no `.gitignore` e as variáveis já definidas no sistema têm prioridade sobre ele.

| Variável | Para que serve | Padrão |
| --- | --- | --- |
| `ASTRACARE_LLM_PROVIDER` | `groq`, `gemini` ou `offline`. Vazio escolhe o primeiro com chave, começando pelo Groq | vazio |
| `GROQ_API_KEY` | Liga o LLM do Groq no chat (API compatível com a OpenAI, sem pacote extra) | vazio |
| `ASTRACARE_GROQ_REASONING_FORMAT` | Esconde o raciocínio `<think>` do Qwen na resposta | `hidden` |
| `GEMINI_API_KEY` (ou `GOOGLE_API_KEY`) | Alternativa: Gemini via LangChain. Requer `pip install -r requirements-llm.txt` | vazio |
| `ASTRACARE_LLM_MODEL` | Modelo do provedor escolhido | `qwen/qwen3.8-27b` (Groq) ou `gemini-2.5-flash` |
| `ASTRACARE_LLM_MAX_TOOL_ROUNDS` | Rodadas de tool calls encadeadas por mensagem | `5` |
| `ASTRACARE_LLM_TIMEOUT_S` | Timeout de cada chamada ao LLM, em segundos | `12` |
| `NASA_API_KEY` | Chave da api.nasa.gov para o DONKI (TODO: trocar a `DEMO_KEY`) | `DEMO_KEY` |
| `ASTRACARE_SCHEDULER_ENABLED` | Liga o laço que roda os exames agendados do smartwatch | `true` |
| `ASTRACARE_SCHEDULER_TICK_S` | Intervalo de verificação do laço, em segundos | `30` |
| `ASTRACARE_ALERT_COOLDOWN_MIN` | Janela, em minutos, sem reenviar o mesmo alerta central | `30` |
| `ASTRACARE_STATE_DIR` | Pasta do ledger, dos casos e do cache do DONKI | `backend/data` |

No frontend, a única variável é `VITE_API_BASE` (`frontend/.env.example`). Chaves secretas nunca entram lá, porque tudo que começa com `VITE_` vai para o navegador.

## Agente multi-tool (encadeamento)

Quatro tools em `app/agent/mission_tools.py`, que só orquestram os serviços existentes. A saída de cada uma decide a próxima:

1. `schedule_smartwatch_exam`: agenda um exame periódico (`interval_minutes`) e/ou coleta agora (`trigger_now`). Os tipos são `full_panel`, `cardio`, `cognitive_ctb`, `dosimetry`, `respiratory` e `metabolic`.
2. `analyze_telemetry_and_diagnose`: cruza o payload com o baseline individual, os limites da NASA e o DONKI (SEP/FLR/RBE). Devolve `status` (NORMAL/WARNING/CRITICAL), `category` (NONE/PHYSICAL_ENVIRONMENTAL/PSYCHOLOGICAL), `probable_diagnosis`, `confidence_score` e `next_tools`. Uma alteração comportamental só vira PSYCHOLOGICAL quando não há causa física nem DONKI.
3. `trigger_central_alert`: dispara em CRITICAL, ou em WARNING com prioridade PRIORITY/IMMEDIATE. Gera o alerta à tripulação, o pacote para os cirurgiões de voo e o registro no log de auditoria, com cooldown.
4. `activate_psychological_stimuli`: aciona o Personal Crew Vault e o console de saúde comportamental, só quando a categoria é PSYCHOLOGICAL (ou quando o astronauta pede).

Endpoints:

- `POST /api/agent/smartwatch/{crew_id}`, `GET /api/agent/smartwatch` e `DELETE /api/agent/smartwatch/{crew_id}/{exam_type}`
- `POST /api/agent/analyze/{crew_id}`
- `POST /api/agent/cycle/{crew_id}` (a cadeia completa)

No chat, o LLM encadeia as tools em várias rodadas. Sem LLM, frases como "agendar exame cardio do Kenji a cada 30 min" rodam a mesma cadeia.

## Testes

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

Os testes cobrem os 5 pilares: quarentena do baseline, tendência vs. pico agudo, contexto sem causalidade, explicabilidade + travas de autonomia em todo alerta, ciclo de acompanhamento completo (incluindo atraso e escalonamento humano), cadeia de hash e fila offline.
