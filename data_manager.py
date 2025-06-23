import json
import os
from datetime import datetime

class DataManager:
    """
    Manages the storage and retrieval of application data, including
    system metrics logs and LLM recommendations.
    """
    def __init__(self, base_data_dir: str = "app_data"):
        """
        Initializes the DataManager.
        :param base_data_dir: The base directory where all application data will be stored.
        """
        self.base_data_dir = base_data_dir
        self.log_dir = os.path.join(self.base_data_dir, "logs")
        self.recommendations_dir = os.path.join(self.base_data_dir, "recommendations")
        self.knowledge_base_dir = os.path.join(self.base_data_dir, "knowledge_base") # For future RAG source data

        # Ensure directories exist
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.recommendations_dir, exist_ok=True)
        os.makedirs(self.knowledge_base_dir, exist_ok=True)

        self.log_file = os.path.join(self.log_dir, "system_metrics.jsonl") # JSON Lines for easy appending

    def log_metrics(self, metrics: dict, context: dict = None):
        """
        Logs system metrics to a JSON Lines file.
        :param metrics: A dictionary of system metrics.
        :param context: Optional additional context (e.g., current recommendation ID).
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
        if context:
            log_entry.update(context)

        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            # print(f"Metrics logged to {self.log_file}") # Uncomment for verbose logging
        except Exception as e:
            print(f"Error logging metrics: {e}")

    def save_recommendation(self, recommendation_text: str, current_metrics: dict, user_goal: str, algorithm: str) -> str:
        """
        Saves an LLM recommendation to a JSON file and returns its unique ID.
        :param recommendation_text: The full text of the LLM's recommendation.
        :param current_metrics: The system metrics at the time the recommendation was made.
        :param user_goal: The user's stated goal for the recommendation.
        :param algorithm: The mining algorithm specified.
        :return: The unique ID of the saved recommendation.
        """
        rec_id = datetime.now().strftime("%Y%m%d%H%M%S") # Unique ID based on timestamp
        rec_file_path = os.path.join(self.recommendations_dir, f"recommendation_{rec_id}.json")
        
        rec_data = {
            "id": rec_id,
            "timestamp": datetime.now().isoformat(),
            "user_goal": user_goal,
            "mining_algorithm": algorithm,
            "system_snapshot_at_recommendation": current_metrics,
            "llm_recommendation_text": recommendation_text,
            "applied_status": "PENDING_USER_APPLY", # Initial status
            "actual_performance_after_apply": {} # To be filled later
        }
        
        try:
            with open(rec_file_path, 'w') as f:
                json.dump(rec_data, f, indent=4)
            print(f"Recommendation saved to {rec_file_path}")
            return rec_id
        except Exception as e:
            print(f"Error saving recommendation: {e}")
            return "ERROR"

    def update_recommendation_status(self, rec_id: str, status: str, actual_metrics: dict = None, notes: str = ""):
        """
        Updates the status and actual performance of a saved recommendation.
        :param rec_id: The ID of the recommendation to update.
        :param status: The new status (e.g., "APPLIED", "FAILED", "REVERTED", "CANCELLED").
        :param actual_metrics: Optional dictionary of actual metrics after applying settings.
        :param notes: Optional notes from the user about the outcome.
        """
        rec_file_path = os.path.join(self.recommendations_dir, f"recommendation_{rec_id}.json")
        if not os.path.exists(rec_file_path):
            print(f"Error: Recommendation ID {rec_id} not found at {rec_file_path}.")
            return

        try:
            with open(rec_file_path, 'r+') as f:
                data = json.load(f)
                data["applied_status"] = status
                if actual_metrics:
                    data["actual_performance_after_apply"] = actual_metrics
                if notes:
                    data["user_notes"] = notes
                data["last_updated"] = datetime.now().isoformat()
                
                f.seek(0) # Rewind to beginning
                json.dump(data, f, indent=4)
                f.truncate() # Trim any leftover content
            print(f"Recommendation {rec_id} status updated to {status}.")
        except Exception as e:
            print(f"Error updating recommendation {rec_id}: {e}")

    def load_recommendation(self, rec_id: str) -> dict or None:
        """
        Loads a specific recommendation by its ID.
        :param rec_id: The ID of the recommendation to load.
        :return: The recommendation dictionary or None if not found/error.
        """
        rec_file_path = os.path.join(self.recommendations_dir, f"recommendation_{rec_id}.json")
        if os.path.exists(rec_file_path):
            try:
                with open(rec_file_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON for recommendation {rec_id}: {e}")
                return None
            except Exception as e:
                print(f"Error loading recommendation {rec_id}: {e}")
                return None
        return None

    def load_all_recommendations(self) -> list:
        """
        Loads all saved recommendations.
        :return: A list of recommendation dictionaries.
        """
        recommendations = []
        for filename in os.listdir(self.recommendations_dir):
            if filename.startswith("recommendation_") and filename.endswith(".json"):
                rec_id = filename.replace("recommendation_", "").replace(".json", "")
                rec = self.load_recommendation(rec_id)
                if rec:
                    recommendations.append(rec)
        # Sort by timestamp (most recent first)
        recommendations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return recommendations

    # --- Methods for future RAG / Knowledge Base ---
    def add_knowledge_chunk(self, content: str, source_info: dict):
        """
        Simulates adding a text chunk to a knowledge base directory.
        In a full RAG setup, this would embed and add to a vector DB.
        For simplicity, we'll save as text files for now.
        """
        filename = os.path.join(self.knowledge_base_dir, f"kb_chunk_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.json")
        chunk_data = {
            "content": content,
            "source": source_info,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(filename, 'w') as f:
                json.dump(chunk_data, f, indent=4)
            print(f"Knowledge chunk saved: {filename}")
        except Exception as e:
            print(f"Error saving knowledge chunk: {e}")

    def get_knowledge_chunks(self) -> list:
        """Retrieves all knowledge chunks (for LLM context assembly if not using a vector DB)."""
        chunks = []
        for filename in os.listdir(self.knowledge_base_dir):
            if filename.startswith("kb_chunk_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.knowledge_base_dir, filename), 'r') as f:
                        chunks.append(json.load(f))
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not decode knowledge chunk {filename}: {e}, skipping.")
                except Exception as e:
                    print(f"Error loading knowledge chunk {filename}: {e}, skipping.")
        return chunks

# Example Usage (for independent testing)
if __name__ == "__main__":
    # Create a dummy config for testing DataManager
    dummy_config = {"app_data_dir": "test_app_data"}
    dm = DataManager(base_data_dir=dummy_config["app_data_dir"])

    # Clean up previous test data
    import shutil
    if os.path.exists(dummy_config["app_data_dir"]):
        shutil.rmtree(dummy_config["app_data_dir"])
        os.makedirs(os.path.join(dummy_config["app_data_dir"], "logs"), exist_ok=True)
        os.makedirs(os.path.join(dummy_config["app_data_dir"], "recommendations"), exist_ok=True)
        os.makedirs(os.path.join(dummy_config["app_data_dir"], "knowledge_base"), exist_ok=True)

    print("Testing DataManager...")
    
    # Mock system metrics
    mock_metrics = {
        "gpu": {"temp_celsius": 65, "power_draw_watts": 200, "hash_rate_mhps": 50},
        "cpu": {"temperature_celsius": 45, "usage_percent": 15},
        "ram": {"total_gb": 16, "used_gb": 8, "usage_percent": 50}
    }

    # Log some metrics
    dm.log_metrics(mock_metrics, context={"test_context": "initial_state"})
    time.sleep(1)
    dm.log_metrics(mock_metrics)

    # Save a mock recommendation
    mock_rec_text = "Core Clock: +100MHz, Memory Clock: +1200MHz, Power Limit: 70%, Fan: 70%. Expect 60MH/s at 120W."
    rec_id = dm.save_recommendation(mock_rec_text, mock_metrics, "Maximize efficiency", "Ethash")
    print(f"Saved recommendation with ID: {rec_id}")
    
    # Simulate user applying settings and getting new metrics
    time.sleep(2) # Simulate time passing
    mock_new_metrics = {
        "gpu": {"temp_celsius": 68, "power_draw_watts": 122, "hash_rate_mhps": 60.5},
        "cpu": {"temperature_celsius": 46, "usage_percent": 20},
        "ram": {"total_gb": 16, "used_gb": 8, "usage_percent": 50}
    }
    dm.update_recommendation_status(rec_id, "APPLIED", mock_new_metrics, "Stable and efficient!")

    # Load and print the updated recommendation
    loaded_rec = dm.load_recommendation(rec_id)
    print("\nLoaded Recommendation:")
    print(json.dumps(loaded_rec, indent=4))

    # Add a knowledge chunk
    dm.add_knowledge_chunk(
        "RTX 3070 often undervolts well. Check junction temps for stability.",
        {"source": "online_guide", "url": "example.com/guide"}
    )
    print("\nKnowledge chunks:")
    for chunk in dm.get_knowledge_chunks():
        print(f"- {chunk['content']} (Source: {chunk['source'].get('source', 'N/A')})")

    # Load all recommendations
    all_recs = dm.load_all_recommendations()
    print(f"\nTotal recommendations loaded: {len(all_recs)}")
    # For cleanup
    # shutil.rmtree(dummy_config["app_data_dir"])
