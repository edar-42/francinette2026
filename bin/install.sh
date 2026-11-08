#!/bin/bash

cd "$HOME" || exit

mkdir temp_____

cd temp_____ || exit
rm -rf francinette

# download github
git clone --recursive https://github.com/edar-42/francinette2026.git francinette

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
		echo "You don't have admin rights: ask for gcc/clang, make and python3-venv to be installed."
	fi
fi

cp -r francinette "$HOME"

cd "$HOME" || exit
rm -rf temp_____

cd "$HOME"/francinette || exit

# start a venv inside francinette
if ! python3 -m venv venv ; then
	echo "Please make sure than you can create a python virtual environment"
	echo 'Contact me if you have no idea how to proceed (fsoares- on slack)'
	exit 1
fi

# activate venv
. venv/bin/activate

# install requirements
if ! pip3 install -r requirements.txt ; then
	echo 'Problem launching the installer. Contact me (fsoares- on slack)'
	exit 1
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