## 0.10.0 (2026-11-08) — new subjects

### Feat

- **push_swap**: new tester for push_swap v1.2 (`--simple`, `--medium`, `--complex`, `--adaptive`, `--bench`,
  disorder metric, errors, leaks, performance 100/500 and the `checker` bonus). The operations are checked with a
  python checker, no `checker_linux` needed
- **subject checks** (printf v12.1, get_next_line v14.3, push_swap v1.2): README.md requirements, Makefile rules and
  flags, relink, `clean`/`fclean`/`re`, allowed external functions and global variables (with `nm`).
  Use `--ignore-subject` / `-is` to skip them
- **gnl**: compiles without `-D BUFFER_SIZE` (required by the subject), tests with `BUFFER_SIZE=9999` and from a pipe,
  `lseek` and the libft are detected as forbidden, the "one static variable" bonus check uses `nm`

### Fix

- **fsoares tests**: a failing test made the test program crash (`fclose(NULL)`), so the errors were lost and the
  result was "All tests passed". A crash of the test program is now reported
- **fsoares tests**: false memory leak (4096 bytes) caused by the buffer of the errors file
- **printf --strict**: false memory leaks (36, 56, 2304, 438... bytes) on every test: the allocations of the
  test framework itself (`backtrace` in the write mock) were counted as leaks of ft_printf
- **printf --strict**: the "write fails -> must return -1" check only worked for the 1st write
- **printf**: address sanitizer + malloc mock crash on recent Linux (disabled on Linux, like in gnl)
- **printf-unit-test**: missing includes (`stdint.h`, `string.h`) with recent compilers
- Python 3.13: `pipes` module removed (replaced by `shlex`), invalid escape sequences
- `NAME = ...` detection in the Makefile accepts `?=` and comments

### Removed

- C Piscine, minitalk and pipex testers (only libft, ft_printf, get_next_line and push_swap are kept)
- install / update scripts now download this fork instead of the original repo

## 0.9.15 (2023-02-08)

### Fix

- **libft**: Remove add_back dependecy on other tests in libftTester #46
- Remove function that appears in error and in passed in summary report #52
- **libft**: Fix possible bug with sprintf #51
- **gnl**: Open all fds except one so that I can open the errors file
- **lifbt**: Add multiple options to multiple nodes added in lstadd_front

## 0.9.14 (2023-01-27)

### Fix

- updated readme
- **libft**: strtrim: repeated chars in the set #41
- **printf**: Fix problem with executing only bonus #39

## 0.9.13 (2023-01-26)

### Fix

- Autorelaunch terminal
- **libft**: Fix missign file on libft tests

## 0.9.12 (2022-12-14)

### Fix

- **minitalk**: Fix not ignoring commented mains, added message on mising executables

## 0.9.11 (2022-12-09)

### Fix

- update cleaner, supress deprecated functions warning

## 0.9.10 (2022-11-30)

### Fix

- **pipex**: fix weirdly behaving quotes

## 0.9.9 (2022-11-30)

### Fix

- Updated gnl and libft tests from Tripouille
- **printf**: Add cast to NULL str, related to #18
- **pipex**: Handle weird exception being thrown

## 0.9.8 (2022-11-17)

### Fix

- **ft_split**: Add test with the string terminator + a non-empty string
- Change strict text to not reference moulinette

## 0.9.7 (2022-11-11)

### Fix

- **libft**: remove spammy messages

## 0.9.6 (2022-11-10)

### Fix

- **gnl**: Improved limits test. Changed on error test

## 0.9.5 (2022-11-10)

### Fix

- **libft**: Fix problem when Makefile has CRLF line endings
- **gnl**: maybe fix linux problem with RTLD_NEXT
- Fix building of some tests with Xcode 14.1

## 0.9.4 (2022-10-25)

### Fix

- **libft**: Fix problem with calloc tests on allevier tests
- **printf**: Make strict tests work in linux
- Change way that chars are escaped to use octal

## 0.9.3 (2022-10-21)

### Fix

- **gnl**: Allow reads of size zero
- **libft**: change atoi character check to have a space to make it easier to understand and easier to copy

## 0.9.2 (2022-10-20)

### Fix

- **gnl**: Import the non bonus header

## 0.9.1 (2022-10-19)

### Fix

- **gnl**: Added some more tests
- **gnl**: Fix bug that wrongly reported tests as ok
- **libft**: added strtrim test without trimming spaces

### Feat

- **install**: provided install for arch

## 0.8.7 (2022-10-13)

### Fix

- **libft**: compile with all bonus
- **libft**: added missing corner test case to strrchr

## 0.8.6 (2022-10-11)

### Fix

- **libft**: Updated libft tests

## 0.8.5 (2022-10-09)

### Fix

- **libft**: Fix lifbt-unit-test test on linux

## 0.8.4 (2022-10-09)

### Fix

- Solve problem with escaped buffer in linux

## 0.8.3 (2022-09-15)

### Fix

- **gnl**: Fix problem with programming hanging on strict gnl

## 0.8.2 (2022-08-09)

### Fix

- force bonus on printf and make timeout actually work

## 0.8.1 (2022-08-09)

### Fix

- **minitalk**: ignore exit code of server on communication test

## 0.8.0 (2022-07-28)

### Fix

- **minitalk**: solve repeated main rewrite
- fix update on always always updating on every run
- **printf**: fix the last fix

## 0.7.3 (2022-06-17)

### Fix

- **printf**: don't error out on comple, just warn

## 0.7.2 (2022-06-17)

### Fix

- Improve leaks message on gnl

## 0.7.1 (2022-06-15)

### Fix

- **pipex**: Fix problem with bonus testing on pipexMedic

## 0.7.0 (2022-06-01)

### Feat

- **pipex**: Add leak check
- Added bonus tests for pipex
- #1: Added timeouts per project

### Fix

- fixed the update.sh script

## 0.4.0 (2022-04-09)

### Feat

- **pipex**: Added pipexMedic tester
- **pipex**: Added pipex-tester to pipex tests
- Added my pipex tester (mandatory only)

## 0.1.1 (2022-03-21)

### Refactor

- #5: ported update script to python
