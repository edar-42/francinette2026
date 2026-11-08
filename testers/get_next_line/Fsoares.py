import logging
import os
import re
from typing import Set

from testers.BaseExecutor import BaseExecutor
from utils.ExecutionContext import has_bonus, is_strict
from utils.TerminalColors import TC
from utils.Utils import show_errors_file
from utils.SubjectChecks import compile_objects, count_static_variables

logger = logging.getLogger("gnl-fsoares")

buffer_size_regex = re.compile(r"BUFFER_SIZE: (\d+)")


class Fsoares(BaseExecutor):

	name = 'fsoares'
	folder = 'fsoares'
	git_url = 'my own tests'
	line_regex = re.compile(r"^([^:]+):(.+)$")
	test_regex = re.compile(r"(\d+)(?:[^ ]+)?\.([^ ]+)")

	def __init__(self, tests_dir, temp_dir, to_execute, missing) -> None:
		super().__init__(tests_dir, temp_dir, to_execute, missing)
		# macOS: suppress inconsequential but intrusive
		# debug messages printed by Apple's libmalloc
		os.environ['MallocNanoZone'] = '0'

	def execute(self):
		bonus_tests = ["open, close, open", "2 file descriptors", "multiple fds", "test limit fds"]

		def validate_one_static():
			project_dir = (self.temp_dir / "..").resolve()
			files = ["get_next_line_bonus.c", "get_next_line_utils_bonus.c"]
			# count with nm on the compiled objects (static functions and prototypes are not counted)
			ok, objects, _ = compile_objects(project_dir, files, "-D BUFFER_SIZE=42", self.temp_dir / "__static_obj")
			static_count = count_static_variables(objects) if ok else None
			if static_count is None:
				static_regex = re.compile(r"^\s*static\s+(?!.*\()[^;]*;")
				static_count = 0
				for file in files:
					with open(project_dir / file) as gnl:
						static_count += len([l for l in gnl.readlines() if static_regex.match(l)])
			if (static_count > 1):
				print(f"{TC.RED}You have more than one {TC.B_BLUE}static{TC.RED} variable ({static_count}){TC.NC}")
				return False
			return True

		def show_errors(errors: Set):
			if errors:
				show_errors_file(self.temp_dir, "error_color.log", "errors.log")

			self.show_test_files(errors, bonus_tests, "tester.c", "bonus.c")
			if has_bonus() and self.exec_bonus:
				if not validate_one_static():
					errors.add("more than one static")
			if not is_strict() and not errors:
				print(f"Want some more thorough tests? run '{TC.B_WHITE}francinette --strict{TC.NC}'.")
			return errors

		def run_part(part, execute, silent=False):
			if not execute:
				return []
			output = self.call_make_command(part, execute, silent)
			errors = list(self.check_errors(output))
			# a test program that does not compile or crashes is ignored by make ('-@'): report it
			problems = re.findall(r"make: \[[^\]]*\] Error (\d+) \(ignored\)", output)
			if problems:
				print(f"{TC.B_RED}{len(problems)} {part} test program(s) did not compile or crashed{TC.NC}")
				errors.append(f"{part} compilation/crash")
			return errors

		errors = run_part("mandatory", self.exec_mandatory)
		logger.info(f"errors: {errors}")
		bonus_errors = set(errors).union(run_part("bonus", self.exec_bonus, True))
		bonus_errors = show_errors(bonus_errors)
		return [self.name] if bonus_errors else []
