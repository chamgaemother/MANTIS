import os
import json
import json5 
import re

input_dir = "./result"
output_dir = "./result/scenarios"

_illegal_backslash = re.compile(r'\\(?!["\\/bfnrtu])')  # 허용되지 않은 \escape
_missing_comma = re.compile(r'([}\]"])\s*\n\s*["{\[]')   # 줄바꿈 다음 요소인데 , 누락

def fix_json(text: str) -> str:
    """JSON 표준 위반을 최소한으로 보정"""
    text = _illegal_backslash.sub(r'\\\\', text)         # \ → \\ (불법 escape)
    text = _missing_comma.sub(r'\1,\n', text)            # 줄바꿈 뒤 , 삽입
    return text


def main() :
    # 출력 디렉토리 생성 (없으면)
    os.makedirs(output_dir, exist_ok=True)

    # 결과 출력용
    print(f"Splitting JSON 'scenarios' into chunks of 5...")

    # .txt 파일 반복 처리
    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(input_dir, filename)

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e1:
                    # 2) json5 (주석·싱글쿼트·트레일링 콤마 등 허용)
                    if json5:
                        try:
                            data = json5.loads(content)
                        except Exception as e2:        # json5.JSONDecodeError 포함
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
                    continue  # 세 번 모두 실패 → 다음 파일로
                
            # 시나리오 추출 및 분할
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