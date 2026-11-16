# Rotina Diária de Preservação e Autocuidado do Tripulante

Este documento define o modelo operacional e científico da **Rotina Diária de Preservação** dos astronautas em missões de longa duração. Ele serve como base direta de regras de negócio, métricas e fluxos de interface para o software de monitoramento autônomo de saúde.

---

## 1. Visão Geral: Por que a Rotina Diária é Vital?

No espaço profundo, a prevenção é a principal linha de defesa. Sem gravidade, sem luz solar natural (ciclo de 24h) e em ambiente confinado, o corpo humano sofre degradação silenciosa e cumulativa:
* **Músculos e ossos** atrofiam rapidamente se não forem estimulados todos os dias.
* **A percepção de sede diminui** no espaço (devido à subida de líquidos para a cabeça), aumentando drasticamente o risco de desidratação e pedras nos rins (cálculos renais).
* **O relógio biológico desregula**, gerando insônia, fadiga crônica e queda de atenção em operações críticas.

A **Rotina de Preservação** transforma o cuidado médico complexo em um **Checklist Diário Interativo** dividido em 3 turnos: **Despertar (Manhã)**, **Manutenção Ativa (Dia)** e **Recuperação (Noite)**.

---

## 2. Os 4 Pilares do Checklist Diário

### 2.1 Condicionamento Físico (Preservação Muscular, Óssea e Cardíaca)
* **Meta Padrão (Microgravidade / Estação / Nave):** `120 a 150 minutos/dia` divididos entre treino resistido (força) e aeróbico (cardio).
* **Meta em Gravidade Parcial (Base Lunar / Marciana) ou Rover:** `60 a 90 minutos/dia` (ajustado se houver caminhada espacial/EVA no dia).
* **O que o tripulante registra no app:**
  * [ ] Sessão Aeróbica concluída (Esteira / Bicicleta) — *Duração e Percepção de Esforço (Leve, Moderado, Intenso)*.
  * [ ] Sessão de Resistência/Força concluída — *Foco em membros inferiores e coluna*.
  * [ ] Alongamento e mobilidade articular pós-treino (alívio de dores lombares comuns na microgravidade).
* **Consequência de falha (Gatilho do Sistema):**
  * **1 dia sem treino:** Status **Amarelo (Atenção)** — Sugere sessão compacta de 45 min no dia seguinte.
  * **3+ dias sem treino:** Status **Vermelho (Risco de Descondicionamento)** — Alerta de perda acelerada de massa muscular e óssea; prioriza exercício na agenda da missão.

---

### 2.2 Hidratação e Nutrição Protetora (Prevenção Renal e Metabólica)
No espaço, os rins eliminam mais cálcio (que sai dos ossos). Se o astronauta beber pouca água, esse cálcio forma cálculos renais dolorosos que podem comprometer a missão.
* **Meta Padrão de Hidratação:** `2.000 ml a 2.500 ml/dia` (cerca de 8 a 10 bolsas de hidratação de 250 ml).
* **O que o tripulante registra no app:**
  * [ ] Contador rápido de bolsas de água consumidas (`+250 ml` por clique).
  * [ ] Consumo das 3 refeições principais planejadas.
  * [ ] Suplementação diária obrigatória de **Vitamina D** (essencial pois não há exposição solar direta).
  * [ ] Check visual rápido da urina pela manhã (Escala de cor de 1 a 5: *Clara/Hidratado* até *Escura/Desidratado*).
* **Consequência de falha (Gatilho do Sistema):**
  * **Hidratação < 60% da meta até as 16h:** Alerta **Amarelo** — Lembrete imediato para ingerir 500 ml de água nas próximas 2 horas.
  * **Urina escura + Hidratação < 50%:** Alerta **Vermelho (Risco Renal / Desidratação)** — Protocolo de reidratação imediata com eletrólitos e suspensão temporária de treinos intensos.

---

### 2.3 Sono e Ciclo Circadiano (Preservação Cognitiva e Alerta)
A falta de um nascer e pôr do sol naturais bagunça a produção de melatonina. A privação de sono aumenta erros operacionais e irritabilidade.
* **Meta Padrão de Sono:** `7 a 8,5 horas por noite` de sono efetivo.
* **O que o tripulante registra / sincroniza (via pulseira de actigrafia ou manual):**
  * [ ] Horas totais dormidas e quantidade de despertares noturnos.
  * [ ] Sensação ao acordar (Descansado, Regular, Cansado, Exausto).
  * [ ] Protocolo "Wind-down" (Desaceleração noturna): 45 min antes de dormir sem telas brilhantes e com luz do módulo ajustada para tom âmbar/quente.
* **Consequência de falha (Gatilho do Sistema):**
  * **Sono < 6h em 1 noite:** Status **Amarelo (Fadiga Leve)** — Recomenda um *Power Nap* (cochilo estratégico de 20 a 30 min) à tarde e atenção redobrada em tarefas manuais.
  * **Sono < 5h por 2+ noites seguidas:** Status **Vermelho (Fadiga Crítica)** — Alerta de risco cognitivo alto; recomenda não realizar atividades extraveiculares (EVA) ou manobras críticas sem revisão de outro tripulante.

---

### 2.4 Higiene Mental e Descompressão (Combate ao Isolamento e Confinamento)
O estresse acumulado em ambientes fechados afeta a imunidade, o sono e a convivência da equipe.
* **Meta Padrão:** `30 a 45 minutos/dia` de pausa desconectada de tarefas técnicas.
* **O que o tripulante registra no app:**
  * [ ] Check-in rápido de Humor e Energia (Escala visual rápida de 1 a 5: *Calmo, Focado, Ansioso, Irritado, Sobrecarregado*).
  * [ ] Pausa de Descompressão realizada (leitura, música, observação pela janela/cúpula, escrita no diário pessoal ou mensagem para a família).
  * [ ] Prática de respiração guiada (5 min) caso o nível de estresse esteja alto.
* **Consequência de falha (Gatilho do Sistema):**
  * **Humor "Sobrecarregado/Ansioso" por 2 dias:** Status **Amarelo** — O app abre automaticamente um guia interativo de respiração (Box Breathing 4-4-4-4) e sugere pausa de 20 min.
  * **Estresse Crítico + Isolamento prolongado:** Status **Vermelho** — Recomenda reorganização imediata da carga de trabalho do dia e sessão de apoio com a tripulação/protocolo de bem-estar.

---

## 3. Fluxo da Jornada Diária no Software (UX/UI)

Para que o astronauta use o sistema sem atrito (em menos de 2 minutos por turno), a tela de **Rotina de Preservação** deve funcionar em 3 blocos temporais:

| Turno | Duração no App | Ações do Astronauta | Feedback Imediato do Sistema |
| :--- | :--- | :--- | :--- |
| **1. Check-in Matinal (Ao acordar)** | ~45 segundos | • Confirma horas de sono (ou lê do sensor)<br>• Registra como acordou e cor da 1ª urina<br>• Toma suplemento de Vitamina D + 1ª bolsa de água | Calcula o **"Índice de Prontidão do Dia"** (Verde: Apto para qualquer missão / Amarelo: Ritmo moderado / Vermelho: Priorizar recuperação). |
| **2. Manutenção Ativa (Durante o dia)** | Cliques rápidos | • Cliques no botão `+250ml Água`<br>• Marca conclusão do treino físico<br>• Check de refeições realizadas | Atualiza as barras de progresso diárias e ajusta metas se o ambiente mudar (ex: se entrar em modo Rover/EVA, aumenta a meta de água). |
| **3. Fechamento Noturno (Antes de dormir)** | ~45 segundos | • Registra humor/estresse final do dia<br>• Marca se fez a pausa mental<br>• Ativa modo "Preparação para o Sono" | Gera o resumo de preservação do dia e exibe recomendações preventivas simples para a manhã seguinte. |

---

## 4. Adaptação da Rotina por Ambiente Operacional

O software deve alterar automaticamente os pesos da rotina conforme o ambiente selecionado pelo usuário:

1. **Estação Espacial / Nave em Trânsito (Microgravidade):**
   * **Prioridade Máxima:** Exercício físico rigoroso (2,5h) e controle de deslocamento de fluidos/visão.
2. **Rover (Exploração em Trânsito Terrestre Lunar/Marciano):**
   * **Prioridade Máxima:** Ergonomia/alongamento (espaço muito apertado), hidratação constante e monitoramento de fadiga/sono do motorista/operador.
3. **Base Planetária (Lua / Marte - Gravidade Parcial):**
   * **Prioridade Máxima:** Recuperação pós-EVA (caminhada externa), saúde respiratória (monitorar tosse/irritação por poeira lunar/marciana) e qualidade do sono.

---

## 5. Estrutura de Dados Sugerida para o Código (JSON / LocalStorage)

Esta estrutura serve de referência para os agentes de código implementarem o estado da rotina no Front-end:

```json
{
  "date": "2026-11-14",
  "environment": "SPACE_STATION",
  "readinessScore": 85,
  "status": "GREEN",
  "pillars": {
    "hydration": {
      "currentMl": 1750,
      "targetMl": 2500,
      "urineColorScale": 2,
      "vitaminDTaken": true
    },
    "exercise": {
      "aerobicMinutes": 45,
      "resistanceMinutes": 60,
      "targetMinutes": 120,
      "stretchingDone": true,
      "perceivedEffort": "MODERATE"
    },
    "sleep": {
      "hoursSlept": 7.2,
      "targetHours": 7.5,
      "quality": "GOOD",
      "windDownCompleted": true
    },
    "mental": {
      "mood": "FOCUSED",
      "stressLevel": 2,
      "decompressionBreakDone": true
    }
  }
}
```
