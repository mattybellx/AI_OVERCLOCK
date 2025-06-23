import ollama # For Ollama
# import lmstudio as lms # Uncomment if using LM Studio instead
import json

class LLMInterface:
    """
    Handles interaction with a local Large Language Model (LLM) for generating
    overclocking recommendations.
    Assumes Ollama is running and the specified model is pulled.
    """
    def __init__(self, config: dict):
        """
        Initializes the LLMInterface.
        :param config: A dictionary containing LLM configuration details (model name, base URL).
        """
        self.config = config
        self.llm_model = config.get("llm_model_name", "llama3")
        self.ollama_base_url = config.get("ollama_base_url", "http://localhost:11434")

        # You can technically instantiate the ollama client explicitly if needed:
        # self.ollama_client = ollama.Client(host=self.ollama_base_url)
        # For LM Studio, it would be:
        # self.lmstudio_client = lms.Client(base_url=self.lmstudio_base_url)
        print(f"LLMInterface initialized for model: {self.llm_model} via Ollama at {self.ollama_base_url}")

    def get_overclock_recommendations(self, system_summary: str, current_mining_algorithm: str, user_goal: str) -> str:
        """
        Sends a detailed prompt to the LLM to get overclocking recommendations.
        :param system_summary: A string containing the system's static and real-time metrics.
        :param current_mining_algorithm: The cryptocurrency mining algorithm being used.
        :param user_goal: The user's primary goal for optimization (e.g., "maximize efficiency").
        :return: A string containing the LLM's recommendation, or an error message.
        """
        prompt = f"""
You are an expert GPU overclocking and crypto mining advisor. Your goal is to provide safe, efficient, and detailed overclocking recommendations for a user's specific GPU and mining setup.

Here is the current system summary and real-time telemetry:
{system_summary}

The user's primary goal for overclocking is: '{user_goal}'.
The current crypto mining algorithm they are using (or plan to use) is: '{current_mining_algorithm}'.

Based on this information and your extensive knowledge of GPU performance, mining algorithms, and hardware stability, provide the following sections:

1.  **Recommended Overclock Settings:**
    * **Core Clock (MHz):** Specify either a fixed clock (e.g., 1800) or an offset (e.g., +150). Prefer fixed clocks for better efficiency if possible for the GPU/algorithm.
    * **Memory Clock (MHz):** Specify an offset (e.g., +1200).
    * **Power Limit (%):** Percentage of the maximum allowed TDP (e.g., 70%).
    * **Fan Speed (% or Curve Description):** A target percentage (e.g., 70%) or a brief description of a desired fan curve (e.g., "aggressive to maintain 60C").
2.  **Expected Outcomes:**
    * **Estimated Hash Rate:** (e.g., XX MH/s, YY Sol/s, ZZ H/s - provide a realistic estimate based on common benchmarks for this GPU/algorithm/settings if possible).
    * **Estimated Power Draw:** (e.g., WW watts).
    * **Estimated Efficiency:** (e.g., EE J/MH, or Watts/Sol - calculate if possible from estimated hash rate and power draw).
    * **Expected Temperature:** (e.g., TT°C for GPU core, and if applicable, junction/hotspot temp).
3.  **Reasoning:**
    * Explain *why* these specific values are chosen, referencing the system's current state, the mining algorithm, and common community best practices or scientific principles.
    * Discuss the trade-offs (e.g., hash rate vs. power efficiency vs. heat, stability).
4.  **Potential Risks & Precautions:**
    * What are the risks of applying these settings (e.g., instability, crashes, reduced hardware lifespan, invalid shares)?
    * What precautions should the user take (e.g., incremental changes, continuous monitoring, thorough testing, ensuring adequate PSU)?
5.  **Step-by-Step Instructions:**
    * Provide clear, concise instructions on how to apply these settings using common tools.
    * **For Windows users, focus on MSI Afterburner.**
    * **For Linux users (NVIDIA), focus on `nvidia-smi` commands.**
    * **For Linux users (AMD), focus on `amdgpu-clocks` or `roc_smi` (if applicable and safe) or other common Linux tools.**
    * Remind the user that direct software control might require specific tools or administrator privileges.

Format your output clearly with bold headings. Be precise with numerical recommendations. If you cannot provide a specific value, explain why. Prioritize safety and stability.
"""
        # --- LLM API Call ---
        try:
            print(f"\n[LLM] Sending prompt to LLM for recommendations ({self.llm_model})...")
            # Using ollama.generate for simplicity to get a single response string
            # For more advanced conversational flows, ollama.chat can be used
            response = ollama.generate(
                model=self.llm_model,
                prompt=prompt,
                stream=False, # Set to True if you want to process text as it's generated
                options={
                    "temperature": 0.5, # Controls randomness: lower for more factual, higher for more creative
                    "num_ctx": 4096, # Context window size. Adjust based on your model and prompt length
                    "top_k": 40,
                    "top_p": 0.9,
                    "num_gpu": -1 # Use all available GPU layers if model is GPU-accelerated
                }
            )
            # Ollama's generate returns a dictionary, with the actual response in ['response']
            return response.get('response', "LLM did not return a valid response.")

        except Exception as e:
            error_message = f"Error: Could not get recommendations from LLM. Details: {e}\n"
            if "status code: 404" in str(e) and self.llm_model in str(e):
                error_message += f"Please ensure the model '{self.llm_model}' is downloaded and available in your Ollama installation. Run `ollama pull {self.llm_model}` in your terminal."
            else:
                error_message += "Please ensure your Ollama server is running and accessible (e.g., at http://localhost:11434)."
            
            print(f"[LLM ERROR] {error_message}")
            return error_message

# Example Usage (for independent testing)
if __name__ == "__main__":
    mock_config = {
        "llm_model_name": "llama3", # Make sure you have 'llama3' pulled in Ollama
        "ollama_base_url": "http://localhost:11434"
    }

    llm_advisor = LLMInterface(mock_config)

    # Mock system summary (replace with real data from SystemMonitor)
    mock_system_summary = """
    System Summary:
    ---
    GPU (Brand: NVIDIA):
      Model: NVIDIA GeForce RTX 3070
      Driver Version: 535.12.0
      Total VRAM: 8192 MB
      Current Temp: 65°C
      Current Hot Spot Temp: 75°C
      Current Power Draw: 220W
      Current Core Clock: 1800MHz
      Current Memory Clock: 7000MHz
      Current Fan Speed: 60%
      Current VRAM Used: 7800 MB

    CPU:
      Temperature: 50°C
      Usage: 10%

    RAM:
      Total: 32 GB
      Used: 10 GB (31%)

    Operating System: Linux
    """

    mock_current_mining_algorithm = "Ethash" # Example: Ethereum Classic mining
    mock_user_goal = "Maximize power efficiency while maintaining stability and extending GPU lifespan."

    print("\nAttempting to get LLM recommendations (this might take a while)...")
    recommendations = llm_advisor.get_overclock_recommendations(
        mock_system_summary,
        mock_current_mining_algorithm,
        mock_user_goal
    )
    print("\n--- LLM Recommendations ---")
    print(recommendations)
    print("--------------------------")
