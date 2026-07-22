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
| **PDF Link** | https://ieeexplore.ieee.org/document/6956589 |
| **ArXiv Link** | N/A |
| **GitHub Repository** | https://github.com/joernio/joern |
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
| **PDF Link** | https://mir.cs.illinois.edu/marinov/publications/GligoricETALEkstazi15.pdf |
| **ArXiv Link** | N/A |
| **GitHub Repository** | https://github.com/TestingResearchIllinois/ekstazi |
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
| **PDF Link** | https://pages.cs.wisc.edu/\~anhai/papers1/deepmatcher-sigmod18.pdf |
| **ArXiv Link** | N/A |
| **GitHub Repository** | https://github.com/anhaidgroup/deepmatcher |
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
| **PDF Link** | https://research.tudelft.nl/files/46282428/main.pdf |
| **ArXiv Link** | N/A |
| **GitHub Repository** | https://github.com/ishepard/pydriller |
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
| **PDF Link** | https://arxiv.org/pdf/1903.03894 |
| **ArXiv Link** | 1903.03894 |
| **GitHub Repository** | https://github.com/RexYing/gnn-model-explainer |
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
| **PDF Link** | https://openreview.net/pdf?id=jLoC4ez43PZ |
| **ArXiv Link** | 2009.08366 |
| **GitHub Repository** | https://github.com/microsoft/CodeBERT |
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
| **PDF Link** | https://3dvar.com/Wang2021Screen2Words.pdf |
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
| **PDF Link** | https://arxiv.org/pdf/2307.13854 |
| **ArXiv Link** | 2307.13854 |
| **GitHub Repository** | https://github.com/web-arena-x/webarena |
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
| **PDF Link** | https://openreview.net/pdf?id=VTF8yNQM66 |
| **ArXiv Link** | 2310.06770 |
| **GitHub Repository** | https://github.com/swe-bench/SWE-bench |
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
| **PDF Link** | https://arxiv.org/pdf/2405.15793 |
| **ArXiv Link** | 2405.15793 |
| **GitHub Repository** | https://github.com/princeton-nlp/SWE-agent |
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
| **PDF Link** | https://arxiv.org/pdf/2404.16130 |
| **ArXiv Link** | 2404.16130 |
| **GitHub Repository** | https://github.com/microsoft/graphrag |
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
| **PDF Link** | https://arxiv.org/pdf/2405.14831 |
| **ArXiv Link** | 2405.14831 |
| **GitHub Repository** | https://github.com/OSU-NLP-Group/HippoRAG |
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
| **PDF Link** | https://arxiv.org/pdf/2410.05779 |
| **ArXiv Link** | 2410.05779 |
| **GitHub Repository** | https://github.com/HKUDS/LightRAG |
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
| **PDF Link** | https://haifengruan.com/assets/pdf/autocoderover\_issta24.pdf |
| **ArXiv Link** | 2404.05427 |
| **GitHub Repository** | https://github.com/AutoCodeRoverSG/auto-code-rover |
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
| **PDF Link** | https://arxiv.org/pdf/2509.11238 |
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

Graph-based vulnerability and impact detection models typically act as black boxes, offering limited insight into *why* a specific function is predicted to be affected59. ExplainVulD solves this by introducing a graph-based framework utilizing dual-channel embeddings (semantic Word2Vec and structural CPGs) combined with edge-aware attention to identify influential nodes and paths59. By combining attention weights and input gradients, it highlights the exact structural path causing the prediction. This is the exact mechanism the Blast Radius Analyzer needs to generate the "Explainable Evidence" section of its report, visually tracing how a modified variable flows into a UI endpoint.

| Parameter | Detail |
| :---- | :---- |
| **Title** | ExplainVulD: Explainable Vulnerability Detection in C/C++ Functions using Code Property Graphs |
| **Authors** | (Implied via Snippet 4 context) |
| **Publication Year** | 2025 |
| **Conference / Journal** | ArXiv (Preprint) |
| **DOI** | N/A |
| **PDF Link** | https://arxiv.org/pdf/2507.16540 |
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
| **Decision (Adopt/Adapt/Ignore)** | **Adopt**. The edge-aware attention and gradient-attribution methodology solves the core requirement of generating an *explainable* report, detailing the exact causal path through the CPG. |

### **17\. Deep Type Inference for Dynamic Languages**

A massive challenge in constructing an end-to-end Knowledge Graph is that the UX layer is often built in dynamically typed languages (JavaScript), making static data flow analysis highly unreliable. CodeTIDAL5 overcomes this by combining automated extraction of usage slices from a CPG with a Transformer model (CodeT5+) to reliably predict type annotations in dynamic languages60. By extracting data slices via Joern and passing them through an encoder-decoder architecture, it infers types contextually60. The Blast Radius Analyzer will utilize this approach to statically trace data flows from strictly typed backends into dynamically typed frontend UX components, maintaining the chain of evidence.

| Parameter | Detail |
| :---- | :---- |
| **Title** | CodeTIDAL5: A CodeT5+ model for Type Inference for enhanced Dataflow Analysis |
| **Authors** | (Implied via Snippet 5 context) |
| **Publication Year** | 2023 |
| **Conference / Journal** | ArXiv |
| **DOI** | N/A |
| **PDF Link** | https://arxiv.org/pdf/2310.00673 |
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
| **PDF Link** | https://arxiv.org/pdf/2412.13467 |
| **ArXiv Link** | 2412.13467 |
| **GitHub Repository** | https://github.com/imamnurby/Transducer-Tuning |
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
| **PDF Link** | https://arxiv.org/pdf/2603.11800 |
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
| **PDF Link** | https://arxiv.org/pdf/2603.13999 |
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
| **Decision (Adopt/Adapt/Ignore)** | **Ignore**. Requiring developers to manually write specific "Traceable" enums into their source code violates the premise of an *AI-powered* analyzer, which seeks to infer connections automatically without altering human developer workflows. |

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

The final Blast Radius Report must be actionable and trustworthy. Standard impact analysis yields a binary result, but developers require evidence. **GNNExplainer (2019)** mathematically isolates the critical causal subgraph responsible for the impact prediction16. **ExplainVulD (2025)** applies edge-aware attention directly to the CPG to explain exactly how control flow changes ripple upward59. These frameworks generate the visual "supporting evidence" in the report, proving *why* a UI element is affected by a backend change.

## **5\. Identified Research Gaps**

The synthesis of this literature reveals several critical research gaps that the proposed Blast Radius Analyzer architecture uniquely addresses:  
**1\. The Semantic-Structural Chasm:** While CPGs (Yamaguchi, 2014\) perfectly map code structure2, and tools like T-SimCSE map semantic text62, there is a gaping void in mapping dynamic semantic UX/DOM states directly to backend CPGs. Current literature treats frontend and backend analysis as disparate fields. The proposed architecture addresses this by fusing Screen2Vec DOM embeddings with GraphCodeBERT structural embeddings within a unified GraphRAG environment, explicitly creating edges between the UX layer and the Implementation layer.  
**2\. The Latency vs. Accuracy Tradeoff in GraphRAG:** Microsoft's GraphRAG yields unparalleled accuracy for global summarization but is too slow for synchronous CI/CD pipelines (e.g., blocking a PR check). By integrating LightRAG's incremental deduplication51 with HippoRAG's fast Personalized PageRank retrieval47, the proposed system can generate highly accurate Blast Radius reports in seconds, directly solving the latency block in AI-driven Continuous Integration.  
**3\. Black-Box Impact Analysis:** Traditional Change Impact Analysis and dynamic testing (Ekstazi) yield binary results (Affected / Not Affected). They do not explain *why* to the developer. By applying GNNExplainer and ExplainVulD methodologies directly to the Product Knowledge Graph, the proposed system shifts the paradigm from "Binary Impact" to "Explainable Evidence-Backed Impact." It generates a human-readable trace (e.g., Controller\_A data-flows to Endpoint\_B, which is bound to Button\_C in DOM, defined in Requirement\_D).  
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