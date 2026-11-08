import logging
import re
from pathlib import Path
from testers.BaseTester import BaseTester
from testers.get_next_line.Fsoares import Fsoares

from testers.get_next_line.Tripouille import Tripouille
from utils.ExecutionContext import TestRunInfo, has_bonus, is_strict, set_bonus
from utils.Utils import show_banner
from utils.TerminalColors import TC
from utils import SubjectChecks as sc

logger = logging.getLogger("gnl")


class GetNextLine(BaseTester):

	name = "get_next_line"
	my_tester = Fsoares
	testers = [Tripouille, Fsoares]
	timeout = 10

	def __init__(self, info: TestRunInfo) -> None:
		super().__init__(info)
		if (info.source_dir / "get_next_line_bonus.c").exists() \
				and not info.args.mandatory:
			logger.info("Has bonus")
			set_bonus(True)
		self.execute_testers()

	@staticmethod
	def is_project(current_path):
		file_path = current_path / 'get_next_line.c'
		logger.info(f"Testing: {file_path}")
		if not file_path.exists():
			return False
		return GetNextLine


	# get_next_line subject (version 14.3)
	allowed_functions = {"read", "malloc", "free"}
	mandatory_files = ["get_next_line.c", "get_next_line_utils.c", "get_next_line.h"]
	bonus_files = ["get_next_line_bonus.c", "get_next_line_utils_bonus.c", "get_next_line_bonus.h"]

	def subject_checks(self):
		sc.header("get_next_line v14.3")
		errors = sc.check_readme(self.source_dir,
		                         extra_hint="The README must also explain and justify the chosen algorithm")
		work = self.subject_work_dir()
		bonus = has_bonus()

		print(f"{TC.B_CYAN}Files{TC.NC}")
		to_check = self.mandatory_files + (self.bonus_files if bonus else [])
		missing = [f for f in to_check if not Path(work, f).exists()]
		if missing:
			sc._ko(f"missing files at the root of the repository: {', '.join(missing)}")
			errors.append("turn in files")
		else:
			sc._ok(f"{', '.join(to_check)} at the root")
		uses_libft = []
		for file in to_check:
			path = Path(work, file)
			if path.exists():
				with open(path, errors="replace") as f:
					if re.search(r'#\s*include\s*[<"][^>"]*libft\.h[>"]', f.read()):
						uses_libft.append(file)
		if uses_libft:
			sc._ko(f"the libft is forbidden in this project (included in {', '.join(uses_libft)})")
			errors.append("libft used")

		print(f"{TC.B_CYAN}Compilation{TC.NC} (cc -Wall -Wextra -Werror)")
		parts = [("mandatory", self.mandatory_files[:2])]
		if bonus:
			parts.append(("bonus", self.bonus_files[:2]))
		for label, files in parts:
			if any(not Path(work, f).exists() for f in files):
				continue
			ok, _, out = sc.compile_objects(work, files, "-Wall -Wextra -Werror", work / f"__obj_nobs_{label}")
			if not ok:
				sc._ko(f"{label}: does not compile without '-D BUFFER_SIZE' (the subject requires it):")
				print(TC.YELLOW + "\n".join(out.splitlines()[:10]) + TC.NC)
				errors.append(f"compile without BUFFER_SIZE ({label})")
			else:
				sc._ok(f"{label}: compiles without -D BUFFER_SIZE")
			ok, objects, out = sc.compile_objects(work, files, "-Wall -Wextra -Werror -D BUFFER_SIZE=42",
			                                      work / f"__obj_{label}")
			if not ok:
				sc._ko(f"{label}: does not compile with -D BUFFER_SIZE=42:")
				print(TC.YELLOW + "\n".join(out.splitlines()[:10]) + TC.NC)
				errors.append(f"compilation ({label})")
				continue
			errors += sc.check_functions(objects, self.allowed_functions, f"({label})")
			errors += sc.check_no_globals(objects, f"({label})")
			if label == "bonus":
				count = sc.count_static_variables(objects)
				if count is not None and count > 1:
					sc._ko(f"bonus: only one static variable is allowed (found {count})")
					errors.append("more than one static")
				elif count is not None:
					sc._ok(f"bonus: {count} static variable")
		return errors
