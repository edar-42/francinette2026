#!/bin/bash
# Updates tests/<project>/auto-tester with the last version of https://github.com/Elwynn18/42-auto-tester
set -e

cd "$(dirname "${BASH_SOURCE[0]}")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git clone --quiet --depth 1 https://github.com/Elwynn18/42-auto-tester "$tmp/repo"

cp "$tmp/repo/test_libft.sh" tests/libft/auto-tester/
cp "$tmp/repo/test_gnl.sh" tests/get_next_line/auto-tester/
cp "$tmp/repo/test_ft_printf.sh" tests/printf/auto-tester/
cp "$tmp/repo/test_push_swap.sh" tests/push_swap/auto-tester/

echo "42-auto-tester updated to $(git -C "$tmp/repo" rev-parse --short HEAD)"
