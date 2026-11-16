# AstraCare AI — Backend

API FastAPI que concentra o monitoramento de saúde da tripulação: baseline individual, inteligência contextual, ML calibrado, árvore de causas, ciclo de acompanhamento, continuidade nave–Terra e o agente de IA do chat. Funciona 100% offline; os serviços externos (NASA DONKI, NASA JPL Horizons, Groq) são opcionais e têm cache e fallback.

## Arquitetura

| Camada | Arquivos | O que faz |
| --- | --- | --- |
| **Estado da missão** | `app/state_manager.py` | 5 tripulantes (`elena_vance`, `lucas_ferreira`, `kenji_sato`, `amara_okafor`, `liam_soren`), cada um com cenário, ambiente, sinais vitais, dor relatada e histórico próprios. |
| **Calibração NASA** | `app/engine/nasa_calibration.py` | Fonte única dos limites (NASA-STD-3001, OCHMO, HRP, OSDR, CSA). Cada valor traz a `source` e um `verified` que diz se foi conferido no documento. |
| **Gerador de telemetria** | `app/engine/telemetry_generator.py` | Leituras estocásticas por astronauta e fase da missão, com 8 perfis de crise e versões prodrômicas (início do quadro). |
| **Baseline adaptativo** | `app/ml/adaptive_baseline.py` | EWMA + MAD, covariância Ledoit-Wolf e distância de Mahalanobis, *priors* OSDR (`OSD-570`/`OSD-571`) por gravidade e quarentena de leituras anômalas (> 2,5σ), para que uma deriva lenta não vire "normal". |
| **Inteligência contextual** | `app/ml/contextual_intelligence.py` | Exercício (ARED/T2/CEVIS), EVA, sono, CO₂ da cabine e fase gravitacional explicam desvios benignos. Correlação, nunca causalidade automática. |
| **Regras clínicas** | `app/engine/clinical_rules.py` | Avaliação por sistema (`NOMINAL`/`ATTENTION`/`WARNING`/`CRITICAL`), checklists NASA-STD-3001/OCHMO e travas de autonomia (`AutonomyGuardrail`). |
| **ML calibrado e explicável** | `app/ml/predictor.py`, `app/ml/features.py` | HistGradientBoosting + RandomForest calibrados (Platt, 5 folds) + IsolationForest, 26 features, 8 síndromes; incerteza epistêmica + do sensor, atribuição contrafactual e previsão de 72 h (`BayesianRidge`). |
| **Árvore de causas** | `app/engine/cross_diagnosis.py` | Camada 0 nominal → 1 clima espacial (DONKI) → 2 ambiente/fisiologia → 3 psicológico, só por exclusão. Linguagem de risco grave sempre escala para a Terra. |
| **Mapa de dor** | `app/engine/body_regions.py` | 25 regiões do corpo 3D; a dor relatada vira feature do ML e evidência na árvore. |
| **Acompanhamento** | `app/engine/followup_loop.py` | Cada alerta abre um caso: confirmação → ação → reavaliação com prazo (`OVERDUE`) → resolvido ou escalado por um humano. Casos resolvidos são imutáveis (HTTP 409). |
| **Nave–Terra** | `app/engine/earth_sync.py` | Pacotes *store-and-forward* e log de auditoria encadeados por SHA-256 (`GET /api/earth-sync/verify` detecta edição, remoção ou reordenação). |
| **Dados da NASA** | `app/engine/nasa_feeds.py` | DONKI (SEP, FLR, RBE) e JPL Horizons ao vivo, com cache e fallback (detalhes abaixo). |
| **Biofeedback psicológico** | `app/ml/psych_biofeedback.py` | Pondera desvios individuais em 6 diagnósticos e aciona o *Personal Crew Vault* (vídeos da família, áudios de amigos, sons da natureza e de animais, jogos de interesse), com alerta à Central em Terra. |
| **Agente de IA** | `app/agent/` | 16 tools, provedores Groq/Gemini e pipeline offline (detalhes abaixo). |

## Dados da NASA ao vivo

- **DONKI (`api.nasa.gov`, SEP / FLR / RBE):** janela de 7 dias, evento "ativo" se começou nas últimas 72 h. Cache de 30 min. Se um feed falhar (por exemplo FLR com 404 do lado da NASA), os outros continuam ao vivo e só o que falhou vem do cache. Sem rede, vale a última resposta boa e, sem nenhuma, a amostra curada `data/nasa_donki_sample.json`. Use uma chave própria (`NASA_API_KEY`): a `DEMO_KEY` permite só 10 requisições por hora por IP.
- **JPL Horizons (`ssd.jpl.nasa.gov/api/horizons.api`, sem chave):** distância real Terra–Marte (`COMMAND=499`) convertida em atraso de luz de ida e de ida e volta para os ambientes `transit` e `planetary_surface`. O trânsito usa a distância até Marte (destino) como pior caso; a estação orbital mantém a latência de referência do relé. Cache de 6 h e fallback em `data/nasa_horizons_sample.json`. O atraso alimenta o estado, o dossiê de telemedicina e a decisão entre tempo real e envio diferido.
- Um laço no `lifespan` atualiza DONKI e Horizons no startup e a cada `ASTRACARE_NASA_REFRESH_MIN` minutos.

## Agente de IA (`app/agent/`)

- **`tools.py`** — 11 tools clínicas: baseline, árvore de causas, contexto, ML com incerteza, auditoria de alertas, acompanhamento, continuidade nave–Terra, DONKI + Horizons, nutrição e hidratação, sono e humor, biofeedback psicológico.
- **`mission_tools.py`** — 4 tools encadeáveis (mais o ciclo completo), que só orquestram os serviços acima. A saída de cada uma decide a próxima:
  1. `schedule_smartwatch_exam`: agenda um exame periódico (`interval_minutes`) e/ou coleta agora (`trigger_now`). Tipos: `full_panel`, `cardio`, `cognitive_ctb`, `dosimetry`, `respiratory`, `metabolic`.
  2. `analyze_telemetry_and_diagnose`: cruza o payload com o baseline, os limites da NASA e o DONKI. Devolve `status` (NORMAL/WARNING/CRITICAL), `category` (NONE/PHYSICAL_ENVIRONMENTAL/PSYCHOLOGICAL), `probable_diagnosis`, `confidence_score` e `next_tools`.
  3. `trigger_central_alert`: só em CRITICAL ou em WARNING com prioridade PRIORITY/IMMEDIATE. Gera o alerta à tripulação, o pacote para os cirurgiões de voo e o registro de auditoria, com cooldown.
  4. `activate_psychological_stimuli`: só quando a categoria é PSYCHOLOGICAL, ou quando o astronauta pede.
  5. `run_monitoring_cycle`: a cadeia inteira de uma vez.
- **`llm_groq.py`** — Groq (API compatível com a OpenAI, via `httpx`, sem pacote extra), modelo padrão `qwen/qwen3.8-27b`. Faz várias rodadas de tool calls, esconde o raciocínio `<think>`, espera o `retry-after` curto do plano gratuito e, se o limite estourar depois que as tools rodaram, monta a resposta a partir delas.
- **`orchestrator.py`** — escolhe o provedor (`groq`, `gemini` via LangChain, ou offline). Para o Groq usa um prompt compacto e só as tools de `ASTRACARE_LLM_TOOLS`, porque o plano gratuito permite 8 mil tokens por minuto. Sem chave, sem rede ou com erro do provedor, o pipeline determinístico bilíngue (PT/EN) roda as mesmas tools; frases como "agendar exame cardio do Kenji a cada 30 min" disparam a cadeia.
- **`app/engine/smartwatch_scheduler.py`** — os exames agendados rodam a cadeia em segundo plano (`ASTRACARE_SCHEDULER_*`).

## Como executar localmente

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env   # opcional: chaves e ajustes
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

A porta 8000 é a que o proxy do Vite (`frontend/vite.config.js`) usa. Para o Gemini, instale também `requirements-llm.txt`.

## Variáveis de ambiente

Copie `backend/.env.example` para `backend/.env`. O arquivo é lido sozinho na inicialização (`app/config.py`), está no `.gitignore` e variáveis já definidas no sistema têm prioridade sobre ele.

| Variável | Para que serve | Padrão |
| --- | --- | --- |
| `ASTRACARE_LLM_PROVIDER` | `groq`, `gemini` ou `offline`. Vazio escolhe o primeiro com chave, começando pelo Groq | vazio |
| `GROQ_API_KEY` | Liga o Groq no chat | vazio |
| `ASTRACARE_GROQ_REASONING_FORMAT` | Esconde o raciocínio `<think>` do Qwen na resposta | `hidden` |
| `ASTRACARE_GROQ_RATE_LIMIT_RETRIES` / `ASTRACARE_GROQ_RATE_LIMIT_MAX_WAIT_S` | Novas tentativas em HTTP 429 e espera máxima, em segundos | `2` / `8` |
| `GEMINI_API_KEY` (ou `GOOGLE_API_KEY`) | Alternativa: Gemini via LangChain (`requirements-llm.txt`) | vazio |
| `ASTRACARE_LLM_MODEL` | Modelo do provedor escolhido | `qwen/qwen3.8-27b` (Groq) ou `gemini-2.5-flash` |
| `ASTRACARE_LLM_TOOLS` | Tools oferecidas ao LLM (lista separada por vírgula, ou `all`) | cadeia de monitoramento + DONKI/Horizons + sono e humor |
| `ASTRACARE_LLM_TOOL_RESULT_MAX_CHARS` | Corte do resultado de cada tool antes de voltar ao modelo | `1200` |
| `ASTRACARE_LLM_MAX_TOOL_ROUNDS` | Rodadas de tool calls encadeadas por mensagem | `5` |
| `ASTRACARE_LLM_TIMEOUT_S` | Timeout de cada chamada ao LLM, em segundos | `30` |
| `NASA_API_KEY` | Chave da api.nasa.gov para o DONKI | `DEMO_KEY` |
| `ASTRACARE_NASA_REFRESH_MIN` | Intervalo de atualização do DONKI e do Horizons, em minutos | `30` |
| `ASTRACARE_SCHEDULER_ENABLED` | Liga o laço dos exames agendados do smartwatch | `true` |
| `ASTRACARE_SCHEDULER_TICK_S` | Intervalo de verificação desse laço, em segundos | `30` |
| `ASTRACARE_ALERT_COOLDOWN_MIN` | Janela, em minutos, sem reenviar o mesmo alerta central | `30` |
| `ASTRACARE_STATE_DIR` | Pasta do ledger, dos casos e dos caches do DONKI e do Horizons | `backend/data` |

No frontend, a única variável é `VITE_API_BASE` (`frontend/.env.example`). Chaves secretas nunca entram lá, porque tudo que começa com `VITE_` vai para o navegador.

## Principais endpoints

| Grupo | Rotas |
| --- | --- |
| Estado e tripulação | `GET /api/state`, `GET /api/crew`, `POST /api/crew/{id}/select`, `/alert`, `/acknowledge`, `/stabilize`, `/measure` |
| Dor | `GET /api/body/regions`, `POST /api/crew/{id}/pain`, `DELETE /api/crew/{id}/pain/{region}` |
| ML e alertas | `GET /api/ml/baseline`, `/api/ml/context`, `/api/ml/validation`, `/api/ml/alerts` |
| Acompanhamento | `GET /api/followup/cases`, `POST /api/followup/{id}/confirm`, `/action`, `/reassess`, `/escalate` |
| Nave–Terra | `POST /api/earth-sync/package`, `/synchronize`, `GET /api/earth-sync/verify`, `/ledger`, `POST /api/telemedicine/dossier` |
| Psicológico | `GET /api/psych/evaluation`, `POST /api/psych/trigger`, `GET /api/psych/central-alerts` |
| NASA | `GET /api/nasa/space-weather?force=`, `GET /api/nasa/horizons?force=` |
| Agente | `POST /api/agent/chat`, `POST/GET/DELETE /api/agent/smartwatch…`, `POST /api/agent/analyze/{id}`, `POST /api/agent/cycle/{id}` |
| Simulação | `POST /api/scenario/{id}`, `POST /api/environment/{id}`, `POST /api/telemetry/next` |

A documentação interativa completa fica em `http://localhost:8000/docs`.

## Testes

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

71 testes, com as APIs externas simuladas:
- **Pilares:** quarentena e tendência do baseline, contexto sem causalidade, explicabilidade e travas de autonomia, ciclo de acompanhamento, cadeia de hash e fila offline.
- **Gerador, DONKI e árvore de causas:** incluindo limite de requisições e falha de um único feed.
- **JPL Horizons:** ao vivo, cache e fallback.
- **Agente:** cada tool, o encadeamento, o agendador e os endpoints.
- **Provedor Groq:** encadeamento, limite de tokens, seleção de tools e fallback offline.

## Limites conhecidos

- O ML é treinado no gerador calibrado, não em registros médicos reais. As métricas (≈ 99 % em dados sintéticos) são otimistas e não estimam desempenho clínico.
- As leituras do smartwatch são simuladas.
- O plano gratuito do Groq comporta cerca de uma pergunta encadeada por minuto.
