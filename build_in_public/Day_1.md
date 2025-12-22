# Day 1

## Setting up the env

- Using `uv` as the package manager
- ChromaDB for vector store
- There needs to be data before a vector store. Thinking of building a code agent.

## Agentic Pipeline

1. Understand the current lay of the land in building an autonomous code agent.
   2. Will be using CodeAct
   3. Will be using OpenHands SDK to execute and iterate over the code
2. Utilise browser based code agents to get the HTML of a few pages of documentation.
3. Use downloaded HTML to build parser and autonomously verify working.
4. Once QA agent gives the go ahead, allow the scraper to scrape and save the entire documentation as MD files
5. Think of a plan to know when the underlying documentation has changed and to download it again.

### ToDo
- [ ] Build agentic pipeline to scrape documentation from websites
- [ ] Utilise GitHub API to get issues related to software

### Documentation to scrape
- vLLM
- HuggingFace
- sgLang
- LangGraph
- LangChain
- AWS Strands
