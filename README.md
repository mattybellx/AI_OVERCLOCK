LLM-Powered GPU OC Advisor
An AI-driven GPU overclocking advisor application built with Tkinter, providing real-time system monitoring and intelligent recommendations for optimized cryptocurrency mining performance, efficiency, and stability.

Features
Real-time System Monitoring: Get live telemetry data for your GPU (temperature, power draw, clock speeds, VRAM usage, fan speed), CPU (temperature, usage), and RAM.

LLM-Powered Overclocking Recommendations: Leverage a local Large Language Model (LLM) (e.g., Llama 3 via Ollama) to receive tailored overclocking settings based on your current system state, desired mining algorithm, and optimization goals (e.g., efficiency, hash rate, longevity).

Historical Data Logging: Automatically logs real-time metrics to help you track performance over time.

Recommendation Management: Save and view past LLM recommendations, and update their status (e.g., Applied, Failed, Reverted, Cancelled) with notes on actual observed performance.

LLM Fine-tuning Guidance: Detailed instructions on how to use your collected data to fine-tune your local LLM, making its recommendations even more precise and personalized for your hardware and mining habits.

Responsive GUI: A clean, intuitive Tkinter user interface with both light and dark modes for comfortable use.

SAFETY WARNING
GPU overclocking carries inherent risks, including system instability, crashes, and potential hardware damage (e.g., due to excessive heat or voltage).

This application provides AI-generated recommendations based on its training data and your system's reported telemetry. It DOES NOT GUARANTEE SAFETY, OPTIMAL PERFORMANCE, or prevent hardware damage.

ALWAYS proceed with extreme caution:

Apply changes incrementally: Never apply extreme overclocks all at once.

Monitor your system closely: Continuously watch temperatures, power draw, and stability using this tool and other monitoring software.

Thoroughly test: Use benchmarks or actual mining workloads to test stability after any changes.

Ensure adequate cooling and Power Supply Unit (PSU): Do not exceed your hardware's limits.

You are solely responsible for any consequences of applying these recommendations.

Installation
Prerequisites
Python 3.9+:
Download and install Python from python.org. Ensure you check the "Add Python to PATH" option during installation.

Ollama (for the LLM):
Download and install Ollama from ollama.com/download. Ollama allows you to run large language models locally.
After installing Ollama, you need to pull the specific LLM model used by the application (default is llama3). Open your terminal/command prompt and run:

ollama pull llama3

(If you wish to use a different model, update the llm_model_name in config.json accordingly, and pull that model with ollama pull your_model_name)

Application Setup
Clone the Repository:

git clone https://github.com/YOUR_USERNAME/LLM-GPU-OC-Advisor.git
cd LLM-GPU-OC-Advisor

(Replace YOUR_USERNAME with your GitHub username).

Create a Virtual Environment (Recommended):

python -m venv venv

On Windows:

.\venv\Scripts\activate

On macOS/Linux:

source venv/bin/activate

Install Dependencies:

pip install -r requirements.txt

(Note: pynvml is a dependency. If you have an NVIDIA GPU, this should install correctly. If you encounter issues, ensure your NVIDIA drivers are up to date. If you have an AMD GPU or no GPU, pynvml might not fully initialize, but the app is designed to handle this gracefully by reporting "N/A" for NVIDIA-specific metrics.)

🛠️ Configuration (config.json)
When you first run the application, a config.json file will be created in the root directory if it doesn't exist. You must review and edit this file:

{
    "llm_model_name": "llama3",         // IMPORTANT: Change this to the LLM model you pulled via Ollama (e.g., "llama3", "mistral").
    "ollama_base_url": "http://localhost:11434", // Your Ollama server URL. Default is usually correct.
    "gpu_brand": "NVIDIA",             // IMPORTANT: Change to "NVIDIA" or "AMD". This affects which monitoring methods are attempted.
    "target_temperature_celsius": 70,   // Your preferred maximum GPU temperature for longevity.
    "priority": "efficiency",           // Your default optimization goal: "efficiency", "hashrate", or "longevity".
    "data_collection_interval_seconds": 10, // How often (in seconds) to collect and log metrics.
    "app_data_dir": "app_data"          // Directory to store logged metrics and recommendations.
}

Usage
Start the Application:
Ensure your virtual environment is activated (if you created one) and run:

python main.py

Initial Safety Warning:
A critical safety warning will appear. Read it carefully and understand the risks before proceeding.

Monitor Metrics:
The left panel will continuously display real-time metrics for your GPU, CPU, and RAM. This data is also logged in the app_data/metrics directory.

Get Overclocking Recommendations:

In the "Get New Recommendation" section, enter the Mining Algorithm (e.g., "Ethash", "KawPow", "GrinCuckatoo32").

Enter your Optimization Goal (e.g., "maximize efficiency", "highest hash rate", "best stability for 24/7").

Click "Get Recommendation". The LLM will process your request (this may take some time depending on your LLM and hardware) and display the detailed recommendation in the right panel.

View Past Recommendations:
Click "View Past Recommendations" to open a new window showing a list of all previously saved recommendations. You can select one and click "View Details" to see the full recommendation, the system snapshot at that time, and any performance notes you added.

Update Recommendation Status:
After applying an LLM recommendation to your hardware (manually, using tools like MSI Afterburner or nvidia-smi), you can update its status:

Click "Update Recommendation Status".

Enter the Recommendation ID (from the past recommendations list or the status bar).

Select a New Status (APPLIED, FAILED, REVERTED, CANCELLED).

Optionally, enter the "Observed Hash Rate (MH/s)" and "Observed Power (W)" you achieved, and any "Your Notes" about stability, issues, or observations.

Click "Update Status". This feedback is crucial for potential future LLM fine-tuning.

LLM Fine-tuning Guidance:
Click "LLM Fine-tuning Guidance" to open a window with detailed information on how to use the collected data to fine-tune your local LLM, making it more accurate and personalized.

Toggle Theme:
Use the "Light Mode" / "Dark Mode" button in the top right to switch between themes for a more comfortable viewing experience.

Exit the Application:
Close the application window. You will be prompted to confirm the exit, which also gracefully stops the background metric logging.

Troubleshooting
"LLM did not return a valid response." or "Failed to connect to Ollama."

Ensure Ollama is running in the background. You might need to start it manually or check its service status.

Verify the ollama_base_url in config.json is correct (http://localhost:11434 is the default).

Make sure the llm_model_name in config.json matches a model you have pulled in Ollama (e.g., llama3). If not, run ollama pull your_model_name in your terminal.

"NVML_TEMP_GPU not found" / "nvmlDeviceGetClockInfo() takes 2 positional arguments but 3 were given" etc. (pynvml errors):

These errors indicate issues with pynvml interacting with your NVIDIA drivers.

Solution: Ensure your NVIDIA GPU drivers are fully up to date. You can download the latest drivers from nvidia.com/drivers.

A clean reinstallation of pynvml might also help: pip uninstall pynvml && pip install pynvml.

The application includes error handling to try and prevent crashes and report "N/A" if specific metrics cannot be retrieved due to driver/pynvml issues.

Unreadable text in dark mode (white text on white background or dark text on dark background):

The latest version of the code has implemented robust theme switching to prevent this.

If you still experience this, ensure you are running the most up-to-date main.py from this repository.

Sometimes, Tkinter themes can behave differently across various OS versions. If the issue persists, consider trying a different self.style.theme_use("clam") in _setup_styles (e.g., "alt", "default", "vista", "xpnative" on Windows, or "aqua" on macOS) to see if a different base theme resolves it.

Contributing
Contributions are welcome! If you have suggestions, bug reports, or want to contribute code, please:

Fork the repository.

Create a new branch (git checkout -b feature/your-feature-name).

Make your changes.

Commit your changes (git commit -m 'Add new feature').

Push to the branch (git push origin feature/your-feature-name).

Open a Pull Request.

or

Reach out at mattybell.co.uk!

License
This project is licensed under the MIT License.

Acknowledgements
Ollama: For making local LLM execution so accessible.

pynvml: For NVIDIA GPU monitoring.

psutil: For system resource monitoring.

The Tkinter community for GUI development.

and you, for being legendary.
