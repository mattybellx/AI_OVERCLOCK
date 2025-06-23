import platform
import subprocess
import json
import psutil
import time
from datetime import datetime

# Import pynvml for NVIDIA GPUs if available
try:
    import pynvml
    NVIDIA_NVML_AVAILABLE = True
except ImportError:
    NVIDIA_NVML_AVAILABLE = False
except Exception as e:
    print(f"Warning: Could not import or initialize pynvml (NVIDIA GPU monitoring). Error: {e}. NVIDIA monitoring will be disabled.")
    NVIDIA_NVML_AVAILABLE = False

class SystemMonitor:
    """
    Monitors system hardware components, including GPU, CPU, and RAM.
    Supports NVIDIA GPUs via pynvml and provides placeholders/subprocess for AMD/general CPU metrics.
    """
    def __init__(self, gpu_brand: str):
        """
        Initializes the SystemMonitor.
        :param gpu_brand: The brand of the GPU ("NVIDIA" or "AMD").
                          Note: AMD support is rudimentary and platform-dependent.
        """
        self.gpu_brand = gpu_brand.upper()
        self.os = platform.system()
        self.gpu_static_info = self._get_gpu_static_info()

    def _get_gpu_static_info(self) -> dict:
        """
        Attempts to get static GPU information (model, VRAM, driver version).
        Returns a dictionary with GPU info.
        """
        info = {"model": "Unknown", "vram_total_mb": "Unknown", "driver_version": "Unknown"}

        if self.gpu_brand == "NVIDIA" and NVIDIA_NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0) # Assuming single GPU for simplicity
                info["model"] = pynvml.nvmlDeviceGetName(handle)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                info["vram_total_mb"] = mem_info.total // (1024 * 1024) # Bytes to MB
                info["driver_version"] = pynvml.nvmlSystemGetDriverVersion()
            except pynvml.NVMLError as error:
                print(f"NVIDIA NVML Static Info Error: {error}. Check NVIDIA driver installation.")
            except Exception as e: # Catch any other unexpected errors during static info gathering
                print(f"Unexpected error getting NVIDIA static info: {e}")
            finally:
                try:
                    pynvml.nvmlShutdown()
                except pynvml.NVMLError_Uninitialized:
                    pass # Already shutdown or never initialized

        elif self.gpu_brand == "AMD":
            # AMD GPU static info is highly dependent on OS and specific AMD tools.
            # On Linux, 'amdgpu_top --json' can provide some details.
            if self.os == "Linux":
                try:
                    result = subprocess.run(['amdgpu_top', '--json'], capture_output=True, text=True, check=False)
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        if data and 'cards' in data and len(data['cards']) > 0:
                            card = data['cards'][0]
                            info["model"] = card.get("name", "AMD GPU (via amdgpu_top)")
                            info["vram_total_mb"] = card.get("vbios", {}).get("vram_size", "Unknown") # May vary
                            info["driver_version"] = "Check system info (Linux)"
                    else:
                        print(f"amdgpu_top error (static info): {result.stderr}")
                except FileNotFoundError:
                    print("amdgpu_top not found. Install it for better AMD GPU detection on Linux.")
                except json.JSONDecodeError:
                    print("Could not parse amdgpu_top JSON output for static info.")
                except Exception as e:
                    print(f"Error getting AMD GPU static info: {e}")
            else:
                print("Automated AMD GPU static info on Windows is challenging without vendor SDKs.")
        
        return info

    def get_realtime_metrics(self) -> dict:
        """
        Gathers real-time GPU, CPU, and RAM metrics.
        Returns a dictionary with current metric values.
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "gpu": {
                "temp_celsius": "N/A",
                "hotspot_temp_celsius": "N/A",
                "power_draw_watts": "N/A",
                "core_clock_mhz": "N/A",
                "memory_clock_mhz": "N/A",
                "fan_speed_percent": "N/A",
                "vram_used_mb": "N/A",
                "hash_rate_mhps": "N/A", # Placeholder: to be filled by parsing miner logs or user input
                "efficiency_jpmh": "N/A" # Placeholder: calculated if hash_rate and power_draw are available
            },
            "cpu": {
                "temperature_celsius": "N/A",
                "usage_percent": "N/A"
            },
            "ram": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
                "usage_percent": psutil.virtual_memory().percent
            }
        }

        # --- GPU Metrics ---
        if self.gpu_brand == "NVIDIA" and NVIDIA_NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0) # Assuming first GPU

                # Guard specific NVML attribute access
                if hasattr(pynvml, 'NVML_TEMP_GPU'):
                    metrics["gpu"]["temp_celsius"] = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMP_GPU)
                else:
                    metrics["gpu"]["temp_celsius"] = "N/A (NVML_TEMP_GPU not found)"

                if hasattr(pynvml, 'NVML_TEMP_GPU_MEM'):
                    try:
                        metrics["gpu"]["hotspot_temp_celsius"] = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMP_GPU_MEM)
                    except pynvml.NVMLError_NotSupported:
                        metrics["gpu"]["hotspot_temp_celsius"] = "N/A (Not Supported)"
                else:
                    metrics["gpu"]["hotspot_temp_celsius"] = "N/A (NVML_TEMP_GPU_MEM not found)"

                metrics["gpu"]["power_draw_watts"] = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                
                # Corrected nvmlDeviceGetClockInfo calls: removed third argument
                graphics_clock = "N/A"
                if hasattr(pynvml, 'NVML_CLOCK_GRAPHICS'):
                    try:
                        graphics_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
                    except pynvml.NVMLError_NotSupported:
                        graphics_clock = "N/A (Not Supported)"
                metrics["gpu"]["core_clock_mhz"] = graphics_clock

                memory_clock = "N/A"
                if hasattr(pynvml, 'NVML_CLOCK_MEM'):
                    try:
                        memory_clock = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM)
                    except pynvml.NVMLError_NotSupported:
                        memory_clock = "N/A (Not Supported)"
                metrics["gpu"]["memory_clock_mhz"] = memory_clock

                try:
                    metrics["gpu"]["fan_speed_percent"] = pynvml.nvmlDeviceGetFanSpeed(handle)
                except pynvml.NVMLError_NotSupported:
                    metrics["gpu"]["fan_speed_percent"] = "N/A (Not Supported)"

                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                metrics["gpu"]["vram_used_mb"] = mem_info.used // (1024 * 1024)

            except pynvml.NVMLError as error:
                print(f"NVIDIA NVML Runtime Error: {error}. Check if NVIDIA driver is loaded.")
            except Exception as e: # Catch any other unexpected errors during NVIDIA metric gathering
                print(f"Unexpected error getting NVIDIA real-time metrics: {e}")
            finally:
                try:
                    pynvml.nvmlShutdown()
                except pynvml.NVMLError_Uninitialized:
                    pass

        elif self.gpu_brand == "AMD" and self.os == "Linux":
            # Placeholder for AMD Linux using amdgpu_top via subprocess
            try:
                result = subprocess.run(['amdgpu_top', '--json'], capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if data and 'cards' in data and len(data['cards']) > 0:
                        card = data['cards'][0]
                        metrics["gpu"]["temp_celsius"] = card.get("temp", {}).get("edge", "N/A")
                        metrics["gpu"]["hotspot_temp_celsius"] = card.get("temp", {}).get("junction", "N/A")
                        metrics["gpu"]["power_draw_watts"] = card.get("power_average", "N/A") / 1000.0 if isinstance(card.get("power_average"), (int, float)) else "N/A"
                        metrics["gpu"]["core_clock_mhz"] = card.get("gfx_clk_freq", "N/A") / 1000000.0 if isinstance(card.get("gfx_clk_freq"), (int, float)) else "N/A"
                        metrics["gpu"]["memory_clock_mhz"] = card.get("mem_clk_freq", "N/A") / 1000000.0 if isinstance(card.get("mem_clk_freq"), (int, float)) else "N/A"
                        metrics["gpu"]["fan_speed_percent"] = card.get("fan_speed_percent", "N/A")
                        metrics["gpu"]["vram_used_mb"] = card.get("vram_used", "N/A")
                else:
                    print(f"amdgpu_top error (realtime info): {result.stderr}")
            except FileNotFoundError:
                print("amdgpu_top not found. Install it for better AMD GPU monitoring on Linux.")
            except json.JSONDecodeError:
                print("Could not parse amdgpu_top JSON output for real-time info.")
            except Exception as e:
                print(f"Error getting AMD GPU real-time metrics: {e}")
        else:
            # Fallback or message for unsupported AMD/Windows cases
            pass

        # --- CPU Metrics ---
        metrics["cpu"]["usage_percent"] = psutil.cpu_percent(interval=None) # Non-blocking

        # CPU Temperature (platform-dependent)
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                metrics["cpu"]["temperature_celsius"] = temps['coretemp'][0].current
            elif 'k10temp' in temps:
                metrics["cpu"]["temperature_celsius"] = temps['k10temp'][0].current
            elif 'cpu_thermal' in temps:
                 metrics["cpu"]["temperature_celsius"] = temps['cpu_thermal'][0].current

        return metrics

    def get_system_summary_string(self, realtime_metrics: dict) -> str:
        """
        Formats the static and real-time info into a string for the LLM prompt.
        :param realtime_metrics: The dictionary of real-time metrics.
        :return: A formatted string summary.
        """
        static_info = self.gpu_static_info
        summary = f"""
System Summary:
---
GPU (Brand: {self.gpu_brand}):
  Model: {static_info['model']}
  Driver Version: {static_info['driver_version']}
  Total VRAM: {static_info['vram_total_mb']} MB
  Current Temp: {realtime_metrics['gpu']['temp_celsius']}°C
  Current Hot Spot Temp: {realtime_metrics['gpu']['hotspot_temp_celsius']}°C
  Current Power Draw: {realtime_metrics['gpu']['power_draw_watts']}W
  Current Core Clock: {realtime_metrics['gpu']['core_clock_mhz']}MHz
  Current Memory Clock: {realtime_metrics['gpu']['memory_clock_mhz']}MHz
  Current Fan Speed: {realtime_metrics['gpu']['fan_speed_percent']}%
  Current VRAM Used: {realtime_metrics['gpu']['vram_used_mb']} MB

CPU:
  Temperature: {realtime_metrics['cpu']['temperature_celsius']}°C
  Usage: {realtime_metrics['cpu']['usage_percent']}%

RAM:
  Total: {realtime_metrics['ram']['total_gb']} GB
  Used: {realtime_metrics['ram']['used_gb']} GB ({realtime_metrics['ram']['usage_percent']}%)

Operating System: {self.os}
"""
        return summary

# Example Usage (for independent testing)
if __name__ == "__main__":
    # IMPORTANT: Set your GPU brand here for testing
    monitor = SystemMonitor(gpu_brand="NVIDIA") 
    print("Static GPU Info:", monitor.gpu_static_info)

    print("\nReal-time Metrics (Looping for 3 samples):")
    for _ in range(3):
        metrics = monitor.get_realtime_metrics()
        print(monitor.get_system_summary_string(metrics))
        print("-" * 30)
        time.sleep(2) # Shorter interval for testing
