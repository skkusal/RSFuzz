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
def generate_input_files(testcase_dir, recurrent_sequences, rule_dict, depths_dict,n_inputs):
    n_geninputs = Generator.parse_args(
        "." + fileExtension,
        testcase_dir + "/samples",
        testcase_dir + "/trees",
        20,
        n_inputs,
        rule_dict,
        depths_dict,
        recurrent_sequences,
        k_paths,
        kpath_prefixes
    )
    return n_geninputs
    # print("Generated input files.")
    
def compute_tree_hash(dt_name, hash_algo='sha256'):
    hash_func = hashlib.new(hash_algo)
    with open(dt_name, 'rb') as file:
        chunk = file.read()
    hash_func.update(chunk)
    return hash_func.hexdigest()

def compute_coverage_hash(cov, hash_algo='sha256'):
    return hash(tuple(cov))

def gcov_handler(ktest_gcov):
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
    
def dt_to_sequences(dt_name, rule_dict):
    with open(dt_name, 'rb') as f:
        dt = pickle.load(f)
    sequences = set()
    queue = [[0, 0, []]]
    while queue:
        cur_i, cur_j, cur_seq = queue.pop()
        cur_symbol, cur_children, cur_dn, cur_pi = dt[cur_i][cur_j]
        
        if cur_dn == -2:
            continue
        if cur_dn == -1 :
            tmp_idx = len(cur_seq)

            while cur_seq[tmp_idx-1] in one_child_symbols and tmp_idx > 1:
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

def get_file_coverage_cprog(input_name, csv_name):
    os.system("find " + test_dir + ' -name "*.gcda" -exec rm {} \;')
    try:
        error_code = subprocess.run([test_pgm, input_name],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=to).returncode
    except subprocess.TimeoutExpired:
            print("time out")
            return []
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
            return []
    os.system(f"ps -ef | grep ../benchmark/{subject}-analyser.jar"+"| awk '{print $2}' | xargs kill -9 1>/dev/null 2>/dev/null")
    if not os.path.exists(csv_name):
        return []
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
            return []
    os.system(f"ps -ef | grep ../benchmark/{subject}-analyser.jar"+"| awk '{print $2}' | xargs kill -9 1>/dev/null 2>/dev/null")
    if not os.path.exists(csv_name):
        return []
    tmp_cov = jacoco_handler2(csv_name)

    return tmp_cov

def create_csv(total_clusters, unique_dt, unique_seqs, n_iter, recurrent_sequences, n_lines, info_num, rule_dict):
    input_files = os.path.join(testcase_dir, "samples")
    tree_files = os.path.join(testcase_dir, "trees")
    csv_files = os.path.join(testcase_dir, "csv")
    if not os.path.isdir(csv_files):
        os.mkdir(csv_files, 0o755)
    
    updated_covs = set()
    if not is_java:
        os.chdir(test_dir)

    for i in range(len(os.listdir(input_files))):
        input_name = input_files + "/" + str(i).zfill(8) + "." + fileExtension
        dt_name = tree_files + "/" + str(i).zfill(8) + "_tree.pickle"
        csv_name = csv_files + "/" + str(i).zfill(8) + ".csv"
        tmp_dt_hash = compute_tree_hash(dt_name)
        
        if tmp_dt_hash in dt_idx_dict:
            dt_key = dt_idx_dict[tmp_dt_hash]
            seqs_key = unique_seqs[dt_key]
            cov_key = unique_dt[seqs_key]

        else:                        
            dt_key = len(dt_idx_dict)
            os.system(f"cp {dt_name} {capture_dir}/unique_trees/{dt_key}.pickle")
            dt_idx_dict[tmp_dt_hash] = dt_key  
            tmp_seqs = dt_to_sequences(dt_name, rule_dict)
            tmp_seqs_hash = hash(tmp_seqs)
            if tmp_seqs_hash not in seqs_idx_dict:
                with open(f"{capture_dir}/unique_trees/{len(seqs_idx_dict)}_seqs.pickle", 'wb') as f:
                    pickle.dump(tmp_seqs, f)
                seqs_idx_dict[tmp_seqs_hash] = len(seqs_idx_dict)
            seqs_key = seqs_idx_dict[tmp_seqs_hash]
            unique_seqs[dt_key] = seqs_key
            
            if seqs_key not in unique_dt:
                tmp_cov = get_1input_cov(input_name, csv_name)
                if len(tmp_cov) == 0:
                    # continue
                    os.system(f"cp {input_name} {capture_dir}/error/{info_num}_{i}.{fileExtension}")
                    os.system(f"cp {dt_name} {capture_dir}/error/{info_num}_{i}_tree.pickle")
                    tmp_cov = np.full(n_lines, False)
                tmp_cov_hash = compute_coverage_hash(tmp_cov)

                if tmp_cov_hash not in cov_idx_dict:
                    total_clusters[len(cov_idx_dict)] = {}
                    with open(f"{capture_dir}/unique_covs/{len(cov_idx_dict)}.pickle", 'wb') as f:
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
                if exceptions_cnt[e_key] > 100000:
                    break
                tc_idx = int(tc.split('.')[0])
                input_name = input_dir + "/" + str(tc_idx).zfill(8) + "." + fileExtension
                dt_name = tree_dir + "/" + str(tc_idx).zfill(8) + "_tree.pickle"            
                os.system(f"cp {input_name} {capture_dir}/error/{info_num}_{tc_idx}.{fileExtension}")
                os.system(f"cp {dt_name} {capture_dir}/error/{info_num}_{tc_idx}_tree.pickle")

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

def test_input_files(info_num, start_time, n_iter):
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
    remaining_seqs = []
    removed_seqs = set()
    for short_idx in range(len(refined_seqs)):
        if short_idx in removed_seqs:
            continue
        remaining_seqs.append(refined_seqs[short_idx])
        for long_idx in range(short_idx+1, len(refined_seqs)):
            if compare_subpaths(refined_seqs[long_idx], refined_seqs[short_idx]):
                removed_seqs.add(long_idx)
        
    return tuple(sorted(remaining_seqs, key=lambda x:len(x)))

def clustering(values, eps=0.05):
    cluster_labels = [0]
    curr_point = values[0]
    n_clusters = 0
    for point in values[1:]:
        if point < curr_point - eps:
            n_clusters += 1
            cluster_labels.append(n_clusters)
            curr_point = point
        else:
            cluster_labels.append(n_clusters)      
    return cluster_labels

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
  
def capture_rule_from_cluster(seqs_list, parameter_dict, covkey, update_param, rule_dict):
    captured_sequences = {}
    labels = [0]
 
    refined_seqs_list = set()
    for seqs, cnt in seqs_list:
        refined_seqs_list.add(simplify_subpaths(seqs))

    total_cnt = len(refined_seqs_list)
    
    for seqs in refined_seqs_list:
        for seq in seqs:
            if seq not in captured_sequences:
                captured_sequences[seq] = 0
            captured_sequences[seq] += 1
    
    tmp_sorted_seqs = sorted(captured_sequences.keys(), key=lambda x : len(x))
    
    removed_seqs = set()
    for short_idx in range(len(tmp_sorted_seqs)):
        if short_idx in removed_seqs:
            continue
        for long_idx in range(short_idx+1, len(tmp_sorted_seqs)):
            if compare_subpaths(tmp_sorted_seqs[long_idx], tmp_sorted_seqs[short_idx]):
                removed_seqs.add(long_idx)
                captured_sequences[tmp_sorted_seqs[short_idx]] += captured_sequences[tmp_sorted_seqs[long_idx]]

    for remove_idx in removed_seqs:
        del captured_sequences[tmp_sorted_seqs[remove_idx]]
                
    
    captured_sequences = sorted(captured_sequences.items(), key=lambda x: x[1], reverse=True)

    with open(f"{capture_dir}/recurrent_sequencess/simplified_cluster_{covkey}.pickle", 'wb') as f:
        pickle.dump(refined_seqs_list, f)
    
    values = np.array([min(x[1]/total_cnt, 1.0) for x in captured_sequences]).reshape(-1,1)

    best_bandwidth = estimate_bandwidth(values, quantile=0.25)
    if best_bandwidth == 0.0:
        print("best bandwidth == 0")
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

    # labels = clustering(values)
      
    if not update_param:
        n_used_clusters = 1
    else:
        with open(f"{capture_dir}/recurrent_sequencess/prev_captured_{covkey}.pickle", 'rb') as f:
            _, prev_n_clusters, prev_captured_sequences = pickle.load(f)
        print(f"{covkey} re-capture")
        
        prev_data_wrong = False
        
        cluster_labels = set()
        for used_seq in prev_captured_sequences:
            for idx, (seq, ratio) in enumerate(captured_sequences):
                if used_seq == seq:
                    cluster_labels.add(labels[idx])
        
        cluster_labels = sorted(cluster_labels)
        for idx, v in enumerate(cluster_labels[:-1]):
            # if cluster_labels[idx+1] - v > 1:
            if max(cluster_labels) > prev_n_clusters:
                prev_data_wrong = True

        n_used_clusters = prev_n_clusters
        if not prev_data_wrong:
            print("prev data OK")
            n_used_clusters += 1
        

    tmp_captured_sequences = set()
    tmp_seqidx = 0        
    while labels[tmp_seqidx] < n_used_clusters:
        tmp_captured_sequences.add(captured_sequences[tmp_seqidx][0])
        tmp_seqidx += 1
        if tmp_seqidx == len(captured_sequences):
            break
        
    print(tmp_seqidx, len(captured_sequences))

    with open(f"{capture_dir}/recurrent_sequencess/prev_captured_{covkey}.pickle", 'wb') as f:
        pickle.dump((max(labels),n_used_clusters,tmp_captured_sequences), f)
    
    parameter_dict[covkey].append((n_used_clusters, len(tmp_captured_sequences)))
    
    tmp_pl = []
    
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

def including_sequence(seq1, seq2):
    if len(seq1) > len(seq2):
        return False
    if seq1[-2:] != seq2[-2:]:
        return False
    cur_idx = 0
    for token in seq1[:-2]:
        if cur_idx > len(seq2) - 2:
            return False
        for token2 in seq2[cur_idx:-2]:
            if token == token2:
                break
            cur_idx += 1
    return True
            
def including_seqs(seqs1, seqs2):
    if not (seqs1 - seqs2):
        return True
    for seq1 in seqs1 - seqs2:
        containing = False
        for seq2 in seqs2:
            if including_sequence(seq1, seq2):
                containing = True
                break
        if not containing:
            return False
    return True

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
            if including_seqs(original_seqs[i], original_seqs[j]):
                idx_to_remove.add(j)
    
    refined_seqs = []
    for i in range(len(original_seqs)):
        if i not in idx_to_remove:
            refined_seqs.append(original_seqs[i])
    
    return refined_seqs

def update_recurrent_sequences(info_num, recurrent_sequences, parameter_dict, updated_covs, total_clusters, captured_covs, rule_dict):
    print(
        "---------------------------------------- Analyze Tests ----------------------------------------"
    )
    start_time = time.time()
    clusters_to_recapture = updated_covs & captured_covs
    result = sorted(set(total_clusters.keys()) - captured_covs, key=lambda x: sum(total_clusters[x].values()), reverse=True)
    cluster_diff_list = [sum(total_clusters[result[i]].values()) - sum(total_clusters[result[i+1]].values()) for i in range(len(result)-1)]
    if cluster_diff_list:
        new_top_k = cluster_diff_list.index(max(cluster_diff_list)) + 1
    else:
        new_top_k = len(result)
    # new_top_k = int(0.1 * len(cluster_diff)) + 1

    new_recurrent_sequences = copy.deepcopy(recurrent_sequences)
    clusters_to_update = set(result[:new_top_k])
    clusters_to_update |= clusters_to_recapture

    sequence_list_size_dict = {}
    for cov_key in clusters_to_update:
        seqs_list = []
        for seqs_key,cnt in total_clusters[cov_key].items():
            with open(f"{capture_dir}/unique_trees/{seqs_key}_seqs.pickle", 'rb') as f:
                tmp_seqs = pickle.load(f)
                seqs_list.append([set(tmp_seqs), cnt])

        sequence_list_size_dict[cov_key] = (len(total_clusters[cov_key]), len(seqs_list))
        if cov_key not in captured_covs:
            captured_covs.add(cov_key)
            parameter_dict[cov_key] = []
            update_param = False
        else:             
            update_param = True
        
        new_recurrent_sequences[cov_key] = capture_rule_from_cluster(seqs_list, parameter_dict, cov_key, update_param, rule_dict)
    
    with open(f"{capture_dir}/other_info/{info_num}_seqlist_size.pickle", 'wb') as f:
        pickle.dump(sequence_list_size_dict, f)

    logs = f"{time.time()-start_time}\tCapture top {len(clusters_to_update)} / {len(result)} Clusters\n"
    with open(capture_dir + "/logs.txt", "a") as f:
        f.write(logs)
           
    return new_recurrent_sequences

def no_newline(cov1, cov2):
    for i in range(len(cov1)):
        a = cov1[i]
        b = cov2[i]
        if a != b and b:
            return False
    return True

def merge_rules(rss):
    intersections = []
    
    for idx1, rs1 in enumerate(rss):
        for rs2 in rss[idx1+1:]:
            tmp_inter = rs1 & rs2
            if len(rs1) == len(rs2) and len(tmp_inter) + 1 == len(rs1):
                if tmp_inter not in intersections:
                    intersections.append(tmp_inter)

    merge_result = []
    
    merged_idx = set()
    
    for inter in intersections:
        subpaths_to_merge = set()
        for idx, rs in enumerate(rss):
            if len(rs - inter) == 1:
                subpaths_to_merge.add((idx,(rs - inter).pop()))
        merged_subpaths = set()
        for idx1, subpath1 in subpaths_to_merge:
            similar_subpaths = set([subpath1])
            similar_idx = set([idx1])
            
            for idx2, subpath2 in subpaths_to_merge:
                if subpath1 != subpath2 and subpath1[:-1] == subpath2[:-1]:
                    similar_subpaths.add(subpath2)
                    similar_idx.add(idx2)
                    
            if len(similar_subpaths) == len(rule_dict[subpath1[-2]]):
                merged_idx |= similar_idx
                for symbols, dn, _ in rule_dict[subpath1[-3]]:
                    if subpath1[-2] in symbols:
                        merged_subpaths.add(subpath1[:-2]+tuple([dn]))
        for subpath in merged_subpaths:
            new_rule = inter | set([subpath])
            if new_rule not in merge_result:
                merge_result.append(new_rule)
    
    for idx, rs in enumerate(rss):
        if idx not in merged_idx:
            merge_result.append(rs)
    print(f"{len(merged_idx)} rules are merged")
    print(f"{len(rss)} merged to {len(merge_result)}")
    return merge_result
               
def run(rule_dict, depths_dict, number_individuals):
    start_time = time.time()
    now_parameter_dict = {}
    before_recurrent_sequences_name = "-"
    now_recurrent_sequences_name = None
    n_chance = 0
    
    # best_recurrent_sequences = {}
    total_clusters = {}
    unique_dt = {}
    unique_seqs = {}

    # n_iter = 100
    n_iter = number_individuals
    max_n_chance = 1
    
    possible_children_devnums = {}
    for token in rule_dict:
        possible_children_devnums[token] = set()
        for child in rule_dict[token]:
            if child[2] > 0:
                possible_children_devnums[token].add(child[1])
    total_ninputs = 0
    info_num = 0
    os.system(f'rm -rf "{testcase_dir}"')
    os.system(f'mkdir "{testcase_dir}"')
    total_ninputs += generate_input_files(testcase_dir, ({}, {}, {}), rule_dict, depths_dict, n_iter)
    before_cov_vec = test_input_files(0, start_time, n_iter)
    logs = f"Generate Redundant Sequences\n"
    logs += f"{time.time()-start_time}\tIter-{info_num}\t{before_cov_vec.sum()}\t{total_ninputs}\n"
    with open(capture_dir + "/logs.txt", "a") as f:
        f.write(logs)
        
    info_num += 1
    do_update = True
    recurrent_sequences = {}
    n_lines = len(before_cov_vec)
    captured_covs = set()
    while True:
    # while max_n_chance < 20:
        if do_update:
            updated_covs = create_csv(total_clusters, unique_dt, unique_seqs, n_iter, recurrent_sequences, n_lines, info_num, rule_dict)
                   
            os.system(f"ps -ef | grep ../benchmark/{subject}-analyser.jar"+"| awk '{print $2}' | xargs kill -9 1>/dev/null 2>/dev/null")

            with open(f"{capture_dir}/dts_infos.pickle", 'wb') as f:
                pickle.dump(unique_dt, f)

            with open(f"{cluster_data_dir}/{info_num}_total_clusters.pickle", 'wb') as f:
                pickle.dump(total_clusters, f)
                
            recurrent_sequences = update_recurrent_sequences(info_num, recurrent_sequences, now_parameter_dict, updated_covs, total_clusters, captured_covs, rule_dict) 
            
            with open(f"{capture_dir}/other_info/parameters_{str(info_num).zfill(5)}.pickle", 'wb') as f:
                pickle.dump(now_parameter_dict, f)

            # Make PL for generator
            subseq_for_generator = {}
            idx_subseq = {}
            rs_for_generator = {}
            n_subseq = 0

            tmp_rss = []
            for cov_key in recurrent_sequences:
                tmp_rss += recurrent_sequences[cov_key]
            
            # tmp_rss = filter_useless_subpaths(tmp_rss, rule_dict)
            tmp_rss = sorted(tmp_rss, key=lambda x:len(x))
            tmp_rss = remove_included_seqs(tmp_rss)
            tmp_rss = merge_rules(tmp_rss)
            tmp_rss = sorted(tmp_rss, key=lambda x:len(x))
            tmp_rss = remove_included_seqs(tmp_rss)
            

            for recurrent_sequence in tmp_rss:
                converted_rs = set()
                tmp_keys_for_generator = []
                for sub_sequence in recurrent_sequence:
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

                   
            now_recurrent_sequences_name = f"{capture_dir}/recurrent_sequencess/recurrent_sequences_{info_num}.pickle"
            with open(now_recurrent_sequences_name, "wb") as f:
                pickle.dump((subseq_for_generator, idx_subseq, rs_for_generator), f)
 
            with open(f"{capture_dir}/recurrent_sequencess/covs_rule_dict_{info_num}.pickle", "wb") as f:
                pickle.dump(recurrent_sequences, f)

        os.system(f'rm -rf "{testcase_dir}"')
        os.system(f'mkdir "{testcase_dir}"')
        
        n_iter = number_individuals
        total_ninputs += generate_input_files(testcase_dir, (subseq_for_generator, idx_subseq, rs_for_generator), rule_dict, depths_dict, n_iter)
        new_cov_vec = test_input_files(info_num, start_time, n_iter)


        if no_newline(before_cov_vec, new_cov_vec):
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
            with open(capture_dir + "/total_coverage.pickle", "wb") as f:
                pickle.dump(before_cov_vec, f)
            # always_covered_lines = np.logical_and(always_covered_lines, new_cov_vec)
        before_recurrent_sequences_name = now_recurrent_sequences_name
        logs = f"{time.time()-start_time}\tIter-{info_num}\t{before_cov_vec.sum()}\t{total_ninputs}\n"
        with open(capture_dir + "/logs.txt", "a") as f:
            f.write(logs)
        os.system(f"cp {before_recurrent_sequences_name} {capture_dir}/recurrent_sequences.pickle")

        info_num += 1


if __name__ == "__main__":
    print("#################Generate Redundant Sequences######################")
    parser = optparse.OptionParser()
    parser.add_option("--benchmark",dest="benchmark",)
    parser.add_option("--fileExtension",dest="fileExtension",)
    parser.add_option("--basefuzzer",dest="basefuzzer",)
    parser.add_option("--capture_dir",dest="capture_dir",)
    parser.add_option("--testcase_dir",dest="testcase_dir",)
    parser.add_option("--n_num",dest="n_num",type="int",)
    parser.add_option("--test_dir",dest="test_dir",)
    parser.add_option("--test_pgm",dest="test_pgm",)
    (options, args) = parser.parse_args()

    subject = options.benchmark
    capture_dir = os.path.abspath(options.capture_dir)
    fileExtension = options.fileExtension
    testcase_dir = os.path.abspath(options.testcase_dir)
    
    if options.test_pgm == "java":
        is_java = True
        test_dir = None
        test_pgm = None
    else:
        is_java = False
        test_dir = options.test_dir
        test_pgm = options.test_pgm

    # Parameters
    number_individuals = options.n_num # // 10
    to = 3
    cov_idx_dict = {}
    dt_idx_dict = {}
    seqs_idx_dict = {}
    coverage_list = []
    root_dir = os.getcwd()

    inv_benchmarks = ['Rhino', 'Argo', 'Genson', 'Gson' ]
    # separator_tokens = ['"["', '"]"', '","', '"{"', '"}"', ' ']
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

    one_child_symbols = set()
    for symbol in rule_dict:
        if len(rule_dict[symbol]) == 1:
            one_child_symbols.add(symbol)

    if fileExtension == 'json' or subject == 'Rhino':
        get_1input_cov = get_file_coverage_javaprog_1
        get_dir_cov = get_dir_coverage_javaprog_1
    elif fileExtension == 'js':
        get_1input_cov = get_file_coverage_cprog
        get_dir_cov = get_dir_coverage_cprog
    else:
        get_1input_cov = get_file_coverage_javaprog_2
        get_dir_cov = get_dir_coverage_javaprog_2
    
    exceptions_cnt = {}

    cluster_data_dir = os.path.abspath(f"{capture_dir}/captured_clusters")

    run(rule_dict, depths_dict, number_individuals)