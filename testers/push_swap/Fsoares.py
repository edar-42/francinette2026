"""
push_swap tests, written for the subject version 1.2:

	./push_swap [--simple | --medium | --complex | --adaptive] [--bench] <numbers>

Everything is checked with a checker written in python (so no checker_linux / checker_Mac is needed).
"""

import logging
import math
import os
import random
import re
import shutil
import statistics
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from testers.BaseExecutor import BaseExecutor
from utils.ExecutionContext import get_timeout, has_bonus, is_strict
from utils.TerminalColors import TC
from utils.Utils import is_mac

logger = logging.getLogger("ps-fsoares")

OPERATIONS = ["sa", "sb", "ss", "pa", "pb", "ra", "rb", "rr", "rra", "rrb", "rrr"]
STRATEGIES = {
    "--simple": "O(n²)",
    "--medium": "O(n√n)",
    "--complex": "O(n log n)",
    "--adaptive": "adaptive",
}
INT_MAX = 2**31 - 1
INT_MIN = -2**31

# (size, excellent, good, pass)
BENCHMARKS = [(100, 700, 1500, 2000), (500, 5500, 8000, 12000)]


# --------------------------------------------------------------------------- python checker


def apply_operations(numbers: List[int], ops: List[str]):
	"""Executes the operations. Returns (stack_a, stack_b). Index 0 is the top of the stack"""
	a = list(numbers)
	b = []

	def swap(s):
		if len(s) > 1:
			s[0], s[1] = s[1], s[0]

	def rot(s):
		if len(s) > 1:
			s.append(s.pop(0))

	def rrot(s):
		if len(s) > 1:
			s.insert(0, s.pop())

	for op in ops:
		if op == "sa": swap(a)
		elif op == "sb": swap(b)
		elif op == "ss": swap(a); swap(b)
		elif op == "pa":
			if b: a.insert(0, b.pop(0))
		elif op == "pb":
			if a: b.insert(0, a.pop(0))
		elif op == "ra": rot(a)
		elif op == "rb": rot(b)
		elif op == "rr": rot(a); rot(b)
		elif op == "rra": rrot(a)
		elif op == "rrb": rrot(b)
		elif op == "rrr": rrot(a); rrot(b)
		else:
			raise ValueError(op)
	return a, b


def is_sorted(numbers):
	return all(numbers[i] < numbers[i + 1] for i in range(len(numbers) - 1))


def disorder(numbers: List[int]) -> float:
	n = len(numbers)
	if n < 2:
		return 0.0
	mistakes = sum(1 for i in range(n) for j in range(i + 1, n) if numbers[i] > numbers[j])
	return mistakes / (n * (n - 1) / 2)


def simple_sort_ops(numbers: List[int]) -> List[str]:
	"""A (bad but correct) sort used to generate valid instructions for the checker tests"""
	a = list(numbers)
	ops = []
	while a:
		idx = a.index(min(a))
		if idx <= len(a) // 2:
			ops += ["ra"] * idx
		else:
			ops += ["rra"] * (len(a) - idx)
		a = a[idx:] + a[:idx]
		a.pop(0)
		ops.append("pb")
	ops += ["pa"] * len(numbers)
	return ops


def random_numbers(n, lo=INT_MIN, hi=INT_MAX):
	return random.sample(range(lo, hi), n) if hi - lo > 10 * n else random.sample(range(lo, hi + 1), n)


def numbers_with_disorder(n, low, high, tries=2000):
	"""Generates n numbers with low <= disorder < high"""
	base = sorted(random_numbers(n, -10000, 10000))
	for _ in range(tries):
		target = random.uniform(low, high)
		numbers = list(base)
		if target >= 0.5:
			random.shuffle(numbers)
			if target > 0.75:
				numbers.sort(reverse=True)
				for _ in range(int((1 - target) * n)):
					i, j = random.randrange(n), random.randrange(n)
					numbers[i], numbers[j] = numbers[j], numbers[i]
		else:
			swaps = max(1, int(target * n * 1.3))
			for _ in range(swaps):
				i, j = random.randrange(n), random.randrange(n)
				numbers[i], numbers[j] = numbers[j], numbers[i]
		d = disorder(numbers)
		if low <= d < high and not is_sorted(numbers):
			return numbers
	return None


# --------------------------------------------------------------------------- running


class Run:

	def __init__(self, args, stdout: bytes, stderr: bytes, code: Optional[int], timeout=False):
		self.args = args
		self.raw_out = stdout
		self.out = stdout.decode("ascii", errors="backslashreplace")
		self.err = stderr.decode("ascii", errors="backslashreplace")
		self.code = code
		self.timeout = timeout

	@property
	def crashed(self):
		return self.code is not None and self.code < 0

	def problem(self):
		if self.timeout:
			return "timeout"
		if self.crashed:
			return f"crashed (signal {-self.code})"
		return None


def quote(arg):
	if arg == "" or re.search(r"[^\w+\-.,/=]", arg):
		return "'" + arg.replace("'", "'\\''") + "'"
	return arg


def cmd_str(binary, args, stdin=None):
	line = f"./{binary} " + " ".join(quote(a) for a in args)
	if stdin is not None:
		shown = stdin.replace("\n", "\\n")
		if len(shown) > 60:
			shown = shown[:60] + "..."
		line = f"printf '{shown}' | " + line
	return line.strip()


class Fsoares(BaseExecutor):

	name = "fsoares"
	folder = "fsoares"
	git_url = "my own tests"

	def __init__(self, tests_dir, temp_dir, to_execute, missing) -> None:
		super().__init__(tests_dir, temp_dir, to_execute, missing)
		self.project_dir = (self.temp_dir / "..").resolve()
		self.push_swap = self.project_dir / "push_swap"
		self.checker = self.project_dir / "checker"
		self.failed: Dict[str, List[str]] = {}
		self.timeout = get_timeout()
		self.valgrind = shutil.which("valgrind")
		self.mac_leaks = is_mac() and shutil.which("leaks")
		self.log = open(self.temp_dir / "errors.log", "w")
		random.seed()

	# ---------------------------------------------------------------- helpers

	def run(self, binary: Path, args: List[str], stdin: str = "", timeout=None) -> Run:
		try:
			p = subprocess.run([str(binary)] + args,
			                   input=stdin.encode(),
			                   capture_output=True,
			                   timeout=timeout or self.timeout,
			                   cwd=self.temp_dir)
			return Run(args, p.stdout, p.stderr, p.returncode)
		except subprocess.TimeoutExpired as ex:
			return Run(args, ex.stdout or b"", ex.stderr or b"", None, timeout=True)

	def leaks(self, binary: Path, args: List[str], stdin: str = "") -> Optional[str]:
		"""Returns a description of the leak, or None if no leak (or no tool to check)"""
		if self.valgrind:
			command = [
			    self.valgrind, "--leak-check=full", "--show-leak-kinds=definite,indirect,possible",
			    "--errors-for-leak-kinds=definite,indirect,possible", "--error-exitcode=242", "-q",
			    str(binary)
			] + args
		elif self.mac_leaks:
			command = ["leaks", "-quiet", "-atExit", "--", str(binary)] + args
		else:
			return None
		try:
			p = subprocess.run(command, input=stdin.encode(), capture_output=True, timeout=self.timeout * 10,
			                   cwd=self.temp_dir)
		except subprocess.TimeoutExpired:
			return None
		err = p.stderr.decode(errors="backslashreplace")
		if self.valgrind:
			if p.returncode == 242:
				lines = [l for l in err.splitlines() if "lost" in l or "Invalid" in l]
				return "\n".join(lines[:4]) or "memory errors / leaks"
			return None
		out = p.stdout.decode(errors="backslashreplace")
		if p.returncode != 0 and "leaks for" in out:
			return next((l for l in out.splitlines() if "leaks for" in l), "leaks")
		return None

	def record(self, category, ok, message=None):
		"""Prints the result of one test and saves the error message"""
		results = self.results.setdefault(category, [])
		results.append(ok)
		n = len(results)
		color = TC.GREEN if ok is True else (TC.YELLOW if ok == "warn" else TC.RED)
		tag = "OK" if ok is True else ("WARN" if ok == "warn" else "KO")
		print(f"{color}{n}.{tag} {TC.NC}", end="", flush=True)
		if ok is not True and not message:
			message = "failed"
		if ok is not True:
			self.log.write(f"[{category}] test {n} ({tag}): {message}\n")
			if ok is not True and ok != "warn":
				self.failed.setdefault(category, []).append(message)
			else:
				self.warnings.append(f"[{category}] {message}")

	def start_category(self, title):
		print(f"\n{TC.B_BLUE}{title:<22}{TC.NC}: ", end="", flush=True)

	def parse_ops(self, run: Run):
		"""Returns (ops, error_message)"""
		out = run.out
		if out == "":
			return [], None
		if "\r" in out:
			return None, "the output contains '\\r'"
		lines = out.split("\n")
		if lines[-1] == "":
			lines = lines[:-1]
		for i, line in enumerate(lines):
			if line not in OPERATIONS:
				if line.strip() in OPERATIONS:
					return None, f"operation {i + 1} has spaces around it: {line!r} (only '\\n' is allowed)"
				if line == "":
					return None, f"empty line after operation {i}"
				return None, f"invalid operation {i + 1}: {line[:30]!r}"
		return lines, None

	def check_sort(self, args: List[str], numbers: List[int], run: Run, binary="push_swap"):
		"""Validates a push_swap run. Returns (ok, message, n_ops)"""
		cmd = cmd_str(binary, args)
		if run.problem():
			return False, f"{cmd}\n    -> {run.problem()}", None
		if run.err.strip():
			return False, f"{cmd}\n    -> printed on stderr: {run.err.strip()[:80]!r}", None
		ops, error = self.parse_ops(run)
		if error:
			return False, f"{cmd}\n    -> {error}", None
		a, b = apply_operations(numbers, ops)
		if b or not is_sorted(a) or len(a) != len(numbers):
			return False, f"{cmd}\n    -> KO (stack not sorted after {len(ops)} operations{', b not empty' if b else ''})", len(ops)
		return True, None, len(ops)

	# ---------------------------------------------------------------- tests

	def execute(self):
		self.results = {}
		self.warnings = []
		if not self.push_swap.exists():
			print(f"{TC.B_RED}push_swap executable not found after make{TC.NC}")
			return ["push_swap"]
		if not self.valgrind and not self.mac_leaks:
			print(f"{TC.YELLOW}valgrind not found: the leaks will not be checked{TC.NC}")

		if self.exec_mandatory:
			print(f"{TC.B_WHITE}[Mandatory]{TC.NC}", end="")
			self.test_no_args()
			self.test_errors()
			self.test_parsing()
			self.test_sorted()
			self.test_small()
			self.test_strategies()
			self.test_disorder_regimes()
			self.test_bench()
			self.test_leaks()
			self.test_performance()
		if self.exec_bonus:
			print(f"\n\n{TC.B_WHITE}[Bonus]{TC.NC}", end="")
			if not self.checker.exists():
				print(f"\n{TC.B_RED}'make bonus' does not create the 'checker' executable{TC.NC}")
				self.failed["checker"] = ["checker not created by make bonus"]
			else:
				self.test_checker()
		print("\n")
		self.log.close()
		self.show_problems()
		return list(self.failed.keys())

	def test_no_args(self):
		self.start_category("no arguments")
		run = self.run(self.push_swap, [])
		ok = not run.problem() and run.out == "" and run.err == ""
		self.record("no arguments", ok, f"./push_swap\n    -> must display nothing (stdout: {run.out[:40]!r}, "
		            f"stderr: {run.err[:40]!r}) {run.problem() or ''}")

	def expect_error(self, category, binary, args, stdin="", severity=False, name="push_swap"):
		run = self.run(binary, args, stdin)
		cmd = cmd_str(name, args, stdin if stdin else None)
		if run.problem():
			self.record(category, severity, f"{cmd}\n    -> {run.problem()}")
		elif run.err != "Error\n":
			self.record(category, severity, f"{cmd}\n    -> expected 'Error\\n' on stderr, got {run.err[:60]!r}")
		elif run.out != "":
			self.record(category, severity, f"{cmd}\n    -> nothing should be printed on stdout, got {run.out[:60]!r}")
		else:
			self.record(category, True)

	def test_errors(self):
		self.start_category("errors")
		cases = [
		    ["1", "a", "3"], ["0", "one", "2", "3"], ["--adaptive", "0", "one", "2", "3"], ["--simple", "3", "2", "3"],
		    ["1", "2", "1"], ["5", "-3", "8", "-3"], ["0", "-0"], ["1", "+1"], ["2147483648"], ["-2147483649"],
		    ["1", "2147483648", "3"], ["1", "99999999999999999999"], ["4294967296"], ["-"], ["+"], ["1", "-", "2"],
		    ["12a"], ["1", "2", "+-4"], ["1", "--2"], ["1.5", "2"], ["--medium", "1", "1"], ["--complex", "x"],
		    ["--unknown", "3", "2", "1"],
		]
		for case in cases:
			self.expect_error("errors", self.push_swap, case)
		# Not explicitly in the subject, but usually asked during the evaluation
		for case in [["", "1"], [" "], ["1", "", "2"]]:
			self.expect_error("errors", self.push_swap, case, severity="warn")

	def test_parsing(self):
		self.start_category("valid arguments")
		cases = [
		    ["+5", "-3", "0"], ["2147483647", "-2147483648", "0"], ["-2147483648", "2147483647"], ["007", "8", "-01"],
		    ["42"], ["--adaptive", "3", "1", "2"], ["--simple", "-1"],
		]
		for case in cases:
			numbers = [int(x) for x in case if not x.startswith("--")]
			run = self.run(self.push_swap, case)
			ok, msg, _ = self.check_sort(case, numbers, run)
			self.record("valid arguments", ok, msg)

	def test_sorted(self):
		self.start_category("already sorted")
		cases = [["1"], ["1", "2"], ["1", "2", "3"], ["-5", "0", "5", "10", "99"], [str(i) for i in range(100)]]
		cases += [[strategy] + ["1", "2", "3", "4", "5"] for strategy in STRATEGIES]
		for case in cases:
			run = self.run(self.push_swap, case)
			cmd = cmd_str("push_swap", case if len(case) < 10 else case[:5] + ["..."])
			if run.problem():
				self.record("already sorted", False, f"{cmd}\n    -> {run.problem()}")
			elif run.out != "" or run.err != "":
				ops = run.out.count("\n")
				self.record("already sorted", False,
				            f"{cmd}\n    -> already sorted: must not display any operation (got {ops})")
			else:
				self.record("already sorted", True)

	def test_small(self):
		import itertools
		maxes = {}
		for size in [2, 3, 4, 5]:
			self.start_category(f"{size} numbers")
			worst = 0
			perms = list(itertools.permutations(range(size)))
			if size == 5 and not is_strict():
				perms = random.sample(perms, 40)
			for perm in perms:
				numbers = [x * 7 - 10 for x in perm]
				args = [str(x) for x in numbers]
				run = self.run(self.push_swap, args)
				ok, msg, n_ops = self.check_sort(args, numbers, run)
				self.record(f"{size} numbers", ok, msg)
				worst = max(worst, n_ops or 0)
			maxes[size] = worst
		print(f"\n{TC.CYAN}max operations: 3 numbers -> {maxes[3]}, 5 numbers -> {maxes[5]}{TC.NC}", end="")
		if maxes[3] > 3:
			self.warnings.append(f"3 numbers can be sorted with at most 3 operations (yours: {maxes[3]})")
		if maxes[5] > 12:
			self.warnings.append(f"5 numbers can be sorted with at most 12 operations (yours: {maxes[5]})")

	def test_strategies(self):
		"""Every selector must sort every valid input"""
		self.stats = {}
		sizes = [5, 20, 100, 500]
		repeat = 3 if not is_strict() else 10
		for strategy in STRATEGIES:
			self.start_category(strategy)
			for size in sizes:
				for _ in range(repeat if size < 500 else 1):
					numbers = random_numbers(size)
					args = [strategy] + [str(x) for x in numbers]
					run = self.run(self.push_swap, args, timeout=self.timeout * 3)
					ok, msg, n_ops = self.check_sort(args if size <= 20 else [strategy, f"<{size} random numbers>"],
					                                 numbers, run)
					if not ok and size > 20:
						msg += "\n    numbers: " + " ".join(str(x) for x in numbers)
					self.record(strategy, ok, msg)
					if ok:
						self.stats.setdefault((strategy, size), []).append(n_ops)

	def test_disorder_regimes(self):
		self.start_category("disorder regimes")
		self.regime_stats = {}
		regimes = [("low  (< 0.2)", 0.0001, 0.2), ("medium [0.2, 0.5[", 0.2, 0.5), ("high (>= 0.5)", 0.5, 1.0001)]
		for label, low, high in regimes:
			for strategy in STRATEGIES:
				numbers = numbers_with_disorder(100, low, high)
				if numbers is None:
					continue
				args = [strategy] + [str(x) for x in numbers]
				run = self.run(self.push_swap, args, timeout=self.timeout * 3)
				ok, msg, n_ops = self.check_sort([strategy, f"<100 numbers, disorder {disorder(numbers):.2f}>"],
				                                 numbers, run)
				if not ok:
					msg += "\n    numbers: " + " ".join(str(x) for x in numbers)
				self.record("disorder regimes", ok, msg)
				if ok:
					self.regime_stats[(label, strategy)] = n_ops
		self.show_strategy_table()

	def show_strategy_table(self):
		print(f"\n{TC.CYAN}Average number of operations per strategy (random numbers):{TC.NC}")
		header = f"  {'':<12}" + "".join(f"{s:>12}" for s in [5, 20, 100, 500]) + f"{'500/100':>10}  expected"
		print(TC.B_WHITE + header + TC.NC)
		expected = {"--simple": 25, "--medium": 11.2, "--complex": 6.7}
		for strategy in STRATEGIES:
			values = [self.stats.get((strategy, s)) for s in [5, 20, 100, 500]]
			avgs = [statistics.mean(v) if v else None for v in values]
			line = f"  {strategy:<12}" + "".join(f"{a:>12.0f}" if a is not None else f"{'-':>12}" for a in avgs)
			if avgs[2] and avgs[3]:
				line += f"{avgs[3] / avgs[2]:>10.1f}"
				if strategy in expected:
					line += f"  ~{expected[strategy]} for {STRATEGIES[strategy]}"
			print(line)
		print(f"{TC.CYAN}Operations for 100 numbers by disorder:{TC.NC}")
		print(TC.B_WHITE + f"  {'':<20}" + "".join(f"{s:>12}" for s in STRATEGIES) + TC.NC)
		for label in ["low  (< 0.2)", "medium [0.2, 0.5[", "high (>= 0.5)"]:
			print(f"  {label:<20}" + "".join(f"{str(self.regime_stats.get((label, s), '-')):>12}" for s in STRATEGIES))
		print(f"{TC.CYAN}(the growth ratio 500/100 gives an idea of the real complexity of each strategy){TC.NC}", end="")

	def test_bench(self):
		self.start_category("--bench")
		numbers = numbers_with_disorder(100, 0.2, 0.5) or random_numbers(100)
		args = [str(x) for x in numbers]
		expected_disorder = disorder(numbers) * 100

		normal = self.run(self.push_swap, args)
		ok, msg, _ = self.check_sort(["<100 numbers>"], numbers, normal)
		self.record("--bench", ok, msg)
		if normal.err != "":
			self.record("--bench", False, f"without --bench nothing must be printed on stderr (got {normal.err[:60]!r})")
		else:
			self.record("--bench", True)

		def bench_run(flags):
			return self.run(self.push_swap, flags + args), cmd_str("push_swap", flags + ["<100 numbers>"])

		run, cmd = bench_run(["--bench"])
		if run.problem() or run.err.startswith("Error"):
			self.record("--bench", False, f"{cmd}\n    -> {run.problem() or 'printed Error'}")
			return
		ops, error = self.parse_ops(run)
		if error:
			self.record("--bench", False, f"{cmd}\n    -> stdout must only contain the operations: {error}")
			return
		a, b = apply_operations(numbers, ops)
		self.record("--bench", is_sorted(a) and not b, f"{cmd}\n    -> the operations on stdout do not sort the stack")
		bench = run.err
		self.log.write(f"--bench output (stderr):\n{bench}\n")
		if not bench.strip():
			self.record("--bench", False, f"{cmd}\n    -> nothing printed on stderr")
			return
		# disorder with 2 decimals
		percents = [float(x) for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", bench.replace(",", "."))]
		two_dec = re.findall(r"\d+\.\d{2}\s*%", bench)
		good = any(abs(p - expected_disorder) <= 0.011 for p in percents)
		self.record("--bench", good and bool(two_dec),
		            f"{cmd}\n    -> the disorder must be displayed in % with two decimals: "
		            f"expected {expected_disorder:.2f}%, found {', '.join(str(p) + '%' for p in percents) or 'nothing'}")
		# total operations
		numbers_in_bench = [int(x) for x in re.findall(r"\b\d+\b", bench)]
		self.record("--bench", len(ops) in numbers_in_bench,
		            f"{cmd}\n    -> the total number of operations ({len(ops)}) is not in the bench output")
		# count of each operation
		counts = {op: ops.count(op) for op in OPERATIONS}
		missing, wrong = [], []
		for op in OPERATIONS:
			after = re.search(rf"(?<![a-z]){op}(?![a-z])\s*[:=]?\s*(\d+)", bench)
			before = re.search(rf"(\d+)\s*[:=x]?\s*(?<![a-z]){op}(?![a-z])", bench)
			if not after and not before:
				missing.append(op)
			elif not ((after and int(after.group(1)) == counts[op]) or (before and int(before.group(1)) == counts[op])):
				wrong.append(f"{op}={counts[op]}")
		self.record("--bench", not missing, f"{cmd}\n    -> count of these operations not found: {', '.join(missing)}")
		self.record("--bench", not wrong, f"{cmd}\n    -> wrong count for: {', '.join(wrong)}")
		# strategy + complexity
		has_strategy = re.search(r"adaptive|simple|medium|complex", bench, re.IGNORECASE)
		has_class = re.search(r"O\s*\(|log|n\^?2|n²|√|sqrt", bench, re.IGNORECASE)
		self.record("--bench", bool(has_strategy and has_class),
		            f"{cmd}\n    -> the name of the strategy and its complexity class must be displayed")
		# with a selector (the order of the flags is not specified, so one of the orders must work)
		results = []
		for flags in (["--bench", "--complex"], ["--complex", "--bench"]):
			r, c = bench_run(flags)
			ops2, error = self.parse_ops(r)
			sorted_ok = not r.problem() and not error and r.err.strip() and not r.err.startswith("Error")
			if sorted_ok:
				a, b = apply_operations(numbers, ops2)
				sorted_ok = is_sorted(a) and not b
			results.append(bool(sorted_ok) and bool(re.search(r"complex", r.err, re.IGNORECASE)))
		self.record("--bench", any(results),
		            "./push_swap --bench --complex <numbers> (or --complex --bench)\n"
		            "    -> does not work / does not show the 'complex' strategy")

	def test_leaks(self):
		if not self.valgrind and not self.mac_leaks:
			return
		self.start_category("leaks")
		cases = [[], ["3", "2", "1"], ["1", "2", "3"], ["1", "a"], ["1", "2", "1"], ["2147483648"],
		         ["--bench", "5", "1", "4", "2", "3"]]
		cases += [[s] + [str(x) for x in random_numbers(50)] for s in STRATEGIES]
		for case in cases:
			leak = self.leaks(self.push_swap, case)
			shown = case if len(case) < 10 else case[:1] + ["<50 numbers>"]
			self.record("leaks", leak is None, f"{cmd_str('push_swap', shown)}\n    -> {leak}")

	def test_performance(self):
		repeats = {100: 100 if is_strict() else 20, 500: 50 if is_strict() else 8}
		for size, excellent, good, passing in BENCHMARKS:
			category = f"{size} numbers perf"
			self.start_category(category)
			results = []
			for _ in range(repeats[size]):
				numbers = random_numbers(size)
				args = [str(x) for x in numbers]
				run = self.run(self.push_swap, args, timeout=self.timeout * 3)
				ok, msg, n_ops = self.check_sort([f"<{size} random numbers>"], numbers, run)
				if not ok:
					self.record(category, False, msg + "\n    numbers: " + " ".join(args))
					continue
				results.append(n_ops)
				if n_ops >= passing:
					self.record(category, False, f"{n_ops} operations for {size} numbers (must be < {passing})\n"
					            f"    numbers: {' '.join(args)}")
				else:
					self.record(category, True)
			if results:
				worst = max(results)
				grade = (f"{TC.B_GREEN}excellent (< {excellent})" if worst < excellent else
				         f"{TC.GREEN}good (< {good})" if worst < good else
				         f"{TC.YELLOW}pass (< {passing})" if worst < passing else f"{TC.B_RED}KO (>= {passing})")
				print(f"\n{TC.CYAN}  min: {min(results)}  avg: {statistics.mean(results):.0f}  max: {worst}  "
				      f"-> {grade}{TC.NC}", end="")

	# ---------------------------------------------------------------- checker (bonus)

	def checker_expect(self, category, args, stdin, expected, severity=False):
		run = self.run(self.checker, args, stdin)
		cmd = cmd_str("checker", args if len(args) < 10 else [f"<{len(args)} numbers>"], stdin)
		if run.problem():
			self.record(category, severity, f"{cmd}\n    -> {run.problem()}")
		elif run.out != expected:
			self.record(category, severity, f"{cmd}\n    -> expected {expected!r} on stdout, got {run.out[:40]!r}"
			            + (f" (stderr: {run.err[:40]!r})" if run.err else ""))
		else:
			self.record(category, True)

	def test_checker(self):
		self.start_category("checker no args")
		run = self.run(self.checker, [], "")
		self.record("checker no args", not run.problem() and run.out == "" and run.err == "",
		            f"./checker\n    -> must display nothing (stdout: {run.out[:30]!r}, stderr: {run.err[:30]!r})")

		self.start_category("checker OK/KO")
		# the two examples of the subject
		self.checker_expect("checker OK/KO", ["3", "2", "1", "0"], "rra\npb\nsa\nrra\npa\n", "OK\n")
		self.checker_expect("checker OK/KO", ["3", "2", "1", "0"], "sa\nrra\npb\n", "KO\n")
		cases = [
		    (["1", "2", "3"], []), (["2", "1", "3"], []), (["2", "1", "3"], ["sa"]), (["1", "2", "3"], ["pb"]),
		    (["1", "2", "3"], ["pb", "pb", "pa"]), (["1", "2", "3"], ["pb", "pb", "ss", "rr", "rrr", "pa", "pa"]),
		    (["1", "2", "3"], ["pb", "pb", "ss", "pa", "pa"]), (["1"], ["sa", "ra", "rra", "pb", "pa"]),
		    (["1", "2"], ["pa", "sb", "rb", "rrb"]), (["3", "1", "2"], ["rra", "rra", "rra", "ra"]),
		    (["5", "4", "3", "2", "1"], ["pb", "pb", "ss", "rrr", "rr", "sa", "pa", "pa"]),
		]
		for args, ops in cases:
			a, b = apply_operations([int(x) for x in args], ops)
			expected = "OK\n" if is_sorted(a) and not b else "KO\n"
			self.checker_expect("checker OK/KO", args, "".join(op + "\n" for op in ops), expected)
		for size in [5, 100, 500]:
			numbers = random_numbers(size)
			args = [str(x) for x in numbers]
			ops = simple_sort_ops(numbers)
			self.checker_expect("checker OK/KO", args, "\n".join(ops) + "\n", "OK\n")
			# remove one operation -> not sorted
			broken = list(ops)
			del broken[random.randrange(len(broken))]
			a, b = apply_operations(numbers, broken)
			expected = "OK\n" if is_sorted(a) and not b else "KO\n"
			self.checker_expect("checker OK/KO", args, "\n".join(broken) + "\n", expected)
		# push_swap | checker
		for size in [3, 100, 500]:
			numbers = random_numbers(size)
			args = [str(x) for x in numbers]
			ps = self.run(self.push_swap, args, timeout=self.timeout * 3)
			if not ps.problem():
				self.checker_expect("checker OK/KO", args, ps.out, "OK\n")

		self.start_category("checker errors")
		for args in [["3", "2", "one", "0"], ["", "1"], ["1", "2", "1"], ["2147483648"], ["-2147483649"], ["1", "a"],
		             ["1", "--2"]]:
			self.expect_error("checker errors", self.checker, args, "", name="checker")
		for stdin in ["sx\n", "sa \n", " sa\n", "SA\n", "sa\nrra\nfoo\n", "pb\n\npa\n", "ra\nrrrr\n"]:
			self.expect_error("checker errors", self.checker, ["3", "2", "1"], stdin, name="checker")

		if self.valgrind or self.mac_leaks:
			self.start_category("checker leaks")
			numbers = random_numbers(50)
			ops = "\n".join(simple_sort_ops(numbers)) + "\n"
			for args, stdin in [([], ""), (["3", "2", "1"], "sa\nrra\n"), (["3", "2", "1"], "sa\nra\n"),
			                    (["1", "a"], ""), (["3", "2", "1"], "sa\nfoo\n"), ([str(x) for x in numbers], ops)]:
				leak = self.leaks(self.checker, args, stdin)
				shown = args if len(args) < 10 else ["<50 numbers>"]
				self.record("checker leaks", leak is None, f"{cmd_str('checker', shown, stdin)}\n    -> {leak}")

	# ---------------------------------------------------------------- report

	def show_problems(self):
		for warning in self.warnings:
			print(f"{TC.YELLOW}⚠ {warning}{TC.NC}")
		if self.warnings:
			print()
		if not self.failed:
			return
		print(f"{TC.B_RED}Errors found{TC.NC}:")
		shown = 0
		for category, messages in self.failed.items():
			print(f"{TC.B_PURPLE}{category}{TC.NC}:")
			for message in messages[:3]:
				first, *rest = message.split("\n")
				print(f"  {TC.B_WHITE}{first}{TC.NC}")
				for line in rest:
					if len(line) > 200:
						line = line[:200] + "..."
					print(f"  {TC.YELLOW}{line}{TC.NC}")
			if len(messages) > 3:
				print(f"  {TC.YELLOW}... and {len(messages) - 3} more{TC.NC}")
			shown += 1
		print(f"\nFull report: {TC.PURPLE}{(self.temp_dir / 'errors.log').resolve()}{TC.NC}\n")
