# Streamlit UI

**Design Principles for the Streamlit UI:**

1.  **Minimal User Input:** Keep the initial user input as simple as possible.  A single text area for the user's request is a good starting point.  Avoid overwhelming the user with options upfront.
2.  **Verbose Output:**  Provide detailed, step-by-step output explaining what the agents are doing, why they're doing it, and the results of their actions.  This transparency is crucial for understanding the agentic process.
3.  **Clear Progress Indication:** Use Streamlit's progress bars (`st.progress`) and status messages (`st.info`, `st.success`, `st.warning`, `st.error`) to keep the user informed about the progress of the task.
4.  **Agent-Specific Sections:**  Organize the output into sections for each agent (Super, Inspector, Journey agents).  This will make it easier to follow the flow of execution.
5.  **Step-by-Step Breakdown:**  Within each agent's section, display the individual steps of the playbook being executed, along with the inputs, outputs, and any relevant Bayesian calculations (in a simplified, understandable form).
6.  **Cost Tracking (Visible):** Display a running estimate of the cost of the task, updating it as the agents consume resources.
7.  **Error Handling (Clear):**  If an error occurs, clearly display the error message, the agent that encountered the error, and any relevant context.
8.  **"Show Details" Option (Optional):** For advanced users, consider adding a "Show Details" checkbox or button that reveals more technical information (e.g., the full Bayesian calculations, raw agent outputs).
9.  **Feedback Mechanism (Optional):** Include a simple feedback mechanism (e.g., thumbs up/down buttons) to allow users to rate the quality of the results. This can be used to improve the framework over time.
10. **Iterative Refinement:** Allow the user to refine their request or provide additional information based on the agent's output. This can be done using a text input box at the end of the process.

**Streamlit UI Structure (Example):**

Here's a conceptual outline of how the Streamlit UI might be structured:

```python
import streamlit as st
import time  # For simulating agent activity

# --- Sidebar (Optional - for settings and advanced options) ---
with st.sidebar:
    st.header("Settings")
    show_details = st.checkbox("Show Details", value=False) # Example setting

# --- Main Area ---
st.title("Agentic Framework")

# --- User Input ---
user_request = st.text_area("Enter your request:", height=100)

if st.button("Submit"): # Only start processing when the button is clicked
    # --- Initialize Cost ---
    total_cost = 0.0
    cost_placeholder = st.empty() # Placeholder for updating cost
    cost_placeholder.markdown(f"**Estimated Cost:** ${total_cost:.4f}")


    # --- Super Agent Section ---
    with st.expander("Super Agent", expanded=True): # Use expander to manage verbosity
        st.info("Super Agent is analyzing the request...")
        time.sleep(1) # Simulate processing time

        # Display Super Agent's actions and reasoning (example)
        st.markdown("**Step 1:** Decompose the request into subtasks.")
        st.markdown("**Reasoning:** Based on prior experience and the user's input, the request can be broken down into...")
        st.markdown("**Subtasks:** [Subtask 1, Subtask 2, ...]")
        time.sleep(1)

        st.info("Super Agent is assigning roles and tools...")
        # ... (Display role/tool assignment) ...
        time.sleep(1)

        st.success("Super Agent has created the execution plan.")

    # --- Inspector Agent Section ---
    with st.expander("Inspector Agent", expanded=True):
        st.info("Inspector Agent is monitoring the process...")
        # ... (Inspector will update this section later) ...

    # --- Journey Agent Sections (Dynamic - based on the plan) ---
    journey_agents = ["WebResearcher", "CodeGenerator"]  # Example - this would come from the Super Agent
    journey_agent_progress = {} # dictionary to track progress per agent

    for agent_name in journey_agents:
        with st.expander(f"{agent_name} Agent", expanded=True):
            st.info(f"{agent_name} is starting its task...")
            time.sleep(1)
            progress_bar = st.progress(0) #Initialize progress bar
            journey_agent_progress[agent_name] = progress_bar

            # Simulate playbook execution (replace with actual agent logic)
            for step in range(1, 6): # Simulate 5 steps in the playbook
                st.markdown(f"**Step {step}:** Performing action...")
                time.sleep(2)  # Simulate processing time
                st.markdown("**Input:** ...")
                st.markdown("**Output:** ...")
                st.markdown("**Reasoning (Simplified Bayesian):** Probability of success for this step: 0.95") # Example

                # Update cost (example)
                total_cost += 0.01  # Simulate a small cost increment
                cost_placeholder.markdown(f"**Estimated Cost:** ${total_cost:.4f}")
                # Update the progress bar.
                progress_bar.progress(step * 20)

            st.success(f"{agent_name} has completed its task.")

    # --- Inspector Agent (Final Evaluation) ---
    with st.expander("Inspector Agent", expanded=True):
        st.info("Inspector Agent is evaluating the results...")
        time.sleep(1)
        st.success("Inspector Agent approves the results.")

    # --- Final Output ---
    st.header("Final Result")
    st.write("Here is the final result based on your request:")
    # ... (Display the final result) ...

    # --- Iterative Refinement (Optional) ---
    st.header("Refine Request (Optional)")
    refinement_input = st.text_area("Provide additional information or refine your request:", height=50)
    if st.button("Submit Refinement"):
        # ... (Handle the refinement input - restart the process) ...
        pass

```

**Key Implementation Details:**

*   **`st.expander`:**  Use `st.expander` to group the output of each agent and allow users to collapse sections they're not interested in. This helps manage the verbosity.
*   **`st.progress`:**  Use `st.progress` to visually represent the progress of each `Journey` agent.
*   **`st.info`, `st.success`, `st.warning`, `st.error`:**  Use these status messages to provide clear feedback to the user.
*   **`st.markdown`:**  Use Markdown formatting to make the output more readable.
*   **`st.empty`:** Use `st.empty` as a placeholder for elements that will be updated dynamically (like the cost estimate).
*   **`time.sleep`:** In this example, `time.sleep` is used to simulate agent activity. Replace this with your actual agent logic.
*   **Dynamic Agent Sections:** The code shows how to dynamically create sections for each `Journey` agent based on the plan generated by the `Super` agent.
* **Cost Placeholder**: The `cost_placeholder` is initialized and then updated in the loop to reflect increasing cost.

**Next Steps (Development Process):**

1.  **Basic Structure:** Implement the basic structure of the UI, including the user input, agent sections, and progress indicators (using placeholders and `time.sleep` to simulate agent activity).
2.  **Super Agent Integration:** Connect the `Super` agent to the UI. Display the `Super` agent's analysis, role/tool assignment, and plan generation.
3.  **Journey Agent Integration (One at a Time):** Integrate one `Journey` agent at a time.  Display the agent's execution steps, inputs, outputs, and (simplified) reasoning.
4.  **Inspector Agent Integration:** Connect the `Inspector` agent. Display its monitoring and evaluation results.
5.  **Cost Tracking:** Implement the cost tracking logic and display the running cost estimate.
6.  **Error Handling:** Add error handling and display error messages clearly.
7.  **Iterative Refinement (Optional):** Implement the optional iterative refinement feature.
8.  **"Show Details" (Optional):** Add the optional "Show Details" feature for advanced users.
9.  **Feedback Mechanism (Optional):** Add the optional feedback mechanism.
10. **YAML Configuration Integration**: Load configurations dynamically.

