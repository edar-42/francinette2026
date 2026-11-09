#!/bin/bash

fail() {
	echo -e "\033[1;31m$1\033[0m" >&2
	exit 1
}

# creates the venv, even without python3-venv/ensurepip (no admin rights needed)
create_venv() {
	rm -rf venv
	python3 -m venv venv >/dev/null 2>&1 && return 0

	echo "python3-venv is not available: installing pip in the virtual environment with get-pip"
	rm -rf venv
	python3 -m venv --without-pip venv || return 1
	local py_version
	py_version=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
	curl -fsSL https://bootstrap.pypa.io/get-pip.py -o venv/get-pip.py || return 1
	venv/bin/python venv/get-pip.py --quiet --disable-pip-version-check 2>/dev/null && return 0
	# get-pip.py refuses the python versions it does not support anymore
	curl -fsSL "https://bootstrap.pypa.io/pip/$py_version/get-pip.py" -o venv/get-pip.py || return 1
	venv/bin/python venv/get-pip.py --quiet --disable-pip-version-check
}

cd "$HOME" || exit

# never replace a folder that is not francinette
if [ -e "$HOME/francinette" ] && [ ! -f "$HOME/francinette/tester.sh" ]; then
	fail "~/francinette already exists and is not francinette: move it somewhere else and try again."
fi

rm -rf temp_____
mkdir temp_____

cd temp_____ || exit

# download github
git clone --recursive https://github.com/edar-42/francinette2026.git francinette || fail "Could not download francinette: nothing was changed."

# install the system packages only if something is missing (no sudo needed at 42)
has_tools() {
	command -v cc >/dev/null 2>&1 && command -v make >/dev/null 2>&1 && \
	python3 -c "import venv, ensurepip" >/dev/null 2>&1
}

if [ "$(uname)" != "Darwin" ] && ! has_tools; then
	echo "Some packages are missing (C compiler, make or python3-venv)."
	if sudo -n true 2>/dev/null || groups | grep -qwE "sudo|wheel|admin"; then
		echo "Admin permissions needed to install them"
		case $(lsb_release -is 2>/dev/null) in
			"Ubuntu"|"Debian")
				sudo apt update
				sudo apt install gcc clang make libbsd-dev libncurses-dev valgrind -y
				sudo apt install python3-dev python3-pip python3-venv -y
				;;
			"Arch")
				sudo pacman -S gcc clang make libbsd ncurses valgrind python-pip --noconfirm
				;;
		esac
	else
		echo "You don't have admin rights, so nothing was installed. If the tests do not compile, ask for gcc/clang and make to be installed."
	fi
fi

# replace the previous install: copying over it fails on its read-only git files
cd "$HOME" || exit
rm -rf "$HOME/francinette"
mv temp_____/francinette "$HOME/francinette" || fail "Could not create ~/francinette."

rm -rf temp_____

cd "$HOME"/francinette || exit

# start a venv inside francinette
if ! create_venv ; then
	fail "Could not create the python virtual environment: check that python3 is installed and that you have an internet connection."
fi

# activate venv
. venv/bin/activate

# install requirements
if ! pip3 install -r requirements.txt ; then
	fail "Problem installing the python dependencies."
fi

RC_FILE="$HOME/.zshrc"

if [ "$(uname)" != "Darwin" ]; then
	RC_FILE="$HOME/.bashrc"
	if [[ -f "$HOME/.zshrc" ]]; then
		RC_FILE="$HOME/.zshrc"
	fi
fi

echo "try to add alias in file: $RC_FILE"

# set up the alias
if ! grep "francinette=" "$RC_FILE" &> /dev/null; then
	echo "francinette alias not present"
	printf "\nalias francinette=%s/francinette/tester.sh\n" "$HOME" >> "$RC_FILE"
fi

if ! grep "paco=" "$RC_FILE" &> /dev/null; then
	echo "Short alias not present. Adding it"
	printf "\nalias paco=%s/francinette/tester.sh\n" "$HOME" >> "$RC_FILE"
fi

# print help
"$HOME"/francinette/tester.sh --help

# automatically replace current shell with new one.
exec "$SHELL"

printf "\033[33m... and don't forget, \033[1;37mpaco\033[0;33m is not a replacement for your own tests! \033[0m\n"