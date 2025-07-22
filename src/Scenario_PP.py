import os
import json
import json5 
import re

input_dir = "./result"
output_dir = "./result/scenarios"

_illegal_backslash = re.compile(r'\\(?!["\\/bfnrtu])')  # 
_missing_comma = re.compile(r'([}\]"])\s*\n\s*["{\[]')   # 

def fix_json(text: str) -> str:

    text = _illegal_backslash.sub(r'\\\\', text)         # \ → \\ 
    text = _missing_comma.sub(r'\1,\n', text)            # 
    return text


def main() :

    os.makedirs(output_dir, exist_ok=True)

  
    print(f"Splitting JSON 'scenarios' into chunks of 5...")

    #
    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(input_dir, filename)

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e1:
                    # 2) json5 
                    if json5:
                        try:
                            data = json5.loads(content)
                        except Exception as e2:        # json5.JSONDecodeError 
                            data = None
                            e_last = e2
                        else:
                            e_last = None
                    else:
                        data = None
                        e_last = e1
            if data is None:
                try:
                    data = json.loads(fix_json(content))
                except json.JSONDecodeError as e3:
                    print(f"❌ Error parsing {filename}: {e_last or e3}")
                    continue  # 
                
            #
            scenarios = data.get("scenarios", [])
            chunks = [scenarios[i:i + 5] for i in range(0, len(scenarios), 5)]

            base_name = os.path.splitext(filename)[0]
            for idx, chunk in enumerate(chunks, start=1):
                output_data = {"scenarios": chunk}
                out_filename = f"{base_name}_part_{idx}.txt"
                out_path = os.path.join(output_dir, out_filename)
                with open(out_path, "w", encoding="utf-8") as out_f:
                    json.dump(output_data, out_f, indent=2, ensure_ascii=False)

            print(f"✅ {filename} → {len(chunks)} parts saved to {output_dir}/")

    print("🎉 Done.")

main()
