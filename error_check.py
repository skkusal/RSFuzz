import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--benchmark", dest="benchmark",required=True)
parser.add_argument("--error_dir", dest="error_dir",required=True)

options = parser.parse_args()
pgm = options.benchmark
input_dir = options.error_dir

if pgm not in "JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava":
    print("Please input available benchmark name\nAvailable benchmarks : JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava")
    exit(1)

if not os.path.exists(input_dir):
    print(f"{input_dir} is not exist")
    exit(1)

input_dir = os.path.abspath(input_dir)

if len(os.listdir(input_dir)) == 0:
    print(f"{input_dir} is empty")
    exit(1)

result_csvfile = f"{input_dir}/result.csv"
result_txtfile = f"{input_dir}/errorcheck_result.txt"

os.system(f"java -jar benchmark/{pgm}-analyser.jar {pgm} file-coverage-all {input_dir} {result_csvfile} > {result_txtfile} 2>&1")

with open(result_txtfile, 'r') as f:
    lines = f.readlines()

for idx, l in enumerate(lines):
    if input_dir in l:
        lines[idx] = ""

exception_dict = {}
start_idx = None

for idx, l in enumerate(lines):
    if l == "":
        if start_idx:
            if ':' in lines[start_idx]:
                exception_case = lines[start_idx][:lines[start_idx].index(':')+1]
            else:
                exception_case = lines[start_idx]
            exception_trace = "".join(lines[start_idx+1:idx])
            
            if exception_case not in exception_dict:
                exception_dict[exception_case] = set()
            exception_dict[exception_case].add(exception_trace)
        start_idx = None
    elif start_idx == None:
        start_idx = idx

with open(f"{input_dir}/bug-result.txt", 'w') as f:
    for exception_case in exception_dict:
        f.write(f"{exception_case}\n")
        for trace in exception_dict[exception_case]:
            f.write(f"{trace}\n\n")

print(f"{'Exception Type'.ljust(50)}# uniques")
for exception_case in exception_dict:
    print(f"{exception_case[:-1].ljust(50)}{len(exception_dict[exception_case])}")

print(f"Detail reports : {input_dir}/bug-result.txt")

os.system(f"rm {result_csvfile} {result_txtfile}")
    
    