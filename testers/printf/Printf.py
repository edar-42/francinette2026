import logging
from pathlib import Path

from testers.BaseTester import BaseTester
from testers.printf.Cacharle import Cacharle
from testers.printf.Fsoares import Fsoares
from testers.printf.Tripouille import Tripouille
from testers.printf.UnitTest import UnitTest
from utils.ExecutionContext import TestRunInfo
from utils.TerminalColors import TC
from utils.Utils import is_makefile_project
from utils import SubjectChecks as sc

logger = logging.getLogger('printf')


class Printf(BaseTester):

	name = "printf"
	my_tester = Fsoares
	testers = [Tripouille, UnitTest, Cacharle, Fsoares]
	timeout = 2

	def __init__(self, info: TestRunInfo) -> None:
		super().__init__(info)
		self.execute_testers()
		pass

	@staticmethod
	def is_project(current_path):
		return is_makefile_project(current_path, "libftprintf.a", Printf)

	# ft_printf subject (version 12.1)
	allowed_functions = {"malloc", "free", "write"}  # va_start, va_arg, va_copy, va_end are macros/builtins

	def subject_checks(self):
		sc.header("ft_printf v12.1")
		errors = sc.check_readme(self.source_dir,
		                         extra_hint="The README must also explain and justify the chosen algorithm and data structure")
		work = self.subject_work_dir()
		has_bonus = bool(self.has_bonus())
		errors += sc.check_makefile_content(work, has_bonus)

		headers = list(work.glob("ft_printf.h")) + list(work.glob("*/ft_printf.h"))
		if not headers:
			sc._ko("header 'ft_printf.h' not found (must be at the root or in a sub folder)")
			errors.append("ft_printf.h")
		if Path(work, "libft").is_dir() and not Path(work, "libft", "Makefile").exists():
			sc._ko("the libft folder must contain its Makefile")
			errors.append("libft Makefile")

		print(f"{TC.B_CYAN}Compilation{TC.NC}")
		lib = work / "libftprintf.a"
		errors += sc.check_relink(work, "libftprintf.a", "", "")
		if lib.exists():
			errors += sc.check_functions([lib], self.allowed_functions, "(mandatory)")
		if has_bonus:
			errors += sc.check_relink(work, "libftprintf.a", "bonus", "bonus")
			if lib.exists():
				errors += sc.check_functions([lib], self.allowed_functions, "(bonus)")
		errors += sc.check_clean_rules(work, ["libftprintf.a"])
		return errors
