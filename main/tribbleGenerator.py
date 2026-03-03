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

_RE_Q = r'(?:[+*?])?$'
_RE_BRACKET = re.compile(r'^/\[.*\]/' + _RE_Q + r'$')
_RE_PAREN_ALT = re.compile(r'^/\(.*\)/' + _RE_Q + r'$')

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

def is_regex_terminal(sym):
    return bool(_RE_BRACKET.match(sym) or _RE_PAREN_ALT.match(sym))

def include_regexp(expansion):
    for i in expansion:
        if type(i) == tuple:
            return True
        elif type(i) == list:
            if include_regexp(i):
                return True
    return False

class InputGenerator:
    def __init__(self, grammar, depths_dict, config, recurrent_sequences, k_paths, prefixes, log=False):
        self.grammar = grammar
        self.depths_dict = depths_dict
        self.config = config
        self.log = log
        self.sub_sequences = recurrent_sequences[0]
        self.idx_subseq_dict = recurrent_sequences[1]
        self.recurrent_sequence = recurrent_sequences[2]
        self.possible_kpaths = k_paths
        self.prefix_dict = prefixes
        self.k_value = 5
        self.regex_terminals = set()
        for symbol in self.grammar:
            for children in self.grammar[symbol]:
                for x in children[0]:
                    if is_regex_terminal(x):
                        self.regex_terminals.add(x)

        self.nonterminals = set(grammar.keys())
        self.cost_map = {}
        for sym, (exp_with_cost, _) in depths_dict.items():
            d = {}
            for exp, cost in exp_with_cost:
                d[tuple(exp)] = cost
            self.cost_map[sym] = d
        # self.recurrent_sequences = recurrent_sequences

        # self.s_pattern = re.compile("/\[\\\\u....\]")
        # self.l_pattern = re.compile("/\[\\\\u....-\\\\u....\]/")

    def pcfg_update(self, rule_dict):
        self.grammar = rule_dict

    def is_nonterminal(self, s):
        return s in self.nonterminals

    def expansions_to_children(self, symbol, expansions, depth, idx):
        # print("expansions:", expansions)
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
        
        path = []
        while td != -1:
            node = tree[td][ti]
            path.append(node[0])
            td, ti = node[-1]
        path.reverse()
        
        j = 0
        for x in path:
            if x == seq[j]:
                j += 1
                if j == len(seq):
                    return True
        return False          

    def prune_children(self, symbol, tree, node_idx, idx, tmp_sub_seqs):
        deriv_nums_to_prune = []
        if symbol not in self.recurrent_sequence:
            return deriv_nums_to_prune
        
        for dn_to_prune, rs in self.recurrent_sequence[symbol]:
            remained_subseq = rs - tmp_sub_seqs
            # print("bbbbb",len(remained_subseq))
            if len(remained_subseq) != 1:
                continue
            target_subseq = remained_subseq.pop()
            
            if self.satisfy_pre_seq(tree, self.idx_subseq_dict[target_subseq], node_idx):
                deriv_nums_to_prune.append(dn_to_prune)
        # print("AAAAAAAA",deriv_nums_to_prune)/
        return deriv_nums_to_prune

    def expansion_cost(self, symbol, expansion):
        return self.cost_map.get(symbol, {}).get(tuple(expansion), 999)

    def expand_minimum_node_guided(self, tree, tmp_sub_seqs, next_symbol, selected_slot):
        nodes_in_next_depth = []
        depth = len(tree) - 1
        next_slot = None

        for i, (symbol, children, original_dn, parent_info) in enumerate(tree[-1]):
            if children is not None:
                tree[-1][i] = (symbol, (), original_dn, parent_info)
                continue
            
            if i == selected_slot:
                expansions = [(exp, dn, self.expansion_cost(symbol, exp)) for (exp, dn, _) in self.grammar[symbol] if next_symbol in exp]
                poss, dns, costs = self.expansions_to_children(symbol, expansions, depth, i)
                min_cost = min(costs)

                cand = [j for j, (c, dn) in enumerate(zip(costs, dns)) if c == min_cost]
                if not cand:
                    cand = [j for j, c in enumerate(costs) if c == min_cost]
            else:
                expansions = [(exp, dn, self.expansion_cost(symbol, exp)) for (exp, dn, _) in self.grammar[symbol]]
                poss, dns, costs = self.expansions_to_children(symbol, expansions, depth, i)
                prune_dns = set(self.prune_children(symbol, tree, (depth, i), i, tmp_sub_seqs))
                min_cost = min(costs)

                cand = [j for j, (c, dn) in enumerate(zip(costs, dns)) if c == min_cost and dn not in prune_dns]
                if not cand and len(tree) < self.config["max_depths"]:
                    cand = [j for j, c in enumerate(costs)]
                elif not cand:
                    cand = [j for j, c in enumerate(costs) if c == min_cost]

            chosen_j = random.choice(cand)
            new_nodes = poss[chosen_j]
            deriv_num = dns[chosen_j]

            start = len(nodes_in_next_depth)
            tree[-1][i] = (symbol, range(start, start + len(new_nodes)), deriv_num, parent_info)

            if symbol in self.sub_sequences:
                if deriv_num in self.sub_sequences[symbol]:
                    for subseq in self.sub_sequences[symbol][deriv_num]:
                        if self.satisfy_pre_seq(tree, subseq, (depth, i)):
                            tmp_sub_seqs.add(self.sub_sequences[symbol][deriv_num][subseq])

            nodes_in_next_depth.extend(new_nodes)
            if i == selected_slot:
                candidate_slots = [tmp_idx for tmp_idx, tmp_node in enumerate(nodes_in_next_depth[start:]) if tmp_node[0] == next_symbol]
                next_slot = start + random.choice(candidate_slots)
        tree[-1] = tuple(tree[-1])
        tree.append(nodes_in_next_depth)
        return next_slot

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
            if len(symbol) > 1 and (symbol[0] == symbol[-1] == "'" or symbol[0] == symbol[-1] == '"'):
                return symbol[1:-1]
            elif symbol in self.regex_terminals:
                tmp_symbol = symbol[1:]
                if tmp_symbol[-1] != "/":
                    tmp_symbol = tmp_symbol[:-2] + tmp_symbol[-1]
                else:
                    tmp_symbol = tmp_symbol[:-1]
                return exrex.getone(tmp_symbol)
            return symbol
        elif children == None:
            raise Exception("Not expended symbol:", symbol)
        else:
            result = ""
            for i in children:
                result += self.tree_to_string(tree, depth+1,i)
            return result

    def generate_input(self, output_dir, tree_dir, prev_ninputs):
        uncovered_paths = set(self.possible_kpaths)
        n_inputs = 0
        while uncovered_paths:
            target_path = uncovered_paths.pop()
            prefix = random.choice(self.prefix_dict[target_path[0]])
            target_path = prefix[:-1] + target_path
            tree = [[[self.config["start_rule"], None, -1, (-1, -1)]]]
            tmp_sub_seqs = set()
            cur_depth = 0
            selected_slot = 0
            while self.any_possible_expansions(tree[-1]):
                if selected_slot != None:
                    next_symbol = target_path[cur_depth+1]
                else:
                    next_symbol = None
                selected_slot = self.expand_minimum_node_guided(tree, tmp_sub_seqs, next_symbol, selected_slot)
                cur_depth += 1
                if cur_depth == len(target_path) - 1:
                    selected_slot = None

            tree[-1] = tuple(tree[-1])

            input_num_string = str(n_inputs + prev_ninputs).zfill(8)
            with open(f"{output_dir}/{input_num_string}" + self.config["extension"], "w") as f:
                f.write(self.tree_to_string(tree,0,0))
            with open(f"{tree_dir}/{input_num_string}_tree.pickle", "wb") as f:
                pickle.dump(tuple(tree), f)
            
            stack = []
            for d in range(len(tree)):
                for i, (sym, _ch, _dn, _p) in enumerate(tree[d]):
                    if sym in self.nonterminals:
                        stack.append((d, i, (sym,)))

            while stack and uncovered_paths:
                d, i, path = stack.pop()

                # record k-path
                if len(path) == self.k_value:
                    if path in uncovered_paths:
                        uncovered_paths.remove(path)
                    continue

                # stop if node has no children
                sym, children_idx, _dn, _p = tree[d][i]
                if children_idx == ():
                    continue

                nd = d + 1
                if nd >= len(tree):
                    continue

                # expand to children (parent -> child, contiguous)
                for ci in children_idx:
                    child_sym = tree[nd][ci][0]
                    stack.append((nd, ci, path + (child_sym,)))
                
            n_inputs += 1
        return n_inputs

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

def _is_escaped(s: str, pos: int) -> bool:
    k = pos - 1
    cnt = 0
    while k >= 0 and s[k] == '\\':
        cnt += 1
        k -= 1
    return (cnt % 2) == 1

def expansion_to_tokens(expansion):
    tokens = []
    buf = []
    i = 0
    n = len(expansion)
    while i < n:
        c = expansion[i]
        if c.isspace():
            if buf:
                tokens.append("".join(buf))
                buf.clear()
            i += 1
            continue

        # quoted terminal
        if c == '"':
            if buf:
                tokens.append("".join(buf))
                buf.clear()
            j = i + 1
            while j < n:
                if expansion[j] == '"' and not _is_escaped(expansion, j):
                    break
                j += 1
            tokens.append(expansion[i:j + 1])
            i = j + 1
            continue

        # regex token
        if c == '/':
            if buf:
                tokens.append("".join(buf))
                buf.clear()
            j = i + 1
            while j < n:
                if expansion[j] == '/' and expansion[j - 1] != '\\' and expansion[j-1] in [']', ')']:
                    break
                j += 1
            if j < len(expansion)-1 and expansion[j+1] != " ":
                j += 1
            tokens.append(expansion[i:j + 1])
            i = j + 1
            continue

        # symbol
        buf.append(c)
        i += 1

    if buf:
        tokens.append("".join(buf))

    return tokens

def parse_bnf(bnf_file, suffix):
    pcfg = {}
    prob_pattern = re.compile(" @@ [0-9.E-]+([ ]*\|[ ]*|;\n)")
    prob_simple = re.compile("@@ [0-9.E-]+")
    bar = re.compile("( )*\|( )*")
    with open(bnf_file, "r") as f:
        bnf_list = f.readlines()
    if suffix in [".json", ".csv", ".url"]:
        for line in bnf_list:
            if line == "\n":
                continue
            else:
                line = codecs.decode(line, "unicode_escape")
                splited_line = line.split(" = ", 1)
                rule_name = splited_line[0]
                pcfg[rule_name] = []
                derivations = re.split(prob_pattern, splited_line[1])
                # print("derivations:", derivations)

                prob_list_raw = prob_simple.findall(splited_line[1])
                # print("prob_list_raw:", prob_list_raw)
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
                        # print("word_list:", word_list)
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
                        # print("word_list_final:", word_list)
                        pcfg[rule_name].append(
                            [word_list, deriv_num, float(prob_list_raw[prob_num][3:])]
                            # [word_list, prob_num, float(prob_list_raw[prob_num][3:])]
                        )
                        prob_num += 1
        if suffix == '.json':
            with open("../bnf/json_depths.pickle", "rb") as f:
                depths_dict = pickle.load(f)
        else:
            depths_dict = calculate_depths(pcfg)
        # print(pcfg)
        return (pcfg, depths_dict)

    elif suffix == ".md":
        for line in bnf_list:
            if line == "\n":
                continue
            else:
                # line = codecs.decode(line, "unicode_escape")
                splited_line = line.split(" = ", 1)
                rule_name = splited_line[0]
                pcfg[rule_name] = []
                derivations = re.split(prob_pattern, splited_line[1])
                # print("derivations:", derivations)

                prob_list_raw = prob_simple.findall(splited_line[1])
                # print("prob_list_raw:", prob_list_raw)
                prob_num = 0
                used_sets = []
                for words in derivations:
                    if words in [";\n", ''] or bar.match(words) is not None:
                        pass
                    else:
                        word_list = expansion_to_tokens(words)
                        word_set = set(word_list) - separator_tokens
                        if word_set not in used_sets:
                            used_sets.append(word_set)
                        deriv_num = used_sets.index(word_set)
                        # print(rule_name,words)
                        # print("word_list:", word_list)
                        
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
                        # print("word_list_final:", word_list)
                        pcfg[rule_name].append(
                            [word_list, deriv_num, float(prob_list_raw[prob_num][3:])]
                            # [word_list, prob_num, float(prob_list_raw[prob_num][3:])]
                        )
                        prob_num += 1
        depths_dict = calculate_depths(pcfg)
        return (pcfg, depths_dict)
    elif suffix == ".css":
        print("Not implimented.")
        exit(0)
        # return pcfg, "stylesheet"
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
            with open(
                "/home/yunji/Project/PGFuzzer/js_approach/bnf/js_base.pickle", "rb"
            ) as f:
                js_dict = pickle.load(f)

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
        # repeatable_rules = get_repeatinfo(js_dict)
        js_dict = trans_regexp(js_dict)
        depths_dict = calculate_depths(js_dict)

        return (js_dict, depths_dict)
    else:
        print("Not implimented.")
        exit(0)
        # return pcfg, "program"

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


def main(rule_dict, depths_dict, config, input_num, output_dir, tree_dir, recurrent_sequences, k_paths, prefixes):
    for key, value in rule_dict.items():
        rule_dict[key] = normalize_prob(value)
    generator = InputGenerator(rule_dict, depths_dict, config, recurrent_sequences,k_paths, prefixes,  log=False)
    # for token in generator.non_sequence_terminals:
    #     print(token, generator.non_sequence_terminals[token])
    n_inputs = 0
    while n_inputs < input_num:
        n_inputs += generator.generate_input(output_dir, tree_dir, n_inputs)
    return n_inputs


def parse_args(
    suffix, output_dir, tree_dir, max_depths, input_num, rule_dict, depths_dict, recurrent_sequences, k_paths, prefixes
):
    input_num = input_num
    output_dir = output_dir
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    if not os.path.isdir(tree_dir):
        os.makedirs(tree_dir)
    start_rule = list(rule_dict.keys())[0]
    config = {"extension": suffix, "start_rule": start_rule, "max_depths": max_depths}

    return main(rule_dict, depths_dict, config, input_num, output_dir, tree_dir, recurrent_sequences, k_paths, prefixes,)
