import os

def main():
    log_path = "C:/Users/rudra/.gemini/antigravity-ide/brain/c2a3c5df-a720-4502-a4f4-6c8c3f170ded/.system_generated/tasks/task-714.log"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            print("--- LOG TAIL (last 20 lines) ---")
            for line in lines[-20:]:
                print(line, end="")
    else:
        print(f"Log path does not exist: {log_path}")
        # Let's search the directory for any .log files in tasks
        tasks_dir = "C:/Users/rudra/.gemini/antigravity-ide/brain/c2a3c5df-a720-4502-a4f4-6c8c3f170ded/.system_generated/tasks/"
        if os.path.exists(tasks_dir):
            print("Available task logs:")
            for f in os.listdir(tasks_dir):
                if f.endswith(".log"):
                    print(f"  {f}")

if __name__ == "__main__":
    main()
