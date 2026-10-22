# Biblioteca — Catálogo de Referências

**Última atualização:** 2026-09-23  
**Total de referências:** 15 artigos + 1 apostila (existentes) + novas referências em download

> Sistema de organização: os PDFs estão distribuídos em subpastas temáticas.  
> Para adicionar novos artigos: copie o PDF na subpasta correta e adicione uma linha neste catálogo.

---

## Estrutura de Pastas

```
Biblioteca/
├── 01_PID_Classico/          — Fundamentos, sintonia, implementação digital
├── 02_Redes_Neurais_Controle/ — Neuro-PID, PINN, RL para controle
├── 03_MPC_Preditivo/          — Model Predictive Control, controle preditivo
├── 04_Sistemas_Termicos/      — Trocadores, CSTR, sistemas de aquecimento
├── 05_Agentes_LangGraph/      — LLM agents, multi-agent, ControlAgent, PIDAgent
└── README.md                  — Este catálogo
```

---

## 📁 00 — Teses e Relatórios Técnicos do Projeto (PROIC/UESC)

| # | Arquivo | Título | Autor / Orientador | Ano | Descrição / Contribuição |
|---|---|---|---|---|---|
| **0** | [`../Artigos_Rascunhos/Tese.pdf`](../Artigos_Rascunhos/Tese.pdf) | **Contornabilidade, Saturação de Atuador e Trade-offs de Robustez no Controle PID Clássico de CSTRs Exotérmicos Altamente Não Lineares** | Gabriel Marques de Andrade (Orientador: Prof. Dr. Elilton Rodrigues Edwards) | 2026 | Relatório técnico-científico final PROIC/UESC/FAPESB/CNPq (Edital 34/2026). 39 páginas de fundamentação teórica rigorosa, modelagem fenomenológica CSTR, análise de Van Heerden, formulação de anti-windup clamping, identificação FOPTD, sintonia e construção da fronteira de Pareto contínua. |

---

## 📁 01 — PID Clássico

| # | Arquivo | Título | Ano | Palavras-chave | Notas |
|---|---|---|---|---|---|
| 1 | `APOSTILA-CONTROLE-PROCESSOS.pdf` | Apostila de Controle de Processos | — | PID, controle, processos | Material didático base |
| 2 | `Simple analytic rules for model reduction and PID.pdf` | Simple Analytic Rules for Model Reduction and PID Controller Tuning | 2003 | IMC, lambda-tuning, sintonia | Skogestad — referência central para IMC |
| 3 | `Using controller tuning formulae to improve performance.pdf` | Using Controller Tuning Formulae to Improve Performance | — | sintonia, desempenho, PID | Comparação de métodos |
| 4 | `PID TEMPERATURE CONTROL OF A CHEMICAL PROCESS.pdf` | PID Temperature Control of a Chemical Process | — | temperatura, processo químico, PID | Aplicação direta ao projeto |
| 5 | `Comparative study between a GA-tuned PID.pdf` | Comparative Study Between a GA-tuned PID and Classical PID | — | Algoritmo Genético, PID, otimização | Baseline de comparação evolutiva |

---

## 📁 02 — Redes Neurais para Controle

| # | Arquivo | Título | Ano | Palavras-chave | Notas |
|---|---|---|---|---|---|
| 6 | `NeuralNetworkBasedAdaptivePIDControllerofNonlinearHeatExchanger.pdf` | Neural Network Based Adaptive PID Controller of Nonlinear Heat Exchanger | Dubey & Gupta | 2020 | NN, PID adaptativo, trocador | Referência direta para Fase 4 |
| 7 | `Model predictive control based on neural networks for heat.pdf` | Model Predictive Control Based on Neural Networks for Heat Exchanger | — | — | MPC, redes neurais, calor | Híbrido MPC + NN |
| 8 | `Modeling and Control of Non-Linear CSTH Process using Hybrid.pdf` | Modeling and Control of Non-Linear CSTH Process using Hybrid | — | — | CSTH, não-linear, híbrido | Sistema similar ao CSTR do projeto |
| 9 | `PINN_Adaptive_PID_DataDriven_2025.pdf` | Data-Driven Adaptive PID Control Based on Physics-Informed Neural Networks | Ito & Wasa | 2025 | PINN, PID adaptativo, data-driven | arXiv:2510.04591 — PINN + PID em malha fechada |
| 10 | `CIRL_DeepRL_PID_CSTR_2024.pdf` | Control-Informed Reinforcement Learning for Chemical Processes | — | 2024 | RL, CSTR, deep RL, processo químico | arXiv:2408.13566 — RL com restrições de controle |
| 11 | ⚠️ *baixar manualmente* | Tuning of PID Controllers Using RL (TD3) for Nonlinear System Control | Bujgoi & Sendrescu | 2025 | TD3, RL, PID, biotecnologia | DOI: 10.3390/pr13030735 — Baixar em: https://www.mdpi.com/2227-9717/13/3/735/pdf |

> **⚠️ Download pendente (manual):** MDPI Processes — abrir o link acima no browser e salvar como `RL_TD3_PID_Tuning_Nonlinear_Bioprocess_2025.pdf`.

---

## 📁 03 — MPC e Controle Preditivo

| # | Arquivo | Título | Ano | Palavras-chave | Notas |
|---|---|---|---|---|---|
| 10 | `Robust Model Predictive Control of a Plate Heat Exchanger.pdf` | Robust Model Predictive Control of a Plate Heat Exchanger | — | MPC robusto, trocador de placas | Referência para MPC industrial |
| 11 | `Multiplexed Predictive Control of a Large Commercial Turbofan Eng.pdf` | Multiplexed Predictive Control of a Large Commercial Turbofan Engine | — | MPC, turbofan, multivariável | Aplicação industrial complexa |
| 12 | `Nonlinear modeling, estimation and predictive control in APMonitor.pdf` | Nonlinear Modeling, Estimation and Predictive Control in APMonitor | — | APMonitor, NMPC, estimação | Ferramenta: APMonitor/GEKKO |

---

## 📁 04 — Sistemas Térmicos

| # | Arquivo | Título | Ano | Palavras-chave | Notas |
|---|---|---|---|---|---|
| 13 | `PID Control of Heat Exchanger System.pdf` | PID Control of Heat Exchanger System | — | trocador, PID, temperatura | Aplicação simples de referência |
| 14 | `Internal Model Based PID Control of Shell and Tube.pdf` | Internal Model Based PID Control of Shell and Tube Heat Exchanger | — | IMC, casco-tubo, processo | Sintonia IMC em trocador real |
| 15 | `Design of PID Controller for controlling fluid temperature of.pdf` | Design of PID Controller for Controlling Fluid Temperature | — | temperatura, fluido, PID | Projeto de controlador prático |
| 16 | `A review of principles and applications of thermal control.pdf` | A Review of Principles and Applications of Thermal Control | — | revisão, controle térmico | Survey amplo — boa para intro do artigo |

---

## 📁 05 — Agentes LLM e Multi-Agente

| # | Arquivo | Título | Autores | Ano | Palavras-chave | Notas |
|---|---|---|---|---|---|---|
| 17 | `ControlAgent_LLM_Control_Design_2024.pdf` | ControlAgent: Automating Control System Design via Novel Integration of LLM Agents and Domain Expertise | Guo, Keivan, Syed et al. | 2024 | ControlAgent, LLM, multi-agent, PID | arXiv:2410.19811 — **referência central Fase 5** |
| 18 | `AgenticControl_MultiAgent_PID_LLM_2025.pdf` | AgenticControl: An Automated Control Design Framework Using Large Language Models | — | 2025 | AgenticControl, LLM, PID, JSON | arXiv:2506.19160 — validado em motor DC e pêndulo |
| 19 | ⚠️ *baixar manualmente* | PIDAgent: LLM-Based PID Tuning with RAG | Chen, Su, Zhu | 2026 | PIDAgent, RAG, CCDC | CCDC 2026 — sem arXiv. Salvar como `PIDAgent_LLM_RAG_PID_Tuning_2026.pdf` |

> **⚠️ Download pendente (manual):** PIDAgent — CCDC 2026, sem versão arXiv. Contatar autores (Northeastern University, China) ou acessar via acesso institucional UESC.


---

## 📚 Livros de Referência (não na pasta)

| Título | Autores | Ano | Relevância |
|---|---|---|---|
| *Process Dynamics and Control* (3ª ed.) | Seborg, Edgar, Mellichamp, Doyle | 2010 | ⭐⭐⭐ — Referência mestre do projeto |
| *Advanced PID Control* | Åström & Hägglund | 2006 | ⭐⭐⭐ — PID com anti-windup, filtros |
| *Modern Control Engineering* | Ogata | 2010 | ⭐⭐ — Base de controle clássico |

---

## 🔖 Como Adicionar Novos Artigos

1. Copie o PDF para a subpasta correta (`01_` a `05_`)
2. Adicione uma linha na tabela acima com: arquivo, título, ano, palavras-chave, notas
3. Adicione a entrada BibTeX em `Artigos_Rascunhos/Artigo_01.../references.bib`
4. Faça um fichamento rápido em `Projeto/Fase_1_Revisao_Bibliografica/`

---

## 🗝️ Palavras-chave Centrais do Projeto

`PID control` · `neural network PID` · `adaptive control` · `CSTR` · `nonlinear control`  
`LangGraph` · `multi-agent systems` · `LLM control` · `reinforcement learning PID`  
`Physics-Informed Neural Networks` · `PINN` · `gain scheduling` · `IAE` · `ITAE`
