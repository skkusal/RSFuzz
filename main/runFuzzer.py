#!/usr/bin/env python
import os
import subprocess
import optparse
import pickle
import time
import numpy as np
import json

exceptions_to_skip = set(['InvalidSyntaxException'])
bytecode_dict = {
 'commonmark': os.path.abspath('../benchmark/originalcode/commonmark.jar'),
 'jackson-dataformat-csv': os.path.abspath('../benchmark/originalcode/jackson-dataformat-csv.jar'),
 'super-csv': os.path.abspath('../benchmark/originalcode/super-csv.jar'),
 'txtmark': os.path.abspath('../benchmark/originalcode/txtmark.jar')
 }
###############################
### Generate & Test Inputs. ###
###############################
def generate_input_files(testcase_dir, recurrent_sequences, rule_dict, depths_dict):
    n_geninputs = Generator.parse_args(
        "." + fileExtension,
        testcase_dir + "/samples",
        testcase_dir + "/trees",
        20,
        number_individuals,
        rule_dict,
        depths_dict,
        recurrent_sequences,
        k_paths,
        kpath_prefixes
    )
    return n_geninputs

def gcov_handler(ktest_gcov):
    with open(ktest_gcov, 'r', errors='ignore') as f:
        lines = f.readlines()
    result_vec = []   
    for l in lines:
        if l[8] == '-':
            continue
        if l[8] == '#':
            result_vec.append(False)
        else:
            result_vec.append(True)
    return np.array(result_vec)

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
            
        return np.array(cov_vec)

def jacoco_handler2(csv_name):
    with open(csv_name, "r") as f:
        lines = f.readlines()
    if len(lines) == 0:
        return []
    cov_vec = []
    for l in lines[1:]:
        if l.split(',')[-3] == '1':
            cov_vec.append(False)
        else:
            cov_vec.append(True)
    return np.array(cov_vec)

def get_dir_coverage_javaprog_1(input_dir, tree_dir, csv_name, err_name, info_num):
    subprocess.call(
        f"java -jar ../benchmark/{subject}-analyser.jar {subject} file-coverage-all {input_dir} {csv_name} 1>/dev/null 2>/dev/null",
        shell=True,
    )
    with open(csv_name, "r") as f:
        cov_txt = f.readlines()
    exception_list = []
    for tmpl in cov_txt[1:]:
        exception_list.append(tmpl.split(",")[-1][:-1])
    if exception_list[0] == "1":
        os.system(f"cp {input_dir}/{str(0).zfill(8)}.{fileExtension} {capture_dir}/error/{info_num}_{str(0)}.{fileExtension}")
        os.system(f"cp {tree_dir}/{str(0).zfill(8)}_tree.pickle {capture_dir}/error/{info_num}_{str(0)}_tree.pickle")
    for i in range(len(exception_list) - 1):
        if exception_list[i] != exception_list[i + 1]:
            input_name = input_dir + "/" + str(i + 1).zfill(8) + "." + fileExtension
            dt_name = tree_dir + "/" + str(i + 1).zfill(8) + "_tree.pickle"
            os.system(f"cp {input_name} {capture_dir}/error/{info_num}_{i}.{fileExtension}")
            os.system(f"cp {dt_name} {capture_dir}/error/{info_num}_{i}_tree.pickle")
    subprocess.call(
        f"java -jar ../benchmark/{subject}-analyser.jar {str(subject)} file-coverage-l {input_dir} {csv_name} 1>/dev/null 2>/dev/null",
        shell=True,
    )

    return jacoco_handler1(csv_name)

def get_dir_coverage_javaprog_2(input_dir, tree_dir, csv_name, err_name, info_num):
    subprocess.call(
        f"java -jar ../benchmark/{subject}-analyser.jar --ignore-exceptions --log-exceptions {err_name} --report-coverage {csv_name}-dummy --line-coverage {csv_name} --original-bytecode {bytecode_dict[subject]} {input_dir}",
        shell=True,
    )
    if os.path.exists(err_name):
        with open(err_name, 'r') as f:
            exceptions = json.load(f)
        for e in exceptions:
            if e['name'].split('.')[-1] in exceptions_to_skip:
                continue
            e_key = (e['name'], e['location'])
            if e_key not in exceptions_cnt:
                exceptions_cnt[e_key] = 0
            n_to_copy = min(len(e['files']),100)
            for tc in e['files'][:n_to_copy]:
                if exceptions_cnt[e_key] > 200000:
                    break
                tc_idx = int(tc.split('.')[0])
                input_name = input_dir + "/" + str(tc_idx).zfill(8) + "." + fileExtension
                dt_name = tree_dir + "/" + str(tc_idx).zfill(8) + "_tree.pickle"            
                os.system(f"cp {input_name} {capture_dir}/error/{info_num}_{tc_idx}.{fileExtension}")
                os.system(f"cp {dt_name} {capture_dir}/error/{info_num}_{tc_idx}_tree.pickle")
                exceptions_cnt[e_key] += 1


    return jacoco_handler2(csv_name)

def get_dir_coverage_cprog(input_dir, tree_dir, csv_name, err_name, info_num):
    os.system("find " + test_dir + ' -name "*.gcda" -exec rm {} \;')
    for i in range(len(os.listdir(input_dir))):
        input_name = input_dir + "/" + str(i).zfill(8) + "." + fileExtension
        dt_name = tree_dir + "/" + str(i).zfill(8) + "_tree.pickle"
        try:
            error_code = subprocess.run([test_pgm, input_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=to).returncode
        except:
            error_code = 999
        if error_code < 0:
            os.system(f"cp {input_name} {capture_dir}/error/{info_num}_{i}.{fileExtension}")
            os.system(f"cp {dt_name} {capture_dir}/error/{info_num}_{i}_tree.pickle")
    os.system("find " + test_dir + ' -name "*.gcda" -exec gcov -H {} 1>/dev/null \;')
    os.system('find . -name "*.gcov" -exec cat {}>' + csv_name +' \;')
    os.system('find . -name "*.gcov" -exec rm {} 1>/dev/null 2>/dev/null \;')

    return gcov_handler(csv_name)

def test_input_files(info_num):
    if not is_java:
        os.chdir(test_dir)

    cov_vec = []
    input_files = os.path.join(testcase_dir, "samples")
    tree_files = os.path.join(testcase_dir, "trees")
    result_csv = os.path.join(testcase_dir, "results.csv")
    err_name = os.path.join(testcase_dir, "errs.json")

    tmp_cov_vec = get_dir_cov(input_files, tree_files, result_csv, err_name, info_num)

    if cov_vec == []:
        cov_vec = tmp_cov_vec
    else:
        cov_vec |= tmp_cov_vec

    result_info_file = os.path.join(capture_dir, "coverage", str(info_num).zfill(5) + "_cov.pickle")
    with open(result_info_file, "wb") as f:
        pickle.dump(cov_vec, f)
    
    os.chdir(root_dir)
    return cov_vec

######################
### Util Functions ###
######################

def remove_empty_lines(filename):
    if not os.path.isfile(filename):
        print("{} does not exist ".format(filename))
        return
    with open(filename) as file:
        lines = file.readlines()

    with open(filename, "w") as file:
        lines = filter(lambda x: x.strip(), lines)
        file.writelines(lines)

######################
### Main Functions ###
######################

def run(rule_dict, depths_dict, subject):
    start_time = time.time()
    if os.path.exists(capture_dir + "/total_coverage.pickle"):
        with open(capture_dir + "/total_coverage.pickle", "rb") as f:
            total_cov = pickle.load(f)
    else:
        total_cov = []
    info_num = 0
    total_ninputs = 0
    os.system(f'rm -rf "{testcase_dir}"')
    os.system(f'mkdir "{testcase_dir}"')
    total_ninputs += generate_input_files(testcase_dir, recurrent_sequences, rule_dict, depths_dict)        
    tmp_cov = test_input_files(0)
    if len(total_cov) == 0:
        total_cov = tmp_cov
    else:
        total_cov |= tmp_cov

    if recurrent_sequences == ({},{},{}):
        logs = "# Run Baseline\n"
    else:
        logs = "# Run Base Fuzzer with Redundant Sequences\n"
    logs += f"{time.time()-start_time}\tIter-{info_num}\t{total_cov.sum()}\t{total_ninputs}\n"
    with open(capture_dir + "/logs.txt", "a") as f:
        f.write(logs)
        
    info_num += 1

    while True:

        os.system(f'rm -rf "{testcase_dir}"')
        os.system(f'mkdir "{testcase_dir}"')

        total_ninputs += generate_input_files(testcase_dir, recurrent_sequences, rule_dict, depths_dict)
        tmp_total_cov = test_input_files(info_num)
        if len(tmp_total_cov) != 0:
            total_cov |= tmp_total_cov

        logs = f"{time.time()-start_time}\tIter-{info_num}\t{total_cov.sum()}\t{total_ninputs}\n"
        with open(capture_dir + "/logs.txt", "a") as f:
            f.write(logs)
        with open(capture_dir + "/total_coverage_testing.pickle", "wb") as f:
            pickle.dump(total_cov, f)
        info_num += 1


if __name__ == "__main__":
    print("#################Run BaseFuzzer######################")
    parser = optparse.OptionParser()
    parser.add_option("--benchmark",dest="benchmark",)
    parser.add_option("--fileExtension",dest="fileExtension",)
    parser.add_option("--basefuzzer",dest="basefuzzer",)
    parser.add_option("--capture_dir",dest="capture_dir",)
    parser.add_option("--testcase_dir",dest="testcase_dir",)
    parser.add_option("--n_num",dest="n_num",type="int",)
    parser.add_option("--test_dir",dest="test_dir",)
    parser.add_option("--test_pgm",dest="test_pgm",)
    parser.add_option("--recurrent_sequences", dest="recurrent_sequences", help="Pruning list for test", default="")
    (options, args) = parser.parse_args()

    subject = options.benchmark
    capture_dir = os.path.abspath(options.capture_dir)
    fileExtension = options.fileExtension
    testcase_dir = os.path.abspath(options.testcase_dir)
    if options.recurrent_sequences != "":
        with open(options.recurrent_sequences, 'rb') as f:
            recurrent_sequences = pickle.load(f)
    else:
        recurrent_sequences = ({},{},{})
    
    # print(recurrent_sequences)

    if options.test_pgm == "java":
        is_java = True
        test_dir = None
        test_pgm = None
    else:
        is_java = False
        test_dir = options.test_dir
        test_pgm = options.test_pgm

    # Parameters
    number_individuals = options.n_num
    to = 1
    cov_idx_dict = {}
    dt_idx_dict = {}
    coverage_list = []
    root_dir = os.getcwd()
    
    inv_benchmarks = ['Rhino', 'Argo', 'Genson', 'Gson']
    base_fuzzer = options.basefuzzer
    if base_fuzzer == 'pcfg':
        if subject in inv_benchmarks:
            bnf_file_name_1 = f"../bnf/{fileExtension}/{fileExtension}_inv.bnf"
        else:
            bnf_file_name_1 = f"../bnf/{fileExtension}/{fileExtension}_prob.bnf"
    else:
        bnf_file_name_1 = f"../bnf/{fileExtension}/{fileExtension}_random.bnf"

    if base_fuzzer == 'tribble':
        import tribbleGenerator as Generator
        with open(f"../bnf/{fileExtension}/{fileExtension}_kpathsinfo.pkl", 'rb') as f:
            k_paths, kpath_prefixes = pickle.load(f)
    else:
        import rsfuzzGenerator as Generator
        k_paths = None
        kpath_prefixes = None

    (rule_dict, depths_dict) = Generator.parse_bnf(bnf_file_name_1, "." + fileExtension)
    
    if fileExtension == 'json' or subject == 'Rhino':
        get_dir_cov = get_dir_coverage_javaprog_1
    elif fileExtension == 'js':
        get_dir_cov = get_dir_coverage_cprog
    else:
        get_dir_cov = get_dir_coverage_javaprog_2

    exceptions_cnt = {}
    
    run(rule_dict, depths_dict, number_individuals)
