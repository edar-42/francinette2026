"""
Runs the single-file bash testers of https://github.com/Elwynn18/42-auto-tester.

The scripts are copied as they are in tests/<project>/auto-tester (see bin/sync_auto_tester.sh to update them).
They must be executed from the project folder, and they also check the turn in files, so they get their own clean
copy of the sources: the temp folder is already full of objects and of the files of the other testers.
"""

import logging
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from testers.BaseExecutor import BaseExecutor
from utils.ExecutionContext import get_context
from utils.TerminalColors import TC
from utils.Utils import remove_ansi_colors

logger = logging.getLogger("auto-tester")

result_regex = re.compile(r"^Result:\s+(\d+) OK,\s+(\d+) KO", re.MULTILINE)
ko_function_regex = re.compile(r"^\s*ft_(\w+)\s+KO\s*$", re.MULTILINE)
not_done_function_regex = re.compile(r"^\s*ft_(\w+)\s+--", re.MULTILINE)


class AutoTester(BaseExecutor):

	name = "42-auto-tester"
	folder = "auto-tester"
	git_url = "https://github.com/Elwynn18/42-auto-tester"
	script = None

	def script_args(self):
		"""The arguments for the script, or None if the selected tests can't be executed by it"""
		args = get_context().args
		if get_context().ex_to_execute:
			return list(get_context().ex_to_execute)
		if args.mandatory != args.bonus:
			return self.part_args(args.bonus)
		return []

	def part_args(self, bonus):
		"""The arguments that select only the mandatory or only the bonus part"""
		return []

	def clean_copy(self):
		"""
		A copy of the sources without .git and without the files ignored by git (the same that is turned in).
		Symlinks are followed: the script runs make, and that must never touch something outside of the copy.
		"""
		source = get_context().source_dir
		project = Path(self.temp_dir, "__project")
		shutil.copytree(source, project, ignore=shutil.ignore_patterns(".git"), ignore_dangling_symlinks=True)
		# Only asks git about the original: 'git clean' could also delete files there (core.worktree, GIT_DIR, ...)
		ignored = subprocess.run(["git", "ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
		                         cwd=source, capture_output=True, text=True, errors="surrogateescape")
		if ignored.returncode == 0:
			for file in filter(None, ignored.stdout.split("\0")):
				Path(project, file).unlink(missing_ok=True)
		return project

	def execute(self):
		script_args = self.script_args()
		if script_args is None:
			print(f"{TC.YELLOW}{self.name} can't select these tests, so it was not executed{TC.NC}\n")
			return []

		os.chdir(self.clean_copy())
		command = " ".join(shlex.quote(str(arg)) for arg in ["bash", self.tests_dir / self.script, *script_args])
		output = remove_ansi_colors(self.run_tests(command))
		print()

		# The last one: the first ones can be something printed by the code that is being tested
		results = result_regex.findall(output)
		counts = tuple(map(int, results[-1])) if results else None
		logger.info(f"{self.name} result (OK, KO): {counts}")
		return self.errors(output, counts)

	def errors(self, output, counts):
		"""
		What is shown as failed in the summary. counts is (OK, KO), or None if the script did not reach the end.
		Not reaching the end, or not having tested anything, can't be reported as a success
		"""
		return self.result(counts is None or counts[0] == 0 or counts[1] > 0)


class LibftAutoTester(AutoTester):

	script = "test_libft.sh"

	def part_args(self, bonus):
		# Without arguments the script would test everything, not "nothing"
		return list(self.to_execute) or None

	def errors(self, output, counts):
		# The summary of libft works by function: the others would be listed in "Passed tests"
		if counts is None:
			return [*self.to_execute, self.name]
		ko = ko_function_regex.findall(output)
		not_done = [func for func in not_done_function_regex.findall(output) if func in self.to_execute]
		other_errors = counts[0] == 0 or counts[1] > len(ko)
		return ko + not_done + ([self.name] if other_errors else [])


class GnlAutoTester(AutoTester):

	script = "test_gnl.sh"

	def script_args(self):
		# The only filter of this script are the BUFFER_SIZEs. It always tests the bonus if the files are present
		exercises = get_context().ex_to_execute or []
		if any(not re.fullmatch(r"[1-9]\d*", exercise) for exercise in exercises):
			return None
		return list(exercises)


class PrintfAutoTester(AutoTester):

	script = "test_ft_printf.sh"

	def part_args(self, bonus):
		return ["bonus" if bonus else "mandatory"]


class PushSwapAutoTester(AutoTester):

	script = "test_push_swap.sh"

	def part_args(self, bonus):
		if bonus:
			return ["bonus"]
		return ["makefile", "submission", "errors", "sort", "perf", "bench"]
