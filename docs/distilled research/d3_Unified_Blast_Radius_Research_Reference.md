# Unified Research Reference

> This document merges the assignment, literature reviews, and GitHub repository research into a single reference intended for implementation.

## Table of Contents

1. AI Engineer Updated - Assignment
2. Literature Review on AI-Powered Blast Radius Analysis - ChatGPT
3. Blast Radius Analyzer Repositories - Gemini
4. AI Blast Radius Literature Review - Gemini
5. Top 50 Relevant Repositories - ChatGPT

---

# AI Engineer Updated - Assignment

# **TESTSIGMA — TAKE-HOME ASSIGNMENT AI Engineer**

|**ROLE**|AI Engineer|
|---|---|
|**DEPARTMENT**|Engineering|
|**DEADLINE**|5 days after receiving|

## **Part 1 — Context**

Testsigma is building the intelligence layer beneath agentic testing — a system that understands a running application semantically, connects it to product intent, and reasons about what's at risk when code changes. This assignment is the truest signal we know of for the work you'd actually do here: a working agent, built from scratch, that crawls a live application, ingests a product spec, builds a knowledge graph across three layers, and uses that graph to reason about real code changes.

This is not a coding test. It's a building test under realistic constraints — limited time, no scaffolding, your own choices on every dimension. We will read your code and your document with equal weight.

## **Part 2 — The Task**

Two parts. The JD describes them in summary; this is the detailed brief. **AI assistants are explicitly permitted** — we care about judgment, not keystrokes. Code and design document are weighted equally.

### **Part A — The Working System**

Build an agent that does all four of the following on a public web application of your choice (a real one — Amazon, GitHub, a public SaaS demo, anything with enough depth):

1. **Crawl.** A browser agent (browser-use, Playwright + LLM, your choice — your selection is part of the signal) explores the application autonomously and captures structured artifacts: DOM, screenshots, interaction transitions, screen relationships.

2. **Ingest.** A public PRD, README, product spec, GitHub wiki, or feature documentation you select. Parse it into a structured form your graph can use.

3. **Graph.** A Neo4j knowledge graph connecting three layers:

- **Requirements** — what was intended (from the PRD)

- **DOM / UI** — what was built (from the crawl)

- **Code** — how it was built (mapped from a public repository linked to the application)

The schema is yours to design. Justify your choices. Specifically: how do you model **absence** — the requirements that _should_ be testable but aren't reflected anywhere in the captured UI?

1. **Reason.** Given a real Pull Request in the public repository, your system outputs the **blast radius** : which UI elements are at risk, which discovered user flows are affected, which requirements lose coverage. The output must be readable by a non-engineer who understands the product but not your code.

### **Hard scope note**

**16 hours is not enough time to do all four of the above to equal depth.** That's deliberate. We want to see what you choose to invest depth in, and what you scope down — and we want you to _tell us_ in the design document, not hide it. A submission that goes deep on two layers and explicitly scopes the third beats a submission that does all three shallowly.

A working narrow slice with honest scope decisions is the strong submission. Three half-done layers is the weak one.

### **Part B — The Design Document**

Treat this as a document you would defend to engineers more senior than you. Be opinionated, show your trade-offs, name what you cut. Address each of the following at minimum:

1. **Agent decomposition —** what are the distinct stages of reasoning in your agent? Where are the boundaries? What is deterministic vs. LLM-driven, and why? We are not looking for a chain of prompts dressed up as an agent.

2. **Graph schema with justification —** your node and edge types, how they connect across the three layers, and specifically how you model absence. Justify your schema against a query you would need to run.

3. **Confidence handling under ambiguity —** when the agent isn't sure (the PRD describes a feature you can't find in the UI; the code change touches a function you can't map to a UI element), what happens? How is confidence represented? When does the system stop and ask a human?

4. **Eval approach —** how do you know your agent's output is right? If we ran your system 100 times on the same input, how would we know which runs were correct?

5. **Scope decisions —** what did you cut, what did you go deep on, and why? This is not optional. Submissions that present polished work without honest scope discussion will score lower on this dimension than submissions that admit and defend their cuts.

10.<sup>**What you would do with another week —**the three highest-value things you would build next, in order, with</sup> reasoning.

## **Part 3 — Deliverables**

- **Code** in a GitHub repository, runnable, with a README we can follow end-to-end

- **Design document** — PDF or Markdown, roughly 8–12 pages, diagrams welcome

- **Sample output** — for a real PR you select, the blast-radius report your system produces, in the form a non-engineer QA lead would actually read

- **A 5–10 minute Loom** walking us through the prototype running and the document

**Submission Format:** GitHub repository URL + PDF/Markdown document + Loom URL

**Submission Method:** Email to [HM email] with subject line [Candidate Name] — AI Engineer Assignment

---

# Literature Review on AI-Powered Blast Radius Analysis - ChatGPT

# Literature Review on AI-Powered Blast Radius Analysis

We surveyed key research (2015–2026) across the 23 topic areas listed.  Each **relevant paper** is summarized with its bibliographic details and key content, and we note how it could inform our system’s components.  (Citations are given to validated sources for claims.)

## Change Impact Analysis  

- **Kretsou et al. (2021)** – _Change Impact Analysis: A Systematic Mapping Study_. **Authors:** M. Kretsou, E.-M. Arvanitou, et al. Published in J. Syst. Softw. (2021). DOI:10.1016/j.jss.2020.110892. **PDF:** (ScienceDirect) – no free PDF. **ArXiv/GitHub:** n/a. **Citations:** ~50. **Area:** CIA (survey). **Problem:** Understand the state of CIA research and metrics. **Core Idea:** Mapped 111 papers on CIA, categorizing methods and quantified factors (instability, change-proneness, amount of change, changeability). **Architecture:** Systematic literature review. **Algorithms/Models:** N/A. **Data:** Academic papers (2010–2020). **Evaluation:** Qualitative mapping; identified over- and under-studied areas. **Strengths:** Broad coverage; distilled core metrics (e.g. instability). **Weaknesses:** No empirical evaluation on actual code, only literature analysis. **Limitations:** Focused on academic studies, may omit industrial practices. **Relevance:** Provides context for CIA concepts (metrics, benefits) useful for our Requirements and Impact components. **Action:** _Read_ – adopt its insights on CIA metrics and practical benefits, adapt by integrating those metrics into our blast radius scoring.

- **Abdurhman & Lee (2023)** – _FCP2Vec: Deep Learning-Based Approach to Software Change Prediction…_ Appl. Sci. 13(11):6453 (2023). **PDF:** [MDPI](https://doi.org/10.3390/app13116453). **ArXiv:** n/a. **GitHub:** n/a. **Citations:** ~6. **Area:** CIA via co-change. **Problem:** Predict which files co-change (impact scope) in large code. **Core Idea:** Treats a changelog as sequences (skip-gram Word2Vec) to embed files (“file commit patterns”), then predicts co-changes via nearest neighbors. **Architecture:** Unsupervised embedding (skip-gram) + kNN. **Algorithms/Models:** Word2Vec (skip-gram), kNN for recommendation. **Data:** 3 open-source projects’ commit logs (Git history for Vuze, Spring, Elasticsearch). **Evaluation:** Hit Ratio@K (recall of co-changed files). Achieves ~21% better recall than traditional dependency networks. **Strengths:** Scales to large codebases, learns from history automatically. **Weaknesses:** Requires rich historical data; only file-level (not semantic). **Limitations:** Evaluated on Java projects only; may not capture semantics of changes. **Relevance:** Useful for our Repository Analysis / Impact component (predicting affected code from PR). **Action:** _Adapt_ – use its embedding idea for recommending potentially affected components from commit diffs.

## Requirements Traceability  

- **Wang et al. (2024)** – _An empirical study on SOTA methods for requirements-to-code traceability link recovery_. J. King Saud Univ. Comp. Info. Sci., 36(6):102118 (2024). **DOI:**10.1016/j.jksuci.2024.102118. **PDF:** (Open access via ScienceDirect). **Citations:** 0. **Area:** Traceability (requirements-code). **Problem:** Lack of a benchmark comparing RC traceability methods. **Core Idea:** Systematic literature review (2018–2023) of methods for linking requirements to code, with an experimental replication on 13 datasets. **Architecture:** Review+empirical evaluation framework. **Algorithms:** Evaluated 6 SOTA methods (mostly IR-based and ML-based). **Models:** IR (CRT, TAROT, Fine-grained TLR, POS+IR), ML (Random Forest). **Data:** 13 standard traceability datasets (COEST, large industrial ones). **Evaluation:** Replicated methods, measured precision/recall. Findings: CRT, TAROT, FTLR work well on medium data; ConPos and TAROT good on large sets; RandomForest strong across the board. **Strengths:** First comparative benchmark in RC-TLR, open resources provided. **Weaknesses:** Only covers methods up to 2023; evaluation limited to preset datasets. **Limitations:** Focused on IR and basic ML, not neural methods. **Relevance:** Guides linking PRDs to code (our requirement linking component). **Action:** _Read_ – adapt insights on effective traceability features (TF-IDF, POS, etc.) and consider implementing TAROT or RandomForest as part of our link recovery.

## Software Knowledge Graphs  

- **Zou et al. (2021)** – _Software knowledge graph construction and Q&A technology based on big data_. _大数据_ (Big Data) 7(1):2021002 (Jan 2021). **Authors:** Y. Zou, M. Wang, B. Xie, Z. Lin. **DOI:**10.11959/j.issn.2096-0271.2021002. **PDF:** (no direct link; Chinese journal). **Citations:** unknown. **Area:** Software KGs. **Problem:** Building rich software project KGs from heterogeneous sources (code, docs, Q&A). **Core Idea:** Proposes a _code-centric knowledge model_ and a two-layer plugin framework to construct KGs and integrate Q&A. **Architecture:** Two-layer pipeline (data extraction plugins + Q&A service). **Algorithms:** Not specified (rule-based extraction inferred). **Models:** Ontology model defined in the paper. **Data:** Multi-source: code, issue reports, mailing lists, Q&A docs. **Evaluation:** Deployed KG in Apache projects and enterprises (qualitative). **Strengths:** Holistic integration of many data sources; deployed in real projects. **Weaknesses:** Details on extraction methods are sparse. **Limitations:** Lacks public dataset or code. **Relevance:** Offers a model for combining code and project artifacts into a KG (our Knowledge Graph component). **Action:** _Adapt_ – use its code-centric ontology and plugin idea to incorporate PRDs and UI artifacts into our KG.

- **Wang et al. (2023)** – _Application of knowledge graph in software engineering field: A systematic literature review_. Inf. Softw. Technol. 164:107327 (Dec 2023). **Authors:** L. Wang, C. Sun, C. Zhang. **DOI:**10.1016/j.infsof.2023.107327. **PDF:** (ScienceDirect). **Citations:** 0. **Area:** Software KGs (survey). **Problem:** No comprehensive survey on KGs in SE. **Core Idea:** SLR of 100+ papers (since 2017) on KGs for SE. Answered: “What knowledge is modeled?”, “How built/optimized?”, “Which methods & applications?”. **Architecture:** Literature mapping + analysis of content. **Algorithms:** N/A. **Models:** Summary of KGs and ontologies used across SE tasks. **Data:** 55 key papers selected. **Evaluation:** Qualitative insights; graphs (not provided to us). **Strengths:** Thorough review; identified research trends and gaps. **Weaknesses:** Chinese context, but published in English. **Limitations:** Survey only (no new method). **Relevance:** Summarizes state of Software KGs (background for Knowledge Graph Construction). **Action:** _Read_ – use its taxonomy of KG applications to identify relevant tasks (e.g., KG used in testing, vulnerability). Adapt its identified best practices (e.g. semantic relations used).

## Code Property Graphs (CPG)  

- **Saimbhi (2025)** – _Enhancing Software Vulnerability Detection Using CPGs and CNNs_. In ICCCIT 2025. **Author:** A. S. Saimbhi. **DOI:**10.1109/ICCCIT62592.2025.10928033. **ArXiv:** 2503.18175. **PDF:** [arXiv](https://doi.org/10.48550/arXiv.2503.18175). **Citations:** 0. **Area:** CPG / static analysis. **Problem:** Improve vulnerability detection beyond traditional static analysis. **Core Idea:** Builds Code Property Graphs (AST+CFG+DDG) for functions, and feeds them to CNNs specialized for graph data. **Architecture:** (1) Transform code→CPG; (2) Train CNN on CPG data. **Algorithms/Models:** Graph-based convolutional neural networks (GCNN). **Data:** Newly created dataset of functions labeled by vulnerability type (from open-source). **Evaluation:** Accuracy on function-level vulnerability detection tasks (ICCCIT paper format suggests ROC or accuracy, but details not in abstract). **Strengths:** Bridges graph modeling of code and deep learning. **Weaknesses:** Likely high computational cost; single author preprint (not community-validated). **Limitations:** Focuses only on security vulnerabilities, not general CIA. **Relevance:** Technique could be adapted for analyzing code graph structure in impact analysis (Repository Analysis). **Action:** _Consider_ – investigate using CPG + GNN for structural code similarity or risk scoring (if applicable to our backend component).  

## Graph-based Software Engineering / Ontologies / Knowledge Construction  

- **RepoDoc: Xu et al. (2026)** – _RepoDoc: A Knowledge Graph-Based Framework to Automatic Documentation Generation and Incremental Updates_. _ArXiv_ 2604.26523v1 (29 Apr 2026). **Authors:** D. Xu, M. Liu, X. Wang, J. Zhong, Z. Zheng. **DOI:** (ArXiv 2604.26523). **PDF:** [ArXiv](https://arxiv.org/abs/2604.26523). **GitHub:** [SYSUSELab/RepoDoc](https://github.com/SYSUSELab/RepoDoc). **Citations:** 0 (new). **Area:** Knowledge graphs / documentation (multi-topic: Knowledge Graph, Retrieval, Reasoning). **Problem:** Automated, up-to-date documentation at repository scale. **Core Idea:** Constructs a **Repository Knowledge Graph (RepoKG)** of code entities/relations; clusters modules; uses agent-based LLM queries to generate modular documentation; and propagates changes via graph traversal. **Architecture:** Three-phase pipeline + incremental update: (1) **KG Construction** from AST (entities and relations); (2) **Module Clustering** by graph-based functional cohesion; (3) **LLM Agent Generation** using graph queries (retrieving only relevant code). Plus **Semantic Impact Propagation** for updates. **Algorithms/Models:** AST parsing, graph clustering, topological sort (for update consistency), LLM (DeepSeek V3.2) as generator agents. **Data:** 24 diverse repos (Python, JS/TS, Java, C#, C/C++, PHP) in evaluation. **Evaluation:** Compared against doc baselines (RepoAgent, CodeWiki). Metrics: documentation **coverage** (APIs documented), completeness, time/token usage. RepoDoc improved coverage by 32.5% and completeness by 10.4%, with 3× faster generation and 85% fewer tokens; incremental updates 73% faster, 77% fewer tokens, 10.2% higher recall. **Strengths:** Combines static analysis (RepoKG) with LLMs for structured doc generation; addresses incremental updates explicitly. **Weaknesses:** Depends on LLM backend; metrics specific to docs, not directly to code behavior. **Limitations:** Early-stage (ArXiv), but code is available. **Relevance:** **Crucial** – demonstrates how a knowledge graph can underlie both understanding code/UI and generating text (report generation and documentation). Its impact propagation can inspire our Reasoning component. **Action:** _Adopt/Extend_ – adopt the RepoKG concept for linking code modules and adopt its impact propagation algorithms for our Blast Radius report. Use its GitHub tools if possible.

- **Han et al. (2025)** – _Retrieval-Augmented Generation with Graphs (GraphRAG)_. _ArXiv_ 2501.00309v2 (Jan 2025). **Authors:** H. Han, Y. Wang, H. Shomer, et al. **DOI:** 10.48550/arXiv.2501.00309. **PDF:** [ArXiv](https://arxiv.org/abs/2501.00309). **GitHub:** [GraphRAG repo](https://github.com/Graph-RAG/GraphRAG). **Citations:** 0 (new). **Area:** Graph retrieval + RAG. **Problem:** Integrating graph-structured data as the knowledge source in RAG frameworks. **Core Idea:** Surveys and proposes a **GraphRAG** framework: defines components (retriever, organizer, generator) specialized for graph data. Reviews GraphRAG for multiple graph types (text, knowledge, social, planning graphs). **Architecture:** Conceptual (survey): query processor → graph retriever → organizer → generator. **Algorithms/Models:** Discusses graph embedding (GraphSAGE, GNN), query planning, LLM integration; no single model. **Data:** Domains: Infrastructure graphs, scene graphs, etc. **Evaluation:** None (survey). **Strengths:** Comprehensive overview of how to combine KGs/graph DBs with LLM retrieval, including multi-hop reasoning. **Weaknesses:** No empirical results (conceptual survey). **Limitations:** Very new; primarily high-level. **Relevance:** Provides the theory of using a **Knowledge Graph as a retrieval source for an LLM (i.e. GraphRAG)**. This directly inspires using the Product KG to feed context to LLM for explanation. **Action:** _Read_ – adopt its components (Retriever, Organizer, Generator) design for our Graph Retrieval and Report Generation. Adapt its insights on graph-based retrieval to query our KG effectively.

- **Lewis et al. (2020)** – _Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks_. NeurIPS 2020. **Authors:** P. Lewis, E. Perez, et al. **DOI:**10.48550/arXiv.2005.11401. **PDF:** [ArXiv](https://arxiv.org/abs/2005.11401) / [NeurIPS](https://papers.nips.cc/paper/2020/hash/9671512a5befcf305f4e0b735974b262-Abstract.html). **Citations:** ~2000 (high-impact). **Area:** RAG (text-based). **Problem:** LLMs lack up-to-date or precise world knowledge; hallucinate. **Core Idea:** Introduces _RAG_ models that combine a seq2seq LLM (parametric) with a non-parametric memory (external retriever over Wikipedia) for generation. Two variants: retrieve same passages for all tokens vs. per-token retrieval. **Architecture:** Seq2seq Transformer (BART) + Dense Passage Retriever indexing Wikipedia. At generation, retrieve relevant docs to condition LLM. **Algorithms/Models:** BART / DPR. **Data:** Wikipedia + standard QA tasks (Natural Questions, TriviaQA, etc.). **Evaluation:** Achieved SOTA on open-domain QA; found RAG produces more factual, diverse text than pure LLM. **Strengths:** Pioneering RAG approach, open-sourced. **Weaknesses:** Retrieval limited to text corpus; not graph-structured. **Limitations:** Large compute; retrieval latency. **Relevance:** Conceptual foundation for _Retrieval-Augmented Generation_. Suggests how to augment LLM with evidence (in our case, from the product KG). **Action:** _Adapt_ – use the idea of retrieving contextual evidence (via knowledge graph) for justifying our blast radius explanations.

## Knowledge Graph Construction / Ontology / Knowledge Fusion / Autonomous Crawling  

- **Peshevski et al. (2025)** – _AI Agent-Driven Framework for Automated Product Knowledge Graph Construction in E-Commerce_. First GOBLIN Workshop on KG Tech (2025). **Authors:** D. Peshevski, R. Stojanov, D. Trajanov. **ArXiv:** 2511.11017 (Nov 2025). **DOI:**10.48550/arXiv.2511.11017. **PDF:** [ArXiv](https://doi.org/10.48550/arXiv.2511.11017). **Citations:** 0. **Area:** Autonomous agents / KG construction. **Problem:** Manually building KGs for product data is slow and schema-bound. **Core Idea:** Uses _LLM-based agents_ to fully automate KG construction from unstructured product descriptions (e.g. e-commerce data). Three-agent pipeline: Ontology creation/expansion, ontology refinement, KG population. No predefined schema is needed; agents handle semantics via LLM reasoning. **Architecture:** Multi-agent LLM framework (prompt-based): one agent designs ontology (classes/relations), another refines schema, a third populates KG from text. **Algorithms/Models:** GPT-style LLMs (not specified); agent orchestration. **Data:** Real-world dataset of air conditioner product descriptions. **Evaluation:** Measures coverage (97% of relevant properties captured) and low redundancy. **Strengths:** Scalability, semantic coherence without hard rules, minimal schema overhead. **Weaknesses:** Depends on LLM correctness; domain limited (only products). **Limitations:** Preliminary (workshop), no code public (that we saw). **Relevance:** Shows how autonomous agents (LLMs) can crawl and extract information into a KG (Crawling, KG Construction, Ontology Design). Suggests using LLMs to populate our Product KG from docs. **Action:** _Consider_ – apply agent-based KG population to PRDs and UI docs (we may adapt its agent prompts). Treat it as a model to fuse heterogeneous docs into our graph (knowledge fusion).

- **Aleti et al. (2026)** – _Trustworthy AI Software Engineers_. _ArXiv_ 2602.06310v1 (Feb 2026). **Authors:** A. Aleti, B. Ray, R. Hoda, S. Chen. **PDF:** [ArXiv](https://arxiv.org/abs/2602.06310). **Citations:** 0. **Area:** AI Agents for SE (vision/trust). **Problem:** Defining the role and trustworthiness of AI agents as software engineers. **Core Idea:** Presents a vision of AI coding agents as team members in SE; identifies dimensions of trustworthiness (technical quality, transparency, fairness, epistemic humility, ethical alignment). **Architecture:** Conceptual discussion (no system built). **Algorithms:** N/A. **Data:** N/A. **Evaluation:** N/A (conceptual). **Strengths:** Frames critical questions about AI agents replacing/cooperating with humans; calls for “ethics-by-design” in SE tools. **Weaknesses:** No empirical validation. **Limitations:** Broad; not specific to blast radius but informs design. **Relevance:** Highlights that any autonomous AI module (e.g. for impact analysis) must be trustworthy and auditable – which motivates our Explainable AI component. **Action:** _Read_ – use its trustworthiness dimensions to guide how we present blast radius evidence (transparency, provenance). It suggests rigorous evaluation strategies for AI code assistants.

## GUI/DOM Understanding  

- **Tang et al. (2025)** – _A Survey on (M)LLM-Based GUI Agents_. _ArXiv_ 2504.13865v2 (Apr 2025). **Authors:** F. Tang, H. Xu, et al. (Zhejiang Univ/Microsoft Research Asia). **PDF:** [ArXiv](https://arxiv.org/abs/2504.13865). **Citations:** 0 (new). **Area:** GUI Agents (multimodal LLM). **Problem:** Automating complex GUI tasks (web/mobile/desktop) with AI. **Core Idea:** Surveys the rise of AI-driven GUI agents, analyzing their architectures and components. Identifies four components: (1) **Perception:** multimodal understanding of UI (text+vision); (2) **Exploration:** building knowledge of UI via internal/external info; (3) **Planning:** reasoning for task execution; (4) **Interaction:** generating actions with safety controls. **Architecture:** N/A (survey). **Algorithms:** Discusses OCR, DOM parsing, LLMs, RL for GUI tasks. **Data:** Various GUI benchmarks (not in abstract). **Evaluation:** Categorizes and critiques existing evaluation strategies. **Strengths:** Comprehensive taxonomy; highlights LLMs revolutionizing interface automation. **Weaknesses:** No new model. **Limitations:** Survey covers wide domain; our focus is narrower (DOM understanding). **Relevance:** The _Perception_ component is relevant to parsing UIs/dom (for User Experience linking). Insights on combining text and visual cues can help interpret UI pages and DOM elements in our product graph. **Action:** _Adapt_ – use its identified perception techniques (e.g. text+vision parsing) when ingesting UI docs or screenshots. Its discussion of knowledge operation and planning may inspire how to “traverse” user flows in the KG.

## Static Code Analysis  

- **Salih & Sarhan (2025)** – _A Systematic Survey on LLMs for Static Code Analysis_. ARO (Koya Univ.) 13(1): [2025]. **Authors:** H.A. Salih, Q.I. Sarhan. **DOI:**10.14500/aro.12082. **PDF:** [Journal](https://aro.koyauniversity.org/index.php/aro/article/view/2082). **Citations:** 0. **Area:** Static analysis + LLM. **Problem:** Explore how LLMs can aid static code analysis tasks. **Core Idea:** Reviews recent works applying LLMs (GPT, CodeBERT, etc.) to detect bugs, vulnerabilities, and code smells in source code. **Architecture:** Literature survey. **Algorithms:** Discusses various LLM applications (fine-tuning, few-shot), metrics and tools. **Data:** Published papers on LLM for code analysis. **Evaluation:** Tabulates tasks, advantages, limitations of each approach. **Strengths:** Identifies trends (LLMs handle semantics and context better than traditional static analyzers). **Weaknesses:** Broad summary, not a dataset or new technique. **Limitations:** Survey oriented; quickly outdated in fast-moving field. **Relevance:** Conveys that modern static analysis can leverage LLMs for explainable insights. This supports our need to make analysis explainable (by using LLM interpretations). **Action:** _Read_ – note which static analysis tasks (e.g. vulnerability, type errors) LLMs excel at. Adapt those methods to interpret code changes in pull requests.

## Repository Mining  

- **Romero-Arjona et al. (2026)** – _The Rise of Language Models in Mining Software Repositories: A Survey_. ACM JACM 37(4):111 (Aug 2026). **Authors:** M. Romero-Arjona, S. Barakat, A.B. Sánchez, S. Segura (Sevilla Univ.). **DOI:** (not yet published in this text). **PDF:** [ArXiv](https://doi.org/10.48550/arXiv.2604.00787). **Citations:** 0. **Area:** MSR + LLM (survey). **Problem:** How Transformer LLMs are changing Mining Software Repositories. **Core Idea:** Comprehensive survey of 85 papers on applying LMs/LLMs to MSR tasks. Examines usage trends, data sources, tasks (commit classification, issue analysis, code summary, etc.) and proposes a taxonomy. **Architecture:** Survey methodology. **Algorithms:** Mostly Transformer-based (BERT, GPT variants, CodeBERT). **Data:** Open-source repositories (GitHub, etc.), commit messages, code, issues. **Evaluation:** Meta-analysis (no new experiments). **Strengths:** Up-to-date (2023–2026), covers broad trend of LLM in SW engineering. **Weaknesses:** Overviews only; does not give domain-specific guidance. **Limitations:** Only published works (may miss industry practices). **Relevance:** Highlights cutting-edge ML methods on repository data. Informative for how to preprocess and query repo content for our Analysis module (Repository Mining component). For example, shows feasibility of natural language processing on commit logs, which relates to FCP2Vec and PR analysis. **Action:** _Read_ – use its taxonomy to align our Repository Mining with popular tasks (e.g. commit message classification, code summarization). Consider its observations about reproducibility and data preparation.

## Explainable AI  

- **Arora et al. (2025)** – _Explainable AI Techniques for Software Development Lifecycle: A Phase-specific Survey_. (In press; arXiv 2505.07058). **Authors:** L. Arora, S.S. Girija, A. Raj, et al. (Google). **DOI:**10.48550/arXiv.2505.07058. **PDF:** [ResearchGate/arXiv](https://doi.org/10.48550/arXiv.2505.07058). **Citations:** 0 (new). **Area:** XAI in SE (survey). **Problem:** AI models in software engineering are black boxes; lack XAI. **Core Idea:** Surveys XAI methods (LIME, SHAP, concept-based, attention, counterfactuals, examples) applied across SDLC phases (requirements through maintenance). Reports most research is in maintenance (68% XAI work) and gaps in earlier phases. **Architecture:** Survey. **Algorithms:** Enumerates explanation techniques (model-agnostic and model-specific). **Data:** Literature (33 references). **Evaluation:** Qualitative discussion of technique suitability by phase. **Strengths:** First broad survey of XAI for software engineering. **Weaknesses:** No new experiments or system. **Limitations:** Quickly outdated in fast ML field. **Relevance:** Directly informs our **Explainable AI** component: which XAI methods to use for linking PR changes to outputs. For example, counterfactual or attention explanations may be used to highlight why a component is in the blast radius. **Action:** _Read_ – borrow its mapping of XAI techniques to SE tasks. Adapt methods (e.g. use LIME or SHAP on any ML predictions we use, ensure we provide concrete evidence/support for our report).

## Human-in-the-Loop AI  

- **Wu et al. (2022)** – _A Survey of Human-in-the-Loop for Machine Learning_. Future Gener. Comp. Syst. 135:364 (Oct 2022). **Authors:** X. Wu, L. Xiao, et al. **DOI:**10.1016/j.future.2022.05.014. **PDF:** [ScienceDirect Preview](https://www.sciencedirect.com/science/article/pii/S0167739X22001790). **Citations:** 560 (by 2025). **Area:** HITL in ML. **Problem:** Pure ML often requires too much data/training; incorporating human knowledge can improve efficiency and accuracy. **Core Idea:** Surveys HITL approaches from a data perspective: categorizes works into (1) data-centric (human annotates/improves data), (2) model-centric (human intervenes in training), (3) system design (interactive ML systems). **Architecture:** Survey. **Algorithms:** Not new, but summarizes various interactive learning frameworks, active learning, weak supervision. **Data:** Numerous references. **Evaluation:** Discussion of strengths/weaknesses of HITL in CV, NLP, etc. **Strengths:** Comprehensive categorization (data vs. model vs. system). **Weaknesses:** Broad ML focus, not SE-specific. **Limitations:** Survey – no new ML model. **Relevance:** Suggests our system could involve users (developers) in the loop for validating or guiding analysis (e.g. by giving feedback on identified blast radius). Highlights how to integrate user feedback to refine models. **Action:** _Consider_ – design our report-generation interface to allow developer input (e.g. confirming impacts), and revisit findings; adapt active learning to improve impact predictions.

## Regression Test Selection  

- **Plyusnin et al. (2025)** – _Targeted Test Selection (T-TS) Approach in CI_. _ArXiv_ 2509.10279v1 (Sept 2025). **Authors:** P. Plyusnin, A. Antonov, et al. (T-Technologies). **DOI:** (arXiv 2509.10279). **PDF:** [ArXiv](https://arxiv.org/abs/2509.10279). **Citations:** 0. **Area:** Regression Test Selection (RTS). **Problem:** Running full test suites on every CI commit is costly. **Core Idea:** Proposes **Targeted Test Selection (T-TS)** – an ML method that represents a commit as a “bag-of-words” of changed files plus cross-file features, avoiding heavy coverage maps. Deployed in industry. **Architecture:** ML pipeline: feature extraction (file changes, code analysis), train classifier to predict which tests to run. **Algorithms:** Gradient boosting (likely, or other classifier – not detailed in abstract). **Models:** ML classifier (internally proprietary). **Data:** Both open-source and large private repositories. **Evaluation:** In production CI: T-TS ran only ~15% of tests, cut test time by ~85%, and still detected >95% of failures. **Strengths:** Highly practical; significant savings in a real system. **Weaknesses:** Proprietary (full details not published), unknown generality. **Limitations:** Specific to the T-TS implementation (not open). **Relevance:** Demonstrates ML-based change impact on testing (a form of blast radius analysis for tests). It shows the feasibility of predicting affected components (tests here). **Action:** _Adapt_ – use its data representation idea (commit as changed-file tokens) for modeling blast impact. If available, consider contacting authors for more details; otherwise use as inspiration for our impact scoring.

## Summary of Papers by Component

We group the above (and related) works by architecture component:

- **Crawling / Data Collection:** Peshevski (2025) shows AI agents for **autonomous crawling and KG population** from product pages. (Also Wu’s HITL survey implies combining human web queries.)
- **Documentation Parsing:** RepoDoc (Xu et al.) provides **RepoKG construction from code** and LLM-based documentation generation, which parallels parsing PRDs into KG.
- **Repository Analysis:** Romero (2026) and FCP2Vec (Abdurhman 2023) apply LMs and embeddings on repo artifacts to find patterns (commit/bug prediction).
- **Knowledge Fusion / Ontology:** Peshevski (2025) and Zou (2021) address **KG construction/fusion** – Peshevski merges product data via agents; Zou builds a code-centric KG for project data.
- **Identity Resolution:** (No direct paper found. Standard ER techniques from data science might be used to merge duplicated artifacts in the KG.)
- **Knowledge Graph:** RepoDoc, Zou, Wang (2023), Peshevski all describe building software KGs.
- **Graph Retrieval:** Han (2025) details the **GraphRAG** framework, teaching how to retrieve from KGs; Lewis (2020) provides the baseline RAG.
- **Reasoning:** Aleti (2026) and Arora (2025) highlight _trust and explainability_ issues in AI (ensuring reasoning is auditable). GUI Agents (Tang 2025) cover _planning_ in interface tasks.
- **Report Generation:** RepoDoc uses LLM agents to generate and update documentation; Arora (2025) emphasizes producing explainable decisions (which our report must do).
  
## Comparison Table of Papers

| Paper (Year)          | Area(s)                    | Approach                    | Data      | Key Result                          |
|-----------------------|----------------------------|-----------------------------|-----------|-------------------------------------|
| Kretsou et al. (2021) | CIA (survey)               | Systematic mapping of 111 papers | lit review | Enumerates CIA metrics (instability, etc.) |
| Abdurhman & Lee (2023) | CIA / Co-change          | Skip-gram embeddings (FCP2Vec) | 3 Java repos | +21% recall vs dependency network |
| Wang et al. (2024)    | Traceability (REQ→Code)    | SLR + experiments (IR & ML)    | 13 datasets | RandomForest & TAROT work best   |
| Zou et al. (2021)     | SW Knowledge Graph        | Code-centric KG model + plugin framework | Apache repos | Deployed in practice             |
| Wang et al. (2023)    | SW Knowledge Graph        | SLR of 55 papers           | lit review | Taxonomy of KG methods in SE      |
| Xu et al. (2026)      | Doc Generation / KG       | RepoKG + LLM agents | 24 repos | +32% API coverage; 3× speed up |
| Han et al. (2025)     | GraphRAG                   | Survey & framework        | lit review | GraphRAG conceptual model         |
| Lewis et al. (2020)   | RAG                        | Dense retriever + BART   | Wikipedia/Q&A | SOTA QA; factual generation     |
| Peshevski et al. (2025) | KG Construction/Agents   | LLM agents for ontology/KG | Product descriptions | 97% property coverage |
| Tang et al. (2025)    | GUI/DOM Agents           | Survey of LLM-based GUI agents | lit review | Defines perception & planning components |
| Salih & Sarhan (2025) | Static Analysis + LLMs    | Survey of LLMs for code     | lit review | XAI can aid traditional static analysis |
| Saimbhi (2025)        | CPG + Vulnerability        | CPG + CNN (GraphConvNet) | New vuln. dataset | Basis for graph-based vulndet |
| Romero-Arjona et al. (2026) | MSR + LLM         | SLR of 85 papers | lit review | Taxonomy of LLMs applied to MSR  |
| Arora et al. (2025)   | XAI in SE                 | Survey XAI methods by SDLC phase | lit review | Most XAI in maintenance, few in reqts |
| Wu et al. (2022)      | Human-in-Loop (HITL)      | Survey of HITL ML approaches | lit review | Categorizes data/model/system HITL |
| Aleti et al. (2026)   | AI Agents for SE (Trust)  | Vision on AI agents as engineers | vision paper | Defines trust dimensions         |
| Plyusnin et al. (2025)| Regression Test Selection | ML-based test predictor (T-TS) | Industrial CI data | Runs 15% tests, catches 95% failures |

## Top Papers (Priority)

Based on relevance to our Blast Radius Analyzer, we rank the top 15 (rather than 30 for brevity):

1. **RepoDoc (Xu et al. 2026)** – Introduces the _RepoKG_ and graph-based doc generation. (Adopt: central KG idea; relevant for Documentation and Impact)
2. **Han et al. (2025), GraphRAG Survey** – Defines Graph-RAG framework (Adapt: informs our retrieval component)
3. **Romero-Arjona et al. (2026), MSR+LLM Survey** – Shows LLM uses in repo analysis (Read: guides our repository mining)
4. **Arora et al. (2025), XAI SE Survey** – Survey of XAI methods (Read: for explainable report)
5. **Wu et al. (2022), HITL Survey** – Human-in-loop ML (Read: integrate developer feedback)
6. **Aleti et al. (2026), Trustworthy AI** – Vision on AI agents in SE (Read: design trust aspects of tool)
7. **Plyusnin et al. (2025), T-TS** – ML-driven regression test selection (Adapt: similar ML for impact prediction)
8. **Wang et al. (2024), RC-TLR** – Empirical study of linking requirements-to-code (Read: use its methods for req-code links)
9. **Saimbhi (2025), CPG + CNN** – Vulnerability detection via CPGs (Consider: CPG for code graph analysis)
10. **Salih & Sarhan (2025), LLM+Static Survey** – LLMs in static code analysis (Read: how LLMs can interpret code)
11. **Tang et al. (2025), GUI Agents Survey** – LLM-driven GUI automation (Adapt: UI perception insights for UX)
12. **Peshevski et al. (2025), AI Agents for KG** – LLM agents build e-commerce KG (Adapt: multi-agent KG building approach)
13. **Zou et al. (2021), SW KG Q&A** – Code-centric KG framework (Adopt: foundational KG schema)
14. **Wang et al. (2023), KG in SE Survey** – SLR on Software KGs (Read: high-level overview of SE KGs)
15. **Lewis et al. (2020), RAG** – The classic RAG model (Adapt: basis for retrieval-augmented explanation)

(Others like Kretsou (2021) and Abdurhman (2023) are important background but rank slightly lower; all listed papers are valuable.)

## Research Gaps

Our search highlights several gaps for this architecture:

- **Integrated Semantic Linking:** No existing system fully connects **requirements, UI flows, and source code** in a unified knowledge graph for impact analysis. Most works focus on one or two artifact types (e.g. code→code, code→req, or code documentation). Our _evidence-backed product KG_ addresses this gap directly.
- **Explainable Change Analysis:** Few works generate human-readable explanations of change impact. Most CIA/RAG works produce raw predictions without structured justification. We must innovate by combining XAI and GraphRAG for **explainability** in the blast radius report.
- **LLM-Aided Static Analysis:** While surveys note LLMs in static analysis, concrete systems for LLM-assisted CIA are scarce. We can pioneer by leveraging LLMs (as in RepoDoc and RAG) to reason about graph-structured code changes.
- **Continuous Update / Incremental Learning:** RepoDoc’s incremental doc updating is novel; similar techniques for live CI (dynamic PR analysis) are lacking. Our architecture’s focus on “continual crawling/monitoring” is addressing an open problem.
- **Human-in-the-Loop Interfaces:** Few tools allow developers to guide or correct automated impact analysis. Integrating human feedback loops (as HITL research suggests) remains unexplored in CIA.
- **Unified Ontology:** There is no standard ontology for software artifacts linking UI components, requirements, and code. Building or adopting an appropriate ontology (inspired by Peshevski’s and Zou’s models) is an open challenge.

## Recommended Reading Order

1. **RepoDoc (Xu et al. 2026):** Most directly relevant (KG + documentation).  
2. **GraphRAG Survey (Han et al. 2025):** Framework for graph-RAG, guiding retrieval design.  
3. **Requirements Traceability (Wang et al. 2024):** Techniques for linking PRDs to code.  
4. **KG in SE Survey (Wang et al. 2023):** Overview of KGs and use-cases.  
5. **Software KG Construction (Zou et al. 2021):** Practical KG modeling/architecture.  
6. **Regression Test ML (Plyusnin et al. 2025):** Template for ML-based impact prediction.  
7. **XAI in SE (Arora et al. 2025):** Methods to explain AI outcomes.  
8. **HITL Survey (Wu et al. 2022):** Best practices to involve developers.  
9. **AI Agents KG (Peshevski et al. 2025):** Inspires autonomous KG building.  
10. **LLM in MSR (Romero-Arjona et al. 2026):** Current LLM uses on repos.  
11. **GUI Agents Survey (Tang et al. 2025):** Insights on UI understanding.  
12. **Static Analysis + LLM (Salih 2025):** Role of LLMs in code analysis.  
13. **AI Agents Trust (Aleti et al. 2026):** Consider trust in our agents.  
14. **FCP2Vec (Abdurhman 2023):** Example of change prediction via embeddings.  
15. **Original RAG (Lewis 2020):** Foundation for retrieval-augmented explanation.

Additional papers from our list can be consulted as needed for specific components.  

**Sources:** Key points and citations are drawn from the papers listed above. Each cited excerpt supports our summary of the papers’ content.

---

# Blast Radius Analyzer Repositories - Gemini

# **Architectural Blueprint and Component Analysis for an AI-Powered Blast Radius Analyzer**

The engineering of an autonomous, AI-powered Blast Radius Analyzer represents a highly complex intersection of disparate computer science domains. To successfully crawl live web applications, parse unstructured product requirements, construct an Evidence-backed Product Knowledge Graph, and perform graph-based impact analysis on pull requests, a system must seamlessly orchestrate web automation, document parsing, static code analysis, and advanced graph retrieval architectures.  
An exhaustive technical analysis of the open-source ecosystem reveals that constructing these subsystems from scratch is entirely unnecessary. The open-source community provides production-grade, highly active repositories that solve the foundational challenges of Abstract Syntax Tree (AST) querying, hierarchical Knowledge Graph generation, probabilistic entity resolution, and agent-computer interfacing. The following report systematically deconstructs these repositories to formulate a comprehensive implementation blueprint for the Blast Radius Analyzer.

## **Top 50 Repositories Ranked by Relevance**

The following structured assessment ranks the fifty most relevant open-source projects for the specified architecture. The ranking prioritizes repositories that directly solve sub-problems within crawler automation, parsing, graph construction, static analysis, and agentic pull request evaluation1.

| Rank | Repository Name | Primary Domain | Core Utility for Blast Radius Analyzer |
| :---- | :---- | :---- | :---- |
| 1 | microsoft/graphrag | Knowledge Graph | Hierarchical community detection and graph retrieval pipeline. |
| 2 | joernio/joern | Code Analysis | Construction of Code Property Graphs (CPGs) for impact tracing. |
| 3 | docling-project/docling | Document Parsing | Translating PRDs, wikis, and PDFs into structured knowledge. |
| 4 | ast-grep/ast-grep | Static Analysis | Tree-sitter based structural code search for localized impact. |
| 5 | unclecode/crawl4ai | Web Crawling | LLM-friendly web crawling producing RAG-ready Markdown. |
| 6 | HKUDS/LightRAG | Graph Retrieval | Dual-layer (vector and graph) retrieval for dynamic architectures. |
| 7 | browser-use/browser-use | UI Understanding | Playwright-based autonomous agents for UI and DOM analysis. |
| 8 | qodo-ai/pr-agent | PR Analysis | LLM-based automated pull request review and explainability. |
| 9 | All-Hands-AI/OpenHands | AI Agents | Autonomous agent-computer interface (ACI) for repository tasks. |
| 10 | moj-analytical-services/splink | Entity Resolution | Probabilistic linkage bridging product requirements to source code. |
| 11 | skyvern-ai/skyvern | UI Understanding | Computer vision-based autonomous web workflow automation. |
| 12 | princeton-nlp/SWE-agent | AI Agents | Automated GitHub issue resolution and software engineering tasks. |
| 13 | lavague-ai/LaVague | Web Agents | Web agent framework parsing DOMs into actionable tasks. |
| 14 | crytic/slither | Static Analysis | Reference implementation for AST-based vulnerability traversal. |
| 15 | langchain-ai/langchain | LLM Framework | Foundational orchestration for RAG and agentic workflows. |
| 16 | run-llama/llama\_index | Knowledge Integration | Data framework bridging structured and unstructured software data. |
| 17 | BerriAI/litellm | AI Gateway | Unified API proxy for orchestrating multiple LLM providers. |
| 18 | Aider-AI/aider | AI Agents | Git-native terminal pair programming agent architecture. |
| 19 | langgenius/dify | App Framework | Visual workflow orchestration for connecting LLM nodes. |
| 20 | openai/codex | AI Agents | Containerized, sandboxed execution environment for code analysis. |
| 21 | logspace-ai/langflow | Pipeline Builder | UI for visualizing GraphRAG and multi-agent pipelines. |
| 22 | infiniflow/ragflow | RAG Engine | Deep document understanding with complex chunking strategies. |
| 23 | lobehub/lobe-chat | Explainable UI | Chat interface framework for surfacing blast radius reports. |
| 24 | embedchain/embedchain | RAG Framework | Memory layer abstraction for application context. |
| 25 | deepset-ai/haystack | RAG Framework | Orchestration for advanced retrieval augmented generation. |
| 26 | mindsdb/mindsdb | AI Database | Integrating AI models directly with underlying data sources. |
| 27 | Cinnamon/kotaemon | RAG Chat | Open-source RAG UI for interacting with documentation. |
| 28 | songquanpeng/one-api | LLM Gateway | Key management and load balancing for high-volume LLM calls. |
| 29 | labring/FastGPT | KG App Platform | Knowledge-based platform for deploying question-answering systems. |
| 30 | nomic-ai/gpt4all | Local LLMs | Local execution of models for sensitive repository data. |
| 31 | comfyanonymous/ComfyUI | Pipeline Builder | Node-based workflow execution (reference for visual pipelines). |
| 32 | chatchat-space/Langchain-Chatchat | Local RAG | Offline RAG pipeline for highly secure codebase analysis. |
| 33 | go-skynet/LocalAI | Inference | OpenAI-compatible API for localized model deployment. |
| 34 | flairNLP/flair | NLP Framework | Base entity extraction for parsing software requirements. |
| 35 | xenova/transformers.js | Web Inference | Running LLM inference inside browser-based report viewers. |
| 36 | netease-youdao/QAnything | Enterprise RAG | Cross-modal Q\&A architecture for mixed software assets. |
| 37 | h2oai/h2ogpt | Private LLM | Privacy-first chat interface for proprietary codebases. |
| 38 | pathwaycom/llm-app | Data Pipelines | Real-time syncing with dynamic GitHub and Jira data sources. |
| 39 | stitionai/devika | AI Agents | Autonomous software developer architecture. |
| 40 | sola-st/repairagent | AI Agents | Autonomous bug repair agent evaluation framework. |
| 41 | Forethought-Technologies/AutoChain | Agent Orchestration | Lightweight, extensible framework for testing AI agents. |
| 42 | LAION-AI/Open-Assistant | Conversational AI | Chat-based interactions with third-party software systems. |
| 43 | Mintplex-Labs/anything-llm | Knowledge App | Desktop and Docker app with built-in RAG and agent builders. |
| 44 | ParisNeo/lollms-webui | Multi-modal UI | Interface for interacting with varying code and image inputs. |
| 45 | OpenBMB/UltraRAG | RAG Framework | Low-code framework building complex RAG pipelines. |
| 46 | Agenta-AI/agenta | LLMOps | Prompt management and evaluation for the PR analysis agents. |
| 47 | 0hq/WebGPT | Client Inference | WebGPU-based inference for offline code reasoning. |
| 48 | 23blocks-OS/ai-maestro | Agent Skills | Orchestrator providing code graph queries to sub-agents. |
| 49 | 2dogsandanerd/ClawRag | Vector Integration | Combines Docling document processing with ChromaDB. |
| 50 | BoundaryML/baml | Prompt Engineering | Strongly typed framework bridging LLM output to backend logic. |

## **Exhaustive Repository Technical Analysis**

The following subsections provide a rigorous deconstruction of the most critical repositories. Each analysis details the metadata, technical stack, architectural patterns, and the precise methodology required to integrate the repository into the overarching Blast Radius Analyzer architecture.

### **Crawl4AI**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | unclecode/crawl4ai |
| **GitHub URL** | github.com/unclecode/crawl4ai |
| **Stars** | \~73.8k1 |
| **Forks** | \~7.6k1 |
| **License** | Apache-2.01 |
| **Last Updated** | Active (2026)12 |
| **Primary Language** | Python, HTML14 |
| **Maintainer** | unclecode1 |
| **Installation Complexity** | Low (pip install crawl4ai or Docker)1 |
| **Project Status** | Highly Active1 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | LLM-friendly web crawler extracting structural data into Markdown. |
| **System Architecture** | Asynchronous execution pipeline wrapping headless browsers. |
| **Folder Structure** | Python modules containing strategies for chunking and extraction. |
| **Important Modules** | AsyncWebCrawler, JsonXPathExtractionStrategy, PruningContentFilter. |
| **Technologies Used** | Python asyncio, Playwright. |
| **Database** | Caching layer enabled via CrawlerRunConfig11. |
| **Parsing Libraries** | Heuristic HTML parsers, XPath, CSS selectors. |
| **Graph Technologies** | Generates node-ready semantic clusters via hierarchical chunking. |
| **LLM Framework** | LLM Extraction Strategies via OpenAI-compatible endpoints13. |
| **Agent Framework** | None natively, functions as a tool for external agents13. |

The architectural patterns present in Crawl4AI provide a foundational reference for the autonomous website crawler subsystem. The repository achieves high performance by utilizing an asynchronous architecture built on Python's asyncio and Playwright, enabling the concurrent crawling of modern Single Page Applications (SPAs)1. The implemented algorithms prioritize noise reduction, utilizing heuristic-based filtering mechanisms such as the PruningContentFilter to strip irrelevant DOM elements before they consume valuable LLM context windows11. Furthermore, the repository implements cosine clustering for semantic document filtering and topic-based chunking, ensuring the output is perfectly formatted for Retrieval-Augmented Generation (RAG) pipelines14.  
The exact components that can be directly reused include the AsyncWebCrawler core and the LLM-friendly Markdown extraction pipelines, which are essential for traversing live web applications to map user flows1. When building the data ingestion layer, the LLMExtractionStrategy and JsonXPathExtractionStrategy files should be studied first, as they demonstrate how to pass specific instructions to an LLM to refine the extraction of UI elements11. A notable limitation of the repository is its heavy reliance on underlying browser binaries via Playwright, which can introduce instability in strict, air-gapped Docker environments or Kubernetes clusters requiring extensive proxy configurations1. Despite this limitation, the repository is highly recommended as a direct dependency for the initial stage of constructing the Evidence-backed Product Knowledge Graph.

### **Browser-use**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | browser-use/browser-use |
| **GitHub URL** | github.com/browser-use/browser-use |
| **Stars** | 105.2k16 |
| **Forks** | 11.5k17 |
| **License** | MIT16 |
| **Last Updated** | Active (2026)16 |
| **Primary Language** | Python (99.2%)18 |
| **Maintainer** | browser-use organization19 |
| **Installation Complexity** | Low (uv pip install browser-use)17 |
| **Project Status** | Highly Active19 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Enables AI agents to autonomously control web browsers. |
| **System Architecture** | Decoupled agent logic and browser session contexts. |
| **Folder Structure** | /skills, /open-source, core Python library modules17. |
| **Important Modules** | BrowserSession, Agent, ChatBrowserUse. |
| **Technologies Used** | Python \>= 3.11, asyncio, Playwright17. |
| **Database** | Persistent filesystem memory for session management18. |
| **Parsing Libraries** | Custom accessibility tree extraction. |
| **Graph Technologies** | None natively. |
| **LLM Framework** | Provider-agnostic via ChatBrowserUse (Anthropic, OpenAI, Google)18. |
| **Agent Framework** | Internal Agent class orchestrating tasks via a system prompt18. |

The browser-use repository solves the critical problem of dynamically mapping complex, authenticated user interfaces that static crawlers cannot penetrate. The architectural pattern separates the BrowserSession context from the autonomous Agent logic, allowing multiple LLM-driven agents to operate concurrently on isolated browser instances17. The core algorithm relies on extracting an accessibility tree from the live DOM, compressing the visual layout into a token-efficient semantic representation that allows the LLM to deduce where to click, type, or navigate18. This design idea—translating a visual DOM into a structured semantic tree—is a pattern worth borrowing for the UI Understanding phase of the Blast Radius Analyzer.  
Direct reuse of the Python library is highly recommended for mapping interactive user flows and extracting stateful UI components. The source files defining the Agent and ChatBrowserUse abstractions should be studied first, as they reveal how to handle provider-prefixed model IDs and inject custom system messages without overriding the default browser control instructions17. The primary limitation of this approach is inference latency; because every action requires a sequential LLM call to evaluate the accessibility tree, it is significantly slower than static DOM parsing18. Consequently, browser-use is recommended as a direct dependency specifically for the deep UI Analysis and dynamic flow extraction subsystems, supplementing the faster static crawling mechanisms.

### **Docling**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | docling-project/docling |
| **GitHub URL** | github.com/docling-project/docling |
| **Stars** | 63.5k20 |
| **Forks** | 4.5k20 |
| **License** | MIT20 |
| **Last Updated** | Active (2026)5 |
| **Primary Language** | Python5 |
| **Maintainer** | IBM Research (docling-project)21 |
| **Installation Complexity** | Low (pip install docling)5 |
| **Project Status** | Highly Active5 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Unified document parsing for generative AI ecosystems. |
| **System Architecture** | Multi-modal processing pipeline outputting standard representations. |
| **Folder Structure** | Modular converters for PDF, HTML, Markdown, and visual media. |
| **Important Modules** | DocumentConverter, DoclingDocument, ProvenanceItem. |
| **Technologies Used** | Python 3.10+, PyTorch, OCR, Audio ASR. |
| **Database** | None natively (exports to lossless JSON/Markdown)5. |
| **Parsing Libraries** | Custom layout analysis, table structure, and reading order engines. |
| **Graph Technologies** | Ecosystem includes docling-graph for KG generation23. |
| **LLM Framework** | Integrates Visual Language Models (VLMs) like GraniteDocling5. |
| **Agent Framework** | Exposes MCP server and integrates with LangChain/LlamaIndex5. |

The Docling repository provides an unparalleled architecture for ingesting the vast array of unstructured formats that comprise product documentation. The system architecture is built around a unified, expressive representation format known as the DoclingDocument, which acts as a normalized schema for data extracted from PDFs, Word documents, PowerPoint presentations, and images5. The most valuable algorithm implemented within Docling is its provenance tracking mechanism. The ProvenanceItem schema meticulously records the exact physical location—including page number, bounding box (bbox), and character span—of every extracted data point, tying the semantic text back to its physical origin24. This design idea is critical for generating explainable Blast Radius Reports, as it allows the final AI agent to explicitly cite the exact location in a Product Requirements Document (PRD) that justifies an impact warning.  
The DocumentConverter module can be directly reused as the universal ingestion engine for all documentation parsing5. Developers should first study the data models defining the DoclingDocument and the recent architectural proposals for a generalized ProvenanceType union, which expands tracking beyond spatial layouts to temporal media like video timestamps24. While the core parsing engine is highly robust, deploying the advanced Visual Language Model (VLM) features or the Optical Character Recognition (OCR) engines requires significant computational resources, leading to the distribution of heavily tagged container images (e.g., CUDA 13.0 variants)22. Docling is strongly recommended as a direct dependency for the Requirements Traceability and Documentation Parsing subsystems.

### **ast-grep**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | ast-grep/ast-grep |
| **GitHub URL** | github.com/ast-grep/ast-grep |
| **Stars** | 15.1k10 |
| **Forks** | 41610 |
| **License** | MIT10 |
| **Last Updated** | Active (2026)10 |
| **Primary Language** | Rust (94.8%)10 |
| **Maintainer** | ast-grep organization10 |
| **Installation Complexity** | Low (via npm, pip, brew, or cargo)10 |
| **Project Status** | Highly Active10 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | High-performance structural code search and AST rewriting. |
| **System Architecture** | Multi-threaded AST traversal engine utilizing Tree-sitter. |
| **Folder Structure** | Rust crates (crates/cli), rule configuration directories (rules/). |
| **Important Modules** | YAML rule engine, Model Context Protocol (MCP) server. |
| **Technologies Used** | Rust, Tree-sitter10. |
| **Database** | None natively. |
| **Parsing Libraries** | Tree-sitter language bindings (C, Java, Python, TypeScript, etc.)10. |
| **Graph Technologies** | Abstract Syntax Tree (AST) navigation. |
| **LLM Framework** | None natively in the core, but integrates via the ast-grep-mcp server26. |
| **Agent Framework** | Provides agent skills (e.g., Claude Code plugins) for autonomous search25. |

The ast-grep repository introduces a paradigm shift in static code analysis by allowing developers and AI agents to query codebases using isomorphic syntax patterns rather than abstract graph query languages or brittle regular expressions. The architecture utilizes the Tree-sitter parsing library to generate an Abstract Syntax Tree (AST), over which ast-grep executes multi-threaded structural matching algorithms10. The system allows for the definition of complex relational constraints—such as verifying if a matched node resides inside, precedes, or follows another node—entirely via YAML configurations10. This design provides an incredibly token-efficient mechanism for Large Language Models to explore repository architectures without ingesting massive raw file contexts26.  
The core binary, the YAML rule engine, and specifically the experimental Model Context Protocol (MCP) server (ast-grep-mcp) can be directly reused to form the backbone of the Static Code Analysis subsystem10. By equipping an AI agent with the ast-grep MCP server, the agent can dynamically write search rules, test them against the AST, and map the precise call graphs associated with a modified function in a pull request25. When studying the repository, engineers should focus on the YAML rule configuration schemas and the MCP server implementation logic, as these represent the primary interfaces for AI integration26. While ast-grep is profoundly fast, its limitation lies in cross-file data-flow tracking, as ASTs inherently represent single-file syntactic structures rather than global semantic dependencies. Nonetheless, ast-grep is recommended as a direct dependency for structural search and localized Call Graph Construction.

### **Joern**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | joernio/joern |
| **GitHub URL** | github.com/joernio/joern |
| **Stars** | 3.3k29 |
| **Forks** | 43029 |
| **License** | Apache-2.029 |
| **Last Updated** | Active (2026)29 |
| **Primary Language** | Scala (98.1%)29 |
| **Maintainer** | joernio (industry partners and researchers)29 |
| **Installation Complexity** | High (requires JDK 21, sbt, C++ compilation toolchains)29 |
| **Project Status** | Active (Migrating to Flatgraph)29 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Vulnerability discovery via Code Property Graph (CPG) analysis. |
| **System Architecture** | Multi-language frontends parsing to a unified graph database. |
| **Folder Structure** | Language-specific AST generators (astgen-monorepo)31. |
| **Important Modules** | javasrc2cpg, ghidra2cpg, CPGQL interactive shell. |
| **Technologies Used** | Scala 3, JVM. |
| **Database** | Flatgraph (Custom columnar NoSQL graph storage)29. |
| **Parsing Libraries** | Custom language parsers translating to CPG specifications. |
| **Graph Technologies** | Code Property Graphs (fusing AST, CFG, and PDG). |
| **LLM Framework** | None natively. |
| **Agent Framework** | None natively. |

The Joern repository provides a masterclass in deep, semantic static analysis through the construction of Code Property Graphs (CPGs). A CPG mathematically fuses the Abstract Syntax Tree (AST), Control Flow Graph (CFG), and Program Dependence Graph (PDG) into a single, unified data structure29. The architectural pattern involves language-specific frontends that parse source code and emit intermediate representations, which are then loaded into Flatgraph, a highly optimized, columnar NoSQL graph database written in Scala29. The implemented algorithms allow for complex data-flow tracking, semantic reachability, and taint analysis, enabling queries that can track how an arithmetic expression in one function propagates to a memory allocation call elsewhere in the codebase33.  
While the theoretical depth of Joern is unmatched for analyzing software architecture, direct reuse in a lightweight, LLM-driven Blast Radius Analyzer is challenging. The reliance on the JVM, the steep learning curve of the Scala-based domain-specific query language, and the massive computational overhead required to generate CPGs present significant architectural friction29. Consequently, Joern is recommended strictly as a reference implementation. The design ideas defining how control flow and data flow can be mathematically represented as graph edges should be borrowed to inform the schema design of the overarching Product Knowledge Graph.

### **Microsoft GraphRAG**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | microsoft/graphrag |
| **GitHub URL** | github.com/microsoft/graphrag |
| **Stars** | 34.7k3 |
| **Forks** | 3.7k3 |
| **License** | MIT3 |
| **Last Updated** | Active (2026)3 |
| **Primary Language** | Python (88.4%)3 |
| **Maintainer** | Microsoft Research3 |
| **Installation Complexity** | Moderate (pip install graphrag \+ environment/API configuration)3 |
| **Project Status** | Highly Active3 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Enhancing LLM reasoning via knowledge graph memory structures. |
| **System Architecture** | Multi-stage indexing pipeline generating hierarchical graphs. |
| **Folder Structure** | Workspaces containing .env and settings.yaml for pipeline configs35. |
| **Important Modules** | Indexing pipeline, Global Search, Local Search. |
| **Technologies Used** | Python, OpenAI/Azure API integrations. |
| **Database** | Agnostic (can emit to standard graph or relational formats). |
| **Parsing Libraries** | LLM-driven entity and relationship extraction. |
| **Graph Technologies** | NetworkX, hierarchical graph clustering. |
| **LLM Framework** | OpenAI, Azure OpenAI35. |
| **Agent Framework** | Orchestrates internal prompting pipelines for data extraction. |

The GraphRAG architecture pioneered by Microsoft Research represents a fundamental evolution in how large language models interact with private datasets. Instead of relying purely on vector similarity—which fails when answering global questions that require synthesizing information across multiple documents—the system uses the LLM to extract a dense network of entities and relationships3. The most crucial algorithm implemented is the Leiden community detection algorithm, which partitions the massive knowledge graph into hierarchical communities36. By generating textual summaries for each community, the system can perform a "Global Search" that reasons across the entire dataset simultaneously35.  
The graph extraction pipelines and the distinct query routing mechanisms (specifically the bifurcation of global and local search strategies) can be directly reused for constructing the Evidence-backed Product Knowledge Graph35. Engineers should study the prompt tuning guides and the pipeline configuration mechanics, as tuning the LLM extraction prompts is necessary for accurately identifying software-specific entities like "API Endpoints" or "UI Components"3. The primary limitation of Microsoft's GraphRAG is the extreme computational cost and time required for the indexing phase, as every document chunk must be processed by the LLM to extract relationships3. Because of this, it is recommended as a direct dependency for the initial baseline knowledge graph construction, but may require supplementation for real-time incremental updates.

### **LightRAG**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | HKUDS/LightRAG |
| **GitHub URL** | github.com/HKUDS/LightRAG |
| **Stars** | 5.3k39 |
| **Forks** | 19839 |
| **License** | MIT4 |
| **Last Updated** | Active (2026)39 |
| **Primary Language** | Python4 |
| **Maintainer** | HKUDS (Zirui Guo)4 |
| **Installation Complexity** | Low (pip install lightrag-hku)37 |
| **Project Status** | Highly Active40 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Fast, scalable, and incremental knowledge graph RAG framework. |
| **System Architecture** | Dual-layer architecture managing vector embeddings and graph structures. |
| **Folder Structure** | Abstracted storage backends (llm/llama\_index\_impl.py, etc.)40. |
| **Important Modules** | Query routers, incremental graph merger, storage abstractions. |
| **Technologies Used** | Python 3.10+, LlamaIndex integration4. |
| **Database** | MongoDB, PostgreSQL (pgvector/Apache AGE), Neo4j, Oracle 23ai40. |
| **Parsing Libraries** | Document chunking and entity extraction via LLMs. |
| **Graph Technologies** | Set merging algorithms, directional multi-hop traversals4. |
| **LLM Framework** | OpenAI, Ollama, Hugging Face, LiteLLM40. |
| **Agent Framework** | None natively, functions as a retrieval backend. |

LightRAG directly addresses the computational bottlenecks inherent in Microsoft's GraphRAG by implementing an architecture optimized for rapid adaptation to dynamic data. The system utilizes a dual-layer architecture that maintains both a vector database for semantic similarity and a graph database for complex semantic dependencies4. The most innovative algorithmic approach is its incremental update mechanism. When new documentation or code is analyzed, LightRAG generates a localized graph of the new data and utilizes set merging algorithms to integrate it directly into the global graph, bypassing the need for a total index rebuild4. This pattern is essential for a Blast Radius Analyzer, which must rapidly ingest the delta of a pull request without pausing for hours of re-indexing.  
The abstracted storage layer and the five-mode query routing system (local, global, hybrid, naive, mix) represent components that can be directly reused4. Specifically, the backend implementations that allow the system to utilize PostgreSQL as a one-stop solution for Key-Value storage, vector storage (via pgvector), and graph storage (via Apache AGE) provide immense architectural simplicity for enterprise deployments40. Engineers should study the implementation of the mix retrieval mode, which merges traditional text chunk retrieval with global graph relationship contexts to yield the most comprehensive answers4. LightRAG is highly recommended as a direct dependency for the Graph Construction Pipeline and Graph-based Retrieval subsystems, serving as a highly optimized alternative to Microsoft GraphRAG.

### **Splink**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | moj-analytical-services/splink |
| **GitHub URL** | github.com/moj-analytical-services/splink |
| **Stars** | Not explicitly enumerated in source, widely adopted43 |
| **Forks** | Not explicitly enumerated43 |
| **License** | MIT43 |
| **Last Updated** | Active (2026)43 |
| **Primary Language** | Python43 |
| **Maintainer** | UK Ministry of Justice (moj-analytical-services)43 |
| **Installation Complexity** | Low (pip install splink\[duckdb\])43 |
| **Project Status** | Highly Active43 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Scalable probabilistic data linkage and entity resolution. |
| **System Architecture** | Statistical modeling engine executing over distributed SQL backends. |
| **Folder Structure** | Backend-specific implementation modules (DuckDB, Spark, Postgres). |
| **Important Modules** | Fellegi-Sunter model implementation, interactive visualization suite. |
| **Technologies Used** | Python 3.9+, SQL. |
| **Database** | DuckDB, Apache Spark, PostgreSQL43. |
| **Parsing Libraries** | None natively (operates on pre-parsed tabular data). |
| **Graph Technologies** | Outputs linked clusters that can form graph edges43. |
| **LLM Framework** | None natively. |
| **Agent Framework** | None natively. |

The Splink repository solves a profoundly difficult problem within the Knowledge Fusion subsystem: probabilistic entity resolution. When building a product knowledge graph, an architectural component might be referred to as the "User Authentication Module" in a PRD, but as auth\_controller.ts in the source code. Splink provides the statistical engine to link these disparate records without requiring a unique identifier43. The architecture implements the Fellegi-Sunter mathematical model for record linkage, utilizing unsupervised learning algorithms (specifically Expectation-Maximization) to train the linkage models without requiring human-labeled training datasets43.  
The probabilistic matching engine can be directly reused to construct the edges between the software requirements nodes and the source code nodes within the overarching graph. The ability to execute this logic natively in Python using in-memory databases like DuckDB, or scaling up to Apache Spark for massive repositories, provides excellent architectural flexibility43. The primary limitation is that Splink operates optimally on datasets with multiple, non-correlated columns (e.g., name, date, location), rather than single columns containing a "bag of words"43. Therefore, the data extracted by Docling and ast-grep must be properly structured into distinct metadata columns before being passed to Splink. It is recommended as a direct dependency for the Entity Resolution subsystem.

### **PR-Agent (Qodo Merge)**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | qodo-ai/pr-agent |
| **GitHub URL** | github.com/qodo-ai/pr-agent |
| **Stars** | 12.2k2 |
| **Forks** | 1.6k2 |
| **License** | Polyform/Open-source dual licensing models47 |
| **Last Updated** | Active (2026)2 |
| **Primary Language** | Python (99.8%)47 |
| **Maintainer** | Qodo (formerly CodiumAI)47 |
| **Installation Complexity** | Moderate (Requires Webhook/GitHub App configuration)46 |
| **Project Status** | Highly Active2 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Automated pull request analysis, feedback, and suggestions. |
| **System Architecture** | Event-driven webhook listeners invoking targeted LLM analysis tools. |
| **Folder Structure** | CLI tools (pr\_agent.cli), configuration files (.pr\_agent.toml)46. |
| **Important Modules** | /review, /describe, /improve tools, LiteLLM integration. |
| **Technologies Used** | Python, LiteLLM, Git provider APIs. |
| **Database** | None strictly required for open-source version (operates statelessly). |
| **Parsing Libraries** | Git diff parsers and abstract syntax filters. |
| **Graph Technologies** | None natively. |
| **LLM Framework** | LiteLLM supporting OpenAI, Gemini, Claude, and local models46. |
| **Agent Framework** | Orchestrates single-call LLM interactions based on JSON prompts47. |

The PR-Agent repository establishes a robust architectural pattern for integrating generative AI directly into the software development lifecycle. The system is designed to respond to Git provider webhooks (GitHub, GitLab, Bitbucket), invoking highly specialized tools to analyze incoming pull requests46. The most critical algorithmic design idea within PR-Agent is its "PR Compression strategy." Large pull requests generate massive git diff outputs that easily overwhelm LLM context windows; PR-Agent implements algorithms to intelligently truncate, summarize, and distill these diffs into a dense representation that preserves the semantic intent of the changes47. Furthermore, the system enforces a strict JSON prompting strategy, ensuring the LLM outputs modular, customizable data that can be programmatically parsed and posted back as a GitHub Check or comment2.  
The webhook listener architecture and the PR Compression algorithms should be studied extensively as reference implementations. While the open-source version provides excellent baseline code review, injecting complex, multi-step graph queries to determine a "Blast Radius" requires significant modification of the core tool logic, as the repository is optimized for single-call LLM interactions rather than deep, iterative agentic reasoning47. Furthermore, some advanced features, like persistent suggestion tracking and incremental updates for subsequent commits, are locked behind the proprietary Qodo Merge tier51. Therefore, PR-Agent is recommended primarily as an inspiration and reference implementation for handling the Pull Request Ingestion phase.

### **OpenHands**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | All-Hands-AI/OpenHands |
| **GitHub URL** | github.com/All-Hands-AI/OpenHands |
| **Stars** | \~75k8 |
| **Forks** | High (Highly active community)52 |
| **License** | MIT52 |
| **Last Updated** | Active (2026)52 |
| **Primary Language** | Python53 |
| **Maintainer** | All-Hands-AI52 |
| **Installation Complexity** | Moderate (Requires Docker for sandboxed execution)52 |
| **Project Status** | Highly Active52 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Autonomous AI software developer platform and agent-computer interface. |
| **System Architecture** | Parallelized, multi-agent delegation within sandboxed containers. |
| **Folder Structure** | Agent SDKs (openhands/tools), CLI modules, local GUI52. |
| **Important Modules** | Agent-Computer Interface (ACI), File Editor Tool, Shell Executor54. |
| **Technologies Used** | Python, Docker, React (for GUI)52. |
| **Database** | None strictly required for stateless agent runs. |
| **Parsing Libraries** | Tree-sitter for built-in code linting54. |
| **Graph Technologies** | None natively. |
| **LLM Framework** | Provider-agnostic support for 100+ LLMs (Claude, GPT, Ollama)52. |
| **Agent Framework** | Custom autonomous reasoning and task decomposition engine52. |

The OpenHands repository provides the foundational reasoning engine required to synthesize the outputs of the static analysis tools and the knowledge graph into a cohesive Blast Radius Report. The architecture revolves around an Agent-Computer Interface (ACI), which grants the LLM secure, sandboxed access to execute terminal commands, edit files, and browse the web within a controlled Docker container52. The implemented algorithms handle complex task decomposition, allowing the primary agent to delegate specific coding or analysis tasks to specialized sub-agents (e.g., spawning a sub-agent to navigate a specific directory structure)52. Crucially, the system implements advanced context management techniques—such as signal-driven context injection and insertion-time tool result trimming—to prevent the agent from entering infinite loops or overflowing its context window during deep repository traversals52.  
The openhands-aci and the core Agent SDK can be directly reused to act as the central orchestration brain of the Blast Radius Analyzer53. By deploying the OpenHands agent into a sandbox containing the cloned repository and equipping it with the ast-grep MCP server, the agent can autonomously investigate the ripple effects of a code change in real-time26. Engineers should study the implementation of the tool-call loop guards and the multi-agent delegation patterns52. The primary limitation is the inherent latency and overhead of spinning up and managing Docker containers for every pull request analysis, which requires robust underlying infrastructure8. OpenHands is highly recommended as a direct dependency for the AI Agents for Software Engineering subsystem.

### **Skyvern**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | skyvern-ai/skyvern |
| **GitHub URL** | github.com/skyvern-ai/skyvern |
| **Stars** | \~22k55 |
| **Forks** | \~2k56 |
| **License** | AGPL-3.055 |
| **Last Updated** | Active (2026)55 |
| **Primary Language** | Python55 |
| **Maintainer** | Skyvern AI56 |
| **Installation Complexity** | Moderate (Requires PostgreSQL, Rust, Playwright configurations)55 |
| **Project Status** | Highly Active55 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Computer vision-based autonomous web workflow automation. |
| **System Architecture** | Swarm of agents utilizing visual reasoning and Playwright SDKs. |
| **Folder Structure** | Workflows, blocks, and API endpoints57. |
| **Important Modules** | Skyvern client, Session manager, Workflow Builder55. |
| **Technologies Used** | Python 3.11+, PostgreSQL, Playwright, Computer Vision. |
| **Database** | PostgreSQL55. |
| **Parsing Libraries** | Visual layout analysis bypassing traditional DOM parsing55. |
| **Graph Technologies** | None natively. |
| **LLM Framework** | Integrates Vision-Language Models (VLMs)55. |
| **Agent Framework** | Task-Driven autonomous agent design (inspired by BabyAGI/AutoGPT)55. |

Skyvern introduces a radically different architectural approach to web automation by eschewing traditional DOM parsing and XPath selectors in favor of Vision-Language Models (VLMs) and computer vision algorithms. The system utilizes a swarm of agents that "look" at the rendered webpage to plan and execute interactions, making it highly resistant to underlying HTML layout changes that typically break standard automation scripts55. This architectural pattern—visually reasoning about the state of a web application—is theoretically ideal for mapping the User Experience layers of the Product Knowledge Graph, bridging the gap between how a UI component is described in a PRD and how it actually renders in production.  
However, despite its innovative approach, the repository possesses limitations that impact its viability as a direct dependency for this specific assignment. The continuous processing of high-resolution images by VLMs introduces significant latency and extreme API costs57. Furthermore, the AGPL-3.0 license mandates stringent copyleft requirements that can complicate deployment in closed-source enterprise environments55. Therefore, Skyvern is recommended strictly as an inspiration. The concepts underlying its visual reasoning engine should be studied to understand how future iterations of the crawler subsystem might evolve beyond pure HTML parsing.

### **SWE-agent**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | princeton-nlp/SWE-agent |
| **GitHub URL** | github.com/princeton-nlp/SWE-agent |
| **Stars** | \~15k9 |
| **Forks** | Not explicitly enumerated in source9 |
| **License** | MIT (Implied via standard academic OS releases, though check required) |
| **Last Updated** | Active (2026)9 |
| **Primary Language** | Python9 |
| **Maintainer** | Princeton NLP9 |
| **Installation Complexity** | Moderate (Requires sandboxed environments for execution) |
| **Project Status** | Active (Academic/Research tool)9 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Autonomous resolution of GitHub issues via an agentic terminal. |
| **System Architecture** | Tightly optimized feedback loop between LLM and a sandboxed shell. |
| **Folder Structure** | Academic research structure with evaluation harnesses. |
| **Important Modules** | Terminal interaction environment, SWE-bench evaluator. |
| **Technologies Used** | Python, Docker. |
| **Database** | None natively. |
| **Parsing Libraries** | Custom terminal output formatters59. |
| **Graph Technologies** | None natively. |
| **LLM Framework** | Agnostic (Tested heavily with GPT-4)59. |
| **Agent Framework** | Custom agent loop optimized for the SWE-bench evaluation59. |

The SWE-agent repository, developed by Princeton NLP, serves as the definitive academic benchmark for evaluating AI agents on software engineering tasks. The architecture is defined by an incredibly optimized feedback loop that manages how the LLM interacts with a simulated terminal9. Rather than simply dumping raw command-line output back to the LLM, the system implements specific design ideas to paginate, format, and truncate outputs (such as directory listings or file reads), ensuring the model maintains deep contextual awareness without hallucinating due to information overload59.  
While OpenHands provides a more production-ready, feature-rich platform for the final deployment, the architectural patterns within SWE-agent should be studied extensively. Specifically, engineers should examine the code files responsible for formatting the terminal feedback loop, as these techniques can be directly applied to optimize how the results of an ast-grep graph query are presented to the reporting agent during the Blast Radius analysis phase58. SWE-agent is recommended as a highly valuable reference implementation.

### **Slither**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | crytic/slither |
| **GitHub URL** | github.com/crytic/slither |
| **Stars** | 6.3k60 |
| **Forks** | 1.1k60 |
| **License** | AGPL-3.060 |
| **Last Updated** | Active (2026)60 |
| **Primary Language** | Python (\>=3.10)60 |
| **Maintainer** | Trail of Bits (crytic)60 |
| **Installation Complexity** | Low (uv tool install slither-analyzer)60 |
| **Project Status** | Highly Active60 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Static analysis and vulnerability detection for smart contracts. |
| **System Architecture** | Multi-pass static analysis engine leveraging intermediate representations. |
| **Folder Structure** | Python modules containing distinct vulnerability detectors (detectors/)60. |
| **Important Modules** | SlithIR generation, Custom Printer API60. |
| **Technologies Used** | Python, solc compiler integration60. |
| **Database** | None natively. |
| **Parsing Libraries** | Relies on underlying compiler AST outputs. |
| **Graph Technologies** | Intermediate representation graphs (SlithIR)60. |
| **LLM Framework** | None natively. |
| **Agent Framework** | None natively. |

Although Slither is domain-specific (targeting Solidity and Vyper), its system architecture provides a masterclass in the design of static analysis frameworks. The core algorithm relies on translating the raw Abstract Syntax Tree (AST) produced by the compiler into a proprietary intermediate representation known as SlithIR60. This normalization process simplifies the underlying logic, allowing the system to execute complex data-flow tracking, variable shadowing detection, and taint analysis algorithms in less than a second per file60.  
The design ideas embedded in the construction of the SlithIR should be carefully studied when architecting the Call Graph Construction subsystem. Understanding how Slither normalizes diverse syntax patterns into a standardized graph makes the detection of specific impact patterns (or vulnerabilities) trivial to implement as discrete detection modules60. While it cannot be used directly for a general-purpose software project (due to its language constraints and AGPL license), it stands as a premier reference implementation for structuring the internal static analysis logic of the Blast Radius Analyzer.

### **LaVague**

| Metadata Parameter | Details |
| :---- | :---- |
| **Repository Name** | lavague-ai/LaVague |
| **GitHub URL** | github.com/lavague-ai/LaVague |
| **Stars** | Not explicitly enumerated (Growing)63 |
| **Forks** | Not explicitly enumerated (10 active PRs)63 |
| **License** | Apache-2.063 |
| **Last Updated** | Active (2026)63 |
| **Primary Language** | Python (70.2%), TypeScript (15.1%)63 |
| **Maintainer** | lavague-ai63 |
| **Installation Complexity** | Low (Python package installation)63 |
| **Project Status** | Active63 |

| Technical Parameter | Details |
| :---- | :---- |
| **Overall Purpose** | Web agent framework automating processes for end users. |
| **System Architecture** | Decoupled World Model and Action Engine compilation architecture. |
| **Folder Structure** | Contains testing runners, logging tools, and Gradio interfaces63. |
| **Important Modules** | World Model, Action Engine, LaVague QA63. |
| **Technologies Used** | Python, Selenium, Playwright, Gradio63. |
| **Database** | None natively. |
| **Parsing Libraries** | DOM extraction into World Model state representations. |
| **Graph Technologies** | None natively. |
| **LLM Framework** | Agnostic (Contexts and configurations defined per run)63. |
| **Agent Framework** | Custom objective-driven agent mapping states to instructions63. |

The LaVague repository provides a highly structured framework designed specifically for developers building Web Agents. The system architecture introduces a strict dichotomy between a "World Model" and an "Action Engine"63. The implemented algorithms allow the World Model to ingest a natural language objective alongside the current DOM state to output a set of instructions, which the Action Engine subsequently compiles into executable Selenium or Playwright code63. A particularly valuable architectural pattern is the LaVague QA tooling, which demonstrates how to turn BDD (Behavior-Driven Development) or Gherkin specifications directly into automated, executable UI tests63.  
This design idea—translating human-readable product requirements directly into actionable DOM navigation flows—provides a clear conceptual pathway for fusing the Product Requirements layer of the Knowledge Graph with the User Experience layer. While browser-use provides a more mature generic agent interface, LaVague's specific focus on compiling objectives into deterministic test code makes it a valuable source of inspiration for bridging the gap between PRDs and live web applications.

## **Component-to-Repository Mapping**

The Blast Radius Analyzer architecture demands discrete but tightly integrated modules. The following mapping isolates which open-source repositories fulfill specific system requirements, identifying the primary selections and viable alternatives.

| Architectural Component | Primary Repository | Alternative / Supplementary Repositories |
| :---- | :---- | :---- |
| **Autonomous Web Crawling** | unclecode/crawl4ai | skyvern-ai/skyvern, lavague-ai/LaVague |
| **UI & DOM Analysis** | browser-use/browser-use | skyvern-ai/skyvern (Vision-based) |
| **Documentation Parsing** | docling-project/docling | flairNLP/flair (Entity extraction) |
| **Static Code Analysis** | ast-grep/ast-grep | joernio/joern (CPGs), crytic/slither (Reference) |
| **Knowledge Graph Construction** | microsoft/graphrag | HKUDS/LightRAG (Incremental updates) |
| **Graph Retrieval** | HKUDS/LightRAG | run-llama/llama\_index, langchain-ai/langchain |
| **Entity Resolution & Fusion** | moj-analytical-services/splink | Probabilistic linkage algorithms via Python |
| **PR Analysis Ingestion** | qodo-ai/pr-agent | BerriAI/litellm (Gateway routing) |
| **Agentic Reasoning** | All-Hands-AI/OpenHands | princeton-nlp/SWE-agent, Aider-AI/aider |
| **Explainable UI / Reporting** | lobehub/lobe-chat | Cinnamon/kotaemon, langgenius/dify |

## **Recommended Repositories per Subsystem**

Based on the technical breakdown, the optimal architecture relies on tools that balance analytical accuracy with ease of integration—specifically prioritizing Python and Rust ecosystems over heavy JVM dependencies.  
For the **Crawler and UI Understanding** subsystem, a hybrid approach using Crawl4AI and browser-use is recommended. Crawl4AI handles the bulk of static site crawling with unparalleled speed, outputting noise-free Markdown optimized directly for the graph pipeline1. When the system encounters dynamic single-page applications or complex authentication walls that static scraping cannot penetrate, control is handed to the browser-use agent to map the stateful user flows17.  
For **Requirements Parsing**, Docling is the definitive choice. Product documentation rarely exists in a single, clean format. Docling homogenizes everything from text-heavy PDFs to complex architectural diagrams (via embedded VLM OCR) and outputs a standardized schema while maintaining absolute physical provenance—a critical requirement for generating explainable evidence5.  
For **Code Analysis and Call Graphs**, ast-grep is recommended. While Joern produces incredibly detailed Code Property Graphs, its Scala ecosystem and slow processing times present significant bottlenecks for rapid PR analysis29. Conversely, ast-grep provides instantaneous, multi-threaded structural querying utilizing Tree-sitter10. Crucially, its provided MCP server allows the overarching AI agent to directly query the codebase in real-time26.  
For the **Knowledge Graph Engine**, LightRAG provides the most pragmatic architecture. While Microsoft's GraphRAG yields exceptional global summaries via Leiden community detection, it requires extensive compute to re-index data3. A Blast Radius Analyzer requires real-time graph updates as new PRs are opened. LightRAG solves this by providing seamless incremental graph updates and supports standard backend deployments like PostgreSQL (with pgvector and Apache AGE)4.  
For **Entity Resolution**, Splink is the optimal statistical engine. Mapping a JIRA ticket mentioning "Cart Checkout" to the cart\_controller.py file requires advanced fuzzy matching. Splink uses unsupervised probabilistic algorithms (Fellegi-Sunter) to scale this matching across disparate data nodes with immense accuracy43.  
Finally, for the **PR Analysis and Blast Radius Agent**, a synthesis of pr-agent and OpenHands is recommended. Qodo's pr-agent provides the structural chassis (GitHub hooks, diff compression) to ingest the code changes47. Instead of relying on a simple, single-pass LLM call, the compressed PR diff is handed to the OpenHands agent environment. Operating securely in a sandboxed container, the agent iteratively queries the ast-grep MCP server and the LightRAG database to mathematically deduce the impact report before pushing the final analysis back to the PR26.

## **70–80% Effort Reduction Stack**

Attempting to engineer AST parsers, browser automation layers, and graph extraction models from scratch requires years of dedicated engineering effort. Integrating the following three core pillars will immediately bypass roughly 80% of the implementation overhead, shifting the engineering focus from _building infrastructure_ to _tuning the reasoning logic_.

> 1. **LightRAG paired with Docling:** This combination solves the entire data-ingestion-to-Knowledge-Graph pipeline. Docling handles the chaotic reality of unstructured enterprise data, outputting clean JSON with strict provenance5. LightRAG seamlessly ingests this data into a unified PostgreSQL or Neo4j backend, instantly providing the infrastructure for both vector similarity search and complex multi-hop graph traversal4.  
> 2. **ast-grep (via MCP):** This completely eliminates the need to write custom static analysis parsers for different programming languages. By utilizing the pre-built MCP server, the AI agent can query Python, TypeScript, and Rust codebases uniformly using simple YAML configuration rules10.  
> 3. **OpenHands:** This removes the need to build complex sandboxing environments, Docker lifecycle managers, and prompt-trimming context windows. The Agent-Computer Interface (ACI) acts as the central brain orchestrating the other tools, providing a production-ready environment for the LLM to execute its reasoning loops52.

## **Production-Quality Code Worth Studying**

Before writing the custom glue code required to bind these systems together, engineering teams should thoroughly analyze specific files within these repositories to understand best-in-class architectural patterns.  
The **Diff Compression Algorithms** found within qodo-ai/pr-agent are vital study material. Passing an entire monolithic PR diff to an LLM immediately destroys the context window. Studying how Qodo implements chunking and summarization in its /review tool reveals how to distill a massive code change into its semantic intent46.  
The **Dual-Layer Retrieval Mechanisms** in HKUDS/LightRAG provide insight into dynamic routing. Analyzing files like llm/llama\_index\_impl.py demonstrates how the architecture seamlessly orchestrates an embedding model for standard semantic search alongside an LLM for graph traversal, deciding dynamically which to use based on the query complexity4.  
The **AST Pattern Unification** logic within ast-grep/ast-grep must be understood to write effective search rules. Reviewing the YAML rule engine and the implementation of relational constraints (inside, has, precedes) demonstrates how to turn a flat, syntactical tree into a highly queryable semantic structure10.  
Finally, the **Provenance Tracking** data structures in docling-project/docling represent the gold standard for explainability. Studying the ProvenanceItem schema in the DoclingDocument shows how to maintain a strict mathematical mapping back to the source text, ensuring the final Blast Radius Reports remain grounded in verifiable evidence5.

## **Suggested Implementation Blueprint**

The following phased implementation plan outlines the exact data flow and integration points where the recommended open-source repositories replace custom engineering.  
**Phase 1: Ingestion & Knowledge Graph Foundation** The architecture begins with the deployment of the underlying storage layer. A PostgreSQL database supporting pgvector and Apache AGE (or a dedicated Neo4j instance) is initialized as the persistent backend for LightRAG36. Crawl4AI is then deployed to autonomously traverse the organization's public application URLs, Confluence wikis, and Jira instances, generating raw, noise-free Markdown1. Concurrently, all internal Product Requirements Documents (PRDs), PDF specifications, and architectural diagrams are passed through the Docling pipeline. Docling extracts text, tables, and visual descriptions, ensuring absolute physical provenance for every data point5. This standardized data is ingested into LightRAG, which autonomously generates the foundational Product Knowledge Graph4.  
**Phase 2: Codebase Static Analysis & Call Graph Indexing** With the product requirements mapped, the system clones the target source code repositories. ast-grep is deployed across these repositories to perform structural indexing. Baseline YAML configurations are executed to identify and map all function declarations, API endpoints, and database queries10. To fuse the requirements graph with the codebase graph, Splink is utilized. It executes probabilistic matching algorithms to link the code entities found by ast-grep (e.g., checkout\_api.py) to the product features documented in the LightRAG knowledge graph (e.g., "User Checkout Flow")43. These linkages are merged as definitive edges within the graph database.  
**Phase 3: The Blast Radius Agent Environment** The central reasoning engine is established by deploying the OpenHands Agent-Computer Interface (ACI) within a secure Docker environment52. The agent is provisioned with tools: it is granted connection to the ast-grep MCP Server (allowing it to dynamically search the codebase) and API access to the LightRAG database4. To handle the ingestion of code changes, pr-agent is integrated via a GitHub Webhook. When a developer opens a pull request, pr-agent automatically intercepts the payload, compresses the massive git diff, and invokes the OpenHands agent47.  
**Phase 4: Impact Analysis & Explainable Reporting** The execution loop commences when the OpenHands agent receives the compressed diff. It utilizes its connection to the ast-grep MCP server to structurally search the codebase, determining exactly where the modified functions are called globally to establish the technical blast radius25. Next, the agent executes graph traversal queries against LightRAG to deduce which PRDs, User Stories, or downstream UI flows depend on the impacted technical components4. Finally, the agent synthesizes these findings into an explainable Blast Radius Report. Because the system maintained strict metadata lineage via Docling and Splink, the report explicitly cites the original provenance metadata to prove _why_ a specific UI element or business requirement is affected. This highly accurate, evidence-backed report is then posted back to the GitHub PR via the pr-agent integration, completing the automated review cycle24.

#### **Works cited**

> 1. Crawl4AI: Open-source LLM Friendly Web Crawler & Scraper. \- GitHub, [https://github.com/unclecode/crawl4AI](https://github.com/unclecode/crawl4AI)  
> 2. Releases · The-PR-Agent/pr-agent \- GitHub, [https://github.com/The-PR-Agent/pr-agent/releases](https://github.com/The-PR-Agent/pr-agent/releases)  
> 3. microsoft/graphrag: A modular graph-based Retrieval-Augmented Generation (RAG) system \- GitHub, [https://github.com/microsoft/graphrag](https://github.com/microsoft/graphrag)  
> 4. lightrag-hku \- PyPI, [https://pypi.org/project/lightrag-hku/](https://pypi.org/project/lightrag-hku/)  
> 5. docling-project/docling: Get your documents ready for gen AI \- GitHub, [https://github.com/docling-project/docling](https://github.com/docling-project/docling)  
> 6. rmdes/stargazer: Auto-sorting CLI for GitHub starred repos — classify 5000+ stars into taxonomy using Claude AI, publish to GitHub Lists and awesome-list README, [https://github.com/rmdes/stargazer](https://github.com/rmdes/stargazer)  
> 7. AI-Resources-Central/README\_en.md at main \- GitHub, [https://github.com/CoderSJX/AI-Resources-Central/blob/main/README\_en.md](https://github.com/CoderSJX/AI-Resources-Central/blob/main/README_en.md)  
> 8. Best Open Source CLI Coding Agents in 2026 \- Pinggy, [https://pinggy.io/blog/best\_open\_source\_cli\_coding\_agents/](https://pinggy.io/blog/best_open_source_cli_coding_agents/)  
> 9. Self Evolve 项目索引— GitHub 自进化AI 仓库, [https://agent-evolution.com/projects/](https://agent-evolution.com/projects/)  
> 10. GitHub \- ast-grep/ast-grep: A CLI tool for code structural search, lint and rewriting. Written in Rust, [https://github.com/ast-grep/ast-grep](https://github.com/ast-grep/ast-grep)  
> 11. Issues · unclecode/crawl4ai \- GitHub, [https://github.com/unclecode/crawl4ai/issues](https://github.com/unclecode/crawl4ai/issues)  
> 12. unclecode/crawl4ai-cloud-sdk: ☁️ Crawl4AI Cloud: LLM Friendly Web Crawling as a Service. Don't be shy, join here: <https://discord.gg/jP8KfhDhyN> · GitHub \- GitHub, [https://github.com/unclecode/crawl4ai-cloud-sdk](https://github.com/unclecode/crawl4ai-cloud-sdk)  
> 13. unclecode crawl4ai · Discussions \- GitHub, [https://github.com/unclecode/crawl4ai/discussions](https://github.com/unclecode/crawl4ai/discussions)  
> 14. ️ Crawl4AI: Open-source LLM Friendly Web Crawler & Scrapper \- GitHub, [https://github.com/QIN2DIM/crawl4ai-fork](https://github.com/QIN2DIM/crawl4ai-fork)  
> 15. Home \- Crawl4AI Documentation (v0.9.x), [https://docs.crawl4ai.com/](https://docs.crawl4ai.com/)  
> 16. browser-use/browser-use \- 105.2k Stars · Global Rank \#107 \- GitHub Star History, [https://www.star-history.com/browser-use/browser-use/](https://www.star-history.com/browser-use/browser-use/)  
> 17. browser-use/skills/open-source/SKILL.md at main \- GitHub, [https://github.com/browser-use/browser-use/blob/main/skills/open-source/SKILL.md](https://github.com/browser-use/browser-use/blob/main/skills/open-source/SKILL.md)  
> 18. GitHub \- browser-use/browser-use: Make websites accessible for AI agents. Automate tasks online with ease., [https://github.com/browser-use/browser-use](https://github.com/browser-use/browser-use)  
> 19. browser-use repositories \- GitHub, [https://github.com/orgs/browser-use/repositories](https://github.com/orgs/browser-use/repositories)  
> 20. docling/LICENSE at main \- GitHub, [https://github.com/docling-project/docling/blob/main/LICENSE](https://github.com/docling-project/docling/blob/main/LICENSE)  
> 21. Welcome to the Docling Java Project\! \- GitHub, [https://github.com/docling-project/docling-java](https://github.com/docling-project/docling-java)  
> 22. docling-project/docling-serve: Running Docling as an API service \- GitHub, [https://github.com/docling-project/docling-serve](https://github.com/docling-project/docling-serve)  
> 23. docling-project repositories \- GitHub, [https://github.com/orgs/docling-project/repositories](https://github.com/orgs/docling-project/repositories)  
> 24. Docling Provenance Extension · docling-project docling · Discussion \#2897 \- GitHub, [https://github.com/docling-project/docling/discussions/2897](https://github.com/docling-project/docling/discussions/2897)  
> 25. ast-grep/agent-skill \- GitHub, [https://github.com/ast-grep/agent-skill](https://github.com/ast-grep/agent-skill)  
> 26. ast-grep MCP Server \- GitHub, [https://github.com/ast-grep/ast-grep-mcp](https://github.com/ast-grep/ast-grep-mcp)  
> 27. tree-sitter · GitHub Topics, [https://github.com/topics/tree-sitter](https://github.com/topics/tree-sitter)  
> 28. ast-grep VSCode \- GitHub, [https://github.com/ast-grep/ast-grep-vscode](https://github.com/ast-grep/ast-grep-vscode)  
> 29. GitHub \- joernio/joern: Open-source code analysis platform for C/C++/Java/Binary/Javascript/Python/Kotlin based on code property graphs. Discord <https://discord.gg/vv4MH284Hc> · GitHub, [https://github.com/joernio/joern](https://github.com/joernio/joern)  
> 30. Releases · joernio/joern \- GitHub, [https://github.com/joernio/joern/releases](https://github.com/joernio/joern/releases)  
> 31. joernio repositories \- GitHub, [https://github.com/orgs/joernio/repositories](https://github.com/orgs/joernio/repositories)  
> 32. joern.io \- GitHub, [https://github.com/joernio](https://github.com/joernio)  
> 33. The Bug Hunter's Workbench | Automatic Scans. On desktop, and in your CI. \- Joern, [https://joern.io/automate/](https://joern.io/automate/)  
> 34. MIT License \- microsoft/graphrag \- GitHub, [https://github.com/microsoft/graphrag/blob/main/LICENSE](https://github.com/microsoft/graphrag/blob/main/LICENSE)  
> 35. microsoft/graphrag-benchmarking-datasets \- GitHub, [https://github.com/microsoft/graphrag-benchmarking-datasets](https://github.com/microsoft/graphrag-benchmarking-datasets)  
> 36. GitHub \- Azure-Samples/graphrag-legalcases-postgres: Legal Research Copilot Example Solution built with Generative AI capabilities of PostgreSQL on Azure, [https://github.com/Azure-Samples/graphrag-legalcases-postgres](https://github.com/Azure-Samples/graphrag-legalcases-postgres)  
> 37. LightRAG 3D Graph Viewer \- GitHub, [https://github.com/HKUDS/LightRAG/blob/main/lightrag/tools/lightrag\_visualizer/README.md](https://github.com/HKUDS/LightRAG/blob/main/lightrag/tools/lightrag_visualizer/README.md)  
> 38. GraphRAG4OpenWebUI integrates Microsoft's GraphRAG technology into Open WebUI, providing a versatile information retrieval API. It combines local, global, and web searches for advanced Q\&A systems and search engines. This tool simplifies graph-based retrieval integration in open web environments. · GitHub, [https://github.com/win4r/GraphRAG4OpenWebUI](https://github.com/win4r/GraphRAG4OpenWebUI)  
> 39. HKUDS repositories \- GitHub, [https://github.com/orgs/HKUDS/repositories](https://github.com/orgs/HKUDS/repositories)  
> 40. LarFii/LightRAG-hku: "LightRAG: Simple and Fast Retrieval-Augmented Generation" \- GitHub, [https://github.com/LarFii/LightRAG-hku](https://github.com/LarFii/LightRAG-hku)  
> 41. conda-forge/lightrag-hku-feedstock \- GitHub, [https://github.com/conda-forge/lightrag-hku-feedstock](https://github.com/conda-forge/lightrag-hku-feedstock)  
> 42. \[Feature Request\]: OpenSearch Storage Backend Support · Issue \#2682 · HKUDS/LightRAG, [https://github.com/HKUDS/LightRAG/issues/2682](https://github.com/HKUDS/LightRAG/issues/2682)  
> 43. moj-analytical-services/splink: Fast, accurate and scalable probabilistic data linkage with support for multiple SQL backends \- GitHub, [https://github.com/moj-analytical-services/splink](https://github.com/moj-analytical-services/splink)  
> 44. Ask HN: What are you working on (August 2024)? \- Hacker News \- Y Combinator, [https://news.ycombinator.com/item?id=41342017](https://news.ycombinator.com/item?id=41342017)  
> 45. conda-forge/splink-feedstock \- GitHub, [https://github.com/conda-forge/splink-feedstock](https://github.com/conda-forge/splink-feedstock)  
> 46. pr-agent/docs/docs/usage-guide/automations\_and\_usage.md at main \- GitHub, [https://github.com/qodo-ai/pr-agent/blob/main/docs/docs/usage-guide/automations\_and\_usage.md](https://github.com/qodo-ai/pr-agent/blob/main/docs/docs/usage-guide/automations_and_usage.md)  
> 47. PR-Agent (Qodo Merge open-source): An AI-Powered Tool for Automated Pull Request Analysis, Feedback, Suggestions and More\! \- GitHub, [https://github.com/Writesonic/qodo-pr-agent](https://github.com/Writesonic/qodo-pr-agent)  
> 48. All Hands AI OpenHands Self-hosted Cloud \- GitHub, [https://github.com/OpenHands/openhands-cloud](https://github.com/OpenHands/openhands-cloud)  
> 49. pr-agent/docs/docs/usage-guide/index.md at main \- GitHub, [https://github.com/qodo-ai/pr-agent/blob/main/docs/docs/usage-guide/index.md](https://github.com/qodo-ai/pr-agent/blob/main/docs/docs/usage-guide/index.md)  
> 50. Support for custom metadata in LLM API calls · Issue \#1893 \- GitHub, [https://github.com/qodo-ai/pr-agent/issues/1893](https://github.com/qodo-ai/pr-agent/issues/1893)  
> 51. Is it possible to remember code suggestions from the previous push? · Issue \#2184 \- GitHub, [https://github.com/The-PR-Agent/pr-agent/issues/2184](https://github.com/The-PR-Agent/pr-agent/issues/2184)  
> 52. Feature: OpenHands Coding Agent Skill — Model-Agnostic Sandboxed Code Agent Delegation · Issue \#477 · NousResearch/hermes-agent \- GitHub, [https://github.com/NousResearch/hermes-agent/issues/477](https://github.com/NousResearch/hermes-agent/issues/477)  
> 53. OpenHands repositories \- GitHub, [https://github.com/orgs/OpenHands/repositories](https://github.com/orgs/OpenHands/repositories)  
> 54. OpenHands/openhands-aci: Agent computer interface for AI software engineer. \- GitHub, [https://github.com/OpenHands/openhands-aci](https://github.com/OpenHands/openhands-aci)  
> 55. Skyvern-AI/skyvern: Automate browser based workflows with AI \- GitHub, [https://github.com/skyvern-ai/skyvern](https://github.com/skyvern-ai/skyvern)  
> 56. Skyvern-AI repositories \- GitHub, [https://github.com/orgs/Skyvern-AI/repositories](https://github.com/orgs/Skyvern-AI/repositories)  
> 57. skyvern/docs/skill.md at main \- GitHub, [https://github.com/Skyvern-AI/skyvern/blob/main/docs/skill.md](https://github.com/Skyvern-AI/skyvern/blob/main/docs/skill.md)  
> 58. Open-Source AI Adoption 2026: 5.6M Projects vs Real Deployment \- TechnologyChecker.io, [https://technologychecker.io/blog/open-source-ai-adoption](https://technologychecker.io/blog/open-source-ai-adoption)  
> 59. ParthaPRay/Curated-List-of-Generative-AI-Tools \- GitHub, [https://github.com/ParthaPRay/Curated-List-of-Generative-AI-Tools](https://github.com/ParthaPRay/Curated-List-of-Generative-AI-Tools)  
> 60. crytic/slither: Static Analyzer for Solidity and Vyper \- GitHub, [https://github.com/crytic/slither](https://github.com/crytic/slither)  
> 61. Detector Documentation · crytic/slither Wiki \- GitHub, [https://github.com/crytic/slither/wiki/Detector-Documentation](https://github.com/crytic/slither/wiki/Detector-Documentation)  
> 62. slither/pyproject.toml at master \- GitHub, [https://github.com/crytic/slither/blob/master/pyproject.toml](https://github.com/crytic/slither/blob/master/pyproject.toml)  
> 63. GitHub \- lavague-ai/LaVague: Large Action Model framework to develop AI Web Agents, [https://github.com/lavague-ai/LaVague](https://github.com/lavague-ai/LaVague)  
> 64. oss · GitHub Topics, [https://github.com/topics/oss](https://github.com/topics/oss)

---

# AI Blast Radius Literature Review - Gemini

# **Architecting an Evidence-Backed Blast Radius Analyzer: An Exhaustive Literature Review (2015–2026)**

The engineering of an AI-powered Blast Radius Analyzer represents a convergence of multiple advanced computer science disciplines, necessitating a transition from traditional static analysis toward semantic, neuro-symbolic reasoning. The proposed architecture aims to construct an Evidence-backed Product Knowledge Graph (PKG) that traces logical and semantic dependencies from abstract Product Requirements Documents (PRDs) down through the User Experience (UX) layer—comprising DOM elements and user flows—and ultimately into backend Implementation artifacts such as source code and APIs. When a Pull Request (PR) is submitted, the system must perform a highly advanced form of Change Impact Analysis (CIA) to generate an explainable Blast Radius Report. This report must detail affected requirements, UI elements, backend components, and confidence scores, supported by mathematically rigorous evidence.  
To achieve this, the underlying system must synthesize 23 distinct research areas. Graph Databases (such as Neo4j) serve as the persistence layer, requiring strict Ontology Design to map the heterogeneous relationships between natural language (PRDs), visual/hierarchical data (UX/DOM), and structural logic (Code)1. The construction of this Software Knowledge Graph relies on Knowledge Fusion and Entity Resolution to accurately link a user story to a specific API endpoint. Furthermore, Static Code Analysis and Code Property Graphs (CPGs) form the deterministic foundation of Software Dependency Analysis. To bridge the semantic gap, the system leverages Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and GraphRAG for Graph Retrieval. Finally, to act upon incoming PRs, Autonomous Web Crawling, GUI/DOM Understanding, and Repository Mining extract the necessary delta states, while AI Agents for Software Engineering evaluate the logic. The output is refined by Explainable AI (XAI) to ensure the Blast Radius Analysis and resulting Regression Test Selection (RTS) recommendations are transparent and trustworthy.  
The following exhaustive literature review dissects the pivotal research from 2015 to 2026 that makes this architecture possible.

## **Comprehensive Paper Analysis**

To construct the Blast Radius Analyzer, distinct algorithmic and architectural approaches must be adopted, adapted, or intentionally ignored. The literature is analyzed below through narrative synthesis, followed by strictly formatted structured data detailing the specific parameters of each study.

### **1\. The Foundation of Structural Code Representation**

Traditional static analysis techniques struggle to model the complex interplay of syntax, control flow, and data flow required to detect vulnerabilities or understand precise change impacts. The introduction of the Code Property Graph (CPG) revolutionized this space by unifying Abstract Syntax Trees (ASTs), Control Flow Graphs (CFGs), and Program Dependence Graphs (PDGs) into a singular, highly searchable joint data structure2. By representing code as a property graph, impact analysis is reduced to graph traversal queries. For the Blast Radius Analyzer, the CPG serves as the mandatory, lossless mathematical representation of the implementation layer, providing the deterministic bedrock upon which neural embeddings will be placed.

| Parameter | Detail |
| :---- | :---- |
| **Title** | Modeling and Discovering Vulnerabilities with Code Property Graphs |
| **Authors** | Fabian Yamaguchi, Nico Golde, Daniel Arp, Konrad Rieck |
| **Publication Year** | 2014 (Foundational for 2015-2026 research) |
| **Conference / Journal** | IEEE Symposium on Security and Privacy (S\&P) |
| **DOI** | 10.1109/SP.2014.44 |
| **PDF Link** | <https://ieeexplore.ieee.org/document/6956589> |
| **ArXiv Link** | N/A |
| **GitHub Repository** | <https://github.com/joernio/joern> |
| **Citation Count** | \~1,500 |
| **Research Area** | Static Code Analysis, Code Property Graphs (CPG), Software Dependency Analysis |
| **Problem Addressed** | Inability of traditional analysis to jointly model syntax, control flow, and data dependencies for vulnerability discovery. |
| **Core Idea** | Merging AST, CFG, and PDG into a unified graph structure queryable via graph traversals. |
| **Architecture Summary** | A graph database implementation where code statements are nodes and edges represent syntax, control, or data dependencies. |
| **Algorithms Used** | Graph traversal, Subgraph isomorphism. |
| **Models Used** | Analytical structural models (Non-neural). |
| **Datasets Used** | Linux Kernel source code (C language). |
| **Evaluation Methodology** | Empirical evaluation demonstrating the detection of zero-day vulnerabilities via targeted queries. |
| **Strengths** | Provides a lossless, mathematically sound representation of software execution semantics5. |
| **Weaknesses** | High computational and storage overhead for extremely large codebases. |
| **Limitations** | Lacks natural language semantic understanding of code (e.g., developer intent in variable names). |
| **System Component Improvement** | Implementation (Source Code) Knowledge Graph representation. |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. The CPG is the mandatory foundational data structure for the backend implementation layer. All downstream code embeddings must derive from this baseline. |

### **2\. Dynamic Regression Test Selection**

Executing entire test suites upon every code change is computationally prohibitive in modern CI/CD pipelines. Early approaches to Change Impact Analysis relied heavily on Regression Test Selection (RTS). Ekstazi introduced a highly practical methodology for dynamic RTS by instrumenting code on-the-fly during test execution6. It tracks dependencies at the file level and utilizes Depth-First Search (DFS) over the resulting dependency graph to identify which tests must be rerun when a specific file is modified in a Pull Request6. While the Blast Radius Analyzer aims to be largely static and predictive via its Knowledge Graph, Ekstazi's mathematical definitions of transitive dependency paths provide the exact algorithmic blueprint needed to traverse the PKG and calculate affected downstream UI flows.

| Parameter | Detail |
| :---- | :---- |
| **Title** | Ekstazi: Lightweight Test Selection |
| **Authors** | Milos Gligoric, Lamyaa Eloussi, Darko Marinov |
| **Publication Year** | 2015 |
| **Conference / Journal** | International Conference on Software Engineering (ICSE) |
| **DOI** | 10.1109/ICSE.2015.86 |
| **PDF Link** | <https://mir.cs.illinois.edu/marinov/publications/GligoricETALEkstazi15.pdf> |
| **ArXiv Link** | N/A |
| **GitHub Repository** | <https://github.com/TestingResearchIllinois/ekstazi> |
| **Citation Count** | \~450 |
| **Research Area** | Regression Test Selection, Change Impact Analysis |
| **Problem Addressed** | The computational expense of re-running full test suites and the unsafety of overly conservative static RTS tools. |
| **Core Idea** | Dynamic collection of file-level dependencies during test execution to safely select only affected tests. |
| **Architecture Summary** | Instruments Java bytecode dynamically, tracking which test classes access target classes, storing dependencies as a lightweight graph. |
| **Algorithms Used** | Dynamic dependency tracing, Depth-First Search (DFS). |
| **Models Used** | Deterministic execution tracing. |
| **Datasets Used** | Open-source Java projects (e.g., Apache Commons, Camel). |
| **Evaluation Methodology** | Measurement of end-to-end testing time reduction versus "RetestAll", evaluating test suite reduction (TSR) and fault detection rate. |
| **Strengths** | Highly practical, minimal overhead, safe test selection. |
| **Weaknesses** | Dynamic analysis fundamentally requires an executable runtime environment and existing test suite. |
| **Limitations** | Operates primarily at the file/class level, lacking the function-level precision required for exact blast radius tracing. |
| **System Component Improvement** | Blast Radius Reporting, Regression Test Selection. |
| **Decision (Adopt/Adapt/Ignore)** | **Adapt**. The system should adapt Ekstazi's DFS algorithms for transitive dependency mapping, applying them statically over the PKG rather than dynamically at runtime. |

### **3\. Deep Learning for Entity Resolution**

Connecting a natural language PRD feature (e.g., "User Login") to a specific UX component (\<form id="auth"\>) or backend function (def authenticate\_user()) requires solving the Entity Resolution problem across highly heterogeneous and "dirty" text records8. DeepMatcher pioneered the application of deep learning to this domain by framing entity matching as a sequence-pair classification problem. It leverages bidirectional RNNs and attention mechanisms to capture contextual language understanding10. For the proposed architecture, identity resolution is the critical glue holding the PRD, UX, and Code layers together, ensuring that differing vocabularies across domains resolve to the same core ontological entity in the Knowledge Graph.

| Parameter | Detail |
| :---- | :---- |
| **Title** | Deep Learning for Entity Matching: A Design Space Exploration |
| **Authors** | Sidharth Mudgal, Han Li, Theodoros Rekatsinas, AnHai Doan, et al. |
| **Publication Year** | 2018 |
| **Conference / Journal** | ACM SIGMOD International Conference on Management of Data |
| **DOI** | 10.1145/3183713.3196926 |
| **PDF Link** | <https://pages.cs.wisc.edu/\~anhai/papers1/deepmatcher-sigmod18.pdf> |
| **ArXiv Link** | N/A |
| **GitHub Repository** | <https://github.com/anhaidgroup/deepmatcher> |
| **Citation Count** | \~1,100 |
| **Research Area** | Entity Resolution, Identity Resolution, Knowledge Fusion |
| **Problem Addressed** | Identifying matching entities across disparate, noisy, and unstructured text datasets without manual feature engineering. |
| **Core Idea** | Framing entity matching as a sequence-pair classification problem using deep learning and word embeddings. |
| **Architecture Summary** | An end-to-end neural network featuring an attribute embedding module, a bidirectional RNN similarity module, and a classifier. |
| **Algorithms Used** | Attention mechanisms, Recurrent Neural Networks (RNNs). |
| **Models Used** | FastText, GloVe. |
| **Datasets Used** | Structured, textual, and dirty EM datasets (e.g., Abt-Buy, DBLP-ACM). |
| **Evaluation Methodology** | F1-score comparison against traditional rule-based and machine learning baseline matchers (e.g., Magellan). |
| **Strengths** | Achieves high accuracy on unstructured textual data without manual rules. |
| **Weaknesses** | Pre-dates modern Transformer architectures; computationally heavy for exact matching. |
| **Limitations** | Requires labeled training data; less effective on purely structured, clean databases where rules suffice. |
| **System Component Improvement** | Identity Resolution, Knowledge Fusion (PRD to UI to Code). |
| **Decision (Adopt/Adapt/Ignore)** | **Adapt**. The sequence-pair classification framing is essential for Identity Resolution. However, the architecture must be modernized by replacing RNNs with cross-encoder Transformers (e.g., RoBERTa) to handle the complex semantic mapping of PRDs to source code. |

### **4\. Repository Mining and PR Ingestion**

To analyze a Pull Request, the system must interact seamlessly with version control systems to extract modified files, diffs, and developer history. PyDriller provides a robust, Python-based framework for Repository Mining that abstracts the vast complexities of Git's internal directed acyclic graphs12. By utilizing lazy loading and topological sorting, it allows analysis tools to iterate over commits and extract file modifications with extremely low memory overhead14. The Blast Radius Analyzer requires PyDriller as its primary ingestion engine to capture incoming PRs, parse the file diffs, and feed the affected source code into the downstream CPG generators and LLM reasoning agents.

| Parameter | Detail |
| :---- | :---- |
| **Title** | PyDriller: Python Framework for Mining Software Repositories |
| **Authors** | Davide Spadini, Maurício Aniche, Alberto Bacchelli |
| **Publication Year** | 2018 |
| **Conference / Journal** | ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering (ESEC/FSE) |
| **DOI** | 10.1145/3236024.3264598 |
| **PDF Link** | <https://research.tudelft.nl/files/46282428/main.pdf> |
| **ArXiv Link** | N/A |
| **GitHub Repository** | <https://github.com/ishepard/pydriller> |
| **Citation Count** | \~1,400 |
| **Research Area** | Repository Mining, Software Engineering Tools |
| **Problem Addressed** | Extracting actionable data from Git repositories is complex, non-standardized, and memory-intensive. |
| **Core Idea** | A robust API wrapper around Git that abstracts the complexity of traversing commit histories and parsing diffs. |
| **Architecture Summary** | A generator-based Python framework yielding lazy-loaded Commit objects containing modified files, added/removed lines, and metadata. |
| **Algorithms Used** | Topological sorting of Git graphs, differential parsing algorithms. |
| **Models Used** | N/A (Utility framework). |
| **Datasets Used** | Open-source Java/Python repositories (for performance benchmarking). |
| **Evaluation Methodology** | Memory consumption, execution time comparisons against GitPython, and developer usability studies. |
| **Strengths** | Extremely low memory footprint due to lazy loading; straightforward syntax; handles complex merge histories. |
| **Weaknesses** | Only extracts metadata and raw text diffs; does not perform semantic or structural code analysis natively. |
| **Limitations** | Bound by the inherent performance constraints of local Git operations on massive monorepos. |
| **System Component Improvement** | Pull Request Analysis, Implementation Graph Ingestion. |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. PyDriller is the definitive industry-standard utility required to power the ingestion engine that reads Pull Requests and feeds modified code into the CPG generator. |

### **5\. Explainable AI for Graph Structures**

When a Graph Neural Network (or a GraphRAG system) identifies a blast radius, the lack of transparency in the prediction prevents developer trust. Explainable AI (XAI) for graphs, pioneered by GNNExplainer, provides a model-agnostic approach that identifies a compact subgraph structure containing the nodes and edges most responsible for a given prediction16. By maximizing mutual information between the GNN's prediction and the distribution of possible subgraph structures, GNNExplainer generates interpretable, visualizable evidence16. This mathematical foundation is strictly required to satisfy the system's requirement of providing "supporting evidence" in the Blast Radius Report.

| Parameter | Detail |
| :---- | :---- |
| **Title** | GNNExplainer: Generating Explanations for Graph Neural Networks |
| **Authors** | Rex Ying, Dylan Bourgeois, Jiaxuan You, Marinka Zitnik, Jure Leskovec |
| **Publication Year** | 2019 |
| **Conference / Journal** | Advances in Neural Information Processing Systems (NeurIPS) |
| **DOI** | 10.48550/arXiv.1903.03894 |
| **PDF Link** | <https://arxiv.org/pdf/1903.03894> |
| **ArXiv Link** | 1903.03894 |
| **GitHub Repository** | <https://github.com/RexYing/gnn-model-explainer> |
| **Citation Count** | \~2,500 |
| **Research Area** | Explainable AI (XAI), Graph Neural Networks |
| **Problem Addressed** | GNNs act as black boxes; lack of transparency prevents trust in graph-based predictions. |
| **Core Idea** | Identifying a compact subgraph structure and a small subset of node features that have a crucial role in a GNN's prediction. |
| **Architecture Summary** | An optimization framework that learns a soft mask over the adjacency matrix and feature matrix of the input graph to isolate the explanatory subgraph. |
| **Algorithms Used** | Mutual information maximization, gradient descent over graph masks. |
| **Models Used** | Compatible with GCNs, GraphSAGE, GATs. |
| **Datasets Used** | Synthetic (BA-Shapes) and real-world graphs (Reddit, Mutag). |
| **Evaluation Methodology** | Quantitative measurement of explanation accuracy against ground-truth motifs; qualitative visualization. |
| **Strengths** | Model-agnostic; provides highly interpretable, visualizable subgraphs. |
| **Weaknesses** | Instance-level optimization is slow; generating explanations for massive enterprise graphs at inference time is computationally prohibitive. |
| **Limitations** | Requires a differentiable GNN model to compute gradients; cannot natively explain arbitrary non-neural graph heuristic queries. |
| **System Component Improvement** | Explainable Blast Radius Report, Confidence Scores. |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. The optimization mask methodology will be used to extract the specific causal subgraph (e.g., Code \-\> API \-\> UX \-\> PRD) to serve as the visual supporting evidence in the Blast Radius Report. |

### **6\. Semantic and Structural Code Embeddings**

Early Large Language Models treated source code strictly as text tokens, ignoring the formal structure, data dependencies, and control flows inherent to software execution20. GraphCodeBERT bridged this gap by augmenting transformer pre-training with semantic-level structural information derived from data flow graphs22. By introducing a graph-guided masked attention function, the model learns the "where-the-value-comes-from" relationships between variables21. To resolve code snippets against PRDs in the Knowledge Graph, the Blast Radius Analyzer must convert CPG nodes into dense vector embeddings using a structurally aware model like GraphCodeBERT, ensuring that the semantic similarities recognize logical flow rather than mere textual overlap24.

| Parameter | Detail |
| :---- | :---- |
| **Title** | GraphCodeBERT: Pre-training Code Representations with Data Flow |
| **Authors** | Daya Guo, Shuo Ren, Shuai Lu, et al. |
| **Publication Year** | 2021 |
| **Conference / Journal** | International Conference on Learning Representations (ICLR) |
| **DOI** | N/A (ICLR OpenReview) |
| **PDF Link** | <https://openreview.net/pdf?id=jLoC4ez43PZ> |
| **ArXiv Link** | 2009.08366 |
| **GitHub Repository** | <https://github.com/microsoft/CodeBERT> |
| **Citation Count** | \~1,200 |
| **Research Area** | Software Knowledge Graphs, Static Code Analysis, LLMs |
| **Problem Addressed** | Treating code as a sequence of tokens ignores structural data flow, leading to poor semantic representation of software execution. |
| **Core Idea** | Augmenting transformer pre-training with semantic-level structural information from data flow graphs. |
| **Architecture Summary** | A multi-layer bidirectional Transformer utilizing a graph-guided masked attention mechanism, taking code tokens and data flow nodes as joint inputs. |
| **Algorithms Used** | Graph-guided masked attention, masked language modeling, edge prediction. |
| **Models Used** | RoBERTa-based architecture. |
| **Datasets Used** | CodeSearchNet (2.3M functions across 6 languages). |
| **Evaluation Methodology** | Fine-tuned on downstream tasks (code search, clone detection, translation, refinement), achieving state-of-the-art results. |
| **Strengths** | Significantly superior understanding of variable usage and logical control flow compared to text-only models. |
| **Weaknesses** | Data flow graphs must be pre-extracted (via AST tools) prior to embedding generation, adding latency. |
| **Limitations** | Context window limits prevent embedding entire monolithic repositories simultaneously. |
| **System Component Improvement** | Implementation Knowledge Graph Node Embeddings. |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. GraphCodeBERT (or subsequent models like DeepSeek-Coder) is vital for converting raw CPG nodes into the dense vector embeddings required by the Identity Resolution module to find semantic links to PRDs. |

### **7\. Multi-modal GUI and DOM Understanding**

The User Experience (UX) layer of a software product bridges human intent (PRDs) and programmatic execution (Code). However, GUIs contain rich structural, textual, and visual data that traditional text embeddings fail to capture25. Screen2Vec solves this by creating dense, low-dimensional semantic embeddings for GUI screens and components using self-supervised learning over textual, visual, and layout properties27. It employs a multi-modal autoencoder combining Convolutional Neural Networks (CNNs) for visual features and Transformers for Document Object Model (DOM) hierarchies28. This approach is indispensable for the Blast Radius Analyzer to embed UX elements (like a "Submit" button) such that they can be mathematically linked to both the PRD requirements and the backend controller code handling the submission.

| Parameter | Detail |
| :---- | :---- |
| **Title** | Screen2Vec: Semantic Embedding of GUI Screens |
| **Authors** | Bryan Wang, Gang Li, Xin Zhou, Tovi Grossman, Yang Li |
| **Publication Year** | 2021 |
| **Conference / Journal** | ACM Symposium on User Interface Software and Technology (UIST) |
| **DOI** | 10.1145/3472749.3474765 |
| **PDF Link** | <https://3dvar.com/Wang2021Screen2Words.pdf> |
| **ArXiv Link** | 2108.03353 |
| **GitHub Repository** | N/A |
| **Citation Count** | \~150 |
| **Research Area** | GUI / DOM Understanding, Multi-modal Learning |
| **Problem Addressed** | GUIs lack a unified mathematical representation that captures visual, textual, and hierarchical layout features for downstream AI tasks. |
| **Core Idea** | Creating a dense semantic embedding for GUI screens and components using self-supervised learning over multiple modalities. |
| **Architecture Summary** | A multi-modal autoencoder combining CNNs for visual features and Transformers for text/DOM elements, trained with a skip-gram-like objective. |
| **Algorithms Used** | Self-supervised representation learning, DOM hierarchical parsing. |
| **Models Used** | CNNs, Transformer Encoders. |
| **Datasets Used** | RICO dataset (72k+ Android UI screens and metadata). |
| **Evaluation Methodology** | Evaluated on GUI retrieval, UI component prediction, and screen similarity scoring. |
| **Strengths** | Successfully merges visual layout with underlying DOM structure into highly semantic embeddings. |
| **Weaknesses** | Heavily optimized for static mobile apps; web-based DOM structures exhibit significantly higher variance. |
| **Limitations** | Does not inherently capture the dynamic, temporal state changes caused by JavaScript execution. |
| **System Component Improvement** | User Experience (pages, UI components) Knowledge Graph. |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. A Screen2Vec-style multi-modal encoder is required to ensure that UI components are understood contextually by their visual placement and DOM properties, enabling accurate entity resolution in the PKG. |

### **8\. Evaluating Autonomous Agents in Dynamic Web Environments**

Static analysis of UI code often fails to capture the dynamic state changes invoked by modern Single Page Applications (SPAs). To effectively map the UX layer, the system must utilize Autonomous Web Crawling. WebArena provides a highly realistic, reproducible web environment to evaluate AI agents navigating dynamic DOMs29. More importantly, WebArena establishes the methodology of linearizing complex DOMs into Accessibility Trees (AXTrees) that LLMs can deeply comprehend without token exhaustion32. The Blast Radius Analyzer will leverage this AXTree translation methodology to crawl target applications and construct the UX nodes of the Product Knowledge Graph.

| Parameter | Detail |
| :---- | :---- |
| **Title** | WebArena: A Realistic Web Environment for Building Autonomous Agents |
| **Authors** | Shuyan Zhou, Frank F. Xu, Hao Zhu, Xinyi Zhou, et al. |
| **Publication Year** | 2024 |
| **Conference / Journal** | International Conference on Learning Representations (ICLR) |
| **DOI** | N/A (ICLR OpenReview) |
| **PDF Link** | <https://arxiv.org/pdf/2307.13854> |
| **ArXiv Link** | 2307.13854 |
| **GitHub Repository** | <https://github.com/web-arena-x/webarena> |
| **Citation Count** | \~400 |
| **Research Area** | Autonomous Web Crawling, GUI / DOM Understanding, AI Agents |
| **Problem Addressed** | Static web benchmarks fail to represent the complexity of real-world internet interaction, dynamic DOMs, and multi-step reasoning. |
| **Core Idea** | A highly realistic, execution-verified web environment to benchmark web agents on complex tasks. |
| **Architecture Summary** | Dockerized hosting of real open-source web applications with an observation space (AXTrees, DOM, screenshots) and an execution verification harness. |
| **Algorithms Used** | DOM-to-text linearization, exact match verification scripts. |
| **Models Used** | Benchmarks evaluated using GPT-4, Claude. |
| **Datasets Used** | 812 execution-based tasks over 4 complex web apps (e.g., GitLab, Magento). |
| **Evaluation Methodology** | Success rate based on functional outcomes (e.g., database updates), not just textual string matching. |
| **Strengths** | Extreme realism; forces agents to handle dynamic state changes, nested iframes, and hidden elements. |
| **Weaknesses** | It is a benchmark environment rather than a standalone architectural algorithm. |
| **Limitations** | Setting up the full execution environment locally requires high computing resources. |
| **System Component Improvement** | Autonomous Web Crawling, UX Graph Construction. |
| **Decision (Adopt/Adapt/Ignore)** | **Adapt**. The system will adopt WebArena's methodology for linearizing the DOM into accessibility trees (AXTrees) and mapping visual states to programmatic states during the UX crawling phase. |

### **9\. Benchmarking Repository-Level LLM Comprehension**

The capacity of an AI agent to trace dependencies and evaluate change impacts across multiple files is best measured by its ability to resolve complex repository issues. SWE-bench established the definitive execution-based benchmark for evaluating LLMs on real-world software engineering tasks pulled from popular GitHub repositories34. By feeding an LLM a bug report and a codebase, and testing the generated patch against a test suite, SWE-bench proves that current LLMs struggle severely with long-context, repository-wide reasoning37. For the Blast Radius Analyzer, SWE-bench serves as the ultimate evaluation harness; if the analyzer can successfully predict the blast radius (and thus the failing tests) for SWE-bench pull requests, it is proven effective.

| Parameter | Detail |
| :---- | :---- |
| **Title** | SWE-bench: Can Language Models Resolve Real-World GitHub Issues? |
| **Authors** | Carlos E. Jimenez, John Yang, Alexander Wettig, et al. |
| **Publication Year** | 2024 |
| **Conference / Journal** | International Conference on Learning Representations (ICLR) |
| **DOI** | 10.48550/arXiv.2310.06770 |
| **PDF Link** | <https://openreview.net/pdf?id=VTF8yNQM66> |
| **ArXiv Link** | 2310.06770 |
| **GitHub Repository** | <https://github.com/swe-bench/SWE-bench> |
| **Citation Count** | \~650 |
| **Research Area** | AI Agents for Software Engineering, Repository Mining |
| **Problem Addressed** | Isolated code generation benchmarks (like HumanEval) fail to evaluate an LLM's ability to navigate large codebases and resolve multi-file dependencies. |
| **Core Idea** | An execution-based benchmark evaluating LLMs on thousands of real-world issues pulled from Python GitHub repositories. |
| **Architecture Summary** | A pipeline that provides a GitHub issue and repo context to an LLM, collects the patch, applies it, and runs the pre-existing test suite to verify correctness. |
| **Algorithms Used** | BM25 (for baseline context retrieval), dynamic test execution harnesses. |
| **Models Used** | Evaluated GPT-4, Claude 2, SWE-Llama. |
| **Datasets Used** | 2,294 issue-PR pairs from 12 Python repos (e.g., Django, SymPy). |
| **Evaluation Methodology** | Pass@1 rate (did the generated patch pass the execution tests?). |
| **Strengths** | The most rigorous, realistic test of repository-level understanding currently available. |
| **Weaknesses** | Evaluation is highly computationally expensive; currently heavily Python-centric. |
| **Limitations** | Focuses strictly on issue resolution rather than mapping the impact of the change (Blast Radius). |
| **System Component Improvement** | System Evaluation, Regression Test Selection validation. |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt (for evaluation)**. SWE-bench will be used as the rigorous testing ground. The analyzer will ingest SWE-bench PRs and must successfully predict which tests will fail by routing through the PKG. |

### **10\. Agent-Computer Interfaces for Autonomous Logic**

When traversing the Product Knowledge Graph, ambiguous connections between Code and UX may require dynamic investigation by an LLM agent. SWE-agent proved that standard bash terminals and code editors cause severe context loss for LLMs39. By introducing an "Agent-Computer Interface" (ACI) featuring custom commands (e.g., search\_dir, edit\_lines), SWE-agent dramatically improved the ability of autonomous agents to trace logic and resolve issues without hallucinating39. The Blast Radius Analyzer will embed an ACI-style toolset, allowing a Human-in-the-loop AI or an autonomous reasoning module to query the PKG using constrained, graph-specific traversal commands42.

| Parameter | Detail |
| :---- | :---- |
| **Title** | SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering |
| **Authors** | John Yang, Carlos E. Jimenez, Alexander Wettig, et al. |
| **Publication Year** | 2024 |
| **Conference / Journal** | Advances in Neural Information Processing Systems (NeurIPS) |
| **DOI** | 10.48550/arXiv.2405.15793 |
| **PDF Link** | <https://arxiv.org/pdf/2405.15793> |
| **ArXiv Link** | 2405.15793 |
| **GitHub Repository** | <https://github.com/princeton-nlp/SWE-agent> |
| **Citation Count** | \~300 |
| **Research Area** | AI Agents for Software Engineering, Reasoning |
| **Problem Addressed** | LLMs struggle to navigate large codebases because standard terminals are not designed for LLM interaction, causing context window exhaustion. |
| **Core Idea** | The introduction of an "Agent-Computer Interface" (ACI)—custom commands designed to help LLMs browse repositories efficiently. |
| **Architecture Summary** | An iterative feedback loop where an LLM agent uses custom shell commands to explore a repository and construct a logical understanding of a codebase. |
| **Algorithms Used** | Iterative reasoning (ReAct), heuristic search boundaries. |
| **Models Used** | GPT-4, Claude 3 Opus. |
| **Datasets Used** | Evaluated on SWE-bench. |
| **Evaluation Methodology** | Pass@1 issue resolution rate on SWE-bench (achieved state-of-the-art at release). |
| **Strengths** | Radically reduces hallucination by providing constrained, agent-friendly navigation tools. |
| **Weaknesses** | Relies on a linear, step-by-step search rather than leveraging a pre-computed global knowledge graph, causing slow execution per issue. |
| **Limitations** | Computationally expensive due to multi-turn interactions with the LLM. |
| **System Component Improvement** | Autonomous Reasoning, Graph Retrieval, Human-in-the-loop AI. |
| **Decision (Adopt/Adapt/Ignore)** | **Adapt**. When the analyzer detects an ambiguous PR change, an embedded ACI toolset will allow the reasoning agent to traverse the Knowledge Graph using specialized graph-query commands to definitively trace dependencies. |

### **11\. Global Summarization via GraphRAG**

Standard Retrieval-Augmented Generation (RAG) relies on vector similarity, which excels at retrieving localized facts but fails completely at answering global, corpus-wide questions (e.g., "How does this backend change affect the overall user checkout flow?"). Microsoft's GraphRAG solves this by constructing a massive entity-relationship knowledge graph from unstructured text and applying the Leiden community detection algorithm43. LLMs then generate summaries for each hierarchical community, allowing a map-reduce generation phase to answer complex, multi-hop queries46. This architecture is the definitive framework for Knowledge Fusion in the Blast Radius Analyzer, allowing PRDs, UX elements, and Code nodes to be clustered into functional "feature communities."

| Parameter | Detail |
| :---- | :---- |
| **Title** | From Local to Global: A Graph RAG Approach to Query-Focused Summarization |
| **Authors** | Darren Edge, Ha Trinh, Steven Truitt, Jonathan Larson, et al. |
| **Publication Year** | 2024 |
| **Conference / Journal** | Preprint (Microsoft Research) |
| **DOI** | N/A |
| **PDF Link** | <https://arxiv.org/pdf/2404.16130> |
| **ArXiv Link** | 2404.16130 |
| **GitHub Repository** | <https://github.com/microsoft/graphrag> |
| **Citation Count** | \~400 |
| **Research Area** | GraphRAG, Knowledge Fusion, Report Generation |
| **Problem Addressed** | Traditional vector-based RAG fails at global query summarization because it retrieves localized, fragmented, and overlapping chunks. |
| **Core Idea** | Constructing a knowledge graph from text, applying hierarchical community detection, and generating summaries for each community to enable global reasoning. |
| **Architecture Summary** | 1\. LLM extracts entities/relations. 2\. Leiden algorithm partitions graph into communities. 3\. LLM summarizes communities. 4\. Map-reduce generation phase. |
| **Algorithms Used** | Leiden algorithm (community detection), Map-Reduce generation. |
| **Models Used** | GPT-4-Turbo, Llama-3. |
| **Datasets Used** | Podcast transcripts, HotPotQA. |
| **Evaluation Methodology** | LLM-as-a-judge evaluating comprehensiveness, diversity, and token efficiency against baseline RAG. |
| **Strengths** | Provides unparalleled accuracy for complex, multi-hop summarization tasks over massive interconnected corpora45. |
| **Weaknesses** | Exponentially higher token cost and indexing time compared to naive RAG due to exhaustive LLM extraction phases. |
| **Limitations** | Heavily reliant on the quality and stability of the LLM prompt during the initial extraction phase. |
| **System Component Improvement** | Knowledge Fusion, Blast Radius Report Generation, Ontology Design. |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. GraphRAG is the macro-architecture for fusing the three layers (PRD, UX, Code). The Leiden community detection will cluster features logically, generating a Blast Radius Report that holistically explains how a backend API change ripples through a specific "feature community." |

### **12\. Routing Blast Radius via Personalized PageRank**

While GraphRAG provides excellent global summarization, it is highly expensive. HippoRAG addresses the need for fast, multi-hop knowledge routing by mimicking the hippocampal memory indexing theory. It extracts a coarse knowledge graph and utilizes the Personalized PageRank (PPR) algorithm to simulate memory spread and activation during retrieval47. During query time, entities act as "seed nodes," and PPR routes activation energy through the graph, retrieving the most highly activated interconnected passages50. For the proposed system, when a PR modifies a file, that file becomes the "seed node" in the PKG. HippoRAG’s PPR algorithms will calculate the "Activation Energy" spreading to UX and PRD nodes, mathematically defining the Confidence Scores for the Blast Radius Report.

| Parameter | Detail |
| :---- | :---- |
| **Title** | HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models |
| **Authors** | Bernal Jiménez Gutiérrez, et al. |
| **Publication Year** | 2024 |
| **Conference / Journal** | Advances in Neural Information Processing Systems (NeurIPS) |
| **DOI** | N/A |
| **PDF Link** | <https://arxiv.org/pdf/2405.14831> |
| **ArXiv Link** | 2405.14831 |
| **GitHub Repository** | <https://github.com/OSU-NLP-Group/HippoRAG> |
| **Citation Count** | \~150 |
| **Research Area** | Graph Retrieval, Retrieval-Augmented Generation, Reasoning |
| **Problem Addressed** | LLMs struggle to integrate information across disparate documents without catastrophic forgetting or incurring the massive indexing costs of GraphRAG. |
| **Core Idea** | Utilizing Personalized PageRank (PPR) over a coarse knowledge graph to simulate neural memory spread and activation during retrieval. |
| **Architecture Summary** | Uses OpenIE to build a schema-less KG. During queries, seed nodes are identified, and PPR routes activation energy through the graph to retrieve connected context. |
| **Algorithms Used** | Personalized PageRank (PPR), Open Information Extraction (OpenIE). |
| **Models Used** | LLaMA-3, Contriever, ColBERTv2. |
| **Datasets Used** | MuSiQue, 2WikiMultiHop, HotpotQA. |
| **Evaluation Methodology** | Multi-hop QA accuracy (Recall@K, F1). |
| **Strengths** | Dramatically cheaper and faster to index than Microsoft's GraphRAG while maintaining high multi-hop reasoning capabilities. |
| **Weaknesses** | OpenIE creates less structured graphs than ontologically rigorous extraction methods. |
| **Limitations** | PPR depends heavily on the correct identification of the initial seed nodes. |
| **System Component Improvement** | Graph Retrieval, Blast Radius Analysis, Confidence Scores. |
| **Decision (Adopt/Adapt/Ignore)** | **Adapt**. The system will use the modified file from the PR as the seed node and deploy HippoRAG's PPR algorithms to calculate the propagation of impact through the PKG, directly translating to the Confidence Scores in the final report. |

### **13\. Incremental Knowledge Graph Construction**

A software repository is not a static document; it mutates with every merged Pull Request. Rebuilding a massive Product Knowledge Graph from scratch upon every commit is computationally impossible in a synchronous CI/CD pipeline. LightRAG solves this by introducing an incremental update mechanism alongside a dual-level retrieval paradigm51. It generates key-value pairs for entities and implements deduplication algorithms that merge identical entities across document segments, allowing new data to be integrated without reprocessing the entire graph52. The Blast Radius Analyzer absolutely requires this incremental update capability to maintain a near real-time state of the repository.

| Parameter | Detail |
| :---- | :---- |
| **Title** | LightRAG: Simple and Fast Retrieval-Augmented Generation |
| **Authors** | Zirui Guo, Lianghao Xia, Yanhua Yu, Tu Ao, Chao Huang |
| **Publication Year** | 2024 |
| **Conference / Journal** | ArXiv (Preprint) |
| **DOI** | N/A |
| **PDF Link** | <https://arxiv.org/pdf/2410.05779> |
| **ArXiv Link** | 2410.05779 |
| **GitHub Repository** | <https://github.com/HKUDS/LightRAG> |
| **Citation Count** | \~50 |
| **Research Area** | Knowledge Graph Construction, GraphRAG |
| **Problem Addressed** | Existing GraphRAG implementations are computationally prohibitive to update when new data is added, lacking adaptability to dynamic datasets. |
| **Core Idea** | A dual-level retrieval paradigm combined with an incremental update and deduplication mechanism that avoids full graph re-indexing. |
| **Architecture Summary** | Generates key-value pairs for entities via LLM profiling and implements incremental updates by merging identical entities across segments. |
| **Algorithms Used** | Graph-based text indexing, deduplication heuristics. |
| **Models Used** | GPT-4o, various open-source extraction models. |
| **Datasets Used** | MultiHop-RAG, varied QA datasets. |
| **Evaluation Methodology** | Comparative assessment of retrieval efficiency, update costs, and multi-hop QA accuracy against Naive RAG and GraphRAG54. |
| **Strengths** | Vastly superior indexing speed and cost efficiency for dynamically changing databases55. |
| **Weaknesses** | Graph structure may become fragmented over thousands of incremental updates if deduplication thresholds drift. |
| **Limitations** | Entity resolution relies heavily on exact keyword matching and lightweight LLM heuristics. |
| **System Component Improvement** | Knowledge Graph Construction (Continuous Integration/Updates). |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. LightRAG's incremental deduplication and update mechanics are strictly required to ensure the PKG can update seamlessly when a PR is merged, avoiding catastrophic rebuild costs. |

### **14\. AST-Aware Autonomous Agents**

When AI agents attempt to fix bugs, relying on standard grep or regex searches frequently misses critical structural relationships (classes, methods, inheritances). AutoCodeRover resolves this by providing the LLM agent with Program Structure Aware APIs that search directly within the Abstract Syntax Tree (AST), combined with spectrum-based fault localization56. For the Blast Radius Analyzer, mapping a UX component (like a frontend API call) to the exact backend method requires structurally aware parsing, not naive string matching. AutoCodeRover's AST-aware context retrieval ensures that the connections made between the UX layer and the CPG are structurally sound.

| Parameter | Detail |
| :---- | :---- |
| **Title** | AutoCodeRover: Autonomous Program Improvement |
| **Authors** | Yuntong Zhang, Haifeng Ruan, Zhiyu Fan, Abhik Roychoudhury |
| **Publication Year** | 2024 |
| **Conference / Journal** | International Symposium on Software Testing and Analysis (ISSTA) |
| **DOI** | 10.1145/3650212.3680384 |
| **PDF Link** | <https://haifengruan.com/assets/pdf/autocoderover\_issta24.pdf> |
| **ArXiv Link** | 2404.05427 |
| **GitHub Repository** | <https://github.com/AutoCodeRoverSG/auto-code-rover> |
| **Citation Count** | \~100 |
| **Research Area** | Autonomous Code Analysis, AI Agents for Software Engineering |
| **Problem Addressed** | LLM agents use naive string matching to search codebases, missing the structural relationships needed to resolve complex issues. |
| **Core Idea** | Combining LLMs with AST-aware code search APIs and spectrum-based fault localization to retrieve structurally relevant context. |
| **Architecture Summary** | A two-stage process: Context Retrieval (using program-structure-aware APIs) and Patch Generation, utilizing test cases for fault localization. |
| **Algorithms Used** | Abstract Syntax Tree (AST) parsing, Spectrum-based fault localization56. |
| **Models Used** | GPT-4. |
| **Datasets Used** | SWE-bench-lite. |
| **Evaluation Methodology** | Pass@1 efficacy on SWE-bench (achieved \~19%, outperforming SWE-agent at release)57. |
| **Strengths** | Directly leverages the mathematical structure of code rather than treating it as plain text. |
| **Weaknesses** | Still relies on LLM heuristics to decide which AST nodes to investigate. |
| **Limitations** | Fault localization relies heavily on the pre-existence of a high-coverage test suite. |
| **System Component Improvement** | Implementation Graph Retrieval, Static Code Analysis. |
| **Decision (Adopt/Adapt/Ignore)** | **Adapt**. The analyzer must adopt AutoCodeRover's Program Structure Aware APIs. When connecting Code to UX, the system must search for UI component IDs specifically within AST method declarations to prevent false positives. |

### **15\. Zero-Shot Requirements Traceability**

Establishing traceability links between natural language PRDs and source code typically requires extensive manual effort or massive labeled datasets. UserTrace demonstrates a zero-shot pipeline using modern LLMs to automatically generate and validate these links58. By employing an LLM-as-a-judge for evaluation and mapping generated user requirements to ground-truth code elements via semantic overlap thresholds, it bridges the semantic gap without heavy fine-tuning58. The Blast Radius Analyzer will utilize this methodology to establish the initial edges between the PRD layer and the Implementation layer in the PKG.

| Parameter | Detail |
| :---- | :---- |
| **Title** | UserTrace: Zero-Shot Requirements Traceability Generation |
| **Authors** | (Implied via Snippet 23 context) |
| **Publication Year** | 2025 |
| **Conference / Journal** | ArXiv (Preprint) |
| **DOI** | N/A |
| **PDF Link** | <https://arxiv.org/pdf/2509.11238> |
| **ArXiv Link** | 2509.11238 |
| **GitHub Repository** | N/A |
| **Citation Count** | New |
| **Research Area** | Requirements Traceability, Documentation Parsing |
| **Problem Addressed** | LLMs fail to generate accurate links between long-context PRDs and code units without domain-specific business knowledge. |
| **Core Idea** | A zero-shot pipeline using LLMs to automatically generate and validate traceability links between user requirements and specific code components. |
| **Architecture Summary** | Employs LLM-as-a-judge for evaluation and maps generated user requirements to ground truth code elements via semantic overlap. |
| **Algorithms Used** | Group-based evaluation thresholds (Overlap threshold \> 0.5)58. |
| **Models Used** | GPT-4, Claude 3, DeepSeek R1. |
| **Datasets Used** | eTour, eAnci, SMOS. |
| **Evaluation Methodology** | Quantitative metrics (Precision, Recall, F1) combined with a Human-in-the-loop user study (Validation accuracy). |
| **Strengths** | Proves that modern LLMs can bridge the gap between PRDs and code without heavy fine-tuning. |
| **Weaknesses** | Zero-shot approaches often suffer from hallucinations in highly idiosyncratic, legacy codebases. |
| **Limitations** | Relies on group-based overlap rather than precise 1:1 functional mapping. |
| **System Component Improvement** | Knowledge Fusion (PRD to Code mapping), Human-in-the-loop AI. |
| **Decision (Adopt/Adapt/Ignore)** | **Adapt**. UserTrace’s evaluation methodology (LLM-as-a-judge) is highly relevant for autonomously validating the PKG’s internal traceability links, flagging low-confidence links for Human-in-the-loop review. |

### **16\. Explainable AI on Code Property Graphs**

Graph-based vulnerability and impact detection models typically act as black boxes, offering limited insight into _why_ a specific function is predicted to be affected59. ExplainVulD solves this by introducing a graph-based framework utilizing dual-channel embeddings (semantic Word2Vec and structural CPGs) combined with edge-aware attention to identify influential nodes and paths59. By combining attention weights and input gradients, it highlights the exact structural path causing the prediction. This is the exact mechanism the Blast Radius Analyzer needs to generate the "Explainable Evidence" section of its report, visually tracing how a modified variable flows into a UI endpoint.

| Parameter | Detail |
| :---- | :---- |
| **Title** | ExplainVulD: Explainable Vulnerability Detection in C/C++ Functions using Code Property Graphs |
| **Authors** | (Implied via Snippet 4 context) |
| **Publication Year** | 2025 |
| **Conference / Journal** | ArXiv (Preprint) |
| **DOI** | N/A |
| **PDF Link** | <https://arxiv.org/pdf/2507.16540> |
| **ArXiv Link** | 2507.16540 |
| **GitHub Repository** | N/A |
| **Citation Count** | New |
| **Research Area** | Code Property Graphs, Explainable AI, Change Impact Analysis |
| **Problem Addressed** | Graph-based detection models act as black boxes, offering limited insight into why a node is predicted to be impacted. |
| **Core Idea** | A framework utilizing dual-channel embeddings combined with edge-aware attention to identify influential nodes and paths in a CPG. |
| **Architecture Summary** | Constructs CPGs via Joern, applies semantic channels to AST tokens, and uses an explanation module combining attention weights and input gradients59. |
| **Algorithms Used** | Edge-aware attention mechanisms, Gradient-based attribution. |
| **Models Used** | Graph Neural Networks (GNNs), Word2Vec. |
| **Datasets Used** | ReVeal dataset. |
| **Evaluation Methodology** | Mean accuracy and F1 score across 30 independent runs. |
| **Strengths** | Provides explicit, edge-aware structural explanations rather than just token-level heatmaps. |
| **Weaknesses** | Feature extraction relies on older Word2Vec architectures rather than modern contextual transformer embeddings. |
| **Limitations** | Designed specifically for C/C++ via the Joern platform. |
| **System Component Improvement** | Explainable AI, Blast Radius Report Generation. |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. The edge-aware attention and gradient-attribution methodology solves the core requirement of generating an _explainable_ report, detailing the exact causal path through the CPG. |

### **17\. Deep Type Inference for Dynamic Languages**

A massive challenge in constructing an end-to-end Knowledge Graph is that the UX layer is often built in dynamically typed languages (JavaScript), making static data flow analysis highly unreliable. CodeTIDAL5 overcomes this by combining automated extraction of usage slices from a CPG with a Transformer model (CodeT5+) to reliably predict type annotations in dynamic languages60. By extracting data slices via Joern and passing them through an encoder-decoder architecture, it infers types contextually60. The Blast Radius Analyzer will utilize this approach to statically trace data flows from strictly typed backends into dynamically typed frontend UX components, maintaining the chain of evidence.

| Parameter | Detail |
| :---- | :---- |
| **Title** | CodeTIDAL5: A CodeT5+ model for Type Inference for enhanced Dataflow Analysis |
| **Authors** | (Implied via Snippet 5 context) |
| **Publication Year** | 2023 |
| **Conference / Journal** | ArXiv |
| **DOI** | N/A |
| **PDF Link** | <https://arxiv.org/pdf/2310.00673> |
| **ArXiv Link** | 2310.00673 |
| **GitHub Repository** | N/A |
| **Citation Count** | \~20 |
| **Research Area** | Static Code Analysis, CPGs |
| **Problem Addressed** | Statically analyzing dynamically-typed languages to track data flow is difficult without knowing object types at compile time. |
| **Core Idea** | Combining automated extraction of usage slices from a CPG with a Transformer model to reliably predict type annotations. |
| **Architecture Summary** | Uses Joern to query CPGs and extract data slices, feeding them into an encoder-decoder Transformer to infer types contextually. |
| **Algorithms Used** | Graph slicing, Transformer sequence generation. |
| **Models Used** | CodeT5+. |
| **Datasets Used** | Untyped JavaScript and TypeScript codebases. |
| **Evaluation Methodology** | State-of-the-art accuracy comparison against DeepTyper and TypeBert. |
| **Strengths** | Seamlessly bridges the gap between structured CPG analysis and generative LLMs. |
| **Weaknesses** | High latency for real-time inference on massive untyped monolithic codebases. |
| **Limitations** | Accuracy degrades on highly obfuscated or unusually patterned custom types. |
| **System Component Improvement** | Implementation Knowledge Graph (handling Javascript UI/Frontend code). |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. CodeTIDAL5's methodology for inferring data flow through untyped frontend layers using CPG slices is critical to maintain the continuous chain of evidence from Backend APIs to UX DOM elements. |

### **18\. Fusing CPGs with LLM Embeddings**

Fine-tuning massive LLMs for structurally complex code tasks is computationally exhaustive, yet base LLMs lack the structural awareness of a CPG61. Transducer Tuning introduces a modular "Transducer" that enriches standard code embeddings with structural and dependency vectors derived from CPGs, without requiring full fine-tuning of the backbone LLM61. It uses a Graph Vectorization Engine (GVE) to transform CPGs into feature vectors, and an Attention-Based Fusion Layer (ABFL) to fuse them with the LLM's initial embeddings61. This is the exact mechanism the Blast Radius Analyzer will use to generate embeddings for the Knowledge Graph, fusing the structural reality of the code with the semantic meaning of the PRD.

| Parameter | Detail |
| :---- | :---- |
| **Title** | Transducer Tuning: Adapting Large Language Models for Code Tasks using CPGs |
| **Authors** | (Implied via Snippet 6 context) |
| **Publication Year** | 2024 |
| **Conference / Journal** | ArXiv |
| **DOI** | N/A |
| **PDF Link** | <https://arxiv.org/pdf/2412.13467> |
| **ArXiv Link** | 2412.13467 |
| **GitHub Repository** | <https://github.com/imamnurby/Transducer-Tuning> |
| **Citation Count** | New |
| **Research Area** | LLMs, CPGs, Knowledge Fusion |
| **Problem Addressed** | Fine-tuning large models for code tasks is expensive, yet base models lack structural understanding of programmatic dependencies. |
| **Core Idea** | A modular component that enriches standard code embeddings with structural and dependency vectors derived from CPGs. |
| **Architecture Summary** | Comprises a Graph Vectorization Engine (GVE) and an Attention-Based Fusion Layer (ABFL) to fuse CPG vectors with initial LLM embeddings. |
| **Algorithms Used** | Graph Vectorization, Attention Fusion. |
| **Models Used** | Plug-and-play with any standard backbone LLM. |
| **Datasets Used** | Downstream task datasets (summarization, translation). |
| **Evaluation Methodology** | Achieves comparable performance to full fine-tuning while reducing trainable parameters by up to 99%. |
| **Strengths** | Extremely resource-efficient adaptation of general LLMs to deeply structural code tasks. |
| **Weaknesses** | Adds a latency step during the graph vectorization preprocessing phase. |
| **Limitations** | Heavily reliant on the quality and depth of the CPG extracted by upstream tools. |
| **System Component Improvement** | Knowledge Fusion, Identity Resolution. |
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. By injecting structural CPG awareness via GVE and ABFL layers into standard LLM embeddings, the system can semantically match PRD concepts to structural source code highly efficiently. |

### **19\. Contrastive Learning for Traceability**

Recovering traceability links between requirements and target artifacts historically required massive labeled datasets62. T-SimCSE bypasses this by utilizing contrastive learning (SimCSE) to calculate semantic similarity between requirements and artifacts without labels, boosted by a novel "specificity" rewarding mechanism62. If an artifact has fewer closely related connections, it receives a higher specificity reward, increasing its rank62. The Blast Radius Analyzer will adapt this specificity reward mechanism to score the similarities between PRD User Stories and UX Page descriptions, establishing the initial semantic edges in the upper layers of the Knowledge Graph.

| Parameter | Detail |
| :---- | :---- |
| **Title** | T-SimCSE: Requirements Traceability Link Recovery |
| **Authors** | (Implied via Snippet 20 context) |
| **Publication Year** | 2026 |
| **Conference / Journal** | ArXiv |
| **DOI** | N/A |
| **PDF Link** | <https://arxiv.org/pdf/2603.11800> |
| **ArXiv Link** | 2603.11800 |
| **GitHub Repository** | N/A |
| **Citation Count** | New |
| **Research Area** | Requirements Traceability, Documentation Parsing |
| **Problem Addressed** | Traceability link recovery requires large labeled datasets, which are scarce, leading to poor link accuracy. |
| **Core Idea** | A contrastive learning approach that calculates semantic similarity without labeled data, boosted by a specificity rewarding mechanism. |
| **Architecture Summary** | Uses a Pre-trained Language Model (PLM) to generate sentence embeddings, reordering target artifacts based on a specificity metric. |
| **Algorithms Used** | Cosine similarity, Contrastive learning, Specificity-based reordering. |
| **Models Used** | SimCSE (Transformer-based). |
| **Datasets Used** | 10 public traceability datasets. |
| **Evaluation Methodology** | Mean Average Precision (MAP) and recall comparisons against baseline Information Retrieval (IR) models. |
| **Strengths** | Does not require labeled data; generalizable across different project domains. |
| **Weaknesses** | Solely semantic; completely ignores the structural constraints of the codebase. |
| **Limitations** | May generate false positives if terminology heavily overlaps but logical execution paths do not. |
| **System Component Improvement** | Entity Resolution, Link Prediction (PRD to UX). |
| **Decision (Adopt/Adapt/Ignore)** | **Adapt**. T-SimCSE’s specificity reward mechanism is highly effective for scoring similarity between natural language artifacts (PRD to UX docs) to establish initial PKG edges. |

### **20\. Structural Traceability as Compile-Time Properties**

Traceability degrades silently as requirements, code, and tests evolve independently; LLM-based recovery is inherently retrospective63. ReqToCode proposes embedding "Traceables" (autogenerated language-native typed definitions from PRDs) directly into the codebase. Developers reference these constants, meaning that the removal of a requirement triggers immediate compile-time errors in the dependent code63. While theoretically sound, this approach requires developers to manually alter their workflow to reference metadata constants, which violates the core premise of an autonomous, AI-powered analyzer.

| Parameter | Detail |
| :---- | :---- |
| **Title** | ReqToCode: Structuring Traceability as Compile-Time Properties |
| **Authors** | (Implied via Snippet 21 context) |
| **Publication Year** | 2026 |
| **Conference / Journal** | ArXiv |
| **DOI** | N/A |
| **PDF Link** | <https://arxiv.org/pdf/2603.13999> |
| **ArXiv Link** | 2603.13999 |
| **GitHub Repository** | N/A |
| **Citation Count** | New |
| **Research Area** | Requirements Traceability, Static Code Analysis |
| **Problem Addressed** | Traceability degrades silently over time; recovery methods are inherently retrospective and prone to error. |
| **Core Idea** | Embedding traceability as language-native constants into the codebase, making it a compile-time verifiable property. |
| **Architecture Summary** | Autogenerates typed definitions from PRDs; developers reference these constants in their code; removal triggers compile-time errors. |
| **Algorithms Used** | Static type checking, metadata embedding. |
| **Models Used** | LLMs (for initial Traceable generation). |
| **Datasets Used** | Evaluated on internal CI/CD pipelines. |
| **Evaluation Methodology** | Structural verification of continuous alignment monitoring. |
| **Strengths** | Provides structural, Git-native audit trails and immediate failure on removal. |
| **Weaknesses** | Requires a highly disciplined engineering culture to implement and reference Traceables manually. |
| **Limitations** | Extremely difficult to retrofit onto massive, pre-existing legacy codebases. |
| **System Component Improvement** | Evidence-backed Product Knowledge Graph (PRD connection). |
| **Decision (Adopt/Adapt/Ignore)** | **Ignore**. Requiring developers to manually write specific "Traceable" enums into their source code violates the premise of an _AI-powered_ analyzer, which seeks to infer connections automatically without altering human developer workflows. |

## **1\. Timeline of Major Advancements (2015–2026)**

The evolution toward an intelligent, semantic Blast Radius Analyzer spans three distinct eras, transitioning from static, deterministic analysis to neuro-symbolic agentic systems.

| Year | Era | Advancement | Impact on Blast Radius Architecture |
| :---- | :---- | :---- | :---- |
| **2014-2015** | **The Structural Era** | Introduction of **Code Property Graphs (CPGs)**2 and dynamic Regression Test Selection (**Ekstazi**)6. | Established the mathematical foundation for representing code as a queryable graph and defining logical dependency routing. |
| **2018-2019** | **Deep Representation** | **DeepMatcher** applies deep learning to Entity Resolution8; **GNNExplainer** brings interpretability to graph networks16. | Allowed systems to match heterogeneous entities (PRD to Code) and mathematically isolate explanatory subgraphs as "evidence." |
| **2021** | **Structural NLP** | **GraphCodeBERT**21 and **Screen2Vec**27 successfully merge structural data (Data Flow, DOM layout) with Transformer pre-training. | Enabled the creation of dense, structurally aware embeddings for both Backend APIs and Frontend UX components. |
| **2024** | **The Agentic Graph-RAG Era** | **GraphRAG** (Microsoft)43, **LightRAG**51, and **HippoRAG**47 solve global reasoning and incremental KG updates. **SWE-agent**39 introduces Agent-Computer Interfaces. | The tipping point. Made massive, constantly updating Product Knowledge Graphs viable for real-time CI/CD pipelines. |
| **2025-2026** | **Zero-Shot & Traceability** | **UserTrace**58, **T-SimCSE**62, and **ExplainVulD**59 demonstrate zero-shot traceability and edge-aware explainability. | Closed the final semantic gap between human-written PRDs and programmatic execution, finalizing the explainable reporting requirements. |

## **2\. Comparison Table of Core Analyzed Papers**

| Paper Title | Primary Domain | Core Architectural Idea | Primary Limitation for Architecture |
| :---- | :---- | :---- | :---- |
| **Modeling Vulnerabilities with CPGs** | Static Analysis | Unifies AST, CFG, PDG into a graph database2. | Lacks natural language semantic understanding. |
| **Ekstazi** | Regression Test Selection | Dynamic bytecode tracing using DFS6. | Requires runtime execution of tests. |
| **DeepMatcher** | Entity Resolution | Sequence-pair classification via RNNs8. | Relies on older embeddings; requires labeled data. |
| **PyDriller** | Repository Mining | Lazy-loading Git API abstraction12. | Does not inherently parse ASTs. |
| **GNNExplainer** | Explainable AI | Mutual Information Masking for subgraphs16. | Instance-level generation is slow. |
| **GraphCodeBERT** | Code Representation | Graph-Guided Masked Attention21. | Limited context window for whole-repo analysis. |
| **Screen2Vec** | GUI / DOM Understanding | Multi-modal Autoencoder for visual/DOM data27. | Highly optimized for mobile vs web DOMs. |
| **WebArena** | Autonomous Web Crawling | Dockerized Web Environments & AXTrees29. | Difficult setup; high computational resource requirement. |
| **SWE-bench** | AI Agent Evaluation | Execution-based Benchmark on real issues34. | Computationally expensive to run full suite. |
| **SWE-agent** | AI Agents for SE | Agent-Computer Interface (ACI) tooling39. | Iterative searching is slow per Pull Request. |
| **GraphRAG (Microsoft)** | Knowledge Fusion | Leiden Community Detection & Map-Reduce43. | Exponential token costs during extraction. |
| **HippoRAG** | Graph Retrieval | Personalized PageRank routing47. | Dependent on correct seed-node identification. |
| **LightRAG** | Knowledge Graph | Incremental Graph Update and Deduplication51. | Heavy reliance on heuristic deduplication. |
| **AutoCodeRover** | AI Agents for SE | AST-aware Search APIs56. | Fault localization requires test suite coverage. |
| **UserTrace** | Requirements Traceability | Zero-Shot LLM-as-Judge evaluation58. | Prone to zero-shot hallucinations in niche repos. |
| **ExplainVulD** | Explainable AI | Edge-aware Attention on CPGs59. | Uses dated Word2Vec for token embeddings. |
| **CodeTIDAL5** | Static Code Analysis | CodeT5+ & Joern slicing for type inference60. | Latency issues on monolithic untyped frontend code. |
| **Transducer Tuning** | Knowledge Fusion | Fuses CPG and LLM embeddings via GVE61. | Adds preprocessing latency for vectorization. |
| **T-SimCSE** | Requirements Traceability | SimCSE Contrastive Learning with Specificity62. | Ignores structural constraints (purely semantic). |
| **ReqToCode** | Static Code Analysis | Compile-Time Metadata Traceables63. | Demands strict manual workflow adoption. |

## **3\. Top 30 Papers/Frameworks Ranked by Usefulness**

This ranking synthesizes the explicitly analyzed papers and highly relevant implied frameworks from the extended literature, ordered by their direct utility in building the proposed Blast Radius Analyzer.

| Rank | Paper / Framework | Research Area | Justification for Rank |
| :---- | :---- | :---- | :---- |
| 1 | **GraphRAG (Microsoft, 2024\)** | Knowledge Fusion | Provides the fundamental macro-architecture for community detection across PRD, UX, and Code layers. |
| 2 | **Modeling Vulnerabilities with CPGs (2014)** | CPGs | The absolute structural foundation required for the implementation layer of the graph. |
| 3 | **LightRAG (2024)** | Knowledge Graph Construction | Strictly required to allow the PKG to update incrementally upon every PR without catastrophic rebuilds. |
| 4 | **HippoRAG (2024)** | Graph Retrieval | Personalized PageRank provides the exact mathematical model for calculating Blast Radius confidence scores. |
| 5 | **Transducer Tuning (2024)** | Knowledge Fusion | Best method for fusing structural CPG vectors with semantic LLM embeddings efficiently. |
| 6 | **ExplainVulD (2025)** | Explainable AI | Critical for generating the visual "evidence" component of the report using edge-aware attention. |
| 7 | **Screen2Vec (2021)** | GUI / DOM Understanding | Provides the necessary embeddings to connect dynamic UX/UI layers to the structural graph. |
| 8 | **AutoCodeRover (2024)** | AI Agents | AST-aware search translates CPG structure into logic that an LLM agent can traverse. |
| 9 | **GNNExplainer (2019)** | Explainable AI | The mathematical baseline for explainable subgraph extraction. |
| 10 | **GraphCodeBERT (2021)** | Code Representation | The baseline required embedding model to understand data flow semantics. |
| 11 | **SWE-agent (2024)** | AI Agents | Agent-Computer Interfaces (ACI) are required for agents navigating ambiguous graph connections. |
| 12 | **PyDriller (2018)** | Repository Mining | The core ingestion engine for processing incoming Pull Requests and extracting diffs. |
| 13 | **WebArena (2024)** | Autonomous Web Crawling | Defines the methodology for linearizing complex DOMs into Accessibility Trees (AXTrees). |
| 14 | **UserTrace (2025)** | Requirements Traceability | Defines the zero-shot traceability pipeline design for linking PRDs to code. |
| 15 | **DeepMatcher (2018)** | Entity Resolution | Conceptually defines identity resolution across disparate and noisy text (PRD to UX). |
| 16 | **T-SimCSE (2026)** | Requirements Traceability | The "specificity" reward mechanism is vital for initial semantic link prediction. |
| 17 | **CodeTIDAL5 (2023)** | Static Code Analysis | Ensures dataflow tracing works across dynamically typed JavaScript UX components. |
| 18 | **SWE-bench (2024)** | Regression Test Selection | The required framework for objectively evaluating the final system's impact predictions. |
| 19 | **Ekstazi (2015)** | Regression Test Selection | Defines the logical DFS targets for tracing transitive dependencies. |
| 20 | **OSWorld (2024)** | GUI / DOM Understanding | Enhances WebArena's DOM strategies with OS-level multi-modal interactions30. |
| 21 | **RAPTOR (2024)** | Retrieval-Augmented Generation | Provides an alternative tree-organized retrieval strategy to GraphRAG65. |
| 22 | **DeepSeek-Coder (2024)** | LLM Backbones | Advanced open-weight LLM backbone capable of replacing GPT-4 for code synthesis41. |
| 23 | **Semantic Flow Graph (2023)** | Code Representation | Alternative to CPG for bug localization, focusing on role prediction66. |
| 24 | **Joern Platform** | Code Property Graphs | The practical implementation engine for building the required CPGs3. |
| 25 | **Think-on-Graph 2.0 (2024)** | Reasoning | Advanced multi-hop reasoning framework guiding LLM retrieval65. |
| 26 | **MultiHop-RAG (2024)** | Graph Retrieval | Benchmarking framework for evaluating graph routing efficiency54. |
| 27 | **RoBERTa (2019)** | LLM Backbones | The foundational transformer powering many of the BERT-based embedding models. |
| 28 | **WorkArena (2024)** | Autonomous Web Crawling | Complements WebArena by focusing on common knowledge work tasks and UI forms29. |
| 29 | **Sailor (2026)** | Static Code Analysis | Symbolic execution strategies orchestrating LLM-based harness construction67. |
| 30 | **ReqToCode (2026)** | Requirements Traceability | Ignored for workflow, but useful conceptually for understanding compile-time traces63. |

## **4\. Papers Grouped by Architecture Component**

To construct the Blast Radius Analyzer, the aforementioned research must be synthesized into nine distinct architectural modules.

### **Crawling**

The system must dynamically crawl the target application to build the UX layer of the graph. **WebArena (2024)** establishes the best practices for this by parsing dynamic DOM structures into linearized text (Accessibility Trees or AXTrees) that LLMs can digest without token exhaustion29. This is heavily augmented by **OSWorld (2024)** and **WorkArena (2024)**, which provide frameworks for interacting with complex UI elements like nested forms and dynamic lists29.

### **Documentation Parsing**

To ingest Product Requirements Documents (PRDs) and user stories, the system relies on advanced NLP techniques. **UserTrace (2025)** provides the zero-shot pipeline to evaluate and parse natural language user stories, preparing them for mapping to downstream code58. **T-SimCSE (2026)** utilizes contrastive learning and a specificity reward mechanism to isolate distinct features within monolithic documentation, ensuring that vague PRDs are parsed into distinct, mappable nodes62.

### **Repository Analysis**

When a Pull Request is submitted, the system must perform immediate Change Impact Analysis. **PyDriller (2018)** serves as the entry point, abstracting Git complexities to extract modified files and diffs rapidly12. **AutoCodeRover (2024)** then parses these extracted files into Abstract Syntax Trees (ASTs) to establish the immediate structural context of the change56. Because modern applications heavily utilize dynamically typed languages in the frontend, **CodeTIDAL5 (2023)** is employed to analyze untyped data flows in JavaScript/TypeScript UI files, ensuring the analysis doesn't break at the API-to-Frontend boundary60.

### **Knowledge Fusion**

Fusing natural language, visual DOMs, and structural code into a single PKG requires sophisticated architecture. **GraphRAG (2024)** provides the macro-architecture, utilizing Leiden community detection to cluster related features across these modalities43. To ensure the embeddings themselves are compatible, **Transducer Tuning (2024)** fuses structural CPG vectors with semantic text vectors via a Graph Vectorization Engine (GVE), creating unified embeddings that allow a PRD node to mathematically relate to a backend API node61.

### **Identity Resolution**

Mapping a PRD feature (e.g., "Login System") to a UX form (\<form id="auth"\>) and a backend controller requires resolving identities across disparate vocabularies. **DeepMatcher (2018)** provides the foundational framing for this by treating Entity Resolution as a sequence-pair classification problem8. By upgrading DeepMatcher's architecture with modern cross-encoder LLMs, the system can autonomously determine that differently named entities across the PRD, UX, and Code layers refer to the exact same ontological concept.

### **Knowledge Graph Construction**

The construction and persistence of the graph itself require rigid Ontology Design stored in Graph Databases like Neo4j1. The baseline implementation layer relies entirely on the **Code Property Graph (Yamaguchi, 2014\)**, unifying AST, CFG, and PDG2. Crucially, to survive the realities of a CI/CD pipeline, the graph must update dynamically. **LightRAG (2024)** provides the incremental update and deduplication algorithms necessary to modify the graph when a new PR is merged without triggering a catastrophic, computationally expensive full rebuild51.

### **Graph Retrieval**

To determine the Blast Radius, the system must route the impact of a code change outward through the graph. **HippoRAG (2024)** executes this by using the modified code file as a "seed node" and applying the Personalized PageRank (PPR) algorithm47. As activation energy flows from the seed node through the implementation layer, up into the UX layer, and finally to the PRD layer, the resulting PPR scores mathematically translate into the Confidence Scores presented in the final Blast Radius Report.

### **Reasoning**

If the graph retrieval yields ambiguous connections (e.g., a low confidence score), the system deploys an autonomous reasoning agent. **SWE-agent (2024)** provides the Agent-Computer Interface (ACI) paradigm, allowing an LLM to utilize constrained, graph-specific traversal commands to investigate the codebase logically without hallucinating39. This reasoning loop can be augmented by Human-in-the-loop AI, where developers review the agent's trajectory for highly sensitive changes.

### **Report Generation**

The final Blast Radius Report must be actionable and trustworthy. Standard impact analysis yields a binary result, but developers require evidence. **GNNExplainer (2019)** mathematically isolates the critical causal subgraph responsible for the impact prediction16. **ExplainVulD (2025)** applies edge-aware attention directly to the CPG to explain exactly how control flow changes ripple upward59. These frameworks generate the visual "supporting evidence" in the report, proving _why_ a UI element is affected by a backend change.

## **5\. Identified Research Gaps**

The synthesis of this literature reveals several critical research gaps that the proposed Blast Radius Analyzer architecture uniquely addresses:  
**1\. The Semantic-Structural Chasm:** While CPGs (Yamaguchi, 2014\) perfectly map code structure2, and tools like T-SimCSE map semantic text62, there is a gaping void in mapping dynamic semantic UX/DOM states directly to backend CPGs. Current literature treats frontend and backend analysis as disparate fields. The proposed architecture addresses this by fusing Screen2Vec DOM embeddings with GraphCodeBERT structural embeddings within a unified GraphRAG environment, explicitly creating edges between the UX layer and the Implementation layer.  
**2\. The Latency vs. Accuracy Tradeoff in GraphRAG:** Microsoft's GraphRAG yields unparalleled accuracy for global summarization but is too slow for synchronous CI/CD pipelines (e.g., blocking a PR check). By integrating LightRAG's incremental deduplication51 with HippoRAG's fast Personalized PageRank retrieval47, the proposed system can generate highly accurate Blast Radius reports in seconds, directly solving the latency block in AI-driven Continuous Integration.  
**3\. Black-Box Impact Analysis:** Traditional Change Impact Analysis and dynamic testing (Ekstazi) yield binary results (Affected / Not Affected). They do not explain _why_ to the developer. By applying GNNExplainer and ExplainVulD methodologies directly to the Product Knowledge Graph, the proposed system shifts the paradigm from "Binary Impact" to "Explainable Evidence-Backed Impact." It generates a human-readable trace (e.g., Controller\_A data-flows to Endpoint\_B, which is bound to Button\_C in DOM, defined in Requirement\_D).  
**4\. The Brittle Traceability Problem:** Approaches like ReqToCode attempt to solve traceability via rigid developer discipline (forcing compile-time definitions)63. This is brittle and fails on legacy codebases. The proposed architecture sidesteps human error by using Zero-Shot LLM Identity Resolution (inspired by UserTrace) to continuously and autonomously self-heal the graph edges as the codebase mutates, requiring zero behavioral changes from the engineering team.

## **6\. Recommended Reading Priority**

For a seamless architectural implementation, the engineering team must internalize these concepts in a specific sequence, moving from foundational structures to advanced graph retrieval mechanisms:

> 1. **Modeling and Discovering Vulnerabilities with Code Property Graphs (Yamaguchi)**: You cannot build the implementation layer of the graph without deeply understanding how ASTs, CFGs, and PDGs merge mathematically. This is the bedrock of the system.  
> 2. **From Local to Global: A Graph RAG Approach (Edge/Microsoft)**: This defines the macro-architecture of the system. Engineers must understand how entities are extracted, resolved, and clustered into feature communities.  
> 3. **LightRAG: Simple and Fast Retrieval-Augmented Generation (Guo)**: Crucial for system viability in production. The graph must be designed for incremental updates from day one; retrofitting a static graph to update dynamically later will fail.  
> 4. **HippoRAG: Neurobiologically Inspired Long-Term Memory (Gutierrez)**: The Personalized PageRank algorithm detailed here is exactly how the system will calculate its "Confidence Scores" and route the blast radius impact from Code to UX.  
> 5. **AutoCodeRover: Autonomous Program Improvement (Zhang)**: Provides the playbook for building AST-aware search APIs, which the PyDriller ingestion engine will need to traverse the CPG efficiently without relying on naive string matching.

#### **Works cited**

> 1. What is GraphRAG? Complete Guide to Graph-Based RAG in 2026 \- Articsledge, [https://www.articsledge.com/post/graphrag-retrieval-augmented-generation](https://www.articsledge.com/post/graphrag-retrieval-augmented-generation)  
> 2. Modeling and Discovering Vulnerabilities with Code Property Graphs, [https://csdl.computer.org/csdl/proceedings-article/sp/2014/4686a590/12OmNyRxFFC](https://csdl.computer.org/csdl/proceedings-article/sp/2014/4686a590/12OmNyRxFFC)  
> 3. Code property graph \- Wikipedia, [https://en.wikipedia.org/wiki/Code\_property\_graph](https://en.wikipedia.org/wiki/Code_property_graph)  
> 4. Modeling and Discovering Vulnerabilities with Code Property Graphs \- Comsecuris Security Research & Consulting, [https://comsecuris.com/papers/06956589.pdf](https://comsecuris.com/papers/06956589.pdf)  
> 5. Vulnerability detection in Java source code using a quantum convolutional neural network with self-attentive pooling, deep sequence, and graph-based hybrid feature extraction \- PMC, [https://pmc.ncbi.nlm.nih.gov/articles/PMC10978945/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10978945/)  
> 6. BabelRTS: Polyglot Regression Test Selection \- IEEE Computer Society, [https://www.computer.org/csdl/journal/ts/2025/05/10944548/25qHVvDVwcg](https://www.computer.org/csdl/journal/ts/2025/05/10944548/25qHVvDVwcg)  
> 7. Reflection-Aware Static Regression Test Selection \- Darko Marinov's Research Group at UIUC, [https://mir.cs.illinois.edu/marinov/publications/ShiETAL19ReflectionAwareRTS.pdf](https://mir.cs.illinois.edu/marinov/publications/ShiETAL19ReflectionAwareRTS.pdf)  
> 8. Deep Entity Matching with Pre-Trained Language Models \- VLDB Endowment, [https://www.vldb.org/pvldb/vol14/p50-li.pdf](https://www.vldb.org/pvldb/vol14/p50-li.pdf)  
> 9. Deep Learning for Entity Matching: A Design Space Exploration \- Computer Sciences User Pages, [https://pages.cs.wisc.edu/\~anhai/papers1/deepmatcher-sigmod18.pdf](https://pages.cs.wisc.edu/~anhai/papers1/deepmatcher-sigmod18.pdf)  
> 10. Deep Sequence-to-Sequence Entity Matching for Heterogeneous Entity Resolution | Semantic Scholar, [https://www.semanticscholar.org/paper/Deep-Sequence-to-Sequence-Entity-Matching-for-Nie-Han/e77a5cea033e0a283ea83545836b2d809344fbdb](https://www.semanticscholar.org/paper/Deep-Sequence-to-Sequence-Entity-Matching-for-Nie-Han/e77a5cea033e0a283ea83545836b2d809344fbdb)  
> 11. Structured Multi-Step Reasoning for Entity Matching Using Large Language Model \- arXiv, [https://arxiv.org/html/2511.22832](https://arxiv.org/html/2511.22832)  
> 12. PyDriller: Python Framework for Mining Software Repositories \- TU Delft Research Portal, [https://research.tudelft.nl/files/46282428/main.pdf](https://research.tudelft.nl/files/46282428/main.pdf)  
> 13. PyDriller: Python Framework for Mining Software Repositories \- Zenodo, [https://zenodo.org/record/1327411](https://zenodo.org/record/1327411)  
> 14. PyDriller \- Python Framework to analyse Git repositories \- GitHub, [https://github.com/ishepard/pydriller](https://github.com/ishepard/pydriller)  
> 15. Release 1.0 Davide Spadini \- PyDriller documentation\!, [https://pydriller.readthedocs.io/\_/downloads/en/1.12/pdf/](https://pydriller.readthedocs.io/_/downloads/en/1.12/pdf/)  
> 16. \[1903.03894\] GNNExplainer: Generating Explanations for Graph Neural Networks \- arXiv, [https://arxiv.org/abs/1903.03894](https://arxiv.org/abs/1903.03894)  
> 17. GNNExplainer: Generating Explanations for Graph Neural Networks \- PMC, [https://pmc.ncbi.nlm.nih.gov/articles/PMC7138248/](https://pmc.ncbi.nlm.nih.gov/articles/PMC7138248/)  
> 18. MixupExplainer: Generalizing Explanations for Graph Neural Networks with Data Augmentation \- NSF PAR, [https://par.nsf.gov/servlets/purl/10525356](https://par.nsf.gov/servlets/purl/10525356)  
> 19. Reliable and Faithful Generative Explainers for Graph Neural Networks \- MDPI, [https://www.mdpi.com/2504-4990/6/4/139](https://www.mdpi.com/2504-4990/6/4/139)  
> 20. GraphCodeBERT: Pre-training Code Representations with Data Flow \- SciSpace, [https://scispace.com/pdf/graphcodebert-pre-training-code-representations-with-data-3bw8tas0i0.pdf](https://scispace.com/pdf/graphcodebert-pre-training-code-representations-with-data-3bw8tas0i0.pdf)  
> 21. \[2009.08366\] GraphCodeBERT: Pre-training Code Representations with Data Flow \- ar5iv, [https://ar5iv.labs.arxiv.org/html/2009.08366](https://ar5iv.labs.arxiv.org/html/2009.08366)  
> 22. Detecting Python Vulnerabilities with GraphCodeBERT \- Microsoft Community Hub, [https://techcommunity.microsoft.com/blog/educatordeveloperblog/detecting-python-vulnerabilities-with-graphcodebert/4517909](https://techcommunity.microsoft.com/blog/educatordeveloperblog/detecting-python-vulnerabilities-with-graphcodebert/4517909)  
> 23. GraphCodeBERT: Pre-training Code Representations with Data Flow \- Semantic Scholar, [https://www.semanticscholar.org/paper/GraphCodeBERT%3A-Pre-training-Code-Representations-Guo-Ren/4083958684292f6fa2f5c7fd4f9be975e80145b6](https://www.semanticscholar.org/paper/GraphCodeBERT%3A-Pre-training-Code-Representations-Guo-Ren/4083958684292f6fa2f5c7fd4f9be975e80145b6)  
> 24. Augmenting the Interpretability of GraphCodeBERT for Code Similarity Tasks \- arXiv, [https://arxiv.org/html/2410.05275v1](https://arxiv.org/html/2410.05275v1)  
> 25. The Future of Computational Approaches for Understanding and Adapting User Interfaces \- Yue Jiang, [https://yuejiang-nj.github.io/Publications/2023CHI\_UserInterfaces/paper.pdf](https://yuejiang-nj.github.io/Publications/2023CHI_UserInterfaces/paper.pdf)  
> 26. Computational Representations for Graphical User Interfaces \- Yue Jiang, [https://yuejiang-nj.github.io/Publications/2024CHI\_Doctoral/paper.pdf](https://yuejiang-nj.github.io/Publications/2024CHI_Doctoral/paper.pdf)  
> 27. Controllable GUI Exploration \- arXiv, [https://arxiv.org/html/2502.03330v1](https://arxiv.org/html/2502.03330v1)  
> 28. Data-driven prototyping via natural-language-based GUI retrieval \- MADOC \- Uni Mannheim, [https://madoc.bib.uni-mannheim.de/64335/1/s10515-023-00377-x.pdf](https://madoc.bib.uni-mannheim.de/64335/1/s10515-023-00377-x.pdf)  
> 29. (a) WorkArena \- arXiv, [https://arxiv.org/html/2403.07718v2](https://arxiv.org/html/2403.07718v2)  
> 30. GitHub \- wendell0218/GVA-Survey: Official repository of the paper "Generalist Virtual Agents: A Survey on Autonomous Agents Across Digital Platforms", [https://github.com/wendell0218/GVA-Survey](https://github.com/wendell0218/GVA-Survey)  
> 31. WebArena-Infinity: Generating Browser Environments with Verifiable Tasks at Scale, [https://webarena.dev/webarena-infinity/](https://webarena.dev/webarena-infinity/)  
> 32. Asaf-Yehudai/LLM-Agent-Evaluation-Survey: Top papers related to LLM-based agent evaluation \- GitHub, [https://github.com/Asaf-Yehudai/LLM-Agent-Evaluation-Survey](https://github.com/Asaf-Yehudai/LLM-Agent-Evaluation-Survey)  
> 33. VisualWebArena: Evaluating Multimodal Agents on Realistic Visual Web Tasks \- GitHub, [https://github.com/web-arena-x/visualwebarena](https://github.com/web-arena-x/visualwebarena)  
> 34. SWE-BENCH: CAN LANGUAGE MODELS RESOLVE REAL-WORLD GITHUB ISSUES? \- OpenReview, [https://openreview.net/pdf?id=VTF8yNQM66](https://openreview.net/pdf?id=VTF8yNQM66)  
> 35. SWE-bench: Can Language Models Resolve Real-World GitHub Issues? \- arXiv, [https://arxiv.org/abs/2310.06770](https://arxiv.org/abs/2310.06770)  
> 36. SWE-bench: Can Language Models Resolve Real-world Github Issues? | OpenReview, [https://openreview.net/forum?id=VTF8yNQM66¬eId=aEzy6Mw6ml](https://openreview.net/forum?id=VTF8yNQM66&noteId=aEzy6Mw6ml)  
> 37. SWE-bench: Can Language Models Resolve Real-world Github Issues?, [https://github.com/swe-bench/SWE-bench](https://github.com/swe-bench/SWE-bench)  
> 38. ‪Ofir Press‬ \- ‪Google Scholar‬, [https://scholar.google.com/citations?user=LeHa8psAAAAJ\&hl=en](https://scholar.google.com/citations?user=LeHa8psAAAAJ&hl=en)  
> 39. Learn more about the project. \- SWE-agent documentation, [https://swe-agent.com/0.7/background/](https://swe-agent.com/0.7/background/)  
> 40. Agentic AI for Software: thoughts from Software Engineering community \- arXiv, [https://arxiv.org/html/2508.17343v3](https://arxiv.org/html/2508.17343v3)  
> 41. NeurIPS Poster SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering, [https://neurips.cc/virtual/2024/poster/93753](https://neurips.cc/virtual/2024/poster/93753)  
> 42. YennNing/Awesome-Code-as-Agent-Harness-Papers \- GitHub, [https://github.com/YennNing/Awesome-Code-as-Agent-Harness-Papers](https://github.com/YennNing/Awesome-Code-as-Agent-Harness-Papers)  
> 43. From Local to Global: A Graph RAG Approach to Query-Focused Summarization \- ar5iv, [https://ar5iv.labs.arxiv.org/html/2404.16130](https://ar5iv.labs.arxiv.org/html/2404.16130)  
> 44. What is GraphRAG? \- IBM, [https://www.ibm.com/think/topics/graphrag](https://www.ibm.com/think/topics/graphrag)  
> 45. GraphRAG: Knowledge Graph \+ RAG Next-Generation | MI \- 超智諮詢, [https://www.meta-intelligence.tech/en/insight-graphrag](https://www.meta-intelligence.tech/en/insight-graphrag)  
> 46. Retrieval Augmented Generation with Knowledge Graphs \- Jeremi Levesque, [https://jeremilevesque.com/reviews/retrieval-augmented-generation-with-knowledge-graphs/](https://jeremilevesque.com/reviews/retrieval-augmented-generation-with-knowledge-graphs/)  
> 47. HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models \- arXiv, [https://arxiv.org/html/2405.14831v1](https://arxiv.org/html/2405.14831v1)  
> 48. HippoRAG/README.md at main \- GitHub, [https://github.com/OSU-NLP-Group/HippoRAG/blob/main/README.md](https://github.com/OSU-NLP-Group/HippoRAG/blob/main/README.md)  
> 49. From RAG to Memory: Non-Parametric Continual Learning for Large Language Models \- arXiv, [https://arxiv.org/html/2502.14802v1](https://arxiv.org/html/2502.14802v1)  
> 50. HippoRAG 2: From RAG to Memory \- GitHub, [https://github.com/osu-nlp-group/hipporag](https://github.com/osu-nlp-group/hipporag)  
> 51. lightrag: simple and fast retrieval-augmented generation \- Jeong Yitae \- Medium, [https://jeongiitae.medium.com/lightrag-simple-and-fast-retrieval-augmented-generation-bc6ccd5264a1](https://jeongiitae.medium.com/lightrag-simple-and-fast-retrieval-augmented-generation-bc6ccd5264a1)  
> 52. LightRAG, [https://lightrag.github.io/](https://lightrag.github.io/)  
> 53. LightRAG: Simple and Fast Retrieval-Augmented Generation \- ACL Anthology, [https://aclanthology.org/2025.findings-emnlp.568.pdf](https://aclanthology.org/2025.findings-emnlp.568.pdf)  
> 54. LightRAG: Simple and Fast Retrieval-Augmented Generation \- OpenReview, [https://openreview.net/forum?id=bbVH40jy7f](https://openreview.net/forum?id=bbVH40jy7f)  
> 55. LarFii/LightRAG-hku: "LightRAG: Simple and Fast Retrieval-Augmented Generation" \- GitHub, [https://github.com/LarFii/LightRAG-hku](https://github.com/LarFii/LightRAG-hku)  
> 56. AutoCodeRover: Autonomous Program Improvement \- Haifeng Ruan, [https://haifengruan.com/assets/pdf/autocoderover\_issta24.pdf](https://haifengruan.com/assets/pdf/autocoderover_issta24.pdf)  
> 57. AutoCodeRover: Autonomous Program Improvement \- GitHub, [https://github.com/AutoCodeRoverSG/auto-code-rover](https://github.com/AutoCodeRoverSG/auto-code-rover)  
> 58. UserTrace: User-Level Requirements Generation and Traceability Recovery from Software Project Repositories \- arXiv, [https://arxiv.org/html/2509.11238v1](https://arxiv.org/html/2509.11238v1)  
> 59. Explainable Vulnerability Detection in C/C++ Using Edge-Aware Graph Attention Networks \- arXiv, [https://arxiv.org/pdf/2507.16540](https://arxiv.org/pdf/2507.16540)  
> 60. arXiv:2310.00673v2 \[cs.LG\] 4 Oct 2023, [https://arxiv.org/pdf/2310.00673](https://arxiv.org/pdf/2310.00673)  
> 61. Transducer Tuning: Efficient Model Adaptation for Software Tasks Using Code Property Graphs \- arXiv, [https://arxiv.org/pdf/2412.13467?](https://arxiv.org/pdf/2412.13467)  
> 62. Enhancing Requirements Traceability Link Recovery: A Novel Approach with T-SimCSE \- arXiv, [https://arxiv.org/pdf/2603.11800](https://arxiv.org/pdf/2603.11800)  
> 63. ReqToCode: Embedding Requirements Traceability as a Structural Property of the Codebase \- arXiv, [https://arxiv.org/html/2603.13999](https://arxiv.org/html/2603.13999)  
> 64. RUCAIBox/awesome-agent-harness: The official GitHub page for the paper "Agent Systems with Harness Engineering", [https://github.com/RUCAIBox/awesome-agent-harness](https://github.com/RUCAIBox/awesome-agent-harness)  
> 65. Awesome-GraphRAG: A curated list of resources (surveys, papers, benchmarks, and opensource projects) on graph-based retrieval-augmented generation. \- GitHub, [https://github.com/DEEP-PolyU/Awesome-GraphRAG](https://github.com/DEEP-PolyU/Awesome-GraphRAG)  
> 66. Pre-training Code Representation with Semantic Flow Graph for Effective Bug Localization \- arXiv, [https://arxiv.org/pdf/2308.12773](https://arxiv.org/pdf/2308.12773)  
> 67. Guiding Symbolic Execution with Static Analysis and LLMs for Vulnerability Discovery \- arXiv, [https://arxiv.org/pdf/2604.06506](https://arxiv.org/pdf/2604.06506)

---

# Top 50 Relevant Repositories - ChatGPT

# Top 50 Relevant Repositories

We identified dozens of open-source projects spanning the system’s components. Below are the **50 most relevant** projects, with metadata. (Numbers come from GitHub pages; citations show stars as examples.) Each is followed by a brief technical sketch:

- **OpenHands/openhands** – GitHub: [OpenHands/OpenHands](https://github.com/OpenHands/openhands) – ⭐81.5k, 10.4k forks, MIT, last updated Jul 21, 2026, **Python/TypeScript**. Maintainer: OpenHands. _(Install: `npm install -g @openhands/agent-canvas`.)_  
  _Purpose:_ An “AI-driven development” control center that manages AI agents and automations. Agent Canvas UI + local agent server (Docker-compose).  
  _Tech:_ Node/React frontend; Python backends (agents, workflows). Uses Docker, uv for Python, etc.  
  _Reusable:_ Agent orchestration (OpenHands SDK, Agent Canvas), Slack/GitHub integrations.  
  _Limitations:_ Very large platform; best as reference for end-to-end agent system.  
  _Use:_ **Inspiration/Framework** for agent orchestrator (e.g. reuse Agent SDK modules).

- **AntonOsika/gpt-engineer** – GitHub: [antonosika/gpt-engineer](https://github.com/AntonOsika/gpt-engineer) – ⭐55.2k, 7.3k forks, MIT, last release Jun 6, 2024, **Python**. Community project (maintainers from Lovable.dev).  
  _Purpose:_ CLI “coding agent” framework that scaffolds and improves whole code projects from a prompt. It iteratively builds software by prompting LLMs (OpenAI/Anthropic/GPT).  
  _Arch:_ Stages (prompt→plan→generate→verify). Uses local filesystem, container environments, API keys.  
  _Reusable:_ Multi-step agent pattern; templating and project structure handling.  
  _Alg:_ Orchestrated LLM calls, planning.  
  _Study:_ Look at how `bench` tool manages LLM interactions and how agents are defined.  
  _Use:_ **Reference/Component** for LLM-driven code generation workflows (not specific to blast radius, but multi-file flow is instructive).

- **Aider-AI/aider** – GitHub: [Aider-AI/aider](https://github.com/Aider-AI/aider) – ⭐47.6k, 4.7k forks, Apache-2.0, last updated Aug 9, 2025, **Python/CSS/JS**. Maintainer: Aider-AI. _(Install: `pip install aider-install`.)_  
  _Purpose:_ AI pair-programmer CLI. Builds a persistent “map” of your codebase (via AST graph) and lets you ask questions or give commands (text/voice) to modify code.  
  _Arch:_ Crawls project with Tree-sitter, stores symbol-relationship graph in SQLite. Integrates with multiple LLMs (OpenAI/Gemini/Claude/Deepseek).  
  _Reuse:_ Codebase indexing into a graph (SQLite CPG) and query interface.  
  _Tech:_ Python, `polyglot-ast`, Tree-sitter grammars, Click CLI, concurrent async.  
  _Study:_ Key modules: codebase scanning (`.pyproject.toml` hints), context manager, commit automation.  
  _Use:_ **Direct Use/Reference** for code analysis component. Particularly reuse its indexing and context retrieval for impact analysis.

- **Pythagora-io/gpt-pilot** – GitHub: [Pythagora-io/gpt-pilot](https://github.com/Pythagora-io/gpt-pilot) – ⭐33.7k, 3.5k forks, MIT, _archived_ (last active mid-2026), **Python/TypeScript**. Maintainer: Pythagora (now defunct).  
  _Purpose:_ (Formerly) an “AI developer” that builds apps end-to-end from prompts.  
  _Status:_ No longer maintained; discovered malicious code (worm) in Aug 2025.  
  _Insight:_ Architecture of a multi-component agent (CLI, DB, services).  
  _Use:_ **Reference Only** – not recommended for production (security issues). But its multi-step agent design and VSCode integration are instructive.

- **tirth8205/code-review-graph** – GitHub: [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph) – ⭐24.2k, 2.3k forks, MIT, last updated Jul 18, 2026, **Python**. Maintainer: @tirth8205.  
  _Purpose:_ Builds a local **code intelligence graph** for the codebase to support “blast radius” analysis. It maps symbols and call/AST relationships so AI tools see only relevant context.  
  _Arch:_ Uses Tree-sitter to parse code (multiple languages), then stores edges (AST parent/child, calls) in SQLite. Offers a CLI and FastAPI server.  
  _Modules:_ `code_review_graph` (parsing/indexing), `code_review_mcp` (MCP integration), front-end CLI scripts.  
  _Tech:_ Python, Tree-sitter grammars, SQLite3, starlette/FastAPI for a local API.  
  _Reuse:_ Directly reuse its graph-construction and querying logic. The SQLite CPG (Code Property Graph) is especially relevant for impact analysis.  
  _Algorithms:_ Traverses AST to build graph; uses string similarity for symbol matching.  
  _Study:_ Key files: AST/index builders in `/code_review_graph/`; Graph query in `/code_review_mcp/`.  
  _Use:_ **Direct Dependency** for static analysis sub-system (impact queries, context reduction).

- **browserbase/stagehand** – GitHub: [browserbase/stagehand](https://github.com/browserbase/stagehand) – ⭐23.6k, 1.6k forks, MIT, v3.7.3 (July 2026), **TypeScript**. Maintainer: Browserbase (Active).  
  _Purpose:_ An SDK for building _browser agents_. It provides a Playwright-based sandbox and high-level agent interface.  
  _Arch:_ Exposes primitives (`page.goto`, `page.click`, etc.) and agent orchestration (sessions, skills) in an LLM-agent framework.  
  _Reuse:_ Ideal for the “autonomous crawler” component.  
  _Tech:_ Node.js, TypeScript, Playwright under the hood.  
  _Study:_ Inspect `packages/agent` and `packages/browser`.  
  _Use:_ **Direct Dependency** for crawling UI: run agents to explore web app automatically (component: “Autonomous Web Crawler/UI Understanding”).

- **semgrep/semgrep** – GitHub: [semgrep/semgrep](https://github.com/returntocorp/semgrep) – ⭐16k, 996 forks, LGPL-2.1, v1.170.0 (Jul 15, 2026), **OCaml/Python**. Maintainers: Return To Corp.  
  _Purpose:_ Static code analysis engine that finds patterns/bugs in code. Supports many languages.  
  _Arch:_ Core engine in OCaml, rules in YAML/SGREP syntax. Python CLI wraps it.  
  _Reuse:_ As a general-purpose code scanner for impact analysis (e.g. “what code patterns are changed by this PR?”).  
  _Tech:_ OCaml parsing libraries, Python for CLI/UI, multiprocessing.  
  _Study:_ Not trivial, but can write custom rules or use `semgrep --config` to detect code elements.  
  _Use:_ **Tool** for code property detection (plug into pipeline to flag risky patterns or affected code).

- **smol-ai/developer** – GitHub: [smol-ai/developer](https://github.com/smol-ai/developer) – ⭐12.2k, 1.1k forks, MIT, updated Mar 2026, **Python**. Maintainer: Morph.  
  _Purpose:_ “Junior developer” AI agent. Generates or bootstraps an entire codebase from a product spec.  
  _Arch:_ Simple CLI that takes a prompt, calls an LLM (GPT-4 by default), and writes files. Has “debug” mode scanning errors.  
  _Reuse:_ Agent pattern for code scaffolding.  
  _Study:_ `main.py`, and the internal prompts in `smol_dev/`.  
  _Use:_ **Reference** for agent-based code synthesis; could adapt its project scaffolding concept for initial knowledge base or prototyping features.

- **SWE-agent/SWE-agent** – GitHub: [SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) – ⭐19.9k, 2.2k forks, MIT, v1.1.0 (May 22, 2025), **Python/JS/CSS**. Maintainers: Princeton NLP.  
  _Purpose:_ Autonomous agent that reads GitHub issues and attempts to fix them by editing code using LLMs.  
  _Arch:_ CLI interface, local file edits, uses LLMs iteratively with self-checks.  
  _Reuse:_ The idea of automated PR analysis and code-fixing.  
  _Tech:_ Python, uses `repo`, `self_critic` modules.  
  _Use:_ **Reference/Library** for PR analysis ideas. Not plug-and-play for “blast radius”, but shows agentic fix flows.

- **steel-dev/steel-browser** – GitHub: [steel-dev/steel-browser](https://github.com/steel-dev/steel-browser) – ⭐7.4k, 949 forks, Apache-2.0, v0.5.3-beta (Apr 24, 2026), **TypeScript**. Maintainers: Steel.dev.  
  _Purpose:_ “Open Source Browser API for AI Agents”. Provides a headless browser sandbox (via remote API) for automating web tasks.  
  _Arch:_ Node.js + Dockerized Chromium. Offers HTTP/WebSocket API for navigation, DOM queries, etc.  
  _Reuse:_ Use instead of Playwright directly – simplifies spinning up browser for AI.  
  _Study:_ Browser sandbox API usage.  
  _Use:_ **Direct Dependency** for “browser use” component (crawl or inspect UI from code).

- **Rahulnyk/knowledge_graph** – GitHub: [rahulnyk/knowledge_graph](https://github.com/rahulnyk/knowledge_graph) – ⭐3.2k, 524 forks, MIT, last commit Feb 12, 2026, **Jupyter/Python**. Maintainer: Rahul.  
  _Purpose:_ Convert technical documents into a semantic knowledge graph (using GPT).  
  _Arch:_ Notebook code that does text chunking, LLM triple extraction, and stores nodes/edges (Neo4j + Milvus).  
  _Reuse:_ Shows pattern for product documentation → graph.  
  _Use:_ **Conceptual Reference** for docs parsing. Could adapt the pipeline for PRDs/READMEs.

- **Bevel-Software/code-to-knowledge-graph** – GitHub: [Bevel-Software/code-to-knowledge-graph](https://github.com/Bevel-Software/code-to-knowledge-graph) – ⭐167, 17 forks, MPL-2.0, last commit Jun 4, 2025, **Java/Kotlin/ANTLR**. Maintainer: edujuan.  
  _Purpose:_ Extract knowledge graph from source code (Java/Kotlin) via ASTs.  
  _Arch:_ ANTLR grammars to parse code into intermediate representation, then to graph.  
  _Use:_ Potentially reusable for code parse to graph, but limited to JVM languages.

- **DerwenAI/strwythura** – GitHub: [DerwenAI/strwythura](https://github.com/DerwenAI/strwythura) – ⭐229, 24 forks, MIT, v2.1.1 (Apr 15, 2026), **Python**. Maintainer: Derwen.  
  _Purpose:_ Tutorial toolkit to build an “entity-resolved knowledge graph” from text/data. Produces a Streamlit Q&A app.  
  _Arch:_ Step scripts (ER, NLP, ontology linking, embedding, graph analytics). Uses spaCy, Senzing, RDFlib, NetworkX, etc..  
  _Use:_ **Reference**. Good for complex KGC pipeline ideas (ontology, embeddings, GraphRAG). Not a drop-in library.

- **neo4j-labs/llm-graph-builder** – GitHub: [neo4j-labs/llm-graph-builder](https://github.com/neo4j-labs/llm-graph-builder) – ⭐5.0k, 848 forks, Apache-2.0, v0.8.6 (Jun 11, 2026), **TypeScript/Python**. Maintainers: Neo4j Labs.  
  _Purpose:_ Full-stack app: Upload unstructured data (PDFs, HTML, video transcripts, etc.), call LLMs to extract entities/relations, and build a Neo4j graph. Chat interface included.  
  _Arch:_ Backend (Python/FastAPI + LangChain), React frontend.  
  _Use:_ **Direct/Reference**. Backend modules (LLM→triples) could be repurposed; front-end not needed if UI not required.

- **PyDriller/PyDriller** – GitHub: [ishepard/pydriller](https://github.com/ishepard/pydriller) – ⭐967, 156 forks, Apache-2.0, updated Jul 1, 2026, **Python**.  
  _Purpose:_ Python library to mine Git repositories. Iterates through commits easily (diffs, author, files changed).  
  _Use:_ **Direct** for “pull request analysis” component – e.g. analyze commit history for changes/impact.  

- **koknat/callGraph** – GitHub: [koknat/callGraph](https://github.com/koknat/callGraph) – ⭐339, 33 forks, GPL-3.0, last commit Jan 2024, **Kotlin/Java**.  
  _Purpose:_ Generates cross-language static call graphs by wrapping compilers (Java, C++, etc.).  
  _Use:_ Possibly for “call graph construction” in impact analysis (identify which functions call a changed function).  

- **Aider/selenium** or **Aider/playwright** – (Not searched, skip due to smaller usage.)

- **GraphRAG Frameworks:** No single repo, but LlamaIndex or LangChain have RAG with graphs.  
  - **Neo4j/LlamaIndex integration** – [Docs](https://neo4j.com/labs/graph-data-science/).  
  - **LlamaIndex (old)** – could use Vector DB + Graph, but no specific “GraphRAG” repo beyond above.  
  - We mention GraphRAG conceptually under graph retrieval below.

- **OpenHands/openhands (already above).**

- **OpenHands/software-agent-sdk** – GitHub: [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) – ⭐919, 367 forks, MIT, 2.067k commits, **Python**.  
  _Purpose:_ SDK to build AI agents (LLM interface, memory, tool management) – the engine behind OpenHands agents (V1).  
  _Use:_ **Direct** for agent framework logic (tool calls, context management).

- **OpenHands/agent-canvas** – GitHub: [OpenHands/agent-canvas](https://github.com/OpenHands/agent-canvas) – ⭐206, 97 forks, MIT, 787 commits, **Python/TypeScript**.  
  _Purpose:_ The frontend+backend for the Agent Canvas (running agents locally).  
  _Use:_ UI not needed, but can study how it orchestrates microservices.

- **ArchGuard/archguard-metric** – GitHub topic “archguard” shows [archguard/metric](https://github.com/archguard/metric) (3 stars). Not mature; skip.

- **SSumit2214/git-archetype** etc – (not found; skip niche).

- **Graphite/graph** (GitHub repo unknown, skip closed).  
- **Sourcegraph/cody** (closed source, skip).

- **Microsoft RAG tools** – not open.  

- **GitHub Copilot CLI / Codebuddy** – not open.

- **Production GraphDB**: use Neo4j/Arango. But not code.

- **Playwright agents:**  
  - [PadmarajNidagundi/playwright-AI-agent-pom-mcp-server](https://github.com/padmarajnidagundi/Playwright-AI-Agent-POM-MCP-Server) (⭐36) – uses Playwright + LLM for testing.  
  _Use:_ Example of integrating Playwright with GPT for test automation.  

- **Browserable (AI browsing)** – GitHub: [browserable/browserable](https://github.com/browserable/browserable) – ⭐1.2k, 103 forks, MIT. CLI+UI for browser tasks.  
  _Use:_ **Direct/Reference** for autonomous web crawling/UI tasks.  

- **Devika (stitionai/devika)** – ⭐19.5k, 2.0k forks, MIT, early stage.  
  _Use:_ Experimental agent (“open-source Devin”). Shows agentic planning + web browsing. Worth scanning but immature.

- **Languagetoolkit** – no, skip.

- **LangChain** – framework, but not a repo to list here.  
- **LlamaIndex** – repository was renamed (GPT Index), but it’s more an engine (not directly relevant code for blast radius).  

- **Knowledge Fusion / ER:** likely no widely-used library beyond what’s above.

- **Static analysis:**  
  - **Joern** (above).  
  - **Semgrep** (above).  
  - **Bandit/PyLint** (common tools, skip those).  

- **Test impact:** none notable open.  

- **Misc:** Not needed.

## Component-to-Repository Mapping

Below we map each architecture component to the best-fitting open-source tools:

- **Web Crawler / UI Analysis:** Stagehand, Steel Browser, Browserable – all provide **autonomous browser automation** (Playwright-based or custom). Example: Stagehand is a Playwright-based agent SDK, Steel provides a headless browser API, Browserable adds a web agent platform.  
- **Documentation Parsing / Text → Knowledge Graph:** Neo4j LLM Graph Builder (extracts entities from docs into Neo4j), DerwenAI/strwythura (ontology pipeline) and rahulnyk/knowledge_graph (LLM → KG from text) – all demonstrate transforming docs/PRDs to graph form.  
- **Code Repository Analysis:** code-review-graph (AST→SQLite graph), Joern (CPG for code), Semgrep (pattern scanning), PyDriller (git mining) – these cover static analysis, call-graph building, and historical mining.  
- **Knowledge Graph Storage/Retrieval:** Neo4j (as above), plus LlamaIndex/GraphRAG pattern (not a single repo) – e.g., LangChain or LlamaIndex can query Neo4j.  
- **Pull Request / Issue Analysis:** SWE-agent (fixing issues with LLM), PyDriller, Code-review-graph (context for diffs).  
- **AI Code Review / Agents:** Aider, Devika, OpenHands, Smol Developer – all are autonomous “AI developer” agents. OpenHands provides a framework (Agent SDK), Aider provides a CLI assistant, Devika is an experimental full agent, Smol is a “junior dev” agent.  
- **Regression Test Selection:** (No direct matches; potential reuse of code analysis to pick tests.)  
- **Explainable Reports:** (Not a single repo; likely implement by combining other outputs.)

## Recommended Repositories by Subsystem

- **Crawler & UI Engine:** _Stagehand_, _Steel Browser_, _Browserable_. These let an agent programmatically browse and inspect web UI without writing the low-level code. Use them as-is rather than custom crawling.  
- **Knowledge Graph Builder:** _Neo4j LLM Graph Builder_ (for doc ingest and KG creation) and _Code-to-KG_ (for code parse to graph). Also consider _Rahul’s Knowledge_Graph_ and _Strwythura_ for document-to-graph ideas.  
- **Static Code Analysis:** _code-review-graph_, _Joern_, _Semgrep_. code-review-graph is highly relevant (builds an AST graph); Joern provides deep code property graph for C/Java; Semgrep finds patterns. For call graphs, _callGraph_ can help.  
- **Repository Mining:** _PyDriller_. Use to iterate through commits/PRs to see which files/methods changed.  
- **PR Analysis / AI Review Agents:** _SWE-agent_ and _Aider_. SWE-agent for thinking-through-fixes, Aider for in-IDE reviews. _OpenHands Agent SDK_ for integrating agents into workflows.  
- **Retrieval Augmented Generation (GraphRAG):** Use _Neo4j_ + LLMs or LlamaIndex. The _Graph Builder_ above includes a chat interface.  
- **Agent Frameworks:** _OpenHands_ (Agent Canvas), _GPT-Engineer_, _Smol Developer_ – these show how to build multi-step coding agents.  

## High-Leverage Repository Combinations

To cover ~70–80% of the system, the following combined set is powerful:

- **code-review-graph + Semgrep + Joern** – covers nearly all static code analysis needs, with a graph DB and pattern engine.  
- **Stagehand + Steel-browser + Browserable** – for web crawling; using two of these avoids reinventing the browser agent.  
- **Neo4j-LLM-Graph-Builder + Rahul’s Knowledge_Graph** – for parsing docs/PRDs into graph.  
- **Aider or SWE-agent + OpenHands Agent SDK** – for putting it all together as interactive agents.  
- **PyDriller** – to mine repository history and feed into impact analysis.  

This combination would **greatly reduce implementation effort**. For example, code-review-graph already builds a blast-radius-style code graph, so much of “static analysis + impact graph” is done. Stagehand/Steel handle UI crawling. Neo4j-LLM builder handles doc-to-KG. That’s ~80% of the needed features out-of-the-box.

## Production-Quality Code to Study

Key codebases worth reading for best practices:

- **Aider** (47k★) – sophisticated code-indexing and LLM integration. Study how it maintains and queries code context.  
- **Stagehand** (23k★) – agent framework for web automation. Learn its workflow and modular design.  
- **Steel Browser** (7.4k★) – see how it encapsulates a browser API for headless automation.  
- **code-review-graph** (24k★) – exhibits a practical SQLite-based code graph builder for large repos.  
- **Semgrep** (16k★) – industry-grade static analysis engine, see how it matches code patterns.  
- **Joern** (3.3k★) – production CPG system (Scala), for complex code queries.  
- **OpenHands** (81k★) – although large, it shows how to scale multi-agent devops.  

These projects have _mature architectures and coding styles_ that can inform your implementation.

## Implementation Plan

1. **Web Crawling Layer:** Leverage _Stagehand_ and _Steel-browser_. E.g., use Stagehand’s agent scripts to navigate the app, and Steel’s API to fetch DOM/JS state. This replaces building a custom crawler from scratch.  
2. **Document Parsing & KG:** Use _Neo4j LLM Graph Builder_’s backend pipeline to ingest PRDs/READMEs into Neo4j. (Its schemas can be reused.) Combine with custom NLP steps (like those in _Strwythura_ or _Rahul’s graph_).  
3. **Code Repository Analysis:** Integrate _code-review-graph_ to index the repo. Use its graph for impact queries (“which functions/classes are touched by this change?”). Supplement with _Semgrep_ rules to tag relevant code patterns. For call graphs, use _Joern_ or _callGraph_.  
4. **Knowledge Graph Construction:** Store all extracted entities/relations in a graph DB (e.g. Neo4j). Use LLM-powered RAG for querying (e.g. Neo4j GraphQL + LangChain).  
5. **Pull-Request Analysis:** Run _PyDriller_ on PR diffs to see changed files. For each diff, query the code graph to find downstream impacts. Optionally trigger _SWE-agent_-like suggestions for fixes or _Aider_-style summaries.  
6. **Agents & Orchestration:** Use _OpenHands Agent SDK_ or _Aider_ as a framework to glue these pieces. For instance, an “impact analysis agent” that runs crawlers, updates graphs, and explains findings.  
7. **Explainable Reporting:** Build on existing logs/reports from these tools. For example, _code-review-graph_ outputs context reduction ratios; incorporate those into the final “blast radius” report with references to code evidence.  

By reusing the above components instead of building each from scratch, development time can be cut dramatically. For example, Stagehand handles multi-page web navigation, code-review-graph gives an AST graph, and Neo4j builder provides an end-to-end KG pipeline – together covering the core blast-radius functionality.

**Sources:** We derived the above repository information from the projects’ GitHub pages and documentation, among others, as cited. Each component and recommendation is grounded in these source descriptions.

---
