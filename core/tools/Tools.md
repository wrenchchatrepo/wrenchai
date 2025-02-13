# Tools

## Core Tools (Often Essential)

Web Search: Accesses external information from the internet.

Retrieval-Augmented Generation (RAG): Combines retrieval and generation for information-based tasks.

Code Generation/Execution: Generates and runs code (e.g., Python) in a secure environment.

Memory (Short-Term and Long-Term):

Short-Term Memory (STM): Stores information relevant to the current task.

Long-Term Memory (LTM): Persists information across sessions.

## Specialized Tools (Task-Specific)

Multimodal Input/Output: Handles non-text data (images, audio, video).

Data Analysis Tools: Performs data manipulation, analysis, and visualization.

API Interaction: Interacts with external services and APIs.

Specialized LLM Tools: LLMs fine-tuned or prompt-engineered for specific tasks.

Cache-Augmented Generation: Caches internally generated results to improve efficiency.

Okay, let's define a set of common tools used in agentic frameworks, categorized for clarity, and with considerations for how they interact with the Bayesian reasoning we discussed earlier. This will give us a practical vocabulary for building our agents.

## Core Tools (Often Essential)

These are tools that almost every sophisticated agentic framework will utilize in some capacity:

1.  **Web Search:**
    *   **Description:** Accesses external information from the internet. This is crucial for grounding the agent in real-world knowledge and staying up-to-date.
    *   **Implementation:** Typically uses APIs like Google Search, Bing Search, or specialized search engines (e.g., academic databases, code repositories).  Libraries like `serpapi` or `googlesearch-python` can simplify integration.
    *   **Bayesian Connection:**
        *   *Evidence:* Search results provide evidence to update the agent's beliefs.  The relevance and credibility of search snippets influence the likelihoods.
        *   *Decision-Making:*  The agent might use Bayesian reasoning to decide *when* to search (e.g., if uncertainty about a fact is high) and *what* to search for (formulating queries to maximize information gain).
    *   **Example:**
        ```python
        # Simplified example (using a hypothetical search API)
        def web_search(query: str) -> list[dict]:
            """Performs a web search and returns a list of results.
            Each result is a dict with 'title', 'snippet', and 'url' keys.
            """
            # In a real implementation, this would call a search API.
            results = [
                {'title': 'Example Result 1', 'snippet': 'Some relevant text...', 'url': 'http://example.com/1'},
                {'title': 'Example Result 2', 'snippet': 'Other information...', 'url': 'http://example.com/2'}
            ]
            return results
        ```

2.  **Retrieval-Augmented Generation (RAG):**
    *   **Description:** Combines the strengths of retrieval (finding relevant information) and generation (creating text).  It's a powerful technique for answering questions, summarizing documents, and generating content based on specific sources.
    *   **Implementation:**  Typically involves:
        *   A *retriever* component (e.g., a dense vector database like FAISS, Pinecone, or Weaviate) that finds relevant documents based on a query.
        *   A *generator* component (usually an LLM) that takes the retrieved documents and the original query as input and generates a response.
        *   Libraries like LangChain and Haystack provide high-level abstractions for building RAG pipelines.
    *   **Bayesian Connection:**
        *   *Evidence:* The retrieved documents serve as evidence.  The similarity scores between the query and the documents can be incorporated into the likelihood calculations.
        *   *Decision-Making:*  The agent might use Bayesian reasoning to decide whether to rely more on retrieved information or its own internal knowledge.  It could also use it to select the best retrieval strategy.
    *   **Example:**
        ```python
        # Simplified RAG example (using hypothetical components)
        def rag(query: str, retriever, generator) -> str:
            """Performs retrieval-augmented generation."""
            documents = retriever.retrieve(query)
            response = generator.generate(query, documents)
            return response
        ```

3.  **Code Generation/Execution:**
    *   **Description:** Allows the agent to generate and execute code (e.g., Python, JavaScript). This is essential for tasks that require computation, data manipulation, or interaction with external systems.
    *   **Implementation:**
        *   Uses an LLM to generate code based on a natural language description.
        *   Uses a secure execution environment (e.g., a sandbox) to run the generated code.  **Crucially important for safety!**
        *   Libraries like `subprocess` (carefully used!), Docker containers, or cloud-based code execution services can be used.
    *   **Bayesian Connection:**
        *   *Evidence:* The output of the executed code (including any errors) provides strong evidence about the correctness of the generated code.
        *   *Decision-Making:*  The agent might use Bayesian reasoning to evaluate the risk of executing a piece of code and to decide whether to generate code at all or use a different tool.
    *   **Example:**
        ```python
        import subprocess
        import re

        def execute_python_code(code: str) -> tuple[str, str]:
            """Executes Python code in a subprocess and returns stdout and stderr."""
            try:
                # VERY IMPORTANT: Sanitize the code to prevent malicious execution.
                # This is a simplified example and NOT suitable for production.
                # Use a proper sandboxing solution in a real-world application.
                if re.search(r'(import\s+(os|subprocess|sys))|(__import__)', code):
                    return "", "Error: Potentially unsafe code detected."

                result = subprocess.run(['python', '-c', code], capture_output=True, text=True, timeout=10)
                return result.stdout, result.stderr
            except subprocess.TimeoutExpired:
                return "", "Error: Code execution timed out."
            except Exception as e:
                return "", f"Error: {e}"
        ```

4.  **Memory (Short-Term and Long-Term):**
    *   **Description:** Allows the agent to store and retrieve information from past interactions.
        *   **Short-Term Memory (STM):**  Typically holds information relevant to the current conversation or task (e.g., the last few turns of a dialogue). Often implemented as a limited-size buffer.
        *   **Long-Term Memory (LTM):** Stores information that needs to be persisted across sessions (e.g., user preferences, learned facts, successful strategies).  Often implemented using databases (vector databases, key-value stores, etc.).
    *   **Implementation:**
        *   STM:  Simple lists, dictionaries, or deque objects in Python.
        *   LTM:  Databases (e.g., ChromaDB, FAISS, Pinecone, Redis), file systems.
    *   **Bayesian Connection:**
        *   *Prior Probabilities:*  Information retrieved from memory can be used to inform the prior probabilities in Bayesian calculations.  For example, past success rates of a particular tool can influence the prior probability of that tool being effective in the current situation.
        *   *Evidence:*  Memories can also serve as evidence, especially in tasks that require recalling past events or reasoning about sequences of actions.
    *   **Example:**
        ```python
        class AgentMemory:
            def __init__(self, stm_capacity=10):
                self.stm = []  # Short-term memory (list)
                self.stm_capacity = stm_capacity
                self.ltm = {}  # Long-term memory (dictionary - simplified)

            def add_to_stm(self, item):
                self.stm.append(item)
                if len(self.stm) > self.stm_capacity:
                    self.stm.pop(0)  # Remove oldest item

            def add_to_ltm(self, key, value):
                self.ltm[key] = value

            def get_from_ltm(self, key):
                return self.ltm.get(key)
        ```

## Specialized Tools (Task-Specific)

These tools are often built on top of the core tools or provide specialized capabilities for particular domains:

5.  **Multimodal Input/Output:**
    *   **Description:** Handles different types of data, such as images, audio, and video, in addition to text.
    *   **Implementation:**  Uses specialized models and libraries for processing each modality (e.g., image recognition models, speech-to-text, text-to-speech).  Often involves converting different modalities into a common representation (e.g., embeddings).
    *   **Bayesian Connection:**  Similar to web search, multimodal inputs provide evidence.  The agent might need to combine evidence from different modalities using Bayesian methods.
    *   **Example:** Image captioning, video summarization, generating images from text descriptions.

6.  **Data Analysis Tools:**
    *   **Description:** Performs operations on data, such as filtering, aggregation, statistical analysis, and visualization.
    *   **Implementation:**  Often involves generating and executing code (e.g., Python with pandas, NumPy, matplotlib). Could also involve specialized data analysis APIs.
    *   **Bayesian Connection:**  Statistical results from data analysis can be directly used as evidence in Bayesian calculations.

7.  **API Interaction:**
    *   **Description:**  Allows the agent to interact with external services and APIs (e.g., calendars, email, databases, cloud services).
    *   **Implementation:**  Uses libraries like `requests` to make API calls.  Often requires handling authentication and authorization.
    *   **Bayesian Connection:**  Responses from API calls provide evidence.  The agent might use Bayesian reasoning to decide which API to call or how to interpret the results.

8.  **Specialized LLM Tools:**
    *   **Description:** Fine-tuned LLMs or prompt-engineered LLMs designed for specific tasks, such as legal reasoning, medical diagnosis, or code debugging.
    *   **Implementation:**  Uses pre-trained models or custom-trained models.
    *   **Bayesian Connection:**  The confidence scores or probabilities provided by these specialized LLMs can be incorporated into the Bayesian framework.

9.  **Cache-Augmented Generation (Expanding on Memory):**
      *   **Description**: A form of LTM, it differs from RAG in that it's not about retrieving external information but about caching *internally* generated results.  If the agent has answered a similar question or performed a similar calculation before, it can retrieve the result from the cache instead of recomputing it.
      *    **Implementation:**  Often a key-value store where the key is a representation of the input (e.g., a hash of the query) and the value is the cached output.
      *   **Bayesian Connection:**  The cache hit rate and the confidence in the cached results can be used to inform Bayesian decisions.

**III. Tool Selection and Orchestration**

The power of an agentic framework lies not just in the individual tools but in the agent's ability to select and orchestrate them effectively. This is where Bayesian reasoning becomes particularly important:

*   **Tool Selection:** The agent uses its current beliefs (prior probabilities) and evidence from the environment (e.g., user input, previous tool outputs) to calculate the posterior probability of success for each available tool.  It then chooses the tool with the highest posterior probability (or uses a probabilistic selection method).
*   **Tool Chaining:** Agents often need to use multiple tools in sequence to accomplish a task.  Bayesian reasoning can be used to plan the sequence of tool calls, evaluating the expected outcome of each step and adjusting the plan based on the results.
*   **Error Handling:** If a tool fails (e.g., a web search returns no results, code execution produces an error), the agent can use Bayesian updating to revise its beliefs and choose a different tool or strategy.
*   **Meta-Reasoning:**  The agent can even reason about its own reasoning process, using Bayesian methods to assess the uncertainty of its beliefs and the effectiveness of its decision-making strategies.


