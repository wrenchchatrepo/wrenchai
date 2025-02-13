# Costs

**I. Cost Categories and Data Sources**

We need to track costs across several categories, each requiring different data sources and calculation methods:

1.  **LLM API Costs:**
    *   **Description:** Cost of using LLMs (Claude, Gemini, DeepSeek) via their respective APIs.
    *   **Data Sources:**
        *   **API Usage Metrics:** Track the number of tokens used for input and output for each LLM call. This is the *most critical* data point.  Your framework *must* log this.
        *   **Pricing Models:** Obtain the current pricing models for each LLM from their respective providers (Anthropic for Claude, Google for Gemini, DeepSeek may have its own or be hosted on a platform with pricing).  These prices are usually per 1,000 tokens (input and output often have different rates).  Ideally, you'd have a mechanism to periodically update these prices.
        *   **Model Version:** Different versions of the same LLM (e.g., Claude 3 Sonnet vs. Claude 3 Opus) may have different prices. Track the specific model used.
    *   **Calculation:**
        ```
        Cost_LLM = (Input_Tokens * Input_Price_Per_1k_Tokens / 1000) + (Output_Tokens * Output_Price_Per_1k_Tokens / 1000)
        ```
        Sum this across all LLM calls within a given time period (e.g., per task, per agent, per day).

2.  **GCP Compute Costs:**
    *   **Description:** Costs associated with running your agent framework on GCP infrastructure (e.g., virtual machines, containers, serverless functions).
    *   **Data Sources:**
        *   **GCP Billing Data:** Use the GCP Billing API or export billing data to BigQuery.  This provides detailed information about resource usage and costs.
        *   **Resource Usage Metrics:** Track the CPU, memory, and disk usage of your agents.  This can be done using GCP's monitoring tools (Cloud Monitoring) or custom instrumentation.
        *   **Machine Types/Instance Types:**  The specific type of virtual machine or container instance (e.g., `n1-standard-1`, `e2-medium`) significantly impacts cost. Track this.
        *   **Run Time:** The duration for which resources are used.
    *   **Calculation:**  This is more complex, as GCP pricing varies based on many factors.  A simplified approach:
        ```
        Cost_Compute = (Resource_Usage * Resource_Price_Per_Hour * Run_Time_Hours)
        ```
        You'll need to map resource usage metrics (CPU, memory, etc.) to the appropriate GCP pricing tiers.  Consider using the GCP Pricing Calculator API for more accurate estimates.

3.  **GCP Storage Costs:**
    *   **Description:** Costs for storing data (e.g., agent configurations, logs, cached results, long-term memory).
    *   **Data Sources:**
        *   **GCP Billing Data:** As with compute, billing data provides detailed storage costs.
        *   **Storage Usage Metrics:** Track the amount of data stored in different GCP storage services (e.g., Cloud Storage, Cloud SQL, Bigtable).
        *   **Storage Class:** Different storage classes (e.g., Standard, Nearline, Coldline) have different prices. Track this.
    *   **Calculation:**
        ```
        Cost_Storage = (Storage_Amount_GB * Price_Per_GB_Per_Month)
        ```
        Again, this is a simplification. Consider factors like data retrieval costs and regional pricing differences.

4.  **GCP Networking Costs:**
    *   **Description:** Costs for data transfer between GCP services and the internet, or between different GCP regions.
    *   **Data Sources:**
        *   **GCP Billing Data:** Provides detailed network usage and costs.
        *   **Network Traffic Metrics:** Track the amount of data transferred in and out of your agents.
    *   **Calculation:** Network costs can be complex, depending on the type of traffic and the regions involved.  A basic approach:
        ```
        Cost_Network = (Data_Transfer_In_GB * Price_Per_GB_In) + (Data_Transfer_Out_GB * Price_Per_GB_Out)
        ```

5.  **Other Service Costs:**
    *   **Description:** Costs for any other services used by your agents (e.g., search APIs, specialized AI services, databases).
    *   **Data Sources:**
        *   **API Usage Metrics:** Track usage of each external service.
        *   **Pricing Models:** Obtain pricing information from each service provider.
    *   **Calculation:**  Each service will have its own pricing model. You'll need to track usage and apply the appropriate pricing formula.

**II. Implementation Requirements**

To implement cost tracking, your framework needs the following:

1.  **Token Counting:** A robust mechanism for counting input and output tokens for *every* LLM call.  Libraries like `tiktoken` (for OpenAI models, but adaptable) can be helpful.
2.  **Usage Logging:**  Every agent should log its resource usage (LLM tokens, compute resources, storage, network traffic) and any external service calls.  This log should include timestamps and agent identifiers.
3.  **Pricing Data:**  A mechanism to store and update pricing information for LLMs, GCP services, and other external services. This could be a simple database or a configuration file that is periodically updated.
4.  **Cost Calculation Module:** A component that takes the usage logs and pricing data as input and calculates the cost for each category.  This module should be able to generate cost reports at different granularities (per agent, per task, per time period).
5.  **Integration with GCP Billing API (Strongly Recommended):**  For accurate GCP cost tracking, integrate with the GCP Billing API or export billing data to BigQuery. This allows you to correlate your agent's usage logs with actual GCP billing information.
6.  **Cost Estimation (Optional but Useful):**  Before running a task, the `Super` agent could use the cost calculation module to estimate the potential cost based on the planned agent configuration, tools, and playbooks.  This allows for cost-aware decision-making.
7. **Cost Thresholds and Alerts (Optional but Useful):** Define cost thresholds for tasks or agents. If a threshold is exceeded, the framework could trigger an alert or even automatically pause or terminate the task.

**III. Simplified Example (Conceptual)**

```python
# Simplified cost calculation example (Conceptual)

def calculate_llm_cost(input_tokens, output_tokens, llm_model):
    """Calculates the cost of an LLM call."""
    pricing = {  # Example pricing (replace with actual values)
        'claude-3.5-sonnet': {'input': 0.003, 'output': 0.015},  # USD per 1k tokens
        'gemini-1.5-flash': {'input': 0.001, 'output': 0.002},
        'deepseek-coder': {'input': 0.0005, 'output': 0.001}
    }
    model_pricing = pricing.get(llm_model)
    if not model_pricing:
        return 0  # Or raise an exception

    input_cost = (input_tokens * model_pricing['input']) / 1000
    output_cost = (output_tokens * model_pricing['output']) / 1000
    return input_cost + output_cost

def calculate_total_cost(usage_logs, pricing_data):
    """Calculates the total cost based on usage logs and pricing data."""
    total_cost = 0

    for log in usage_logs:
        if log['type'] == 'llm':
            total_cost += calculate_llm_cost(log['input_tokens'], log['output_tokens'], log['llm_model'])
        # Add calculations for other cost categories (compute, storage, network, etc.)

    return total_cost

# Example usage log entry
usage_log_entry = {
    'timestamp': '2024-07-27T12:00:00Z',
    'agent_id': 'journey-agent-1',
    'type': 'llm',
    'llm_model': 'claude-3.5-sonnet',
    'input_tokens': 500,
    'output_tokens': 200
}

# Example pricing data (could be loaded from a file or database)
pricing_data = {
   # ... (LLM pricing, GCP pricing, etc.) ...
}

# Calculate total cost (This is a highly simplified example)
# total_cost = calculate_total_cost([usage_log_entry], pricing_data)
# print(f"Total cost: ${total_cost:.4f}")
```

