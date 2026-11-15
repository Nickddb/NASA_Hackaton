# AstraCare AI — Backend Refatorado com Machine Learning Real (`teste/`)

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

## Como executar localmente

```powershell
..\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir . --host 0.0.0.0 --port 8001 --reload
```
