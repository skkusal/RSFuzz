import os
import pickle
import optparse
import time

bytecode_dict = {
 'commonmark': os.path.abspath('../benchmark/originalcode/commonmark.jar'),
 'jackson-dataformat-csv': os.path.abspath('../benchmark/originalcode/jackson-dataformat-csv.jar'),
 'super-csv': os.path.abspath('../benchmark/originalcode/super-csv.jar'),
 'txtmark': os.path.abspath('../benchmark/originalcode/txtmark.jar')
 }

parser = optparse.OptionParser()
parser.add_option("--pgm", dest="pgm")
parser.add_option("--inputs_dir",dest="inputs_dir",)

(options, args) = parser.parse_args()
pgm = options.pgm
inputs_dir = options.inputs_dir
 
def process_1filelog(inputlog):
    if len(inputlog) < 2:
        return "", "", ""
    tcname = inputlog[0].split()[-1]
    splitidx = inputlog[1].index(':')
    exception_key = inputlog[1][:splitidx]
    exception_log = "".join(inputlog[2:])
    return tcname, exception_key, exception_log

if not os.path.exists(inputs_dir):
    print(inputs_dir)
    print("NO inputs_dir")
    exit()

if not os.path.exists(inputs_dir):
    os.makedirs(inputs_dir)


exception_logfile = f"{inputs_dir}/logs.txt"
csv_name = f"{inputs_dir}/coverage.txt"
tc_dir = f"{inputs_dir}/capture_data/error"

if pgm in ["Rhino", "Gson", "Genson", "JsonToJava"]:
    os.system(f"java -jar ../benchmark/coverage-analyser-{pgm}-{core_num}.jar {pgm} file-coverage-l {tc_dir} {csv_name} > {exception_logfile} 2>&1")
elif pgm in ['jackson-dataformat-csv', 'super-csv', 'commonmark', 'txtmark']:
    dummy_name = f"{inputs_dir}/dummy.txt"
    error_json = f"{inputs_dir}/exceptions.json"
    os.system(f"java -jar ../benchmark/coverage-analyser-{pgm}-{core_num}.jar --ignore-exceptions --log-exceptions {error_json} --report-coverage {dummy_name} --line-coverage {csv_name} --original-bytecode {bytecode_dict[pgm]} {tc_dir} > {exception_logfile}")

print("Process log file")

exception_dict = {}
with open(exception_logfile, 'r') as f:
    buf = [f.readline()]
    for l in f:
        if tc_dir in l:
            tcname, exception_type, exception_log = process_1filelog(buf)
            buf = []
            if exception_type not in exception_dict:
                exception_dict[exception_type] = set()
            exception_dict[exception_type].add(exception_log)
        buf.append(l)

    tcname, exception_type, exception_log = process_1filelog(buf)
    if exception_type not in exception_dict:
        exception_dict[exception_type] = set()
    exception_dict[exception_type].add(exception_log)

with open(f"{inputs_dir}/bug-result.txt", 'w') as f:
    for exception_case in exception_dict:
        f.write(f"{exception_case}\n")
        for trace in exception_dict[exception_case]:
            f.write(f"{trace}\n\n")

print(f"{'Exception Type'.ljust(50)}# uniques")
for exception_case in exception_dict:
    print(f"{exception_case[:-1].ljust(50)}{len(exception_dict[exception_case])}")

print(f"Detail reports : {inputs_dir}/bug-result.txt")

os.system(f"rm {result_csvfile} {result_txtfile}")

        
