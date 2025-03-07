#!/usr/bin/env python
import os
import subprocess
import argparse
import Generator
import pickle
import time
import numpy as np

###############################
### Generate & Test Inputs. ###
###############################

def update_total_cov(total_cov, new_cov):
    for i, covered in enumerate(new_cov):
        if covered == "1":
            total_cov[i] = '1'
    return total_cov

def generate_input_files(current_generation, redundant_sequence, rule_dict, depths_dict):
    current_generation_directory = "run-" + str(current_generation).zfill(5)
    current_generation_path = os.path.join(baseDirectory, current_generation_directory)
    os.mkdir(current_generation_path, 0o755)

    Generator.parse_args(
        "." + fileExtension,
        current_generation_path + "/samples",
        20,
        number_individuals,
        rule_dict,
        depths_dict,
        redundant_sequence
    )

def branch_handler(ktest_gcov):
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

def csv_handler(csv_name):
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

def test_input_files(input_set_list, subject, info_num, start_time):
    if is_java:
        cov_vec = []
        for current_generation in input_set_list:
            input_files_directory = (
                "run-" + str(current_generation).zfill(5) + "/samples"
            )
            input_files = os.path.join(baseDirectory, input_files_directory)

            result_csv = os.path.join(
                baseDirectory, "run-" + str(current_generation).zfill(5), "results.csv"
            )
            subprocess.call(
                f"java -jar {options.test_dir} {subject} file-coverage-all {input_files} {result_csv} 1>/dev/null 2>/dev/null",
                shell=True,
            )
            with open(result_csv, "r") as f:
                cov_txt = f.readlines()

            exception_list = []
            for i in range(1, number_individuals + 1):
                exception_list.append(cov_txt[i].split(",")[-1][:-1])
            if exception_list[0] == "1":
                os.system(f"cp {input_files}/{str(0).zfill(8)}.{fileExtension} {list_dir}/error/test{info_num}_{current_generation}_{str(0)}.{fileExtension}")
                os.system(f"cp {input_files}/{str(0).zfill(8)}_tree.pickle {list_dir}/error/test{info_num}_{current_generation}_{str(0)}_tree.pickle")
            for i in range(number_individuals - 1):
                if exception_list[i] != exception_list[i + 1]:
                    input_name = (
                        input_files + "/" + str(i + 1).zfill(8) + "." + fileExtension
                    )
                    tree_name = input_files + "/" + str(i + 1).zfill(8) + "_tree.pickle"
                    os.system(f"cp {input_name} {list_dir}/error/test{info_num}_{current_generation}_{i}.{fileExtension}")
                    os.system(f"cp {tree_name} {list_dir}/error/test{info_num}_{current_generation}_{i}_tree.pickle")


            result_csv = os.path.join(
                baseDirectory, "run-" + str(current_generation).zfill(5), "results.csv"
            )
            subprocess.call(
                f"java -jar {options.test_dir} {str(subject)} file-coverage-l {input_files} {result_csv} 1>/dev/null 2>/dev/null",
                shell=True,
            )

            tmp_cov_vec = csv_handler(result_csv)

            if cov_vec == []:
                for k in tmp_cov_vec:
                    cov_vec.append(k)
            else:
                for k in range(len(tmp_cov_vec)):
                    if tmp_cov_vec[k]:
                        cov_vec[k] = True

        os.system(f"ps -ef | grep 'java -jar' | grep {test_dir}"+"| awk '{print $2}' | xargs kill -9 1>/dev/null 2>/dev/null")
        result_info_file = os.path.join(
            list_dir, "coverage", str(info_num).zfill(5) + "_cov.pickle"
        )
        with open(result_info_file, "wb") as f:
            pickle.dump(cov_vec, f)

        with open(os.path.join(list_dir, "time.txt"), "a") as f:
            f.write(
                str(info_num).zfill(5)
                + "_cov.pickle end time : "
                + str(time.time() - start_time)
                + "\n"
            )
        return np.array(cov_vec)

    os.system("find " + test_dir + ' -name "*.gcda" -exec rm {} \;')
    for current_generation in input_set_list:
        input_files_directory = "run-" + str(current_generation).zfill(5) + "/samples"
        input_files = os.path.join(baseDirectory, input_files_directory)

        to = 5

        for i in range(number_individuals):
            input_name = input_files + "/" + str(i).zfill(8) + "." + fileExtension
            tree_name = input_files + "/" + str(i).zfill(8) + "_tree.pickle"
            try:
                error_code = subprocess.run([test_pgm, input_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=to).returncode
            except:
                error_code = 999
            if error_code < 0:
                os.system(f"cp {input_name} {list_dir}/error/test_{info_num}_{current_generation}_{i}.{fileExtension}")
                os.system(f"cp {tree_name} {list_dir}/error/test_{info_num}_{current_generation}_{i}_tree.pickle")

    result_info_file = os.path.join(list_dir, "coverage", str(info_num).zfill(5) + "_cov.info")
    result_cov_file = os.path.join(list_dir, "coverage", str(info_num).zfill(5) + "_cov.pickle")
    # os.system("lcov -c --directory " + test_dir + " --output-file " + result_info_file + " 1>/dev/null 2>/dev/null")
    root_dir = os.getcwd()
    result_info_file = os.path.abspath(result_info_file)
    result_cov_file = os.path.abspath(result_cov_file)
    os.chdir(test_dir)
    os.system("find " + test_dir + ' -name "*.gcda" -exec gcov -H {} 1>/dev/null \;')
    os.system('find . -name "*.gcov" -exec cat {}>' + result_info_file +' \;')
    os.system('find . -name "*.gcov" -exec rm {} 1>/dev/null 2>/dev/null \;')
    os.chdir(root_dir)
    
    cov_vec = branch_handler(result_info_file)
    os.system(f"rm {result_info_file}")
    with open(result_cov_file, "wb") as f:
        pickle.dump(cov_vec, f)

    with open(os.path.join(list_dir, "time.txt"), "a") as f:
        f.write(
            str(info_num).zfill(5)
            + "_cov.info end time : "
            + str(time.time() - start_time)
            + "\n"
        )
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

def merge_covs(cov1, cov2):
    result = cov1
    for i in range(len(cov2)):
        if cov2[i] == '1':
            result[i] = '1'
    return result       

######################
### Main Functions ###
######################


def run(rule_dict, depths_dict, subject, redundant_sequence):
    start_time = time.time()
    with open(list_dir + "/total_coverage.pickle", "rb") as f:
        total_cov = pickle.load(f)    
    possible_children_devnums = {}
    for token in rule_dict:
        possible_children_devnums[token] = set()
        for child in rule_dict[token]:
            if child[2] > 0:
                possible_children_devnums[token].add(child[1])
    
    os.system(f'rm -rf "{baseDirectory}"')
    os.system(f'mkdir "{baseDirectory}"')
    for current_generation in range(10):
        generate_input_files(current_generation, redundant_sequence, rule_dict, depths_dict)

    total_cov |= test_input_files(range(10), subject, 0, start_time)
    with open(os.path.join(list_dir, "time.txt"), "a") as f:
        f.write(
            str(0).zfill(5)
            + "_cov.info end time : "
            + str(time.time() - start_time)
            + "\n"
        )
    logs = f"Testing started\n{time.time()-start_time}\tIter-0\t{total_cov.sum()}\n"
    with open(list_dir + "/logs.txt", "a") as f:
        f.write(logs)
        
    info_num = 1

    while True:

        os.system(f'rm -rf "{baseDirectory}"')
        os.system(f'mkdir "{baseDirectory}"')
        
        for current_generation in range(10):
            generate_input_files(current_generation, redundant_sequence, rule_dict, depths_dict)
            
        new_cov_vec = test_input_files(range(10), subject, info_num, start_time)
        total_cov |= new_cov_vec

        logs = f"{time.time()-start_time}\tIter-{info_num}\t{total_cov.sum()}\n"
        with open(list_dir + "/logs.txt", "a") as f:
            f.write(logs)
        with open(list_dir + "/total_coverage_testing.pickle", "wb") as f:
            pickle.dump(total_cov, f)
        info_num += 1


if __name__ == "__main__":
    print("#################Run Cutfuzz offline######################")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark",
        dest="benchmark",
    )
    parser.add_argument(
        "--fileExtension",
        dest="fileExtension",
    )
    parser.add_argument(
        "--base_fuzzer",
        dest="base_fuzzer"
    )
    parser.add_argument(
        "--list_dir",
        dest="list_dir",
    )
    parser.add_argument(
        "--result_dir",
        dest="result_dir",
    )
    parser.add_argument(
        "--n_num",
        dest="n_num",
        type=int,
    )
    parser.add_argument(
        "--test_dir",
        dest="test_dir",
    )
    parser.add_argument(
        "--test_pgm",
        dest="test_pgm",
    )
    parser.add_argument(
        "--redundant_sequence", dest="redundant_sequence", help="redundant sequences for testing"
    )
    
    options = parser.parse_args()

    subject = options.benchmark
    list_dir = os.path.abspath(options.list_dir)
    fileExtension = options.fileExtension
    baseDirectory = options.result_dir
    
    if options.redundant_sequence:
        with open(options.redundant_sequence, 'rb') as f:
            redundant_sequence = pickle.load(f)
    else:
        redundant_sequence = ({}, {}, {})
    
    # print(redundant_sequence)

    if options.test_pgm == "java":
        is_java = True
        test_dir = options.test_dir
        test_pgm = None
    else:
        is_java = False
        test_dir = options.test_dir
        test_pgm = options.test_pgm

    # Parameters
    number_individuals = options.n_num // 10
    best_generation_k = 10

    cov_idx_dict = {}
    dt_idx_dict = {}
    coverage_list = []
    
    inv_benchmarks = ['Rhino', 'Argo', 'Genson', 'Gson']

    if options.base_fuzzer == "prob":
        if subject in inv_benchmarks:
            bnf_file_name_1 = os.path.abspath(f"bnf/{fileExtension}_inv.bnf")
        else:
            bnf_file_name_1 = os.path.abspath(f"bnf/{fileExtension}_prob.bnf")
    else:
        bnf_file_name_1 = os.path.abspath(f"bnf/{fileExtension}_random.bnf")

    # remove_empty_lines(bnf_file_name_1)
    (rule_dict, depths_dict) = Generator.parse_bnf(bnf_file_name_1, "." + fileExtension, os.path.abspath("bnf/"))
    cluster_data_dir = os.path.abspath(f"{list_dir}/captured_clusters")

    run(rule_dict, depths_dict, subject, redundant_sequence)