# Guia de Execução e Documentação do Projeto (Padrão NASA)

## Critérios de Avaliação dos Projetos

| Critério | O que significa | Como aplicar ao seu escopo (Saúde e Exploração Espacial) |
| --- | --- | --- |
| **Impacto** | Qual problema resolve e qual potencial de benefício possui | Mitigar riscos críticos à saúde física e comportamental dos astronautas (ex.: trombose venosa, SANS, perda óssea, hipóxia ou estresse em ambientes isolados) em missões de longa duração. |
| **Criatividade** | Originalidade, inovação e abordagem diferenciada | Propor soluções compactas, autônomas ou integradas (inspiradas em tecnologias como *Bio-Monitor*, *ACTIS* ou *Zero T2*) que otimizem massa, volume e autonomia da tripulação. |
| **Validade** | Viabilidade científica, técnica, funcional e lógica| Fundamentar a solução na fisiologia espacial (ex.: Tríade de Virchow, deslocamento cefálico de fluidos, ritmos circadianos) e nos protocolos médicos da NASA (como o *Modelo Médico Integrado* e *Medidas Padrão*).|
| **Relevância** | Quanto realmente responde ao desafio e utiliza os dados da NASA| Conectar diretamente a solução aos documentos oficiais analisados (ex.: *OCHMO-MTB-007*, *OCHMO-TB-016*, *NASA-STD-3001*, *Human Research Program*).|
| **Apresentação** | Clareza, organização, *storytelling* e capacidade de comunicar a solução| Estruturar a narrativa de forma lógica, objetiva e visualmente clara, demonstrando o valor da solução em poucos minutos.|

---
<br>

## Ciclo de Desenvolvimento e Mentoria

Use este fluxo de 6 etapas para validar e amadurecer a ideia antes de estruturar as respostas finais:

1. **ENTENDER** — Qual desafio? Qual problema? Para quem?


* *Foco:* Definir exatamente qual risco espacial (físico, médico ou comportamental) está sendo atacado e quem é o usuário (astronautas em trânsito profundo, tripulação da ISS/Artemis ou cirurgiões de voo em solo).


2. **QUESTIONAR** — O que precisa ser comprovado? Qual hipótese?


* *Foco:* Qual evidência garante que sua proposta funciona sem depender de comunicação em tempo real ou evacuação rápida para a Terra?


3. **PRIORIZAR** — O que cabe no tempo e gera maior valor?


* *Foco:* Focar nas funcionalidades essenciais que resolvem o problema central dentro das restrições de massa, volume e energia de uma espaçonave.


4. **TESTAR** — Como validar rapidamente dado, fluxo, modelo ou protótipo?


* *Foco:* Criar um fluxo de decisão, protótipo de interface, simulação de protocolo ou modelo de triagem baseado nos parâmetros fisiológicos e psicológicos da NASA.


5. **REFINAR** — O que cortar, melhorar ou explicar melhor?


* *Foco:* Eliminar complexidades desnecessárias para o usuário em situação de estresse ou baixa gravidade e deixar os dados técnicos mais intuitivos.


6. **COMUNICAR** — A equipe consegue contar problema $\rightarrow$ solução $\rightarrow$ impacto?


* *Foco:* Garantir que qualquer membro consiga explicar a proposta de ponta a ponta sem jargões confusos.



---
<br>

## 3. Perguntas-Chave para Destravar e Validar o Escopo

Utilize este checklist para formular suas respostas e garantir que não há lacunas no projeto:

* **Qual é exatamente o problema que vocês estão resolvendo?**
*(Ex.: Detecção precoce e manejo autônomo de condições médicas/comportamentais quando há atraso de até 22,5 minutos na comunicação com a Terra).*


* **Qual parte do desafio é obrigatória e qual é opcional?**
*(Ex.: Obrigatório = responder ao desafio usando dados oficiais da NASA e resolver um risco real; Opcional = recursos secundários que não cabem no MVP).*


* **Qual dado da NASA ou de parceiro sustenta a solução?**
(Ex.: Padrões NASA-STD-3001, relatórios OCHMO sobre trombose venosa e saúde comportamental, dados de experimentos como CIPHER, Standard Measures, WinSCAT ou estudos da CSA como ACTIS e Bio-Monitor).


* **Quem é o usuário e qual decisão ele precisa tomar?**
*(Ex.: O astronauta ou Oficial Médico da Tripulação [CMO] precisando decidir entre monitoramento, intervenção preventiva ou tratamento de emergência a bordo).*


* **O que vocês conseguem demonstrar de verdade até o prazo?**
*(Ex.: Um protótipo navegável, um painel de monitoramento, um protocolo automatizado de triagem ou uma arquitetura de sistema).*


* **Se tivessem metade do tempo, o que manteriam?**
*(O núcleo funcional que prova a validade técnica e o impacto da solução).*


* **Como provarão que a solução funciona?**
*(Cruzando as entradas/saídas do seu sistema com os limiares clínicos e operacionais documentados pela NASA).*


* **Qual é a história que vocês contarão em dois minutos?**
*(Um roteiro enxuto conectando o risco humano no espaço profundo à eficácia prática da solução).*



---
<br>

## 4. Diretrizes de Submissão e Apresentação

Para estruturar o texto final ou o roteiro de apresentação (*pitch*), siga exatamente esta ordem e boas práticas:

### Estrutura Narrativa Obrigatória

> **Problema $\rightarrow$ Solução $\rightarrow$ Uso de dados $\rightarrow$ Funcionamento $\rightarrow$ Impacto $\rightarrow$ Próximo passo**
> 
> 

### Boas Práticas de Execução

* **Mostre o caminho principal da solução;** evite depender de explicações longas.


* **Tenha plano B** para demo, vídeo ou *screenshots* (caso falhe a demonstração ao vivo).


* **Faça um ensaio curto** e identifique onde a narrativa perde força.
***

Abaixo encontra-se a documentação estruturada em Markdown, elaborada com base nas instruções e diretrizes oficiais fornecidas nas imagens para a submissão, descrição, uso de IA e demonstração do projeto no NASA Space Apps Challenge.

---
<br>

# Guia Oficial de Submissão, Documentação e Demonstração do Projeto

Este documento serve como referência passo a passo para a organização, estruturação e envio do seu projeto, cobrindo desde a descrição técnica até os requisitos de demonstração e uso de inteligência artificial.

---

## 5. Descrição Detalhada do Projeto e Campos do Formulário

* **Perguntas Orientadoras:** A secção de descrição do projeto deve detalhar de forma clara e objetiva:


* O que exatamente o projeto faz.


* Como ele funciona tecnicamente.


* Quais os benefícios que oferece.


* O que a equipa espera alcançar com a solução.


* Quais as ferramentas, linguagens de programação, hardware ou softwares foram utilizados no desenvolvimento.




* **Recursos Adicionais e Filtro Web:** Caso tenha criado um novo website para hospedar o projeto, é recomendado solicitar uma Classificação de Filtro Web (ex: *FortiGuard Web Filter*) para prevenir bloqueios de acesso por parte dos jurados. Preencha os campos obrigatórios selecionando a categoria adequada (educação, site/blog pessoal, referência ou aplicação web), indique "N/A" no campo *Company Name* e submeta o pedido.



---
<br>

## 6. Utilização de Dados da NASA e Agências Parceiras

* **Dados Abertos:** É permitida a utilização de quaisquer dados abertos no projeto.


* **Elegibilidade ao Global Award:** Para que a equipa seja elegível a um Global Award, é **obrigatório** utilizar pelo menos um dado ou recurso fornecido pela NASA.


* Recomenda-se fortemente também a integração de dados ou recursos das agências espaciais parceiras do evento.



---
<br>

## 7. Diretrizes para o Uso de Superinteligência (SI / IA)

* **Finalidade Permitida:** O uso de ferramentas de SI (como *machine learning*, chatbots, geração de imagens e LLMs) é autorizado para acelerar a inovação e a criatividade, mas **não** deve ser empregue para conceber a ideia inicial de como resolver o desafio.


* **Restrições de Identidade Visual:** Os conteúdos gerados por IA não podem utilizar, conter ou modificar elementos de design ou identidade visual da NASA, tais como logótipos, bandeiras ou identificadores de missões.


* **Obrigatoriedade de Transparência e Indicação:** Deve indicar claramente onde e como a SI foi aplicada:


* *Imagens e vídeos:* Devem incluir uma marca d’água visível a sinalizar a geração por SI.


* *Áudio:* Deve referir a geração por SI tanto na descrição como nos metadados.


* *Código e dados:* Devem especificar o uso/geração por SI na descrição e nos metadados.




* *Nota:* A pergunta sobre o uso de SI destina-se à recolha de dados internos e não é visualizada diretamente pelos jurados, embora estes possam verificar indicadores visuais, metadados ou textos descritivos para avaliar a originalidade e a execução.



---
<br>

## 8. Requisitos e Passo a Passo para o Envio do Projeto

* **Critérios de Elegibilidade:**
* Todos os elementos da equipa devem estar confirmados no mesmo Evento Local (em caso de lista de espera, contacte o *Local Lead* ou mude de evento).


* Todos os campos obrigatórios do formulário têm de estar preenchidos.


* **Todo o conteúdo do formulário deve ser redigido em inglês**.


* É proibida a inclusão de imagens, vídeos, áudios ou representações de menores de 18 anos.




* **Prazo Limite:** O botão *Submit for Judging* (Enviar para Avaliação) deve ser acionado antes das **23h59 de domingo, 15 de novembro**, no fuso horário do Evento Local.


* **Procedimento de Submissão:**
1. Marque a caixa de aceitação dos *Terms and Conditions*.


2. Marque a caixa *Confirm All Work is Original*.


3. Clique em *Submit for Judging* (o sistema impedirá o envio se faltarem secções obrigatórias).


4. Um banner de confirmação surgirá no topo da página. A submissão pode ser editada e reenviada livremente até ao fim do hackathon (apenas a última versão guardada será avaliada).





---
<br>

## 9. Dicas e Estruturação da Demonstração do Projeto (Demo)

* **Formatos Aceites:**
* **Vídeo:** Com duração máxima de **30 segundos**.


* **Apresentação de Slides:** Com um limite de **até 7 slides** (incluindo título e introdução).


* **Hospedagem:** Os ficheiros devem ser alojados externamente (YouTube, Google Drive, GitHub, OneDrive, Dropbox, etc.) garantindo acesso público, pois não é feito upload direto na plataforma. O vídeo deve conter legendas em inglês caso o áudio esteja noutro idioma.




* **Critérios de Avaliação:** O projeto será avaliado com base em cinco pilares: Impacto, Criatividade, Validade, Relevância e Apresentação.


* **Estrutura Recomendada para a Demo em Vídeo (30 segundos):**
* **** Apresentação pessoal e identificação da equipa.


* **** Contextualização do desafio escolhido e respetiva motivação.


* **** Divulgação do título do projeto e de um slogan (*tagline*) cativante.


* **** Explicação da solução, funcionamento, experiência do utilizador e integração dos dados abertos da NASA e agências parceiras.


* **[0:20–0:30]** Perspetiva de futuro e o potencial de impacto global da solução.




* **Estrutura Recomendada para a Demo em Slides (Até 7 slides):**
* Utilize uma tipografia legível, reduza o excesso de texto e aposte em recursos visuais fortes.


* Apresente imagens reais do protótipo e descreva claramente a experiência do utilizador.


* Demonstre de que forma os dados e tecnologias espaciais da NASA viabilizaram o projeto.


* Assegure que constam explicitamente o nome da equipa, dos elementos e o desafio selecionado.