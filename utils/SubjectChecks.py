"""
Checks that come directly from the (new) subjects and that are common to several projects:

- README.md requirements (present in every subject since 2025)
- Makefile requirements (rules, flags, cc, no relink, clean/fclean really clean)
- Allowed external functions (checked with `nm` on the compiled objects)
- Global variables forbidden (checked with `nm` on the compiled objects)

Every check returns a list of "failed test names" that are added to the final summary,
exactly like the names returned by the testers.
"""

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Set

from utils.TerminalColors import TC
from utils.Utils import is_mac

logger = logging.getLogger("subject")

README_FIRST_LINE = re.compile(
    r"^\s*(\*\*\*|\*|_)\s*This project has been created as part of the 42 curriculum by\s+(.+?)\.?\s*(\*\*\*|\*|_)\s*$")

# Symbols that the compiler / libc runtime add by themselves. They are never a problem.
RUNTIME_SYMBOLS = {
    "__libc_start_main", "__cxa_finalize", "__gmon_start__", "_ITM_deregisterTMCloneTable",
    "_ITM_registerTMCloneTable", "_Jv_RegisterClasses", "__stack_chk_fail", "__stack_chk_guard",
    "_GLOBAL_OFFSET_TABLE_", "dyld_stub_binder", "__dso_handle", "_DYNAMIC", "__TMC_END__",
    "__fprintf_chk", "__printf_chk",
}
# Symbols that the compiler can insert on its own (struct copy / initialisation), but that
# can also be called directly by the student: only a warning.
COMPILER_MAYBE = {"memset", "memcpy", "memmove", "bzero"}

# Prefixes of symbols added by sanitizers / profilers
RUNTIME_PREFIXES = ("__asan", "__ubsan", "__sanitizer", "__lsan", "__tsan", "__msan", "_ZN", "__cxa_", "__gxx_")


def _ok(msg):
	print(f"{TC.GREEN}  ✔ {msg}{TC.NC}")


def _ko(msg):
	print(f"{TC.B_RED}  ✖ {msg}{TC.NC}")


def _warn(msg):
	print(f"{TC.YELLOW}  ⚠ {msg}{TC.NC}")


def _run(command, cwd, timeout=180):
	logger.info(f"running {command} on {cwd}")
	try:
		p = subprocess.run(command, cwd=cwd, shell=isinstance(command, str), capture_output=True, text=True,
		                   timeout=timeout, errors="backslashreplace")
		logger.info(p)
		return p
	except subprocess.TimeoutExpired as ex:
		logger.exception(ex)
		return subprocess.CompletedProcess(command, 124, "", "timeout")


def _clean_symbol(name: str) -> str:
	name = name.split("@")[0]
	if is_mac() and name.startswith("_"):
		name = name[1:]
	return name


# --------------------------------------------------------------------------- README


def check_readme(source_dir: Path, min_logins=1, extra_hint=None) -> List[str]:
	"""Checks the 'Readme Requirements' chapter that is common to all the new subjects"""
	print(f"{TC.B_CYAN}README.md{TC.NC}")
	readme = Path(source_dir, "README.md")
	if not readme.exists():
		_ko("README.md not found at the root of the repository")
		return ["README.md"]

	with open(readme, encoding="utf-8", errors="replace") as f:
		lines = f.read().splitlines()

	errors = False
	first = lines[0] if lines else ""
	match = README_FIRST_LINE.match(first)
	if not match:
		_ko("The very first line must be in italic and read: "
		    "'This project has been created as part of the 42 curriculum by <login1>[, <login2>...]'")
		print(f"    found: {TC.B_WHITE}{first[:100]!r}{TC.NC}")
		errors = True
	else:
		logins = [l.strip() for l in re.split(r",|\band\b|&", match.group(2)) if l.strip()]
		if len(logins) < min_logins:
			_ko(f"The first line must contain the logins of the {min_logins} learners (found: {', '.join(logins)})")
			errors = True
		else:
			_ok(f"first line in italic (logins: {', '.join(logins)})")

	headings = [l.strip("# ").strip().lower() for l in lines if re.match(r"^\s*#{1,6}\s+\S", l)]
	for section in ["Description", "Instructions", "Resources"]:
		if any(section.lower() in h for h in headings):
			_ok(f"'{section}' section")
		else:
			_ko(f"missing a '{section}' section (markdown title like '## {section}')")
			errors = True

	text = "\n".join(lines).lower()
	if not re.search(r"(?<!['’])\b(ai|ia|chatgpt|claude|copilot|llm|intelligence artificielle|artificial intelligence)\b", text):
		_warn("The 'Resources' section must describe how AI was used (for which tasks / parts). Nothing found.")
	if extra_hint:
		_warn(extra_hint)
	return ["README.md"] if errors else []


# --------------------------------------------------------------------------- Makefile


def _makefile_text(path: Path) -> str:
	with open(path, encoding="utf-8", errors="replace") as f:
		return f.read()


def _has_rule(text: str, rule: str) -> bool:
	return re.search(rf"^\s*{re.escape(rule)}\s*:(?!=)", text, re.MULTILINE) is not None


def check_makefile_content(work_dir: Path, has_bonus: bool) -> List[str]:
	print(f"{TC.B_CYAN}Makefile{TC.NC}")
	makefile = Path(work_dir, "Makefile")
	text = _makefile_text(makefile)
	errors = False

	missing = [rule for rule in ["$(NAME)", "all", "clean", "fclean", "re"] if not _has_rule(text, rule)]
	if "$(NAME)" in missing and (_has_rule(text, "${NAME}")):
		missing.remove("$(NAME)")
	if has_bonus and not _has_rule(text, "bonus"):
		missing.append("bonus")
	if missing:
		_ko(f"missing rules: {', '.join(missing)}")
		errors = True
	else:
		_ok("rules $(NAME), all, clean, fclean, re" + (", bonus" if has_bonus else ""))

	flags = [flag for flag in ["-Wall", "-Wextra", "-Werror"] if not re.search(rf"{flag}\b", text)]
	if flags:
		_ko(f"missing compilation flags: {', '.join(flags)}")
		errors = True
	else:
		_ok("flags -Wall -Wextra -Werror")

	cc = re.search(r"^\s*CC\s*:?=\s*(\S+)", text, re.MULTILINE)
	if cc and cc.group(1) not in ("cc", "$(CC)"):
		_warn(f"the subject asks to compile with 'cc' (found CC = {cc.group(1)})")
	if re.search(r"\blibtool\b", text):
		_ko("'libtool' is forbidden (use 'ar')")
		errors = True
	return ["Makefile"] if errors else []


def _snapshot(work_dir: Path):
	result = {}
	for root, dirs, files in os.walk(work_dir):
		dirs[:] = [d for d in dirs if d != ".git"]
		for file in files:
			path = Path(root, file)
			try:
				result[str(path)] = path.stat().st_mtime_ns
			except FileNotFoundError:
				pass
	return result


def _changed(before, after):
	return sorted(set(k for k in after if before.get(k) != after[k]))


def check_relink(work_dir: Path, name: str, rule: str, label: str) -> List[str]:
	"""Calls `make <rule>` twice: the second call must not rebuild anything"""
	shown = f"make {rule}".strip()
	first = _run(f"make {rule}", work_dir)
	if first.returncode != 0:
		_ko(f"'{shown}' failed:")
		print(TC.YELLOW + "\n".join((first.stdout + first.stderr).splitlines()[-15:]) + TC.NC)
		return [shown]
	if not Path(work_dir, name).exists():
		_ko(f"'{shown}' does not create '{name}'")
		return [shown]
	before = _snapshot(work_dir)
	_run("sleep 1.1", work_dir)
	second = _run(f"make {rule}", work_dir)
	changed = [str(Path(c).relative_to(work_dir)) for c in _changed(before, _snapshot(work_dir))]
	if second.returncode != 0 or changed:
		_ko(f"'{shown}' relinks (2nd call rebuilt: {', '.join(changed[:5]) or 'error'})")
		return [f"relink {label}".strip()]
	_ok(f"'{shown}' does not relink")
	return []


def check_clean_rules(work_dir: Path, names: List[str]) -> List[str]:
	errors = []

	def objects():
		return [str(p.relative_to(work_dir)) for p in Path(work_dir).rglob("*.o")]

	_run("make clean", work_dir)
	if objects():
		_ko(f"'make clean' leaves object files: {', '.join(objects()[:5])}")
		errors.append("make clean")
	else:
		_ok("'make clean' removes the object files")
	_run("make fclean", work_dir)
	left = [n for n in names if Path(work_dir, n).exists()]
	if left:
		_ko(f"'make fclean' leaves: {', '.join(left)}")
		errors.append("make fclean")
	else:
		_ok(f"'make fclean' removes {', '.join(names)}")
	re_run = _run("make re", work_dir)
	if re_run.returncode != 0 or not Path(work_dir, names[0]).exists():
		_ko("'make re' does not work")
		errors.append("make re")
	else:
		_ok("'make re' works")
	return errors


# --------------------------------------------------------------------------- nm based checks


def _nm(files: Iterable[Path]):
	"""returns (defined, undefined, globals_data, local_data) symbols of the given objects/archives/binaries"""
	defined, undefined, global_data, local_data = set(), set(), set(), set()
	for file in files:
		p = _run(["nm", str(file)], file.parent)
		for line in p.stdout.splitlines():
			parts = line.split()
			if len(parts) == 2 and parts[0] in ("U", "w", "v"):
				undefined.add(_clean_symbol(parts[1]))
			elif len(parts) >= 3:
				kind, sym = parts[1], _clean_symbol(parts[2])
				defined.add(sym)
				if sym.startswith((".L", "L", "l_", "ltmp", "__", "_ZTV", "_ZTI")):
					continue
				if kind in ("B", "D", "C", "S", "G", "R", "V"):
					global_data.add(sym)
				elif kind in ("b", "d", "s", "g"):
					local_data.add(sym)
	return defined, undefined, global_data, local_data


def check_functions(files: List[Path], allowed: Set[str], label="") -> List[str]:
	"""Checks that only the allowed external functions are used"""
	if not shutil.which("nm"):
		_warn("'nm' not found, not checking the external functions")
		return []
	defined, undefined, _, _ = _nm(files)
	external = {
	    s for s in undefined - defined
	    if s not in RUNTIME_SYMBOLS and not s.startswith(RUNTIME_PREFIXES) and s not in allowed
	}
	maybe = external & COMPILER_MAYBE
	forbidden = sorted(external - COMPILER_MAYBE)
	if maybe:
		_warn(f"{', '.join(sorted(maybe))} used {label}. Can be added by the compiler (struct copy/init), "
		      "but if you call it yourself it is forbidden")
	if forbidden:
		_ko(f"forbidden functions {label}: {TC.B_WHITE}{', '.join(forbidden)}{TC.B_RED} "
		    f"(allowed: {', '.join(sorted(allowed))})")
		return [f"forbidden functions{(' ' + label) if label else ''}"]
	_ok(f"only allowed external functions {label} ({', '.join(sorted(allowed))})".replace("  ", " "))
	return []


def check_no_globals(files: List[Path], label="") -> List[str]:
	if not shutil.which("nm"):
		return []
	_, _, global_data, _ = _nm(files)
	if global_data:
		_ko(f"global variables are forbidden {label}: {TC.B_WHITE}{', '.join(sorted(global_data))}")
		return [f"global variables{(' ' + label) if label else ''}"]
	_ok(f"no global variables {label}")
	return []


def count_static_variables(files: List[Path]) -> Optional[int]:
	"""Number of static variables (local data symbols) in the objects. None if nm is not available"""
	if not shutil.which("nm"):
		return None
	_, _, global_data, local_data = _nm(files)
	# string literals and compiler generated stuff are not named symbols, so what remains are the statics
	local_data = {s for s in local_data if not s.startswith(("str", "__func__", "completed", "dtor_idx"))}
	return len(local_data) + len(global_data)


def find_objects(work_dir: Path, exclude: Iterable[str] = ()) -> List[Path]:
	exclude = set(exclude)
	result = []
	for path in Path(work_dir).rglob("*.o"):
		if not any(part in exclude for part in path.relative_to(work_dir).parts):
			result.append(path)
	return result


def make_work_copy(source: Path, dest: Path) -> Path:
	if dest.exists():
		shutil.rmtree(dest)
	shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".git"))
	return dest


def header(project):
	print(f"\n{TC.B_BLUE}Subject checks{TC.NC} ({project}) — {TC.CYAN}use --ignore-subject to skip{TC.NC}")


def compile_objects(work_dir: Path, sources: List[str], flags: str, out_dir: Path):
	"""Compiles each source with `cc <flags> -c`. Returns (success, objects, output)"""
	out_dir.mkdir(parents=True, exist_ok=True)
	objects, output, success = [], "", True
	for source in sources:
		obj = out_dir / (Path(source).stem + ".o")
		p = _run(f"cc {flags} -c {source} -o {obj}", work_dir)
		output += p.stdout + p.stderr
		if p.returncode != 0:
			success = False
		else:
			objects.append(obj)
	return success, objects, output
