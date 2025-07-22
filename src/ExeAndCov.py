import csv
import os
import re
import subprocess
import pandas as pd
from pathlib import Path
import sys
import io
import xml.etree.ElementTree as ET
import shutil

from Utils import count_txt_files_in_scenarios, count_txt_files_in_enhance, count_txt_files_in_enhance2


SOURCE_DIR = "./result" 

############################################

IMPORT_FLAG = False

PRIM_J2D = {"boolean":"Z","byte":"B","char":"C","short":"S",
            "int":"I","long":"J","float":"F","double":"D","void":"V"}
PRIM_D2J = {v:k for k,v in PRIM_J2D.items()}

def jtype_to_desc(jtype:str)->str:
    arr = jtype.count("[]")
    base = jtype.replace("[]","")
    desc = PRIM_J2D.get(base, f"L{base.replace('.','/')};")
    return "["*arr + desc


def soot_to_desc(soot:str)->str:

    sig = soot.split(":")[1].strip(" >")
    ret, rest = sig.split(None,1)
    name, params = rest.split("(",1)
    params = params.rstrip(")")
    p_desc = "".join(jtype_to_desc(t.strip()) for t in params.split(",") if t)
    return f"({p_desc}){jtype_to_desc(ret)}"

def parse_cannot_find_symbol(error_text):

    pat_file = re.compile(r'\[ERROR\]\s+(.+?\.java):\[\d+,\d+\]\s+cannot\s+find\s+symbol')
    pat_symbol = re.compile(r'symbol:\s*class\s+(\w+)')

    lines = error_text.splitlines()
    results = []
    i = 0

    while i < len(lines):
        line = lines[i]

        m_file = pat_file.search(line)
        if m_file:
            test_file_path = m_file.group(1)
 
            j = i + 1
            found_class = None
            while j < len(lines):
                m_sym = pat_symbol.search(lines[j])
                if m_sym:
                    found_class = m_sym.group(1)
               
                    results.append((test_file_path, found_class))
                    break
                j += 1
            i = j
        else:
            i += 1

    return results


def get_src_main_folder(file_path):

    norm = file_path.replace("\\", "/") 
    if "src/" not in norm:
        print(f"[WARN] 'src/' not found in path: {file_path}")
        return None

    prefix = norm.split("src/")[0] 
    main_java_folder = os.path.join(prefix, "src", "main", "java")

    main_java_folder = main_java_folder.replace("/", os.sep)
    return main_java_folder


def find_java_file_by_classname(root_folder, class_name):

    root_folder = root_folder[1:]
    if not root_folder or not os.path.isdir(root_folder):
        print(f"[WARN] : {root_folder}")
        return None

    target_file = class_name + ".java"
    for base, dirs, files in os.walk(root_folder):
        if target_file in files:
            return os.path.join(base, target_file)

    return None


def parse_package_name(java_file_path):

    if not os.path.isfile(java_file_path):
        return ""
    with open(java_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line_strip = line.strip()
            if line_strip.startswith("package "):
    
                pkg = line_strip.replace("package ", "").replace(";", "").strip()
                return pkg
    return ""


def add_import_to_file(test_file_path, import_statement):
        global IMPORT_FLAG

        test_file_path = test_file_path[1:]
        if not os.path.isfile(test_file_path):
            print(f"[WARN] : {test_file_path}")
            return

        with open(test_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

 
        already_imported = any(import_statement in ln for ln in lines)
        if already_imported:
            print(f"[INFO] 이미 import된 {import_statement} in {test_file_path}")
            return

        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if (not inserted) and line.strip().startswith("package "):
                new_lines.append(import_statement + "\n")
                inserted = True

        if not inserted:
          
            new_lines.insert(0, import_statement + "\n")

        with open(test_file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"[DONE] {test_file_path} → {import_statement} 추가로 import 수정됌.")
        IMPORT_FLAG = True
        



############################################

def add_basic_import(test_file_paths: list, import_statement: str):
    global IMPORT_FLAG

    for test_file_path in test_file_paths :

        path = Path(test_file_path)
        if not path.exists():
            print(f"[ERROR] : {test_file_path}")
            return

        lines = path.read_text(encoding='utf-8').splitlines()


        if any(line.strip() == import_statement for line in lines):
            print(f"[INFO] : {import_statement}")
            return

 
        package_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("package "):
                package_index = i
                break

        insert_index = package_index + 1 if package_index >= 0 else 0

     
        lines.insert(insert_index, import_statement)

    
        path.write_text("\n".join(lines), encoding='utf-8')
        print(f"[SUCCESS] import : {import_statement} -> {test_file_path}")
        IMPORT_FLAG = True


def fix_missing_classes_with_dynamic_src(error_log_text):
    missing_list = parse_cannot_find_symbol(error_log_text)
    print(missing_list)


    for test_file_path, cls_name in missing_list:


        print(test_file_path, cls_name)
  
        src_main_folder = get_src_main_folder(test_file_path)
        if not src_main_folder:
            print(f"[ERROR] src/main/java  ({test_file_path})")
            continue

  
        matched = find_java_file_by_classname(src_main_folder, cls_name)
        if not matched:
            print(f"[ERROR] {cls_name}.java not found in  '{src_main_folder}'")
            continue

        pkg = parse_package_name(matched)
        if not pkg:
            print(f"[WARN] package  {matched}")
            continue

        import_stmt = f"import {pkg}.{cls_name};"
        add_import_to_file(test_file_path, import_stmt)
    return missing_list

import re

FIELDNAMES = ["lib", "class","method" ,"path", "test", "name", "folder", "method_signiture"]
CSV_FILE = "path_temp.csv"

TEST_SUMMARY_PATTERN = re.compile(
    r"(?:\[\w+\])?\s*"
    r"Tests run:\s*(\d+),\s*"
    r"Failures:\s*(\d+),\s*"
    r"Errors:\s*(\d+),\s*"
    r"Skipped:\s*(\d+)"
    r"(?:,\s*Time elapsed:\s*([0-9.]+)\s*s)?"
)

results = []

def count_java_files(directory):
    java_file_count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                java_file_count += 1
    return java_file_count


def run_coverage_for_class(row):
    global IMPORT_FLAG
    return_Flag = False
    IMPORT_FLAG = False
    class_name = row.get("class", "").strip()
    method_name = row.get("method", "").strip()
    method_signiture = row.get("method_signiture", "").strip()
    test_path = row.get("test", "").strip()
    if method_name == "method": 
        return 0, return_Flag
    
    scenario_n = count_txt_files_in_scenarios()
    java_n = count_java_files(SOURCE_DIR)
    enhance_n =count_txt_files_in_enhance()
    enhance2_n = count_txt_files_in_enhance2()
    target_classes = []
    target_files = []
    for i in range(1, scenario_n+1): 
        target_file = os.path.join(test_path, f"{class_name}_{method_name}_0_{i}_Test.java")
        t = f"{class_name}_{method_name}_0_{i}_Test"
        if os.path.exists(target_file):
            target_classes.append(t)
            target_files.append(target_file)
        else:
            break
    if scenario_n - java_n != 0: 
        for j in range(1, enhance_n+ 1):
            target_file = os.path.join(test_path, f"{class_name}_{method_name}_1_{j}_Test.java")
            t = f"{class_name}_{method_name}_1_{j}_Test"
            if os.path.exists(target_file):
                target_classes.append(t)
                target_files.append(target_file)
            else:
                break

        if enhance2_n > 0:
            for j in range(1, enhance2_n+ 1):
                target_file = os.path.join(test_path, f"{class_name}_{method_name}_2_{j}_Test.java")
                t = f"{class_name}_{method_name}_2_{j}_Test"
                if os.path.exists(target_file):
                    target_classes.append(t)
                    target_files.append(target_file)
                else:
                    break

    target_file = ""
    if scenario_n - java_n == 0:
        target_file = os.path.join(test_path, f"{class_name}_{method_name}_0_{len(target_classes)}_Test.java")
    elif enhance2_n == 0 : 
        target_file = os.path.join(test_path, f"{class_name}_{method_name}_1_{len(target_classes) - scenario_n}_Test.java")
    else :
        target_file = os.path.join(test_path, f"{class_name}_{method_name}_2_{len(target_classes) - scenario_n - enhance_n}_Test.java")

        
    target_class = ",".join(target_classes)
 
        
    test_class_name = target_classes[-1]

    print(target_class)
    
    agt_test_folder = row["folder"]
    project_root = os.path.abspath(os.path.join(agt_test_folder, "..", ".."))
    jdk_home       = r"YOUT_JDK_PATH" # your path in

    
    jacoco_cmd = "org.jacoco:jacoco-maven-plugin:report"

    

    env = os.environ.copy()
    env["JAVA_HOME"] = jdk_home
    env["PATH"] = fr"{jdk_home}\bin;{env['PATH']}" 

    mvn_exe = shutil.which("mvn", path=env["PATH"]) 

    mvn_cmd = [
        mvn_exe,
        "clean",
        # "org.jacoco:jacoco-maven-plugin:prepare-agent",
        "test", 
        f"-Dtest={target_class}",
        "-Dmaven.test.failure.ignore=true",
        # "-Dsurefire.exiteTimeout=2",
        "-Drat.skip=true",
        # "-Dgpg.skip=true",
        "org.jacoco:jacoco-maven-plugin:report"
    ]

    print(f"\n=== Processing {class_name} {method_name} ===")
    print("[INFO] Project root :", project_root)
    print("[INFO] Running Maven:", " ".join(mvn_cmd))

    if mvn_exe is None:                                 
        wrapper = Path(project_root) / ("mvnw.cmd" if os.name == "nt" else "mvnw")
        if wrapper.exists():
            mvn_exe = str(wrapper)
        else:
            raise FileNotFoundError(
                "Maven not found"
                "MAVEN_HOME/M2_HOME check"
            )


    try:
        result = subprocess.run(
            " ".join(mvn_cmd),
            env=env,
            cwd=project_root,
            shell=False,
            capture_output=True,
            text=True,
            timeout=300 
        )
    except Exception as e:
        print(f"[ERROR] Maven execution failed for {method_name}:", e)
        return None, return_Flag
    

    stdout_text = result.stdout
    stderr_text = result.stderr


    log_dir = "./error_logs"
    os.makedirs(log_dir, exist_ok=True)

    if stderr_text != None:


        err_filename = f"{test_class_name}_errMsg.txt"
        err_filepath = os.path.join(log_dir, err_filename)
        with open(err_filepath, "w", encoding="utf-8") as f:
            f.write(stderr_text)
        print(f"** Saved stderr to {err_filepath}")
        

    if stderr_text != None: 

        out_filename = f"{test_class_name}_outMsg.txt"
        out_filepath = os.path.join(log_dir, out_filename)
        with open(out_filepath, "w", encoding="utf-8") as f:
            f.write(stdout_text)
        print(f"** Saved stdout to {out_filepath}")

 
    file_map = fix_missing_classes_with_dynamic_src(stdout_text)

    if len(file_map) > 0 :
        add_basic_import(target_files, "import java.util.*;")
        add_basic_import(target_files, "import java.io.*;")
        add_basic_import(target_files, "import static org.mockito.Mockito.*;")
        add_basic_import(target_files, "import java.lang.reflect.*;")

    print("import flag", IMPORT_FLAG)

    if IMPORT_FLAG :

        return 1, return_Flag
    

    tests_run = failures = errors = skipped = None
    time_elapsed = None

    summary_lines = []
    for line in stdout_text.splitlines():
        if "Tests run:" in line:
            summary_lines.append(line)

    if summary_lines:
        match = TEST_SUMMARY_PATTERN.search(summary_lines[-1])
        if match:
            tests_run = int(match.group(1))
            failures = int(match.group(2))
            errors = int(match.group(3))
            skipped = int(match.group(4))
            if match.group(5) is not None:
                time_elapsed = float(match.group(5))
            else:
                time_elapsed = 0.0
            print(f"[save info] Tests run: {tests_run}, Failures: {failures}, Errors: {errors}, Skipped: {skipped}")
            return_Flag = True
    else:
        print(f"[INFO] No test summary line found for {method_name}")

    if result.returncode != 0:
        print(f"[ERROR] Maven build/test failed for {method_name}")
        print("----- Maven stderr -----")
        print(result.stderr)
        return None, return_Flag


    jacoco_xml_path = os.path.join(project_root, "target", "site", "jacoco", "jacoco.xml")
    line_coverage = "-"
    branch_coverage = "-"

    results = []

    if not os.path.exists(jacoco_xml_path):
        print("[ERROR] jacoco.xml not found:", jacoco_xml_path)
        return results, return_Flag
    else :
        print("--coverage--")
        return_Flag =True

    tree = ET.parse(jacoco_xml_path)
    root = tree.getroot()

    found = False
    for package in root.findall("package"):
        for clazz in package.findall("class"):
            fqcn = clazz.get("name").replace("/", ".")
            c_name = fqcn.split(".")[-1]
            if class_name == c_name:
                found = True
                for method in clazz.findall("method"):
                    m_name = method.get("name")
                    m_desc = method.get("desc")

                    if m_name != method_name:
                        continue

                    print(m_desc, method_signiture)
                    if m_desc != soot_to_desc(method_signiture) :
                        continue

                    # Coverage counters
                    counters = {c.get("type"): c for c in method.findall("counter")}

                    # Line Coverage
                    if "LINE" in counters:
                        line_missed = int(counters["LINE"].get("missed"))
                        line_covered = int(counters["LINE"].get("covered"))
                        line_total = line_missed + line_covered
                        line_coverage = (line_covered / line_total * 100) if line_total > 0 else 0
                    else:
                        line_coverage = "-"

                    # Branch Coverage
                    if "BRANCH" in counters:
                        branch_missed = int(counters["BRANCH"].get("missed"))
                        branch_covered = int(counters["BRANCH"].get("covered"))
                        branch_total = branch_missed + branch_covered
 
                        branch_coverage = (branch_covered / branch_total * 100) if branch_total > 0 else 0
                    else:
                        branch_coverage = "-"

                    print(f"{fqcn}::{m_name}{m_desc}")
                    print(f"  line coverage : {line_coverage:.2f}%" if line_coverage != "-" else "  line coverage: -")
                    print(f"  branch coverage: {branch_coverage:.2f}%" if branch_coverage != "-" else "  branch coverage: -")

                    results.append({
                        "class": fqcn,
                        "method": m_name,
                        "desc": m_desc,
                        "line_coverage": line_coverage,
                        "branch_coverage": branch_coverage,
                    })

    if not found:
        print(f"[WARN] class '{class_name}' is not found in jacoco.xml.")

    return results, return_Flag


def main():
    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f, fieldnames=FIELDNAMES)
        for row in reader:
            row_result, Flag = run_coverage_for_class(row)
            if row_result == 1 :

                row_result = run_coverage_for_class(row)
            elif row_result == 0 :
                continue
            if Flag :
                try :
                    print("line_coverage: ", row_result[0]["line_coverage"],", branch_coverage: " , row_result[0]["branch_coverage"] )
                    return row_result[0]["line_coverage"], row_result[0]["branch_coverage"]
                except Exception :

                    return 1, 1
            else :
                return "-", "-"



if __name__ == "__main__":
    l, b = main()
    print(l, b)
