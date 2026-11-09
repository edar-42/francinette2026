#!/bin/bash

REPO="https://github.com/edar-42/francinette2026.git"
INSTALL='bash -c "$(curl -fsSL https://raw.githubusercontent.com/edar-42/francinette2026/master/bin/install.sh)"'

fail() {
	echo -e "\033[1;31m$1\033[0m" >&2
	exit 1
}

# never ask for a username: a wrong url would block here forever
export GIT_TERMINAL_PROMPT=0

cd "$HOME"/francinette 2>/dev/null || fail "Francinette is not installed in ~/francinette. Install it with:\n$INSTALL"

# without its own .git, git would act on a parent folder (like a repo in $HOME)
[ -d .git ] || fail "~/francinette is not a git repository. Reinstall it with:\n$INSTALL"
[ -f venv/bin/activate ] || fail "~/francinette has no python venv. Reinstall it with:\n$INSTALL"

# installs made before the repository was renamed still point to the old url
git remote set-url origin "$REPO" || fail "Could not set the url of the repository."

git fetch origin || fail "Could not download the last version: nothing was updated. Check your internet connection."
git reset --hard origin/master || fail "Could not apply the last version."
git submodule update --init

# activate venv
. venv/bin/activate

echo "Updating python dependencies..."
# install requirements
if ! pip3 install --disable-pip-version-check -q -r requirements.txt ; then
	fail "Problem installing the python dependencies."
fi

echo -e "\033[1;37mFrancinette is updated. You can use it again!\033[0m"

printf "\033[33m... but don't forget, \033[1;37mpaco\033[0;33m is not a replacement for your own tests! \033[0m\n"
