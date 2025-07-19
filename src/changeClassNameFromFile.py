import os
import re
import sys
import io
import json
from pathlib import Path



from config import Config

# 콘솔 출력 인코딩 설정

target_folder = "./result"
JSON_PATH = Config.get_json_path()


def fix_class_name_to_match_filename(file_path):
    filename = os.path.basename(file_path)
    file_class_name = os.path.splitext(filename)[0]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        pattern = r'\bpublic\s+class\s+([A-Za-z_]\w*)'
        match = re.search(pattern, content)

        if not match:
            print(f"[SKIP] public class 선언 없음: {filename}")
            content = content.replace("class", "public class ", 1)
            print(f"[수정] public class 선언 추가됨: {filename}")

        match = re.search(pattern, content)
        if match:
            declared_class_name = match.group(1)
            if declared_class_name != file_class_name:
                print(f"[수정] 파일명: {file_class_name} ← 클래스명: {declared_class_name}")
                # 클래스 이름 교체 (처음 1번만)
                updated_content = re.sub(
                    rf'\bpublic\s+class\s+{declared_class_name}',
                    f'public class {file_class_name}',
                    content,
                    count=1
                )
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
        else:
            print(f"[SKIP] public class 선언 없음: {filename}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        json_file = Path(JSON_PATH)
        with json_file.open(encoding="utf-8") as f:
            data = json.load(f)            # → Python list[ dict ]

        target_dict = dict()

        target_name = file_class_name.split("_")[0]
        method_name = file_class_name.split("_")[1]
    
            
        for d in data:
            if target_name in d["clazz"] and method_name in d["methodName"]:
                target_dict = d
                break


        pakage_name = ".".join(target_dict["clazz"].split(".")[:-1])
        print(pakage_name)
        if f"package {pakage_name}"+";" in content :
            print("package 선언 있음.")
        elif "package" in content :
            print("package 선언 이상함.")
            pattern = r'^\s*package\s+([a-zA-Z_][\w\.]*);'
            match = re.match(pattern, content)
            updated_content = content.replace(match.group(1), f" {pakage_name}")
            with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
            print("package 수정 완료!")
        else : 
            print("package 선언 없음.")
            updated_content = f"package {pakage_name};\n\n" + content
            with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
            print("package 수정 완료.")


    except Exception as e:
        print(f"[에러] {file_path}: {e}")

def fix_all_classes_in_folder(folder_path):
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.java'):
                full_path = os.path.join(root, file)
                fix_class_name_to_match_filename(full_path)

def main():
    fix_all_classes_in_folder(target_folder)

