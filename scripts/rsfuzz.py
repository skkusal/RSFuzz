#!/usr/bin/env python
import os
import subprocess
import argparse
import Generator
import pickle
import time
import numpy as np
import hashlib
import copy
from sklearn.cluster import MeanShift, estimate_bandwidth

###############################
### Generate & Test Inputs. ###
###############################
def generate_input_files(current_generation, redundant_sequence, rule_dict, depths_dict,n_inputs):
    current_generation_directory = "run-" + str(current_generation).zfill(5)
    current_generation_path = os.path.join(baseDirectory, current_generation_directory)
    os.mkdir(current_generation_path, 0o755)

    Generator.parse_args(
        "." + fileExtension,
        current_generation_path + "/samples",
        20,
        n_inputs,
        rule_dict,
        depths_dict,
        redundant_sequence
    )
    # print("Generated input files.")
    
def compute_tree_hash(dt_name, hash_algo='sha256'):
    hash_func = hashlib.new(hash_algo)
    with open(dt_name, 'rb') as file:
        chunk = file.read()
    hash_func.update(chunk)
    return hash_func.hexdigest()

def compute_coverage_hash(cov):
    return hash(tuple(cov))

def branch_handler(ktest_gcov):
    with open(ktest_gcov, 'r', errors='ignore') as f:
        lines = f.readlines()
    # print(len(lines))
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
    
def dt_to_sequences(dt_name):
    with open(dt_name, 'rb') as f:
        dt = pickle.load(f)
    sequences = set()
    queue = [[0, 0, []]]
    while queue:
        cur_i, cur_j, cur_seq = queue.pop()
        cur_symbol, cur_children, cur_dn, cur_pi = dt[cur_i][cur_j]
        
        if cur_dn == -2:
            continue
        if cur_dn == -1 : #or cur_symbol in symbol_with_terminal_children_only:
            tmp_idx = len(cur_seq)

            while cur_seq[tmp_idx-1] in one_child_symbols:
                tmp_idx -= 1
                cur_pi = dt[cur_pi[0]][cur_pi[1]][3]

            
            parent_dn = dt[cur_pi[0]][cur_pi[1]][2]
            sequences.add(tuple(cur_seq[:tmp_idx]+[parent_dn]))
        else:
            for cidx in cur_children:
                queue.append([cur_i + 1, cidx, cur_seq+[cur_symbol]])

    refined_seqs = set()
    
    for seq in sequences:
        stride = 1
        refined_seq = list(seq)
        while stride < len(refined_seq)/2:
            tmp_refined_seq = refined_seq[:stride]
            tmp_idx = stride
            while tmp_idx < len(refined_seq):
                if  tmp_refined_seq[-stride:] == refined_seq[tmp_idx:tmp_idx+stride]:
                    tmp_idx += stride
                else:
                    tmp_refined_seq.append(refined_seq[tmp_idx])
                    tmp_idx += 1
            refined_seq = tmp_refined_seq
            stride += 1
        refined_seqs.add(tuple(refined_seq))
    
    return tuple(sorted(refined_seqs, key=lambda x:len(x)))

def create_csv(best_generation, subject, total_clusters, unique_dt, unique_seqs, n_iter, n_lines, info_num):
    input_files_directory = "run-" + str(best_generation).zfill(5) + "/samples"
    csv_files_directory = "run-" + str(best_generation).zfill(5) + "/csv"

    input_files = os.path.join(baseDirectory, input_files_directory)
    csv_files = os.path.join(baseDirectory, csv_files_directory)
    if not os.path.isdir(csv_files):
        os.mkdir(csv_files, 0o755)

    error_code_file = os.path.join(baseDirectory, "run-" + str(best_generation).zfill(5), "error_code.txt")
    error_code_file = os.path.abspath(error_code_file)
    
    updated_covs = set()
        
    if is_java:
        for i in range(n_iter):
            input_name = input_files + "/" + str(i).zfill(8) + "." + fileExtension
            tree_name = input_files + "/" + str(i).zfill(8) + "_tree.pickle"
            if not os.path.exists(input_name):
                break
            csv_name = csv_files + "/" + str(i).zfill(8) + ".csv"
            dt_name = input_files + "/" + str(i).zfill(8) + "_tree.pickle"
            tmp_dt_hash = compute_tree_hash(dt_name)
            
            if tmp_dt_hash in dt_idx_dict:
                dt_key = dt_idx_dict[tmp_dt_hash]
                seqs_key = unique_seqs[dt_key]
                cov_key = unique_dt[seqs_key]

            else:                        
                dt_key = len(dt_idx_dict)
                os.system(f"cp {dt_name} {list_dir}/unique_trees/{dt_key}.pickle")
                dt_idx_dict[tmp_dt_hash] = dt_key
                  
                tmp_seqs = dt_to_sequences(dt_name)
                tmp_seqs_hash = hash(tmp_seqs)

                if tmp_seqs_hash not in seqs_idx_dict:
                    with open(f"{list_dir}/unique_trees/{len(seqs_idx_dict)}_seqs.pickle", 'wb') as f:
                        pickle.dump(tmp_seqs, f)
                    seqs_idx_dict[tmp_seqs_hash] = len(seqs_idx_dict)
                seqs_key = seqs_idx_dict[tmp_seqs_hash]
                unique_seqs[dt_key] = seqs_key
                
                if seqs_key not in unique_dt:
                    if not os.path.isfile(csv_name):
                        subprocess.call(
                            f"java -jar {test_dir} {str(subject)} file-coverage-l {input_name} {csv_name} 1>/dev/null 2>/dev/null",
                            shell=True,
                        )
                    tmp_cov = csv_handler(csv_name)
                    tmp_cov_hash = compute_coverage_hash(tmp_cov)
                    if len(tmp_cov) == 0:
                        os.system(f"cp {input_name} {list_dir}/error/{info_num}_{best_generation}_{i}.{fileExtension}")
                        os.system(f"cp {tree_name} {list_dir}/error/{info_num}_{best_generation}_{i}_tree.pickle")
                        tmp_cov = np.full(n_lines, False)
                    
                    if tmp_cov_hash not in cov_idx_dict:
                        total_clusters[len(cov_idx_dict)] = {}
                        with open(f"{list_dir}/unique_covs/{len(cov_idx_dict)}.pickle", 'wb') as f:
                            pickle.dump(tmp_cov, f)
                        cov_idx_dict[tmp_cov_hash] = len(cov_idx_dict)
                        coverage_list.append(tmp_cov)
                    
                    cov_key = cov_idx_dict[tmp_cov_hash]
                    unique_dt[seqs_key] = cov_key
                    total_clusters[cov_key][seqs_key] = 0
                else:
                    cov_key = unique_dt[seqs_key]

            total_clusters[cov_key][seqs_key] += 1
            updated_covs.add(cov_key)

        return updated_covs
    
    root_dir = os.getcwd()
    input_files = os.path.abspath(input_files)
    csv_files = os.path.abspath(csv_files)
    os.chdir(test_dir)
    
    for i in range(n_iter):
        os.system("find " + test_dir + ' -name "*.gcda" -exec rm {} \;')
        input_name = input_files + "/" + str(i).zfill(8) + "." + fileExtension
        tree_name = input_files + "/" + str(i).zfill(8) + "_tree.pickle"
        if not os.path.exists(input_name):
            break
        info_name = csv_files + "/" + str(i).zfill(8) + ".info"
        dt_name = input_files + "/" + str(i).zfill(8) + "_tree.pickle"
        
        tmp_dt_hash = compute_tree_hash(dt_name)
        if tmp_dt_hash in dt_idx_dict:
            dt_key = dt_idx_dict[tmp_dt_hash]
            seqs_key = unique_seqs[dt_key]
            cov_key = unique_dt[seqs_key]
        else:
            dt_key = len(dt_idx_dict)
            os.system(f"cp {dt_name} {list_dir}/unique_trees/{dt_key}.pickle")
            dt_idx_dict[tmp_dt_hash] = dt_key
                
            tmp_seqs = dt_to_sequences(dt_name)
            tmp_seqs_hash = hash(tmp_seqs)

            if tmp_seqs_hash not in seqs_idx_dict:
                with open(f"{list_dir}/unique_trees/{len(seqs_idx_dict)}_seqs.pickle", 'wb') as f:
                    pickle.dump(tmp_seqs, f)
                seqs_idx_dict[tmp_seqs_hash] = len(seqs_idx_dict)
            seqs_key = seqs_idx_dict[tmp_seqs_hash]
            unique_seqs[dt_key] = seqs_key
            
            if seqs_key not in unique_dt:
                try:
                    error_code = subprocess.run(
                        [test_pgm, input_name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1,
                    ).returncode
                except:
                    error_code = -999
                with open(error_code_file, "a") as f:
                    f.write(str(i).zfill(8) + " : " + str(error_code) + "\n")
                # os.system("lcov -c --directory " + test_dir + " --output-file " + info_name + " 1>/dev/null 2>/dev/null")
                os.system("find " + test_dir + ' -name "*.gcda" -exec gcov -H {} 1>/dev/null \;')
                os.system('find . -name "*.gcov" -exec cat {}>' + info_name +' \;')
                os.system('find . -name "*.gcov" -exec rm {} 1>/dev/null 2>/dev/null \;')

                    
                tmp_cov = branch_handler(info_name)
                
                
                if len(tmp_cov) == 0:
                    os.system(f"cp {input_name} {list_dir}/error/{info_num}_{best_generation}_{i}.{fileExtension}")
                    os.system(f"cp {tree_name} {list_dir}/error/{info_num}_{best_generation}_{i}_tree.pickle")
                    tmp_cov = np.full(n_lines, False)
                
                tmp_cov_hash = compute_coverage_hash(tmp_cov)
                 
                if tmp_cov_hash not in cov_idx_dict:
                    total_clusters[len(cov_idx_dict)] = {}
                    with open(f"{list_dir}/unique_covs/{len(cov_idx_dict)}.pickle", 'wb') as f:
                        pickle.dump(tmp_cov, f)
                    cov_idx_dict[tmp_cov_hash] = len(cov_idx_dict)
                    coverage_list.append(tmp_cov)
                
                cov_key = cov_idx_dict[tmp_cov_hash]
                unique_dt[seqs_key] = cov_key
                total_clusters[cov_key][seqs_key] = 0
            else:                   
                cov_key = unique_dt[seqs_key]
                
        total_clusters[cov_key][seqs_key] += 1
        updated_covs.add(cov_key)
        
    os.chdir(root_dir)
    
    return updated_covs

def test_input_files(input_set_list, subject, info_num, start_time, n_iter):
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
                f"java -jar {test_dir} {subject} file-coverage-all {input_files} {result_csv} 1>/dev/null 2>/dev/null",
                shell=True,
            )
            with open(result_csv, "r") as f:
                cov_txt = f.readlines()

            exception_list = []
            for i in range(1, n_iter + 1):
                exception_list.append(cov_txt[i].split(",")[-1][:-1])
            if exception_list[0] == "1":
                os.system(f"cp {input_files}/{str(0).zfill(8)}.{fileExtension} {list_dir}/error/{info_num}_{current_generation}_{str(0)}.{fileExtension}")
                os.system(f"cp {input_files}/{str(0).zfill(8)}_tree.pickle {list_dir}/error/{info_num}_{current_generation}_{str(0)}_tree.pickle")

            for i in range(n_iter - 1):
                if exception_list[i] != exception_list[i + 1]:
                    input_name = input_files + "/" + str(i + 1).zfill(8) + "." + fileExtension
                    tree_name = input_files + "/" + str(i + 1).zfill(8) + "_tree.pickle"
                    os.system(f"cp {input_name} {list_dir}/error/{info_num}_{current_generation}_{i}.{fileExtension}")
                    os.system(f"cp {tree_name} {list_dir}/error/{info_num}_{current_generation}_{i}_tree.pickle")

            result_csv = os.path.join(
                baseDirectory, "run-" + str(current_generation).zfill(5), "results.csv"
            )
            subprocess.call(
                f"java -jar {test_dir} {str(subject)} file-coverage-l {input_files} {result_csv} 1>/dev/null 2>/dev/null",
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
            list_dir, "coverage", str(info_num).zfill(5) + "test_cov.pickle"
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

        to = 1

        for i in range(n_iter):
            input_name = input_files + "/" + str(i).zfill(8) + "." + fileExtension
            tree_name = input_files + "/" + str(i).zfill(8) + "_tree.pickle"
            try:
                error_code = subprocess.run([test_pgm, input_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1).returncode
            except:
                error_code = 999
            if error_code < 0:
                os.system(f"cp {input_name} {list_dir}/error/{info_num}_{current_generation}_{i}.{fileExtension}")
                os.system(f"cp {tree_name} {list_dir}/error/{info_num}_{current_generation}_{i}_tree.pickle")

    result_info_file = os.path.join(list_dir, "coverage", str(info_num).zfill(5) + "_cov.info")
    result_cov_file = os.path.join(list_dir, "coverage", str(info_num).zfill(5) + "test_cov.pickle")
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


####################################
### Generate Redundant Sequences ###
####################################
def compare_subpaths(long_sp, short_sp):
    if long_sp == short_sp:
        return True
    if long_sp[-2:] != short_sp[-2:]:
        return False
    idx = 0
    result = True
    for symbol in short_sp[:-2]:
        if symbol in long_sp[idx:-2]:
            idx = long_sp.index(symbol)
        else:
            return False
    return True

def simplify_subpaths(subpaths):
    refined_seqs = set()
    
    for seq in subpaths:
        refined_seq = list(seq)
        
        stride = 1
        while stride < len(refined_seq)/2:
            tmp_refined_seq = refined_seq[:stride]
            tmp_idx = stride
            while tmp_idx < len(refined_seq):
                if  tmp_refined_seq[-stride:] == refined_seq[tmp_idx:tmp_idx+stride]:
                    tmp_idx += stride
                else:
                    tmp_refined_seq.append(refined_seq[tmp_idx])
                    tmp_idx += 1
            refined_seq = tmp_refined_seq
            stride += 1

        refined_seqs.add(tuple(refined_seq))

    refined_seqs = sorted(refined_seqs, key=lambda x:len(x))
    remaining_seqs = list(refined_seqs)

    return tuple(sorted(remaining_seqs, key=lambda x:len(x)))
 
def capture_rule_from_cluster(seqs_list, parameter_dict, covkey, update_param):
    captured_sequences = {}
    labels = [0]

    refined_seqs_list = set()
    for seqs, _ in seqs_list:
        refined_seqs_list.add(simplify_subpaths(seqs))

    total_cnt = len(refined_seqs_list)
    
    for seqs in refined_seqs_list:
        for seq in seqs:
            if seq not in captured_sequences:
                captured_sequences[seq] = 0
            captured_sequences[seq] += 1
                  
    captured_sequences = sorted(captured_sequences.items(), key=lambda x: x[1], reverse=True)
    
    ### clustering

    values = np.array([min(x[1]/total_cnt, 1.0) for x in captured_sequences]).reshape(-1,1)

    best_bandwidth = estimate_bandwidth(values, quantile=0.25)
    if best_bandwidth == 0.0:
        best_bandwidth = 0.001

    mean_shift = MeanShift(bandwidth=best_bandwidth)
    cluster_labels = mean_shift.fit(values)
    result_labels = cluster_labels.labels_
    labels = []
    prev_rl = result_labels[0]
    converted_label = 0
    for rl in result_labels:
        if prev_rl != rl:
            converted_label += 1
        prev_rl = rl
        labels.append(converted_label)

    ### Collect seqs in captured cluster

    tmp_captured_sequences = set()
    tmp_seqidx = 0

    ### update parameter
    
    if not update_param:
        n_used_clusters = 1  
    else:
        with open(f"{list_dir}/redundant_sequences/prev_captured_{covkey}.pickle", 'rb') as f:
            _, n_used_clusters, prev_captured_sequences = pickle.load(f)
        print(f"{covkey} re-capture")

        while labels[tmp_seqidx] < n_used_clusters:
            tmp_captured_sequences.add(captured_sequences[tmp_seqidx][0])
            tmp_seqidx += 1
            if tmp_seqidx == len(captured_sequences):
                break

        if prev_captured_sequences == tmp_captured_sequences:
            print(f"Increase parameter for group {covkey}")
            n_used_clusters += 1
            
    while labels[tmp_seqidx] < n_used_clusters:
        tmp_captured_sequences.add(captured_sequences[tmp_seqidx][0])
        tmp_seqidx += 1
        if tmp_seqidx == len(captured_sequences):
            break

    with open(f"{list_dir}/redundant_sequences/prev_captured_{covkey}.pickle", 'wb') as f:
        pickle.dump((max(labels),n_used_clusters,tmp_captured_sequences), f)
    
    parameter_dict[covkey].append((n_used_clusters, len(tmp_captured_sequences)))
    
    tmp_pl = []
    
    ### Intersection with original Tree
    
    for seqs in refined_seqs_list:
        remaining_seqs = set()
        for seq in tmp_captured_sequences:
            for tmpseq in seqs:
                if compare_subpaths(seq, tmpseq):
                    remaining_seqs.add(seq)
        if remaining_seqs:
            tmp_pl.append(remaining_seqs)
    
    redundant_seqs = remove_included_seqs(tmp_pl)
        
    return redundant_seqs

def remove_included_seqs(original_seqs):
    idx_to_remove = set()
    original_seqs = sorted(original_seqs, key=lambda x:len(x))
    for i in range(len(original_seqs)-1):
        if i in idx_to_remove:
            continue
        if len(original_seqs[i]) == 0:
            idx_to_remove.add(i)
            continue
        for j in range(i+1, len(original_seqs)):
            if j in idx_to_remove:
                continue
            if original_seqs[i] < original_seqs[j]:
                idx_to_remove.add(j)
    
    refined_seqs = []
    for i in range(len(original_seqs)):
        if i not in idx_to_remove:
            refined_seqs.append(original_seqs[i])
    
    return refined_seqs

def update_redundant_sequence(info_num, redundant_sequence, parameter_dict, updated_covs, total_clusters, captured_covs):
    print(
        "---------------------------------------- Analyze Tests ----------------------------------------"
    )
    start_time = time.time()
    clusters_to_recapture = updated_covs & captured_covs
    result = sorted(set(total_clusters.keys()) - captured_covs, key=lambda x: sum(total_clusters[x].values()), reverse=True)
    cluster_diff_list = [sum(total_clusters[result[i]].values()) - sum(total_clusters[result[i+1]].values()) for i in range(len(result)-1)]
    new_top_k = cluster_diff_list.index(max(cluster_diff_list)) + 1

    new_redundant_sequence = copy.deepcopy(redundant_sequence)
    clusters_to_update = set(result[:new_top_k])
    clusters_to_update |= clusters_to_recapture

    sequence_list_size_dict = {}
    for cov_key in clusters_to_update:
        seqs_list = []
        for seqs_key,cnt in total_clusters[cov_key].items():
            with open(f"{list_dir}/unique_trees/{seqs_key}_seqs.pickle", 'rb') as f:
                tmp_seqs = pickle.load(f)
                seqs_list.append([set(tmp_seqs), cnt])

        sequence_list_size_dict[cov_key] = (len(total_clusters[cov_key]), len(seqs_list))
        if cov_key not in captured_covs:
            captured_covs.add(cov_key)
            parameter_dict[cov_key] = []
            update_param = False
        else:             
            update_param = True
        new_redundant_sequence[cov_key] = capture_rule_from_cluster(seqs_list, parameter_dict, cov_key, update_param)
    
    with open(f"{list_dir}/other_info/{info_num}_seqlist_size.pickle", 'wb') as f:
        pickle.dump(sequence_list_size_dict, f)

    logs = "--------------------------------------------------------------\n"
    logs += f"Capture from top {len(clusters_to_update)} clusters over {len(result)} in {time.time()-start_time}\n"
    with open(list_dir + "/logs.txt", "a") as f:
        f.write(logs)
               
    return new_redundant_sequence


######################
### Util Functions ###
######################

def no_newline(cov1, cov2):
    for i in range(len(cov1)):
        a = cov1[i]
        b = cov2[i]
        if a != b and b:
            return False
    return True

######################
### Main Functions ###
######################
                        
def run(rule_dict, depths_dict, subject, number_individuals):
    start_time = time.time()
    now_parameter_dict = {}
    now_redundant_sequence_name = None
    n_chance = 0

    total_clusters = {}
    unique_dt = {}
    unique_seqs = {}

    n_iter = 10
    max_n_chance = 1
    
    os.system(f'rm -rf "{baseDirectory}"')
    os.system(f'mkdir "{baseDirectory}"')
    for current_generation in range(10):
        generate_input_files(current_generation, ({}, {}, {}), rule_dict, depths_dict, n_iter)
        
    before_cov_vec = test_input_files(range(10), subject, 0, start_time, n_iter)
    with open(os.path.join(list_dir, "time.txt"), "a") as f:
        f.write(
            str(0).zfill(5)
            + "_cov.info end time : "
            + str(time.time() - start_time)
            + "\n"
        )
    logs = "base naive coverage : " + str(before_cov_vec.sum()) + f" in {time.time()-start_time}\n"
    with open(list_dir + "/logs.txt", "a") as f:
        f.write(logs)
        
    info_num = 1
    do_update = True
    redundant_sequence = dict()
    n_lines = len(before_cov_vec)
    captured_covs = set()
    while True:
        if do_update:
            updated_covs = set()    
                 
            for current_generation in range(10):
                updated_covs |= create_csv(current_generation, subject, total_clusters, unique_dt, unique_seqs, n_iter, n_lines, info_num)
                   
            os.system(f"ps -ef | grep 'java -jar' | grep {test_dir}"+"| awk '{print $2}' | xargs kill -9 1>/dev/null 2>/dev/null")
            logs = f"Created CSV files in {time.time()-start_time}\n"
            with open(f"{list_dir}/dts_infos.pickle", 'wb') as f:
                pickle.dump(unique_dt, f)

            with open(f"{cluster_data_dir}/{info_num}_total_clusters.pickle", 'wb') as f:
                pickle.dump(total_clusters, f)

            with open(list_dir + "/logs.txt", "a") as f:
                f.write(logs)

            redundant_sequence = update_redundant_sequence(info_num, redundant_sequence, now_parameter_dict, updated_covs, total_clusters, captured_covs) 

            with open(f"{list_dir}/other_info/parameters_{str(info_num).zfill(5)}.pickle", 'wb') as f:
                pickle.dump(now_parameter_dict, f)

            # Make PL for generator
            subseq_for_generator = {}
            idx_subseq = {}
            rs_for_generator = {}
            n_subseq = 0

            tmp_rss = []
            for cov_key in redundant_sequence:
                tmp_rss += redundant_sequence[cov_key]

            tmp_rss = sorted(tmp_rss, key=lambda x:len(x))
            tmp_rss = remove_included_seqs(tmp_rss)
            
            for rs in tmp_rss:
                converted_rs = set()
                tmp_keys_for_generator = []
                for sub_sequence in rs:
                    last_symbol, last_dn = sub_sequence[-2:]
                    prev_subseq = sub_sequence[:-1]
                    if last_symbol not in subseq_for_generator:
                        subseq_for_generator[last_symbol] = {}
                    if last_dn not in subseq_for_generator[last_symbol]:
                        subseq_for_generator[last_symbol][last_dn] = {}
                    if prev_subseq not in subseq_for_generator[last_symbol][last_dn]:
                        subseq_for_generator[last_symbol][last_dn][prev_subseq] = n_subseq
                        idx_subseq[n_subseq] = prev_subseq
                        n_subseq += 1
                    converted_rs.add(subseq_for_generator[last_symbol][last_dn][prev_subseq])
                    tmp_keys_for_generator.append((last_symbol, last_dn))
                    
                for last_symbol, last_dn in tmp_keys_for_generator:
                    if last_symbol not in rs_for_generator:
                        rs_for_generator[last_symbol] = []
                    if (last_dn,converted_rs) not in rs_for_generator[last_symbol]:
                        rs_for_generator[last_symbol].append((last_dn, converted_rs))

            now_redundant_sequence_name = f"{list_dir}/redundant_sequences/redundant_sequence_{info_num}.pickle"
                    
            with open(now_redundant_sequence_name, "wb") as f:
                pickle.dump((subseq_for_generator, idx_subseq, rs_for_generator), f)
                
            os.system(f"cp {now_redundant_sequence_name} {list_dir}/redundant_sequence.pickle")
 
            with open(f"{list_dir}/redundant_sequences/covs_rule_dict_{info_num}.pickle", "wb") as f:
                pickle.dump(redundant_sequence, f)

        os.system(f'rm -rf "{baseDirectory}"')
        os.system(f'mkdir "{baseDirectory}"')
        
        n_iter = number_individuals
        for current_generation in range(10):
            generate_input_files(current_generation, (subseq_for_generator, idx_subseq, rs_for_generator), rule_dict, depths_dict, n_iter)
        new_cov_vec = test_input_files(range(10), subject, info_num, start_time, n_iter)

        if no_newline(before_cov_vec, new_cov_vec):
            logs = f"Iter {info_num} : {before_cov_vec.sum()} in {time.time() - start_time} with {n_iter*10} inputs\n"
            with open(list_dir + "/logs.txt", "a") as f:
                f.write(logs)
            n_chance += 1
            if n_chance == max_n_chance:
                do_update = True
                n_chance = 0
                max_n_chance += 1
            else:
                do_update = False
        else:
            do_update = False
            n_chance = 0

            before_cov_vec |= new_cov_vec
            with open(list_dir + "/total_coverage.pickle", "wb") as f:
                pickle.dump(before_cov_vec, f)
            logs = f"Iter {info_num} : {before_cov_vec.sum()} in {time.time() - start_time} with {n_iter*10} inputs\n"
            with open(list_dir + "/logs.txt", "a") as f:
                f.write(logs)
        

        info_num += 1


if __name__ == "__main__":
    print("################# Run RSFuzz #################")
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
    options = parser.parse_args()

    subject = options.benchmark
    list_dir = os.path.abspath(options.list_dir)
    fileExtension = options.fileExtension
    baseDirectory = options.result_dir

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

    initial_param = 1
    cov_idx_dict = {}
    dt_idx_dict = {}
    seqs_idx_dict = {}
    coverage_list = []
    
    inv_benchmarks = ['Rhino', 'Argo', 'Genson', 'Gson' ]

    if options.base_fuzzer == "prob":
        if subject in inv_benchmarks:
            bnf_file_name_1 = os.path.abspath(f"bnf/{fileExtension}_inv.bnf")
        else:
            bnf_file_name_1 = os.path.abspath(f"bnf/{fileExtension}_prob.bnf")
    else:
        bnf_file_name_1 = os.path.abspath(f"bnf/{fileExtension}_random.bnf")

    if fileExtension == "js":
        symbol_with_terminal_children_only = set(['UnicodeLetter'])#, 'UnicodeCombiningMark'])
    elif fileExtension == "json":
        symbol_with_terminal_children_only = set(['letter'])

    (rule_dict, depths_dict) = Generator.parse_bnf(bnf_file_name_1, "." + fileExtension, os.path.abspath("bnf/"))

    one_child_symbols = set()
    for symbol in rule_dict:
        if len(rule_dict[symbol]) == 1:
            one_child_symbols.add(symbol)

    cluster_data_dir = os.path.abspath(f"{list_dir}/captured_clusters")

    run(rule_dict, depths_dict, subject, number_individuals)