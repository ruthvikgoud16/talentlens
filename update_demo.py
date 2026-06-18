import re
import csv

def main():
    # 1. Read final_submission.csv
    cands = []
    with open("final_submission.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if row:
                cid, rank, score, reasoning = row
                
                # Parse recruitability score from reasoning
                val_match = re.search(r"(?:Recruitability:\s*|score of\s*)(\d+)", reasoning)
                if val_match:
                    val = int(val_match.group(1))
                else:
                    val = 70
                    
                if val >= 75:
                    recruit = f"High ({val})"
                elif val >= 50:
                    recruit = f"Mod ({val})"
                else:
                    recruit = f"Low ({val})"
                    
                cands.append({
                    "rank": int(rank),
                    "id": cid,
                    "score": round(float(score), 2),
                    "recruit": recruit,
                    "recruitVal": val,
                    "reasoning": reasoning.replace('"', '\\"')
                })

    print(f"Loaded {len(cands)} candidates from final_submission.csv")

    # 2. Format as Javascript array block
    js_lines = []
    js_lines.append("    const candidates = [")
    for c in cands:
        line = f'        {{ rank:{c["rank"]}, id:"{c["id"]}", score:{c["score"]:.2f}, recruit:"{c["recruit"]}", recruitVal:{c["recruitVal"]}, reasoning:"{c["reasoning"]}" }},'
        js_lines.append(line)
    js_lines.append("    ];")
    
    js_block = "\n".join(js_lines)

    # 3. Read submission_demo.html and replace candidates array using string slicing
    with open("submission_demo.html", "r", encoding="utf-8") as f:
        content = f.read()

    start_str = "const candidates = ["
    start_idx = content.find(start_str)
    if start_idx != -1:
        # Find the closing "];" after start_idx
        end_idx = content.find("];", start_idx)
        if end_idx != -1:
            end_idx += 2 # include the "];"
            new_content = content[:start_idx] + js_block + content[end_idx:]
            
            with open("submission_demo.html", "w", encoding="utf-8") as f:
                f.write(new_content)
            print("Successfully updated submission_demo.html with new candidates array!")
        else:
            print("ERROR: Could not find closing ]; in submission_demo.html")
    else:
        print("ERROR: Could not find start of candidates array in submission_demo.html")

if __name__ == "__main__":
    main()
