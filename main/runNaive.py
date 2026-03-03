import optparse
import os
import subprocess
import time

benchmark_dir = os.path.abspath("../benchmark")

def run_rsfuzz_online(opt):
    if not os.path.isdir(opt.result_dir):
        os.makedirs(opt.result_dir)
    if os.path.isdir(os.path.join(opt.result_dir, "capture_data")):
        os.system("rm -rf " + os.path.join(opt.result_dir, "capture_data"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "coverage"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "unique_covs"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "unique_trees"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "captured_clusters"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "recurrent_sequencess"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "other_info"))
    os.mkdir(os.path.join(opt.result_dir, "capture_data", "error"))
    if os.path.isdir(os.path.join(opt.result_dir, "test_data")):
        os.system("rm -rf " + os.path.join(opt.result_dir, "test_data"))
    os.mkdir(os.path.join(opt.result_dir, "test_data"))

    if opt.benchmark in ["JerryScript", "Jsish", "QuickJS"] and (
        opt.test_dir is None or opt.test_pgm is None
    ):
        print("Please input test directory and program")
        exit(1)

    if opt.benchmark in ["JerryScript", "Jsish", "QuickJS"]:
        file_extension = "js"
        test_pgm = opt.test_pgm
    elif opt.benchmark in ["jackson-dataformat-csv", "super-csv"]:
        file_extension = "csv"
        test_pgm = "java"
    elif opt.benchmark in ["commonmark", "txtmark",]:
        file_extension = "md"
        test_pgm = "java"
    else:
        file_extension = "json"
        test_pgm = "java"

    if opt.benchmark == "Rhino":
        file_extension = "js"

    start_time = time.time()
    subprocess.call(
        f"timeout {str(opt.capture_time)} python3 naive_genRS.py --benchmark {opt.benchmark} --fileExtension {file_extension} --basefuzzer {opt.basefuzzer} --capture_dir {os.path.join(opt.result_dir, 'capture_data')} --testcase_dir {os.path.join(opt.result_dir, 'test_data')} --n_num {str(opt.n_num)} --test_dir {opt.test_dir} --test_pgm {test_pgm} --naive_version {opt.naive_version}",
        shell=True,
        stderr=subprocess.STDOUT,
    )
    
    recurrent_sequences = os.path.abspath(os.path.join(opt.result_dir, "capture_data","recurrent_sequences.pickle"))
    print("Capture finished")

    subprocess.call(
        f"timeout {str(opt.test_time)} python3 runFuzzer.py --benchmark {opt.benchmark} --fileExtension {file_extension} --basefuzzer {opt.basefuzzer} --capture_dir {os.path.join(opt.result_dir, 'capture_data')} --testcase_dir {os.path.join(opt.result_dir, 'test_data')} --n_num {10000} --test_dir {opt.test_dir} --test_pgm {test_pgm} --recurrent_sequences {recurrent_sequences}",
        shell=True,
        stderr=subprocess.STDOUT,
    )

    print(f"{opt.benchmark} {opt.result_dir} finished")
    # return recurrent_sequences

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("--benchmark", dest="benchmark", help="Available benchmark: JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava",)
    parser.add_option("--basefuzzer", dest="basefuzzer", help="Base Fuzzer : [random, pcfg, tribble]",)
    parser.add_option("--capture_time", dest="capture_time", type="int", default=43200, help="Capture time(sec) (Default: 43200 = 12h)",)
    parser.add_option("--test_time", dest="test_time", type="int", default=43200, help="Test time(sec) (Default: 43200 = 12h)",)
    # parser.add_option("--recurrent_sequences", dest="recurrent_sequences", help="Pruning list for test")
    parser.add_option("--result_dir", dest="result_dir", default="results", help="Result directory (Default: results)",)
    parser.add_option("--n_num", dest="n_num", type="int", default=3000, help="Hyperparameter: n_num (Default: 2000)",)
    parser.add_option("--test_dir", dest="test_dir", help="Directory to capture coverage data (Required to test JerryScript, Jsish, or QuickJS)",)
    parser.add_option("--test_pgm", dest="test_pgm", help="Program to run (Required to test JerryScript, Jsish, or QuickJS)",)
    parser.add_option("--naive_version", dest="naive_version", default="naive", help="naive approach version (naive, select, capture)")

    (options, args) = parser.parse_args()

    if options.benchmark is None:
        print("Please input benchmark name")
        exit(1)

    if options.benchmark == "QuickJS":
        options.test_pgm = f"{benchmark_dir}/quickjs/qjs"
        options.test_dir = f"{benchmark_dir}/quickjs"
    elif options.benchmark == "JerryScript":
        options.test_pgm = f"{benchmark_dir}/jerryscript/build/bin/jerry"
        options.test_dir = f"{benchmark_dir}/jerryscript/build"
    elif options.benchmark == "Jsish":
        options.test_pgm = f"{benchmark_dir}/jsish/jsish"
        options.test_dir = f"{benchmark_dir}/jsish"
    else:
        options.test_pgm = "java"

    options.result_dir += "/" + options.benchmark
    
    print(options.test_pgm)
    print(options.test_dir)

    recurrent_sequences = run_rsfuzz_online(options)
