#!/usr/bin/env python3
import os
import pickle
import random
import re
import codecs
import exrex

max_repeat = 3
separator_tokens = ['"{"', '"}"', '","', '":"', '"["', '"]"', '"""']
separator_tokens += [' ', '', ',', '\n', '{', '}', '(', ')', ';', '[', ']']
separator_tokens = set(separator_tokens)

def pprint_tree(tree, file=None, _prefix="", _last=True):
    result = ""
    (_, _, value, _, children) = tree
    result += _prefix + ("└─ " if _last else "├─ ") + value + "\n"
    _prefix += "   " if _last else "│  "
    child_count = len(children)
    for i, child in enumerate(children):
        _last = i == (child_count - 1)
        result += pprint_tree(child, file, _prefix, _last)
    return result

def include_regexp(expansion):
    for i in expansion:
        if type(i) == tuple:
            return True
        elif type(i) == list:
            if include_regexp(i):
                return True
    return False

class InputGenerator:
    def __init__(self, grammar, depths_dict, config, redundant_sequence, log=False):
        self.grammar = grammar
        self.depths_dict = depths_dict
        self.config = config
        self.log = log
        self.sub_sequences = redundant_sequence[0]
        self.idx_subseq_dict = redundant_sequence[1]
        self.pruning_rules = redundant_sequence[2]

    def pcfg_update(self, rule_dict):
        self.grammar = rule_dict

    def is_nonterminal(self, s):
        return s in self.grammar

    def expansions_to_children(self, symbol, expansions, depth, idx):
        possible_children = []
        children_probability = []
        deriv_num_list = []
        for expansion, deriv_num, prob in expansions:
            children = []
            nonterminals = [self.is_nonterminal(x) for x in expansion]
            if any(nonterminals):
                for i in range(len(expansion)):
                    if type(expansion[i]) == str:
                        if not nonterminals[i] and expansion[i] in separator_tokens:
                            children.append((expansion[i], (), -2, (depth, idx)))
                        elif not nonterminals[i]:
                            children.append((expansion[i], (), -1, (depth, idx)))
                        else:
                            children.append((expansion[i], None, -1, (depth, idx)))
                    else:
                        raise Exception("Strange expr: " + str(expansion[i]))
            else:
                for i in range(len(expansion)):
                    if type(expansion[i]) == str:
                        children.append((expansion[i], (), -1, (depth, idx)))
                    else:
                        raise Exception("Strange expr: " + str(expansion[i]))                
            possible_children.append(children)
            deriv_num_list.append(deriv_num)
            children_probability.append(prob)

        return (possible_children, deriv_num_list, children_probability)

    def satisfy_pre_seq(self, tree, seq, node_idx):
        if not seq:
            return True
        
        if len(tree) < len(seq):
            return False
        
        td, ti = node_idx
        if tree[td][ti][0] != seq[-1]:
            return False
        
        main_seq = [] 
        while td != -1:
            main_seq.append(tree[td][ti][0])
            td, ti = tree[td][ti][-1]
        main_seq = main_seq[::-1]
        
        last_idx = -1
        for n in seq:
            if n in main_seq[last_idx + 1:]:
                last_idx = main_seq.index(n)
            else:
                return False
        return True            

    def prune_children(self, symbol, tree, node_idx, idx, tmp_sub_seqs):
        deriv_nums_to_prune = []
        if symbol not in self.pruning_rules:
            return deriv_nums_to_prune
        
        for dn_to_prune, rs in self.pruning_rules[symbol]:
            remained_subseq = rs - tmp_sub_seqs
            if len(remained_subseq) != 1:
                continue
            target_subseq = remained_subseq.pop()
            
            if self.satisfy_pre_seq(tree, self.idx_subseq_dict[target_subseq], node_idx):
                deriv_nums_to_prune.append(dn_to_prune)
        return deriv_nums_to_prune


    def expand_node_randomly(self, tree, tmp_sub_seqs):
        nodes_in_next_depth = []
        depth = len(tree) - 1
        for i, node in enumerate(tree[-1]):
            # node : [token, list of children indexes, sequence_idx]
            symbol, children, original_dn , parent_info = node
            if children is None:
                expansions = self.grammar[symbol]
                (possible_children, deriv_num_list, children_probability) = self.expansions_to_children(symbol, expansions, depth, i)
                deriv_num_to_prune = self.prune_children(symbol, tree, (depth, i), i, tmp_sub_seqs)
                
                remaining_possible_children = []
                remaining_deriv_num_list = []
                remaining_children_probability = []
                
                for idx_to_remove in range(len(deriv_num_list)):
                    if deriv_num_list[idx_to_remove] not in deriv_num_to_prune:
                        remaining_possible_children.append(possible_children[idx_to_remove])
                        remaining_deriv_num_list.append(deriv_num_list[idx_to_remove])
                        remaining_children_probability.append(children_probability[idx_to_remove])

                if remaining_possible_children and sum(remaining_children_probability):
                    temp_idx_list = range(len(remaining_possible_children))
                    chosen_child_idx = random.choices(population=temp_idx_list, weights=remaining_children_probability, k=1)[0]
                    new_nodes = remaining_possible_children[chosen_child_idx]
                    deriv_num = remaining_deriv_num_list[chosen_child_idx]
                elif remaining_possible_children:
                    temp_idx_list = range(len(remaining_possible_children))
                    chosen_child_idx = random.choices(population=temp_idx_list, k=1)[0]
                    new_nodes = remaining_possible_children[chosen_child_idx]
                    deriv_num = remaining_deriv_num_list[chosen_child_idx]
                else:
                    temp_idx_list = range(len(possible_children))
                    chosen_child_idx = random.choices(population=temp_idx_list, k=1)[0]
                    new_nodes = possible_children[chosen_child_idx]
                    deriv_num = deriv_num_list[chosen_child_idx]
                
                tree[-1][i] = (symbol, range(len(nodes_in_next_depth), len(nodes_in_next_depth)+len(new_nodes)), deriv_num, parent_info)
                
                if symbol in self.sub_sequences:
                    if deriv_num in self.sub_sequences[symbol]:
                        for subseq in self.sub_sequences[symbol][deriv_num]:
                            if self.satisfy_pre_seq(tree, subseq, (depth, i)):
                                tmp_sub_seqs.add(self.sub_sequences[symbol][deriv_num][subseq])
                
                for child_node in new_nodes:               
                    nodes_in_next_depth.append(child_node)
                
            else:
                tree[-1][i] = (symbol, (), original_dn, parent_info)
        tree[-1] = tuple(tree[-1])
        tree.append(nodes_in_next_depth)


    def expansion_cost(self, symbol, expansion):
        expansions_with_depths = self.depths_dict[symbol][0]
        for expansion_with_depths in expansions_with_depths:
            if expansion_with_depths[0] == expansion:
                return expansion_with_depths[1]
        return 999

    def expand_minimum_node(self, tree, tmp_sub_seqs):
        nodes_in_next_depth = []
        depth = len(tree) - 1
        for i, node in enumerate(tree[-1]):
            symbol, children, _, parent_info = node
            if children is None:
                expansions = [(expansion, devnum, self.expansion_cost(symbol, expansion)) for (expansion, devnum, _) in self.grammar[symbol]]
                (possible_children, deriv_num_list, children_cost)= self.expansions_to_children(symbol, expansions, depth, i)
                deriv_num_to_prune = self.prune_children(symbol, tree, (depth, i), i, tmp_sub_seqs)
                
                remaining_possible_children = []
                remaining_deriv_num_list = []

                chosen_cost = min(children_cost)

                for idx_to_check in range(len(children_cost)):
                    if children_cost[idx_to_check] == chosen_cost and deriv_num_list[idx_to_check] not in deriv_num_to_prune:
                        remaining_possible_children.append(possible_children[idx_to_check])
                        remaining_deriv_num_list.append(deriv_num_list[idx_to_check])

                if not remaining_possible_children:             
                    for idx_to_check in range(len(children_cost)):
                        if children_cost[idx_to_check] == chosen_cost:
                            remaining_possible_children.append(possible_children[idx_to_check])
                            remaining_deriv_num_list.append(deriv_num_list[idx_to_check])

                temp_idx_list = range(len(remaining_possible_children))
                chosen_child_idx = random.choices(population=temp_idx_list, k=1)[0]
                new_nodes = remaining_possible_children[chosen_child_idx]
                deriv_num = remaining_deriv_num_list[chosen_child_idx]
                
                tree[-1][i] = (symbol, range(len(nodes_in_next_depth), len(nodes_in_next_depth)+len(new_nodes)), deriv_num, parent_info)
                
                for child_node in new_nodes:             
                    nodes_in_next_depth.append(child_node)
            else:
                tree[-1][i] = (symbol, (), -1, parent_info)
        tree[-1] = tuple(tree[-1])
        tree.append(nodes_in_next_depth)

    def any_possible_expansions(self, nodes_to_expand):
        for node in nodes_to_expand:
            if node[1] is None:
                return True
        return False

    def expand_check(self, nodes_to_expand, depth_to_exapnd):
        if depth_to_exapnd >= self.config["max_depths"]:
            return False
        for node in nodes_to_expand:
            if node[1] is None:
                return True
        return False

    def tree_to_string(self, tree, depth, idx):
        symbol, children, _, parent_info = tree[depth][idx]
        if children == ():
            if len(symbol) > 1 and (
                symbol[0] == symbol[-1] == "'" or symbol[0] == symbol[-1] == '"'
            ):
                return symbol[1:-1]
            elif len(symbol) > 4 and symbol[:2] == "/[" and symbol[-2:] == "]/":
                return exrex.getone(symbol[1:-1])
            return symbol
        elif children == None:
            raise Exception("Not expended symbol:", symbol)
        else:
            result = ""
            for i in children:
                result += self.tree_to_string(tree, depth+1,i)
            return result

    def generate_input(self, num, output_dir):
        for i in range(num):
            tree = [[[self.config["start_rule"], None, -1, (-1, -1)]]]
            tmp_sub_seqs = set()
            depth_to_exapnd = 0
            while self.expand_check(tree[-1], depth_to_exapnd):
                self.expand_node_randomly(tree, tmp_sub_seqs)
                depth_to_exapnd += 1

            while self.any_possible_expansions(tree[-1]):
                self.expand_minimum_node(tree, tmp_sub_seqs)
                depth_to_exapnd += 1

            tree[-1] = tuple(tree[-1])

            input_num_string = str(i).zfill(8)
            with open(f"{output_dir}/{input_num_string}" + self.config["extension"], "w") as f:
                f.write(self.tree_to_string(tree,0,0))
            with open(f"{output_dir}/{input_num_string}_tree.pickle", "wb") as f:
                pickle.dump(tuple(tree), f)



def normalize_prob(expr_list):
    probability_sum = 0
    normalized_list = []
    for i in expr_list:
        probability_sum += i[2]

    for i in expr_list:
        if probability_sum > 0:
            normalized_list.append([i[0], i[1], i[2] / probability_sum])
        else:
            normalized_list.append([i[0], i[1], 1 / len(expr_list)])
    return normalized_list


def parse_bnf(bnf_file, suffix, bnf_dir):
    pcfg = {}
    prob_pattern = re.compile(" @@ [0-9.E-]+([ ]*\|[ ]*|;\n)")
    prob_simple = re.compile("@@ [0-9.E-]+")
    bar = re.compile("( )*\|( )*")
    with open(bnf_file, "r") as f:
        bnf_list = f.readlines()
    if suffix == ".json":
        for line in bnf_list:
            if line == "\n":
                continue
            else:
                line = codecs.decode(line, "unicode_escape")
                splited_line = line.split(" = ", 1)
                rule_name = splited_line[0]
                pcfg[rule_name] = []
                derivations = re.split(prob_pattern, splited_line[1])
                prob_list_raw = prob_simple.findall(splited_line[1])
                prob_num = 0
                used_sets = []
                for words in derivations:
                    if words in [";\n", ""] or bar.match(words) is not None:
                        pass
                    else:
                        word_list = words.split(" ")
                        word_set = set(word_list) - separator_tokens
                        if word_set not in used_sets:
                            used_sets.append(word_set)
                        deriv_num = used_sets.index(word_set)
                        i = 0
                        while i < len(word_list):
                            if len(word_list[i]) == 0:
                                del word_list[i]
                            else:
                                if i + 2 <= len(word_list) and word_list[i : i + 2] == [
                                    '"',
                                    '"',
                                ]:
                                    word_list[i : i + 2] = " "
                                i += 1
                        pcfg[rule_name].append(
                            [word_list, deriv_num, float(prob_list_raw[prob_num][3:])]
                        )
                        prob_num += 1
        with open(f"{bnf_dir}/json_depths.pickle", "rb") as f:
            depths_dict = pickle.load(f)
        return (pcfg, depths_dict)
    
    elif suffix == ".css":
        print("Not implimented.")
        exit(0)
        
    elif suffix == ".js":
        p = re.compile("@@[ ]?[0-9\.eE\-]+")
        with open(bnf_file, "r") as f:
            lines = f.read()
            prob_list_raw = p.findall(lines)
        prob_list = []
        for i in prob_list_raw:
            prob_list.append(float(i[2:]))

        try:
            with open("../bnf/js_base.pickle", "rb") as f:
                js_dict = pickle.load(f)
        except:
            print("js base missing")
            exit(1)

        js_token_list = js_dict.keys()
        pointer = 0
        try:
            for token in js_token_list:
                for i in range(len(js_dict[token])):
                    if js_dict[token][i][1] == "@@":
                        js_dict[token][i][1] = prob_list[pointer]
                        pointer += 1
        except:
            print("Total prob list:", len(prob_list))
            print("now pointer:", pointer)
            exit(0)
        js_dict = trans_regexp(js_dict)
        depths_dict = calculate_depths(js_dict)

        return (js_dict, depths_dict)
    else:
        print("Not implimented.")
        exit(0)


def trans_regexp(rule_dict):
    tokens = rule_dict.keys()
    for token in tokens:
        new_expand_list = []
        worklist = []
        for expand_idx in range(len(rule_dict[token])):
            worklist.append(
                [
                    rule_dict[token][expand_idx][0],
                    expand_idx,
                    rule_dict[token][expand_idx][1],
                ]
            )
        used_sets = []
        while worklist != []:
            work = worklist.pop()
            work_type = [type(i) for i in work[0]]
            if list in work_type:
                idx = work_type.index(list)
                worklist.append(
                    [work[0][:idx] + work[0][idx] + work[0][idx + 1 :]] + work[1:]
                )
            elif tuple in work_type:
                idx = work_type.index(tuple)
                if work[0][idx][1] == "?":
                    worklist.append(
                        [work[0][:idx] + work[0][idx + 1 :]] + [work[1]] + [work[2] / 2]
                    )
                    worklist.append(
                        [work[0][:idx] + [work[0][idx][0]] + work[0][idx + 1 :]]
                        + [work[1]]
                        + [work[2] / 2]
                    )
                elif work[0][idx][1] == "*":
                    for repeat_count in range(max_repeat):
                        worklist.append([work[0][:idx] + [work[0][idx][0]] * repeat_count + work[0][idx + 1 :]] + [work[1]] + [work[2] / max_repeat])
                elif work[0][idx][1] == "+":
                    for repeat_count in range(1, 1 + max_repeat):
                        worklist.append([work[0][:idx] + [work[0][idx][0]] * repeat_count + work[0][idx + 1 :]] + [work[1]] + [work[2] / max_repeat])
                if work[0][idx][1] == "|":
                    temp = work[0][idx][0]
                    for i in temp:
                        worklist.append(
                            [work[0][:idx] + [i] + work[0][idx + 1 :]]
                            + [work[1]]
                            + [work[2] / len(temp)]
                        )
            else:
                work_set = set(work[0]) - set([token])
                if work_set not in used_sets:
                    used_sets.append(work_set)
                work[1] = used_sets.index(work_set)
                if work[0] == []:
                    work[0].append("")
                new_expand_list.append(work)
        rule_dict[token] = new_expand_list
    return rule_dict


def count_none(depths_dict):
    tokens = depths_dict.keys()
    counter = [depths_dict[i][1] for i in tokens].count(None)
    for token in tokens:
        counter += [i[1] for i in depths_dict[token][0]].count(None)
    return counter


def calculate_depths(rule_dict):
    depths_dict = {}
    tokens = rule_dict.keys()
    for token in tokens:
        new_expand_list = []
        for i in rule_dict[token]:
            new_expand_list.append([i[0], None])
        depths_dict[token] = (new_expand_list, None)
    minimum_cut = 0
    count_None = count_none(depths_dict)
    while count_None > 0:
        old_count_None = count_None
        for token in tokens:
            for expand_idx in range(len(depths_dict[token][0])):
                if depths_dict[token][0][expand_idx][1] is None:
                    if token in depths_dict[token][0][expand_idx][0]:
                        depths_dict[token][0][expand_idx][1] = 999
                    else:
                        max_depth = 0
                        for term in depths_dict[token][0][expand_idx][0]:
                            if term in tokens:
                                temp = depths_dict[term][1]
                                if temp is None:
                                    max_depth = None
                                else:
                                    if max_depth is not None and temp > max_depth:
                                        max_depth = temp
                        if max_depth is not None:
                            depths_dict[token][0][expand_idx][1] = max_depth
            max_depth_list = [i[1] for i in depths_dict[token][0]]
            if depths_dict[token][1] is None and minimum_cut in max_depth_list:
                depths_dict[token] = (depths_dict[token][0], minimum_cut + 1)
            elif None not in max_depth_list:
                depths_dict[token] = (depths_dict[token][0], min(max_depth_list) + 1)
        count_None = count_none(depths_dict)
        if old_count_None == count_None:
            minimum_cut += 1

    return depths_dict


def main(rule_dict, depths_dict, config, input_num, output_dir, redundant_sequence):
    for key, value in rule_dict.items():
        rule_dict[key] = normalize_prob(value)
    generator = InputGenerator(rule_dict, depths_dict, config, redundant_sequence, log=False)
    generator.generate_input(input_num, output_dir)
    return None


def parse_args(
    suffix, output_dir, max_depths, input_num, rule_dict, depths_dict, redundant_sequence
):
    input_num = input_num
    output_dir = output_dir
    if not os.path.isdir(output_dir):
        os.system("mkdir " + output_dir)
    start_rule = list(rule_dict.keys())[0]
    config = {"extension": suffix, "start_rule": start_rule, "max_depths": max_depths}

    return main(rule_dict, depths_dict, config, input_num, output_dir, redundant_sequence)
