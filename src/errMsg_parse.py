from Utils import count_txt_files_in_scenarios, count_txt_files_in_enhance, count_txt_files_in_enhance2
import csv
import os
import re


CSV_FILE = "path_temp.csv"  
log_dir = "./error_logs"
result_dir = "./result"


def err_parse() :
    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f) 
        for row in reader:
            
            class_value = row['class']
            test_path   = row['test']
            name_value  = row['name']

            target_txt= ""
            target_list = []
            save_dict = dict()

            if count_txt_files_in_enhance2() > 0 :
                    i = count_txt_files_in_enhance2()
                    target_txt = os.path.join(log_dir, f"{class_value}_{name_value}_2_{i}_Test_outMsg.txt")
                    for j in range(1, i +1) :
                        target_list.append(f"{class_value}_{name_value}_2_{j}_Test")
                        save_dict[f"{class_value}_{name_value}_2_{j}_Test"] = []
                        
            elif count_txt_files_in_enhance() > 0 :
                    i = count_txt_files_in_enhance()
                    target_txt = os.path.join(log_dir, f"{class_value}_{name_value}_1_{i}_Test_outMsg.txt")
                    for j in range(1, i +1) :
                        target_list.append(f"{class_value}_{name_value}_1_{j}_Test")
                        save_dict[f"{class_value}_{name_value}_1_{j}_Test"] = []
                        
            else : # 
          
                i = count_txt_files_in_scenarios()
                target_txt = os.path.join(log_dir, f"{class_value}_{name_value}_0_{i}_Test_outMsg.txt")
                for j in range(1, i +1) :
                    target_list.append(f"{class_value}_{name_value}_0_{j}_Test")
                    save_dict[f"{class_value}_{name_value}_0_{j}_Test"] = []
            

            if not os.path.exists(target_txt):
                print("⚠️ :", target_txt)
                continue

            with open(target_txt, encoding="utf-8") as log_f:
                current_target = None  # 

                for line in log_f:
                    if "[ERROR]" not in line:
                        # 
                        current_target = None
                        continue

                    # 1) 
                    matched = next(
                        (t for t in target_list if t in line), None
                    )
                    if matched:
                        current_target = matched
                        save_dict[matched].append(line)
                        continue

                    # 2) 
                    if current_target:
                        save_dict[current_target].append(line)

 
            for key, lines in save_dict.items():
                if not lines:
                    continue
                out_path = os.path.join(result_dir, f"{key}_outMsg.txt")
                with open(out_path, "w", encoding="utf-8") as out_f:
                    out_f.writelines(lines)
                print(f"✅ {out_path} save ({len(lines)} lines)")

