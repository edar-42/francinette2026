import logging
import os
from pathlib import Path

from halo import Halo

from testers.AutoTester import PushSwapAutoTester
from testers.BaseTester import BaseTester, run_command
from testers.push_swap.Fsoares import Fsoares
from utils import SubjectChecks as sc
from utils.ExecutionContext import TestRunInfo, has_bonus
from utils.TerminalColors import TC
from utils.Utils import is_makefile_project

logger = logging.getLogger("push_swap")


class PushSwap(BaseTester):
	"""push_swap subject (version 1.2): 4 strategies, --bench mode, disorder metric and the checker bonus"""

	name = "push_swap"
	my_tester = Fsoares
	testers = [Fsoares, PushSwapAutoTester]
	timeout = 10

	allowed_functions = {"read", "write", "malloc", "free", "exit"}

	def __init__(self, info: TestRunInfo) -> None:
		super().__init__(info)
		self.execute_testers()

	@staticmethod
	def is_project(current_path):
		return is_makefile_project(current_path, "push_swap", PushSwap)

	def compile_source(self):
		"""'make bonus' usually only creates the checker, so 'make all' must also be called"""
		os.chdir(self.temp_dir)
		if not Path(self.temp_dir, "Makefile").exists():
			return
		commands = ["make fclean", "make all"] + (["make bonus"] if has_bonus() else [])
		for command in commands:
			logger.info(f"Calling '{command}' on directory {os.getcwd()}")
			text = f"{TC.CYAN}Executing: {TC.B_WHITE}{command}{TC.NC}"
			with Halo(text=text) as spinner:
				run_command(command, spinner)
				spinner.succeed()

	def subject_checks(self):
		sc.header("push_swap v1.2")
		errors = sc.check_readme(
		    self.source_dir,
		    min_logins=2,
		    extra_hint=("The README must also explain the selected algorithms, the contributions of both learners, "
		                "and for the adaptive strategy: the rationale of the thresholds, the techniques used in each "
		                "regime and a complexity argument"))
		work = self.subject_work_dir()
		has_bonus = bool(self.has_bonus())
		errors += sc.check_makefile_content(work, has_bonus)

		print(f"{TC.B_CYAN}Compilation{TC.NC}")
		errors += sc.check_relink(work, "push_swap", "", "")
		binary = work / "push_swap"
		if binary.exists():
			errors += sc.check_functions([binary], self.allowed_functions, "(push_swap)")
		if has_bonus:
			errors += sc.check_relink(work, "checker", "bonus", "bonus")
			checker = work / "checker"
			if checker.exists():
				errors += sc.check_functions([checker], self.allowed_functions, "(checker)")
		errors += sc.check_no_globals(sc.find_objects(work))
		names = ["push_swap"] + (["checker"] if has_bonus else [])
		errors += sc.check_clean_rules(work, names)
		return errors
