#!/usr/bin/env python
import os
import subprocess
import optparse
import pickle
import time
import json
import numpy as np
import hashlib
import copy
from sklearn.cluster import MeanShift, estimate_bandwidth

benchmark_dir = os.path.abspath("../benchmark")
to=10
bytecode_dict = {
 'commonmark': os.path.abspath('../benchmark/originalcode/commonmark.jar'),
 'jackson-dataformat-csv': os.path.abspath('../benchmark/originalcode/jackson-dataformat-csv.jar'),
 'super-csv': os.path.abspath('../benchmark/originalcode/super-csv.jar'),
 'txtmark': os.path.abspath('../benchmark/originalcode/txtmark.jar')
 }

def generate_input_files(testcase_dir, recurrent_sequences, rule_dict, depths_dict,n_inputs):
    n_geninputs = Generator.parse_args(
        "." + fileExtension,
        testcase_dir + f"/samples",
        testcase_dir + f"/trees ",
        20,
        n_inputs,
        rule_dict,
        depths_dict,
        recurrent_sequences,
        k_paths,
        kpath_prefixes
    )
    return n_geninputs
    print("Generated input files.")
 
def gcov_handler(ktest_gcov):
    with open(ktest_gcov, 'r', errors='ignore') as f:
        lines = f.readlines()
    # print(len(lines))
    result_vec = []   
    for l in lines:
        if len(l) < 9:
            return ()
        if l[8] == '-':
            continue
        if l[8] == '#':
            result_vec.append(False)
        else:
            result_vec.append(True)
    return tuple(result_vec)

def jacoco_handler1(csv_name):
    with open(csv_name, "r") as f:
        cov = f.read()
        cov_vec = []
        for k in range(len(cov)):
            if k + 2 > len(cov):
                break
            elif cov[k : k + 2] == "NO":
                cov_vec.append(False)
            elif k + 3 > len(cov):
                break
            elif cov[k : k + 3] == "YES":
                cov_vec.append(True)
            else:
                continue
        return tuple(cov_vec)

def jacoco_handler2(csv_name):
    with open(csv_name, "r") as f:
        lines = f.readlines()
    if len(lines) == 0:
        return []
    cov_vec = []
    for l in lines[1:]:
        tmptoken = l.split(',')
        if len(tmptoken) < 3:
            return ()
        if tmptoken[-3] == '1':
            cov_vec.append(False)
        else:
            cov_vec.append(True)
    return tuple(cov_vec)
   
def get_file_coverage_cprog(input_name, csv_name):
    os.system("find " + test_dir + ' -name "*.gcda" -exec rm {} \;')
    try:
        error_code = subprocess.run([test_pgm, input_name],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=to).returncode
    except subprocess.TimeoutExpired:
            print("time out")
            return ()
    except:
        error_code = -999
    os.system("find " + test_dir + ' -name "*.gcda" -exec gcov -H {} 1>/dev/null \;')
    os.system('find . -name "*.gcov" -exec cat {}>' + csv_name +' \;')
    os.system('find . -name "*.gcov" -exec rm {} 1>/dev/null 2>/dev/null \;')      
    tmp_cov = gcov_handler(csv_name)

    return tmp_cov

def get_file_coverage_javaprog_1(input_name, csv_name):
    if not os.path.isfile(csv_name):
        cmd = ["java", "-jar", f"../benchmark/{subject}-analyser.jar", subject, "file-coverage-l", input_name, csv_name]
        try:
            subprocess.run(cmd, timeout=to, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            print("time out")
            return ()
    os.system(f"ps -ef | grep ../benchmark/{subject}-analyser.jar"+"| awk '{print $2}' | xargs kill -9 1>/dev/null 2>/dev/null")
    if not os.path.exists(csv_name):
        return ()
    tmp_cov = jacoco_handler1(csv_name)

    return tmp_cov

def get_file_coverage_javaprog_2(input_name, csv_name):
    if not os.path.isfile(csv_name):
        cmd = [
            "java", "-jar", f"../benchmark/{subject}-analyser.jar",
            "--ignore-exceptions",
            "--report-coverage", f"{csv_name}-dummy",
            "--line-coverage", csv_name,
            "--original-bytecode", bytecode_dict[subject],
            input_name,
        ]
        try:
            subprocess.run(cmd, timeout=to, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            print("time out")
            return ()
    os.system(f"ps -ef | grep ../benchmark/{subject}-analyser.jar"+"| awk '{print $2}' | xargs kill -9 1>/dev/null 2>/dev/null")
    if not os.path.exists(csv_name):
        return ()
    tmp_cov = jacoco_handler2(csv_name)

    return tmp_cov

def create_csv():
    input_files = os.path.join(testcase_dir, f"samples")
    tree_files = os.path.join(testcase_dir, f"trees")
    csv_files = os.path.join(coverage_dir, "csv")
    if not os.path.isdir(csv_files):
        os.makedirs(csv_files)

    if test_pgm != 'java':
        os.chdir(test_dir) 
    start_cnt = sum(coverage_result.values())
    
    for i in range(start_cnt, 10000):
        print(i)
        print(len(coverage_result))
        input_name = input_files + "/" + str(i).zfill(8) + "." + fileExtension
        csv_name = csv_files + "/" + str(i).zfill(8) + ".csv"
        # dt_name = tree_files + "/" + str(i).zfill(8) + "_tree.pickle"
        if not os.path.exists(input_name):
            break
        tmp_cov = get_1input_cov(input_name, csv_name)
        if tmp_cov not in coverage_result:
            coverage_result[tmp_cov] = 0
        coverage_result[tmp_cov] += 1
        os.system(f"rm {csv_name}")
        if i % 1000 == 999:
            with open(f"{coverage_dir}/coverage_result.pickle", 'wb') as f:
                pickle.dump(coverage_result, f)

    os.chdir(root_dir) 
    return coverage_result

if __name__ == "__main__":
    # print("#################Generate Redundant Sequences######################")
    parser = optparse.OptionParser()
    parser.add_option("--benchmark",dest="benchmark",)
    parser.add_option("--basefuzzer",dest="basefuzzer",)
    parser.add_option("--recurrent_sequence",dest="recurrent_sequence", default=None)
    (options, args) = parser.parse_args()

    subject = options.benchmark
    basefuzzer = options.basefuzzer
    root_dir = os.getcwd()

    if subject in ["Rhino", "Jsish", "QuickJS", "JerryScript"]:
        fileExtension = 'js'
    elif subject in ["Gson", "Genson", "Argo", "JsonToJava"]:
        fileExtension = 'json'
    elif subject in ['jackson-dataformat-csv', 'super-csv']:
        fileExtension = 'csv'
    elif subject in ['commonmark', 'txtmark']:
        fileExtension = 'md'

    if options.recurrent_sequence == None:
        recurrent_sequences = ({},{},{})
        testcase_dir = os.path.abspath(f"result_inputratio/baseline/{basefuzzer}/{subject}")
        coverage_dir = os.path.abspath(f"result_inputratio/baseline/{basefuzzer}/{subject}")
    else:
        with open(options.recurrent_sequence, 'rb') as f:
            recurrent_sequences = pickle.load(f)
        testcase_dir = os.path.abspath(f"result_inputratio/RSFuzz/{basefuzzer}/{subject}")
        coverage_dir = os.path.abspath(f"result_inputratio/RSFuzz/{basefuzzer}/{subject}")
    
    

    if subject == "QuickJS":
        test_pgm = f"{benchmark_dir}/quickjs/qjs"
        test_dir = f"{benchmark_dir}/quickjs"
    elif subject == "JerryScript":
        test_pgm = f"{benchmark_dir}/jerryscript/build/bin/jerry"
        test_dir = f"{benchmark_dir}/jerryscript/build"
    elif subject == "Jsish":
        test_pgm = f"{benchmark_dir}/jsish/jsish"
        test_dir = f"{benchmark_dir}/jsish"
    else:
        test_pgm = "java"

    if fileExtension == 'json' or subject == 'Rhino':
        get_1input_cov = get_file_coverage_javaprog_1
        covhandler = jacoco_handler1
    elif fileExtension == 'js':
        get_1input_cov = get_file_coverage_cprog
        covhandler = gcov_handler
    else:
        get_1input_cov = get_file_coverage_javaprog_2
        covhandler = jacoco_handler2
    # Parameters

    if basefuzzer == 'tribble':
        import tribbleGenerator as Generator
        with open(f"../bnf/{fileExtension}/{fileExtension}_kpathsinfo.pkl", 'rb') as f:
            k_paths, kpath_prefixes = pickle.load(f)
        
    else:
        import rsfuzzGenerator as Generator
        k_paths = None
        kpath_prefixes = None
    
    inv_benchmarks = ['Rhino', 'Argo', 'Genson', 'Gson' ]

    if basefuzzer == 'pcfg':
        if subject in inv_benchmarks:
            bnf_file_name_1 = f"../bnf/{fileExtension}/{fileExtension}_inv.bnf"
        else:
            bnf_file_name_1 = f"../bnf/{fileExtension}/{fileExtension}_prob.bnf"
    else:
        bnf_file_name = f"../bnf/{fileExtension}/{fileExtension}_random.bnf"

    (rule_dict, depths_dict) = Generator.parse_bnf(bnf_file_name, "." + fileExtension)


    total_ninputs = generate_input_files(testcase_dir, recurrent_sequences, rule_dict, depths_dict, 100000)

    coverage_result = {}
    create_csv()

    with open(f"{coverage_dir}/coverage_result.pickle", 'wb') as f:
        pickle.dump(coverage_result, f)
    


