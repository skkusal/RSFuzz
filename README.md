# RSFuzz

RSFuzz is a tool designed to minimize redundant input generation in grammar-based fuzzing. It automatically identifies main causes of redundancy and guides the base fuzzer to avoid them, improving efficiency and effectiveness.

## Installation

We recommend using a Docker image for quick and easy installation.

```bash
$ docker pull {}
$ docker run --rm -it --ulimit='stack=-1:-1' {}
```

## Benchmarks

In the docker image, all 8 benchmarks we used are installed in 'root/rsfuzz/benchmark'. Details of benchmarks are as follows:
![benchmark_table](./Benchmarks.png)

## How to Rrun RSFuzz

You can run RSFuzz and baseline fuzzers with the following commands in the 'root/rsfuzz' directory. There are two required arguments:`benchmark` (target program) and `base_fuzzer` (`random` or `prob`).

```bash
# Run RSFuzz
$ python3 main_rsfuzz.py --benchmark Gson --base_fuzzer random
# Run baselines
$ python3 main_baseline.py --benchmark Gson --base_fuzzer random
```

The results will be saved in the `{result_dir}/{base_fuzzer}/{benchmark}/captured_data` dicrectory. RSFuzz generates 4 main outputs:
1. Redundant sequences : `redundant_sequence.pickle` file
2. Test logs : `logs.txt` file
3. Error cases and their derivation trees : `error/*` files
4. Coverage results : `total_coverage.pickle` and `total_coverage_testing.pickle` files

## Additional Experiments

We also provied some additional approaches: naive versions of RSFuzz
- **naive**: RSFuzz without `Select` and `Capture`
- **select**: RSFuzz without `Capture`
- **capture**: RSFuzz without `Select`

You can execute these experiments with the following commands in the 'root/rsfuzz' directory:
```bash
# run naive: RSFuzz - (Select, Capture) approaches
$ python3 main_naive.py --benchmark Gson --base_fuzzer random --naive_version naive
# run select: RSFuzz - (Capture) approaches
$ python3 main_naive.py --benchmark Gson --base_fuzzer random --naive_version select
# run capture: RSFuzz - (Select) approaches
$ python3 main_naive.py --benchmark Gson --base_fuzzer random --naive_version capture
```

To check the less important input ratio, you can run the following command. If you omit the `redundant_sequence` argument, the experiment will run for baseline fuzzers.

```bash
# Check the less important input ratio (Default: 100,000 inputs)
$ python3 main_inputratio.py --benchmark Gson --base_fuzzer random --redundant_sequence {path/to/redundant_sequence.pickle}
```

## Details

For more details about arguments, you can use `--help` commands:

```bash
$python3 main_rsfuzz.py --help
usage: main_rsfuzz.py [options]

Options for RSFuzz

options:
  -h, --help            show this help message and exit
  --benchmark BENCHMARK
                        Available benchmarks: JerryScript, Jsish, QuickJS, Rhino, Argo, Genson, Gson, JsonToJava
  --base_fuzzer BASE_FUZZER
                        random or prob
  --capture_time CAPTURE_TIME
                        Capture time(sec) (Default: 43200 = 12h)
  --test_time TEST_TIME
                        Test time(sec) (Default: 43200 = 12h)
  --result_dir RESULT_DIR
                        Result directory (Default: rsfuzz_results)
  --n_num N_NUM         Hyperparameter to hanlde n of input generation in a iteration (Default: 2000)
```

## Bug-finding results

Since coverage results are stored in output files, we only provide a Python file, `error_check.py`, to check bug-finding results. There are two required arguments: `benchmark` (target program) and `error_dir` (e.g., `*/capture_data/error`).
```bash
$ python3 error_check.py --benchmark Gson --error_dir rsfuzz_results/random/argo/captured_data/error
Exception Type                                    N uniques
java.lang.ClassCastException                      3
java.lang.IllegalArgumentException                10
Detail reports : rsfuzz_results/random/argo/captured_data/error/bug-result.txt
```
You can check more details (stack traces) in the `{error_dir}/bug-result.txt` file.